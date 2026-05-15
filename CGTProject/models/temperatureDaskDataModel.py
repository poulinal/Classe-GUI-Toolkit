# AP 2026
# Temperature model that keeps NeXus data lazy and exposes Dask/slicing helpers.
from __future__ import annotations

import os
import gc
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

import dask.array as da
from nexusformat.nexus import NXdata, NXfield, nxload
from nxs_analysis_tools import Scissors

from nxs_analysis_tools.datareduction import load_transform
from CGTProject.utilities.nxs_fast import load_transform_fast, save_transform_npy, load_transform_npy, save_transform_standalone_nxs

from matplotlib.collections import QuadMesh
from CGTProject.utilities.HKLPlaneEnum import HKLPlaneEnum
import matplotlib.pyplot as plt
import numpy as np

from CGTProject.models.dataModel import DataModel
from CGTProject.utilities.HKLPlaneEnum import HKLPlaneEnum


@dataclass(frozen=True)
class LazyNXDataView:
    """A thin wrapper around NXdata that avoids materializing the full 3D signal."""
    nx: NXdata
    signal_name: str
    axes_names: Tuple[str, ...]
    chunks: Tuple[int, int, int] = (128, 128, 16)  # tune to your access pattern

    @classmethod
    def from_nxdata(cls, nx: NXdata, chunks=(128, 128, 16)) -> "LazyNXDataView":
        signal_name = nx.attrs.get("signal", None)
        if not signal_name:
            signal_name = getattr(nx.nxsignal, "nxname", None) or "counts"

        axes = nx.attrs.get("axes", [])
        axes_names = tuple(axes) if axes else tuple()

        return cls(nx=nx, signal_name=str(signal_name), axes_names=axes_names, chunks=chunks)

    @property
    def signal(self) -> NXfield:
        return self.nx[self.signal_name]

    @property
    def axes(self) -> List[NXfield]:
        return [self.nx[name] for name in self.axes_names]

    def dask_signal(self, chunks: Optional[Tuple[int, int, int]] = None) -> da.Array:
        use_chunks = chunks or self.chunks
        # NOTE: stays lazy; disk I/O happens when you compute()
        return da.from_array(self.signal, chunks=use_chunks)

    # ---- Convenience readers (these only read the requested region) ----
    def hk_plane(self, l_idx: int):
        return self.signal[:, :, l_idx]

    def hl_plane(self, k_idx: int):
        return self.signal[:, k_idx, :]

    def kl_plane(self, h_idx: int):
        return self.signal[h_idx, :, :]

    def window(self, h: slice, k: slice, l: slice):
        return self.signal[h, k, l]


class TemperatureDaskDataModel(DataModel):
    """
    Memory-efficient temperature model:
      - indexes temperatures -> file paths
      - loads at most 1 NXdata at a time (cache size 1 by default)
      - exposes Dask + slicing so you can work on planes/windows instead of full volumes
    """

    def __init__(self, dataPaths: tuple[str, list] = ("", []), *, chunks: Tuple[int, int, int] = (128, 128, 16)):
        self.dataPathRoot, self.dataMetadata = dataPaths

        self.temperature: str = ""
        self.currentMetadataPath: str = ""
        self._chunks = chunks

        # Lightweight index: temp -> .nxs path
        self.dic_temp_to_path: Dict[str, str] = {}

        # Heavy cache: temp -> NXdata (keep small!)
        self._nx_cache: Dict[str, NXdata] = {}
        self._max_loaded_items = 1

        # Cache 1D axis arrays (Qh/Qk/Ql) as NumPy for faster plotting.
        self._axis_numpy_cache: Dict[str, np.ndarray] = {}

        super().__init__()

    def initializeAllData(self):
        self.dic_temp_to_path.clear()
        self._nx_cache.clear()

        for metadata in self.dataMetadata:
            temp_value = self._extract_temperature_value(metadata)
            if temp_value is not None:
                fullpath = metadata if os.path.isabs(metadata) else os.path.join(self.dataPathRoot, metadata)
                self.dic_temp_to_path[temp_value] = fullpath

    def _extract_temperature_value(self, metadata_path: str) -> Optional[str]:
        base_name = os.path.basename(metadata_path)
        if base_name.endswith("_standalone_hkl.nxs"):
            base_name = base_name[: -len("_standalone_hkl.nxs")]
        elif base_name.endswith("_standalone_native.nxs"):
            base_name = base_name[: -len("_standalone_native.nxs")]
        elif base_name.endswith(".nxs"):
            base_name = base_name[:-4]

        for token in reversed(base_name.split("_")):
            if token.replace(".", "", 1).isdigit():
                return token
        return None

    def getTemperatureValues(self):
        return list(self.dic_temp_to_path.keys())

    def getTemperatureDisplayEntries(self) -> list[tuple[str, str]]:
        display_entries: list[tuple[str, str]] = []
        for metadata in self.dataMetadata:
            temp_value = self._extract_temperature_value(metadata)
            if temp_value is None:
                continue
            fullpath = metadata if os.path.isabs(metadata) else os.path.join(self.dataPathRoot, metadata)
            display_entries.append((self._build_temperature_display_label(fullpath, temp_value), fullpath))
        return display_entries

    def _build_temperature_display_label(self, metadata_path: str, temperature: str) -> str:
        base_name = os.path.basename(metadata_path)
        for suffix in ("_standalone_hkl.nxs", "_standalone_native.nxs", ".nxs"):
            if base_name.endswith(suffix):
                base_name = base_name[: -len(suffix)]
                break

        is_delta_pdf = "deltapdf" in base_name.lower()

        trim_token = None
        for token in base_name.split("_"):
            if token.lower().startswith("trim"):
                trim_token = token[4:]
                break

        if not trim_token:
            return f"{temperature} (deltaPDF)" if is_delta_pdf else f"{temperature} (full data)"

        import re

        trim_parts = []
        for axis_label, range_text in re.findall(r"([HKL])([^HKL_]+)", trim_token):
            cleaned_range = range_text.strip("+")
            if cleaned_range:
                trim_parts.append(f"{axis_label}{cleaned_range}")

        trim_text = "".join(trim_parts) if trim_parts else trim_token
        if is_delta_pdf:
            return f"{temperature} (deltaPDF, trim {trim_text})"
        return f"{temperature} (trim {trim_text})"

    def dataIsValid(self):
        return self.getCurrentData() is not None
    
    def getQuadMeshAtCurrentIndex(
        self,
        ax=None,
        **pcolormesh_kwargs,
    ) -> Optional[tuple[np.ndarray, np.ndarray, np.ndarray]]:
        """
        Return a Matplotlib QuadMesh for the current HKL plane at the current index,
        without using plot_slice().

        Notes:
        - Uses lazy NXfield slicing, so only a 2D plane is read.
        - By default draws into the current axes (plt.gca()) unless ax is provided.
        - pcolormesh expects array shaped (len(y), len(x)), so we transpose the slice.
        """
        if self.HKLPlane is None:
            print("HKL Plane not set.")
            return None

        if not self.dataIsValid():
            print("No data available or temperature not found.")
            return None

        if ax is None:
            ax = plt.gca()

        view = self.getView()
        sig = view.signal
        axes = view.axes

        axisToSlice = self.getSliceAxisIndex()
        if axisToSlice < 0 or axisToSlice >= len(axes):
            print("Invalid slice axis index.")
            return None

        z_axis_values = axes[axisToSlice]
        if self.index < 0 or self.index >= len(z_axis_values):
            print("Index out of range.")
            return None

        # actual_value = z_axis_values[self.index]
        # print(
        #     f"Getting QuadMesh at index: {self.index}, "
        #     f"actual z value: {actual_value}"
        # )

        # Build x/y coordinates and extract the 2D plane.
        # data slice shapes:
        #  - HK: (H, K) from sig[:, :, idx]
        #  - HL: (H, L) from sig[:, idx, :]
        #  - KL: (K, L) from sig[idx, :, :]
        if self.HKLPlane == HKLPlaneEnum.H_K_Plane:
            x = axes[0]  # Qh
            y = axes[1]  # Qk
            plane2d = sig[:, :, self.index]
        elif self.HKLPlane == HKLPlaneEnum.H_L_Plane:
            x = axes[0]  # Qh
            y = axes[2]  # Ql
            plane2d = sig[:, self.index, :]
        elif self.HKLPlane == HKLPlaneEnum.K_L_Plane:
            x = axes[1]  # Qk
            y = axes[2]  # Ql
            plane2d = sig[self.index, :, :]
        else:
            print("Unsupported HKL plane.")
            return None

        # Convert NXfield axes -> NumPy arrays, but cache them so slider updates
        # don't re-read axis vectors from disk.
        def _axis_to_numpy_cached(a):
            if not isinstance(a, NXfield):
                return np.asarray(a)

            name = getattr(a, "nxname", None) or "axis"
            cached = self._axis_numpy_cache.get(str(name))
            if cached is not None:
                return cached

            arr = np.asarray(a[:])  # forces only this 1D axis into memory
            self._axis_numpy_cache[str(name)] = arr
            return arr

        x_np = _axis_to_numpy_cached(x)
        y_np = _axis_to_numpy_cached(y)

        # Ensure C is a NumPy array; plane2d is already just a 2D slice (small compared to 3D)
        C = np.asarray(plane2d).T  # pcolormesh expects (len(y), len(x)) for 1D x/y

        # if "shading" not in pcolormesh_kwargs:
        #     pcolormesh_kwargs["shading"] = "auto"

        # mesh = ax.pcolormesh(x_np, y_np, C, **pcolormesh_kwargs)
        # print(f"Prepared QuadMesh data with shapes x: {x_np.shape}, y: {y_np.shape}, C: {C.shape}")
        return (x_np, y_np, C)

    def build_metadata_path(self, temperatureValue: str) -> Optional[str]:
        # Prefer index if initializeAllData() was called
        if temperatureValue in self.dic_temp_to_path:
            return self.dic_temp_to_path[temperatureValue]

        if os.path.isabs(temperatureValue) and os.path.exists(temperatureValue):
            return temperatureValue

        if not self.dataMetadata:
            return None

        for metadata in self.dataMetadata:
            try:
                temp_value = self._extract_temperature_value(metadata)
            except Exception:
                temp_value = None
            if temp_value == temperatureValue:
                return metadata if os.path.isabs(metadata) else os.path.join(self.dataPathRoot, metadata)

        for metadata in self.dataMetadata:
            name = os.path.basename(metadata)
            if name.endswith(f"{temperatureValue}.nxs") or temperatureValue in name:
                return metadata if os.path.isabs(metadata) else os.path.join(self.dataPathRoot, metadata)

        return None

    def _evict_if_needed(self):
        if self._max_loaded_items <= 0:
            self._nx_cache.clear()
            gc.collect()
            return

        while len(self._nx_cache) > self._max_loaded_items:
            oldest = next(iter(self._nx_cache.keys()))
            del self._nx_cache[oldest]
        gc.collect()

    def _can_write_standalone_cache(self, cache_path: str) -> bool:
        cache_dir = os.path.dirname(os.path.abspath(cache_path)) or "."
        return os.access(cache_dir, os.W_OK | os.X_OK)

    def _load_metadata_path(self, metadata_path: str, *, temperature_value: str, progress_callback: Callable[[int, str], None] | None = None):
        def _report(percent: int, message: str) -> None:
            if progress_callback is not None:
                progress_callback(max(0, min(100, percent)), message)

        self.currentMetadataPath = metadata_path
        self.temperature = temperature_value

        cache_key = metadata_path
        if cache_key not in self._nx_cache:
            if self._max_loaded_items == 1:
                self._nx_cache.clear()
                gc.collect()

            mpath_lower = metadata_path.lower()
            if mpath_lower.endswith("_standalone_hkl.nxs") or mpath_lower.endswith("_standalone_native.nxs"):
                fast_standalone_nxs_path = metadata_path
            elif metadata_path.lower().endswith(".nxs"):
                fast_standalone_nxs_path = metadata_path[:-4] + "_standalone_hkl.nxs"
            else:
                fast_standalone_nxs_path = metadata_path + "_standalone_hkl.nxs"

            if os.path.exists(fast_standalone_nxs_path):
                _report(10, "Loading cached standalone data")
                self._nx_cache[cache_key] = nxload(fast_standalone_nxs_path).entry.transform
            elif self._can_write_standalone_cache(fast_standalone_nxs_path):
                print(f"fast load does not exist already, creating: {fast_standalone_nxs_path}")
                try:
                    _report(5, "Building standalone cache")
                    save_transform_standalone_nxs(
                        metadata_path,
                        out_path=fast_standalone_nxs_path,
                        order="hkl",
                        overwrite=False,
                        progress_callback=lambda percent, message: _report(5 + int(percent * 0.9), message),
                    )
                    _report(96, "Loading cached standalone data")
                    self._nx_cache[cache_key] = nxload(fast_standalone_nxs_path).entry.transform
                except (PermissionError, OSError) as exc:
                    print(f"Could not write standalone cache ({exc}); loading the original NeXus file instead.")
                    _report(10, "Loading original NeXus data")
                    self._nx_cache[cache_key] = load_transform_fast(metadata_path)
            else:
                print("Standalone cache directory is not writable; loading the original NeXus file instead.")
                _report(10, "Loading original NeXus data")
                self._nx_cache[cache_key] = load_transform_fast(metadata_path)

            self._axis_numpy_cache.clear()
            _report(100, "Data ready")
            self._evict_if_needed()

    def setMetadataPath(self, metadata_path: str, progress_callback: Callable[[int, str], None] | None = None):
        if not metadata_path:
            raise ValueError("Metadata path is required.")

        extracted_temperature = self._extract_temperature_value(metadata_path) or "current"
        if not os.path.isabs(metadata_path):
            metadata_path = os.path.join(self.dataPathRoot, metadata_path)

        self._load_metadata_path(metadata_path, temperature_value=extracted_temperature, progress_callback=progress_callback)

    def setTemperature(self, temperatureValue: str, progress_callback: Callable[[int, str], None] | None = None):
        if os.path.isabs(temperatureValue) or temperatureValue.lower().endswith(".nxs"):
            return self.setMetadataPath(temperatureValue, progress_callback=progress_callback)

        metadata_path = self.build_metadata_path(temperatureValue)
        if not metadata_path:
            raise ValueError(f"Temperature '{temperatureValue}' not found in metadata index.")
        return self._load_metadata_path(metadata_path, temperature_value=temperatureValue, progress_callback=progress_callback)

    def getCurrentData(self) -> Optional[NXdata]:
        cache_key = self.currentMetadataPath or self.temperature
        return self._nx_cache.get(cache_key, None)

    def replaceCurrentData(self, data: NXdata):
        cache_key = self.currentMetadataPath or self.temperature
        if not cache_key:
            raise RuntimeError("No active dataset to replace.")
        self._nx_cache[cache_key] = data
        self._axis_numpy_cache.clear()

    def reloadCurrentData(self, progress_callback: Callable[[int, str], None] | None = None):
        cache_key = self.currentMetadataPath or self.temperature
        if not cache_key:
            raise RuntimeError("No active dataset to reload.")
        self._nx_cache.pop(cache_key, None)
        self._axis_numpy_cache.clear()
        if self.currentMetadataPath:
            self.setMetadataPath(self.currentMetadataPath, progress_callback=progress_callback)
        else:
            self.setTemperature(self.temperature, progress_callback=progress_callback)

    def getView(self) -> LazyNXDataView:
        nx = self.getCurrentData()
        if nx is None:
            raise RuntimeError("No current data loaded. Call setTemperature() first.")
        return LazyNXDataView.from_nxdata(nx, chunks=self._chunks)

    # ---- High-level helpers for efficient access ----
    def getDaskSignal(self, chunks: Optional[Tuple[int, int, int]] = None) -> da.Array:
        return self.getView().dask_signal(chunks=chunks)

    def readPlane(self, plane: HKLPlaneEnum, fixed_index: int):
        """
        Reads a single 2D plane into a NumPy array (only that slice is read from disk).
        """
        view = self.getView()
        if plane == HKLPlaneEnum.H_K_Plane:
            return view.hk_plane(l_idx=fixed_index)
        if plane == HKLPlaneEnum.H_L_Plane:
            return view.hl_plane(k_idx=fixed_index)
        if plane == HKLPlaneEnum.K_L_Plane:
            return view.kl_plane(h_idx=fixed_index)
        raise ValueError(f"Unsupported plane: {plane}")

    def readWindow(self, h: slice, k: slice, l: slice):
        """
        Reads a small 3D block into a NumPy array (only that window is read from disk).
        """
        return self.getView().window(h, k, l)
    
    def applyLineCutOptions(self, line_cut_options: dict[str, float], coords: tuple[float, float], verticle: bool):
        # Placeholder for applying line cut options to the data model
        print(f"Applying line cut options: {line_cut_options} at coords: {coords} verticle: {verticle}")
        scissors = Scissors()
        cache_key = self.currentMetadataPath or self.temperature
        scissors.set_data(self._nx_cache[cache_key])
        if line_cut_options and cache_key in self._nx_cache:
            if self.HKLPlane is None:
                print("HKL Plane not set. Cannot apply line cut options.")
                return
            elif self.HKLPlane == HKLPlaneEnum.H_K_Plane:
                hMin = line_cut_options.get('h_min', 0.0)
                hMax = line_cut_options.get('h_max', 0.0)
                kMin = line_cut_options.get('k_min', 0.0)
                kMax = line_cut_options.get('k_max', 0.0)
                lCenter = line_cut_options.get('l_center', 0.0)
                deltaL = line_cut_options.get('delta_l', 0.0)
                h_half = (hMax - hMin) / 2
                k_half = (kMax - kMin) / 2
                l_half = deltaL / 2
                if h_half <= 0 or k_half <= 0 or l_half <= 0:
                    print("Invalid line cut window for H-K plane. All half-widths must be > 0.")
                    return None
                scissors.set_center((coords[0], coords[1], lCenter))  # Assuming the line cut is in the H-K plane for simplicity
                scissors.set_window((h_half, k_half, l_half))
            elif self.HKLPlane == HKLPlaneEnum.H_L_Plane:
                hMin = line_cut_options.get('h_min', 0.0)
                hMax = line_cut_options.get('h_max', 0.0)
                lMin = line_cut_options.get('l_min', 0.0)
                lMax = line_cut_options.get('l_max', 0.0)
                kCenter = line_cut_options.get('k_center', 0.0)
                deltaK = line_cut_options.get('delta_k', 0.0)
                h_half = (hMax - hMin) / 2
                l_half = (lMax - lMin) / 2
                k_half = deltaK / 2
                if h_half <= 0 or k_half <= 0 or l_half <= 0:
                    print("Invalid line cut window for H-L plane. All half-widths must be > 0.")
                    return None
                scissors.set_center((coords[0], kCenter, coords[1]))  # Assuming the line cut is in the H-L plane for simplicity
                scissors.set_window((h_half, k_half, l_half))  # Example window, adjust as needed
            elif self.HKLPlane == HKLPlaneEnum.K_L_Plane:
                kMin = line_cut_options.get('k_min', 0.0)
                kMax = line_cut_options.get('k_max', 0.0)
                lMin = line_cut_options.get('l_min', 0.0)
                lMax = line_cut_options.get('l_max', 0.0)
                hCenter = line_cut_options.get('h_center', 0.0)
                deltaH = line_cut_options.get('delta_h', 0.0)
                k_half = (kMax - kMin) / 2
                l_half = (lMax - lMin) / 2
                h_half = deltaH / 2
                if h_half <= 0 or k_half <= 0 or l_half <= 0:
                    print("Invalid line cut window for K-L plane. All half-widths must be > 0.")
                    return None
                scissors.set_center((hCenter, coords[0], coords[1]))  # Assuming the line cut is in the K-L plane for simplicity
                scissors.set_window((h_half, k_half, l_half))  # Example window, adjust as needed
                
        # scissors.set_center((coords[0], coords[1], 0))  # Assuming the line cut is in the H-K plane for simplicity
        # scissors.set_window((hMin, hMax, kMin, kMax, lCenter - deltaL, lCenter + deltaL))  # Example window, adjust as needed
        # scissors.set_center((0, 0, 0)) # Placeholder center, adjust based on HKL plane and coords
        # scissors.set_window((0.1, 1, 0.2)) # Placeholder window, adjust based on HKL plane and line cut options
        try:
            extracted_data = scissors.cut_data()
        except Exception as exc:
            print(f"Failed to apply line cut options: {exc}")
            return None
        
        #and include graph options like cmap, vmin vmax colorramp, skewangle
        return extracted_data
    
    
    
    
    