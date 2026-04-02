# AP 2026
# Temperature model that keeps NeXus data lazy and exposes Dask/slicing helpers.
from __future__ import annotations

import os
import gc
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

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
            temp_value = metadata.split("_")[-1].split(".nxs")[0]
            fullpath = metadata if os.path.isabs(metadata) else os.path.join(self.dataPathRoot, metadata)
            self.dic_temp_to_path[temp_value] = fullpath

    def getTemperatureValues(self):
        return list(self.dic_temp_to_path.keys())

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

        if not self.dataMetadata:
            return None

        for metadata in self.dataMetadata:
            try:
                temp_value = metadata.split("_")[-1].split(".nxs")[0]
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

    def setTemperature(self, temperatureValue: str):
        metadata_path = self.build_metadata_path(temperatureValue)
        if not metadata_path:
            raise ValueError(f"Temperature '{temperatureValue}' not found in metadata index.")

        self.temperature = temperatureValue

        # Load on demand; keep cache small
        if temperatureValue not in self._nx_cache:
            if self._max_loaded_items == 1:
                self._nx_cache.clear()
                gc.collect()

            # IMPORTANT:
            # This should ideally return NXdata whose NXfield remains HDF5-backed.
            # Avoid calling nxsignal.nxvalue/nxdata anywhere unless you want the full array.
            
            # fast_standalone_nxs_path = os.path.join(os.path.dirname(metadata_path), f"fast_{os.path.basename(metadata_path)}")
            # if os.path.exists(fast_standalone_nxs_path):
            #     print(f"Loading from fast standalone .nxs: {fast_standalone_nxs_path}")
            #     self._nx_cache[temperatureValue] = load_transform_fast(fast_standalone_nxs_path)
            # else:
            #     self._nx_cache[temperatureValue] = load_transform_fast(metadata_path)
            # # self._nx_cache[temperatureValue] = load_transform_npy('/home/apoulin/de-lat-to-4431-b_link/nxrefine/Eu5Sn2As6/sample1/Eu5Sn2As6_300_hkl.npy')
            # # save_transform_npy(metadata_path)
            #     save_transform_standalone_nxs(metadata_path)
            if metadata_path.lower().endswith(".nxs"):
                fast_standalone_nxs_path = metadata_path[:-4] + "_standalone_hkl.nxs"
            else:
                fast_standalone_nxs_path = metadata_path + "_standalone_hkl.nxs"

            if not os.path.exists(fast_standalone_nxs_path):
                # Materialize a standalone file (no NXlink/external-file dependencies) in HKL order.
                save_transform_standalone_nxs(
                    metadata_path,
                    out_path=fast_standalone_nxs_path,
                    order="hkl",
                    overwrite=False,
                )

            # Load the simplified standalone NXdata directly.
            self._nx_cache[temperatureValue] = nxload(fast_standalone_nxs_path).entry.transform

            # New dataset loaded: clear any cached axis arrays.
            self._axis_numpy_cache.clear()
            
            
            self._evict_if_needed()
            
            
            self._evict_if_needed()

    def getCurrentData(self) -> Optional[NXdata]:
        return self._nx_cache.get(self.temperature, None)

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
        scissors.set_data(self._nx_cache[self.temperature])
        if line_cut_options and self.temperature in self._nx_cache:
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
                scissors.set_center((hCenter, coords[0], coords[1]))  # Assuming the line cut is in the K-L plane for simplicity
                scissors.set_window((h_half, k_half, l_half))  # Example window, adjust as needed
                
        # scissors.set_center((coords[0], coords[1], 0))  # Assuming the line cut is in the H-K plane for simplicity
        # scissors.set_window((hMin, hMax, kMin, kMax, lCenter - deltaL, lCenter + deltaL))  # Example window, adjust as needed
        # scissors.set_center((0, 0, 0)) # Placeholder center, adjust based on HKL plane and coords
        # scissors.set_window((0.1, 1, 0.2)) # Placeholder window, adjust based on HKL plane and line cut options
        extracted_data = scissors.cut_data()
        
        #and include graph options like cmap, vmin vmax colorramp, skewangle
        return extracted_data