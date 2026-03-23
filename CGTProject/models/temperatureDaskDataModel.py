# AP 2026
# Temperature model that keeps NeXus data lazy and exposes Dask/slicing helpers.
from __future__ import annotations

import os
import gc
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import dask.array as da
from nexusformat.nexus import NXdata, NXfield

from nxs_analysis_tools.datareduction import load_transform

from matplotlib.collections import QuadMesh
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
    ) -> Optional[QuadMesh]:
        # ...existing code...

        view = self.getView()
        sig = view.signal
        axes = view.axes

        # ...existing code selecting x, y, plane2d ...

        # Convert NXfield axes -> NumPy arrays (Matplotlib cannot handle NXfield/generator inputs)
        def _axis_to_numpy(a):
            if isinstance(a, NXfield):
                return np.asarray(a[:])  # forces only this 1D axis into memory
            return np.asarray(a)

        x_np = _axis_to_numpy(x)
        y_np = _axis_to_numpy(y)

        # Ensure C is a NumPy array; plane2d is already just a 2D slice (small compared to 3D)
        C = np.asarray(plane2d).T  # pcolormesh expects (len(y), len(x)) for 1D x/y

        if "shading" not in pcolormesh_kwargs:
            pcolormesh_kwargs["shading"] = "auto"

        mesh = ax.pcolormesh(x_np, y_np, C, **pcolormesh_kwargs)
        return mesh

        # pcolormesh expects C shaped (len(y), len(x)) when x,y are 1D
        C = plane2d.T

        # defaults (caller can override via **pcolormesh_kwargs)
        if "shading" not in pcolormesh_kwargs:
            pcolormesh_kwargs["shading"] = "auto"

        mesh = ax.pcolormesh(x, y, C, **pcolormesh_kwargs)
        return mesh

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
            self._nx_cache[temperatureValue] = load_transform(metadata_path)
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