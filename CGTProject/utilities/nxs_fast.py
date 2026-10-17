"""Small wrappers for faster I/O with `nxs_analysis_tools`.

Why this exists
---------------
`nxs_analysis_tools.datareduction.load_transform(..., use_nxlink=False)` builds a new
`NXdata` object with the signal transposed into (H, K, L) order. That convenience can be
slow because it typically forces reading the full 3D dataset into memory.

This module provides a wrapper that:
- Defaults to the NXlink-backed "native" order (L, K, H) for speed and low memory.
- Can optionally read only a small region-of-interest (ROI) and return it in (H, K, L)
  order, so only the ROI gets materialized and transposed.

Typical usage in these notebooks
--------------------------------
From within `examples_alex/*.ipynb`:

    from nxs_fast import load_transform_fast

    # Fastest: keep native (L, K, H) axis order, no large reads.
    d_native = load_transform_fast("/path/to/transform.nxs")

    # Fast ROI: request a subset and get standard (H, K, L) ordering.
    d_roi = load_transform_fast(
        "/path/to/transform.nxs",
        order="hkl",
        h=slice(200, 260),
        k=slice(180, 240),
        l=slice(120, 160),
    )

Notes
-----
- When `order="native"`, the returned axes are (Ql, Qk, Qh) to match the underlying data.
- When `order="hkl"` without an ROI, this wrapper falls back to the slow full-load path
  for backwards compatibility.
"""

from __future__ import annotations

import os
from typing import Callable, Literal

import numpy as np
from numpy.lib.format import open_memmap
from nexusformat.nexus import NXdata, NXfield, nxload


Order = Literal["native", "hkl"]


def _default_hkl_cache_path(path: str) -> str:
    """Return a deterministic cache filename next to the source file."""

    if path.lower().endswith(".nxs"):
        return path[:-4] + "_hkl.nxs"
    return path + "_hkl.nxs"


def _default_standalone_cache_path(path: str, *, order: Order) -> str:
    suffix = "_standalone_hkl.nxs" if order == "hkl" else "_standalone_native.nxs"
    if path.lower().endswith(".nxs"):
        return path[:-4] + suffix
    return path + suffix


def build_transform_hkl_cache(
    path: str,
    *,
    cache_path: str | None = None,
    overwrite: bool = False,
    compression: str | None = "lzf",
    chunks: tuple[int, int, int] | Literal["auto"] | None = "auto",
) -> str:
    """Create a cached HKL-ordered transform file for fast repeated loads.

    This reads the source transform (native order is typically L,K,H) and writes a new
    NeXus file where `entry/transform/data` is stored in (H,K,L) order.

    Implementation detail: writes one L-slab at a time:
    `dst[:,:,l] = src[l,:,:].T`, avoiding a full in-memory transpose.

    Parameters
    ----------
    path:
        Source `transform.nxs`.
    cache_path:
        Destination path. If omitted, defaults to `<path>_hkl.nxs`.
    overwrite:
        If False and the cache file exists, raises FileExistsError.
    compression:
        HDF5 compression (e.g. "lzf", "gzip", or None).
    chunks:
        HDF5 chunk shape for the cached data. Use "auto" for a reasonable default.

    Returns
    -------
    str
        Path to the written cache file.
    """

    cache_path = _default_hkl_cache_path(path) if cache_path is None else cache_path

    if os.path.exists(cache_path) and not overwrite:
        raise FileExistsError(
            f"Cache already exists: {cache_path}. Set overwrite=True to rebuild."
        )

    try:
        import h5py  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise ImportError(
            "h5py is required to build an on-disk HKL cache (it is typically installed via nexusformat)."
        ) from exc

    root = nxload(path)
    transform = root.entry.transform
    src = transform.data  # expected shape (L,K,H)

    # Axis arrays in HKL order
    qh = np.asarray(transform.Qh.nxdata)
    qk = np.asarray(transform.Qk.nxdata)
    ql = np.asarray(transform.Ql.nxdata)

    l_size, k_size, h_size = src.shape
    dst_shape = (h_size, k_size, l_size)

    if chunks == "auto":
        chunks = (min(h_size, 64), min(k_size, 64), 1)

    os.makedirs(os.path.dirname(os.path.abspath(cache_path)) or ".", exist_ok=True)

    with h5py.File(cache_path, "w") as f:
        entry = f.create_group("entry")
        entry.attrs["NX_class"] = "NXentry"

        grp = entry.create_group("transform")
        grp.attrs["NX_class"] = "NXdata"
        grp.attrs["signal"] = "data"
        grp.attrs["axes"] = np.array(["Qh", "Qk", "Ql"], dtype="S")

        dset = grp.create_dataset(
            "data",
            shape=dst_shape,
            dtype=src.dtype,
            chunks=chunks,
            compression=compression,
        )

        # Slab-by-slab transpose to keep peak memory low.
        for l_idx in range(l_size):
            slab_kh = src.nxdata[l_idx, :, :]  # (K,H)
            dset[:, :, l_idx] = slab_kh.T  # (H,K)

        # Axes
        qh_ds = grp.create_dataset("Qh", data=qh)
        qk_ds = grp.create_dataset("Qk", data=qk)
        ql_ds = grp.create_dataset("Ql", data=ql)

        # Preserve axis metadata when present.
        for orig, written in ((transform.Qh, qh_ds), (transform.Qk, qk_ds), (transform.Ql, ql_ds)):
            try:
                for k, v in orig.attrs.items():
                    written.attrs[k] = v
            except Exception:
                pass

    return cache_path


def save_transform_cache(
    path: str,
    *,
    out_path: str | None = None,
    overwrite: bool = False,
    compression: str | None = "lzf",
    chunks: tuple[int, int, int] | Literal["auto"] | None = "auto",
) -> str:
    """Save an efficient on-disk cache for future fast loads.

    Currently this writes an HKL-ordered NeXus/HDF5 file (still `.nxs`).
    In practice this is the most compatible "efficient format" for NeXus workflows,
    and it enables fast partial reads via HDF5 chunking.

    Parameters
    ----------
    path:
        Source `transform.nxs`.
    out_path:
        Destination cache file path. Defaults to `<path>_hkl.nxs`.
    overwrite:
        Whether to overwrite an existing cache.
    compression, chunks:
        Passed through to `build_transform_hkl_cache`.

    Returns
    -------
    str
        Path to the written cache file.
    """

    return build_transform_hkl_cache(
        path,
        cache_path=out_path,
        overwrite=overwrite,
        compression=compression,
        chunks=chunks,
    )


def save_transform_standalone_nxs(
    path: str,
    *,
    out_path: str | None = None,
    order: Order = "hkl",
    overwrite: bool = False,
    compression: str | None = "lzf",
    chunks: tuple[int, int, int] | Literal["auto"] | None = "auto",
    progress_callback: Callable[[int, str], None] | None = None,
) -> str:
    """Write a simplified, standalone `.nxs` that contains materialized data.

    This is specifically meant to eliminate NeXus links (NXlink / external links) in
    the source file by copying the actual voxel data into a new HDF5 dataset.

    Output structure
    ----------------
    The output contains only:
      - `entry/transform/data`
      - `entry/transform/Qh`, `Qk`, `Ql`

    Parameters
    ----------
    path:
        Source `transform.nxs` (may contain links to other files).
    out_path:
        Destination `.nxs`. Defaults to `<path>_standalone_hkl.nxs` or `_standalone_native.nxs`.
    order:
        - "hkl": store `data` in (H,K,L) order and set axes to (Qh,Qk,Ql).
        - "native": store `data` in (L,K,H) order and set axes to (Ql,Qk,Qh).
    overwrite:
        Whether to overwrite an existing destination.
    compression, chunks:
        HDF5 dataset options.

    Returns
    -------
    str
        Path to the written `.nxs`.
    """

    if order not in ("hkl", "native"):
        raise ValueError(f"order must be 'native' or 'hkl', got: {order!r}")

    out_path = (
        _default_standalone_cache_path(path, order=order) if out_path is None else out_path
    )
    if os.path.exists(out_path) and not overwrite:
        raise FileExistsError(f"Output already exists: {out_path}. Set overwrite=True.")

    def _report(percent: int, message: str) -> None:
        if progress_callback is not None:
            progress_callback(max(0, min(100, percent)), message)

    try:
        import h5py  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise ImportError(
            "h5py is required to write a standalone .nxs (it is typically installed via nexusformat)."
        ) from exc

    root = nxload(path)
    transform = root.entry.transform
    src = transform.data  # expected shape (L,K,H)
    _report(5, "Opened source data")

    qh = np.asarray(transform.Qh.nxdata)
    qk = np.asarray(transform.Qk.nxdata)
    ql = np.asarray(transform.Ql.nxdata)

    l_size, k_size, h_size = src.shape

    if chunks == "auto":
        if order == "hkl":
            chunks = (min(h_size, 64), min(k_size, 64), 1)
        else:
            chunks = (1, min(k_size, 64), min(h_size, 64))

    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)

    with h5py.File(out_path, "w") as f:
        entry = f.create_group("entry")
        entry.attrs["NX_class"] = "NXentry"

        grp = entry.create_group("transform")
        grp.attrs["NX_class"] = "NXdata"
        grp.attrs["signal"] = "data"

        if order == "hkl":
            grp.attrs["axes"] = np.array(["Qh", "Qk", "Ql"], dtype="S")
            dset = grp.create_dataset(
                "data",
                shape=(h_size, k_size, l_size),
                dtype=src.dtype,
                chunks=chunks,
                compression=compression,
            )
            for l_idx in range(l_size):
                slab_kh = src.nxdata[l_idx, :, :]  # (K,H)
                dset[:, :, l_idx] = slab_kh.T  # (H,K)
                if l_size:
                    _report(5 + int(85 * (l_idx + 1) / l_size), f"Writing slab {l_idx + 1}/{l_size}")
        else:
            grp.attrs["axes"] = np.array(["Ql", "Qk", "Qh"], dtype="S")
            dset = grp.create_dataset(
                "data",
                shape=(l_size, k_size, h_size),
                dtype=src.dtype,
                chunks=chunks,
                compression=compression,
            )
            for l_idx in range(l_size):
                dset[l_idx, :, :] = src.nxdata[l_idx, :, :]
                if l_size:
                    _report(5 + int(85 * (l_idx + 1) / l_size), f"Writing slab {l_idx + 1}/{l_size}")

        grp.create_dataset("Qh", data=qh)
        grp.create_dataset("Qk", data=qk)
        grp.create_dataset("Ql", data=ql)

    _report(100, "Standalone cache ready")

    return out_path


def _default_npy_base_path(path: str, *, order: Order) -> str:
    """Return deterministic base filename (without axis suffixes)."""

    suffix = "_hkl" if order == "hkl" else "_native"
    if path.lower().endswith(".nxs"):
        return path[:-4] + suffix + ".npy"
    return path + suffix + ".npy"


def save_transform_npy(
    path: str,
    *,
    out_path: str | None = None,
    order: Order = "hkl",
    overwrite: bool = False,
    h=None,
    k=None,
    l=None,
) -> dict[str, str]:
    """Save transform data as `.npy` for fast future loads.

    What gets written
    -----------------
    - `<out_path>`: counts array (either HKL or native ordering)
    - sibling axis files:
      - `<out_path>.Qh.npy`, `<out_path>.Qk.npy`, `<out_path>.Ql.npy` (order="hkl")
      - `<out_path>.Ql.npy`, `<out_path>.Qk.npy`, `<out_path>.Qh.npy` (order="native")

    Notes
    -----
    - `.npy` stores arrays only; NeXus metadata is not preserved.
    - For full-volume HKL saves, this uses a memory-mapped `.npy` and fills it slab-by-slab
      to avoid loading/transposing the entire 3D array in RAM.

    Parameters
    ----------
    path:
        Source `transform.nxs`.
    out_path:
        Destination `.npy` for counts. Defaults to `<path>_hkl.npy` or `<path>_native.npy`.
    order:
        "hkl" or "native".
    overwrite:
        Whether to overwrite existing output files.
    h, k, l:
        Optional ROI selectors in *H,K,L* order. If provided, only that subset is saved.
        (Uses the same normalization rules as `load_transform_fast`.)

    Returns
    -------
    dict[str, str]
        Paths written: {"counts": ..., "Qh": ..., "Qk": ..., "Ql": ...}.
    """

    if order not in ("hkl", "native"):
        raise ValueError(f"order must be 'native' or 'hkl', got: {order!r}")

    out_path = _default_npy_base_path(path, order=order) if out_path is None else out_path
    if not out_path.lower().endswith(".npy"):
        raise ValueError(f"out_path must end with .npy, got: {out_path}")

    qh_path = out_path + ".Qh.npy"
    qk_path = out_path + ".Qk.npy"
    ql_path = out_path + ".Ql.npy"

    for p in (out_path, qh_path, qk_path, ql_path):
        if os.path.exists(p) and not overwrite:
            raise FileExistsError(f"Output already exists: {p}. Set overwrite=True.")

    root = nxload(path)
    transform = root.entry.transform

    # Axes in HKL order are always the same arrays, regardless of how we store counts.
    qh = np.asarray(transform.Qh.nxdata)
    qk = np.asarray(transform.Qk.nxdata)
    ql = np.asarray(transform.Ql.nxdata)

    wants_roi = any(v is not None for v in (h, k, l))
    if wants_roi:
        h_idx = _normalize_index(h)
        k_idx = _normalize_index(k)
        l_idx = _normalize_index(l)

        if order == "native":
            # Native is (L,K,H)
            counts = transform.data.nxdata[l_idx, k_idx, h_idx]
        else:
            # Load ROI in native, then transpose to (H,K,L)
            roi_lkh = transform.data.nxdata[l_idx, k_idx, h_idx]
            counts = np.transpose(roi_lkh, (2, 1, 0))

        np.save(out_path, counts)
        np.save(qh_path, qh[h_idx])
        np.save(qk_path, qk[k_idx])
        np.save(ql_path, ql[l_idx])

        return {"counts": out_path, "Qh": qh_path, "Qk": qk_path, "Ql": ql_path}

    # Full volume
    if order == "native":
        counts = np.asarray(transform.data.nxdata)
        np.save(out_path, counts)
    else:
        # Source is (L,K,H); destination is (H,K,L)
        src = transform.data
        l_size, k_size, h_size = src.shape

        mm = open_memmap(out_path, mode="w+", dtype=src.dtype, shape=(h_size, k_size, l_size))
        for l_idx in range(l_size):
            slab_kh = src.nxdata[l_idx, :, :]  # (K,H)
            mm[:, :, l_idx] = slab_kh.T  # (H,K)
        mm.flush()

    np.save(qh_path, qh)
    np.save(qk_path, qk)
    np.save(ql_path, ql)

    return {"counts": out_path, "Qh": qh_path, "Qk": qk_path, "Ql": ql_path}


def load_transform_npy(
    counts_path: str,
    *,
    qh_path: str | None = None,
    qk_path: str | None = None,
    ql_path: str | None = None,
    mmap_mode: str | None = "r",
    order: Order = "hkl",
    print_tree: bool = False,
) -> NXdata:
    """Load an `.npy` transform cache written by `save_transform_npy`.

    Parameters
    ----------
    counts_path:
        Path to the counts `.npy`.
    qh_path, qk_path, ql_path:
        Optional explicit axis paths; by default uses `<counts_path>.Qh.npy`, etc.
    mmap_mode:
        Passed to `np.load` (use "r" for memory-mapped reads).
    order:
        The stored order of `counts_path`.
        - "hkl": axes are (Qh,Qk,Ql)
        - "native": axes are (Ql,Qk,Qh)
    """

    qh_path = counts_path + ".Qh.npy" if qh_path is None else qh_path
    qk_path = counts_path + ".Qk.npy" if qk_path is None else qk_path
    ql_path = counts_path + ".Ql.npy" if ql_path is None else ql_path

    counts = np.load(counts_path, mmap_mode=mmap_mode)
    qh = np.load(qh_path, mmap_mode=mmap_mode)
    qk = np.load(qk_path, mmap_mode=mmap_mode)
    ql = np.load(ql_path, mmap_mode=mmap_mode)

    if order == "hkl":
        data = NXdata(NXfield(counts, name="counts"), (NXfield(qh, name="Qh"), NXfield(qk, name="Qk"), NXfield(ql, name="Ql")))
    elif order == "native":
        data = NXdata(NXfield(counts, name="counts"), (NXfield(ql, name="Ql"), NXfield(qk, name="Qk"), NXfield(qh, name="Qh")))
    else:
        raise ValueError(f"order must be 'native' or 'hkl', got: {order!r}")

    if print_tree:
        print(data.tree)
    return data


def replace_transform_with_cache(
    path: str,
    *,
    backup_suffix: str = ".orig",
    compression: str | None = "lzf",
    chunks: tuple[int, int, int] | Literal["auto"] | None = "auto",
    overwrite_backup: bool = False,
) -> str:
    """Replace the original `.nxs` with an HKL-optimized cached `.nxs`.

    This is the "make the actual file faster" option.

    Safety notes
    -----------
    - A backup is created first (`<path><backup_suffix>`). By default this function
      refuses to overwrite an existing backup.
    - The cached file contains the `entry/transform` NXdata needed by loaders that
      expect transform data. If other tools rely on additional groups in the original
      file, replacing the file may break those tools. Prefer keeping the cache as a
      separate file unless you're sure.

    Returns
    -------
    str
        The original `path` (now pointing to the optimized file).
    """

    backup_path = path + backup_suffix
    if os.path.exists(backup_path) and not overwrite_backup:
        raise FileExistsError(
            f"Backup already exists: {backup_path}. "
            "Choose a different backup_suffix or set overwrite_backup=True."
        )

    tmp_cache = build_transform_hkl_cache(
        path,
        cache_path=_default_hkl_cache_path(path),
        overwrite=True,
        compression=compression,
        chunks=chunks,
    )

    # Swap in optimized file (atomic renames on the same filesystem).
    if overwrite_backup and os.path.exists(backup_path):
        os.remove(backup_path)
    os.replace(path, backup_path)
    os.replace(tmp_cache, path)
    return path


def _normalize_index(idx):
    """Normalize user indices so output stays 3D.

    - None -> slice(None)
    - int  -> slice(int, int+1) (keeps dimension)
    - slice -> slice

    This avoids dimensionality surprises (2D vs 3D) and keeps axes consistent.
    """

    if idx is None:
        return slice(None)
    if isinstance(idx, (int, np.integer)):
        i = int(idx)
        return slice(i, i + 1)
    if isinstance(idx, slice):
        return idx

    raise TypeError(
        f"Index must be None, int, or slice; got {type(idx)}. "
        "If you need fancy indexing, slice after loading a smaller ROI."
    )


def load_transform_fast(
    path: str,
    *,
    order: Order = "native",
    print_tree: bool = False,
    h=None,
    k=None,
    l=None,
    cache_hkl: bool = False,
    cache_path: str | None = None,
    rebuild_cache: bool = False,
    cache_compression: str | None = "lzf",
    cache_chunks: tuple[int, int, int] | Literal["auto"] | None = "auto",
) -> NXdata:
    """Load an nxrefine `transform.nxs` faster by default.

    Parameters
    ----------
    path:
        Path to the `transform.nxs` file.

    order:
        - "native": fastest/lowest-memory. Returns axes in the file's native order (Ql, Qk, Qh)
          matching the underlying dataset layout.
        - "hkl": returns axes in (Qh, Qk, Ql) order.

          If (h, k, l) are provided (ROI), only that subset is read and transposed.
          If no ROI is provided, this falls back to the slower full-load+transpose path
          from `nxs_analysis_tools.datareduction.load_transform`.

    print_tree:
        If True, prints the resulting NXdata tree.

    h, k, l:
        Optional ROI selectors in *H, K, L* axis order.
        Each can be None, an int, or a slice.
        (Ints are converted to 1-wide slices to keep the result 3D.)

    Returns
    -------
    NXdata
        The loaded transform data.
    """

    root = nxload(path)
    transform = root.entry.transform

    if order == "native":
        # This keeps an NXlink-backed signal; it avoids reading the full 3D array.
        data = NXdata(
            NXfield(transform.data, name="counts"),
            (transform.Ql, transform.Qk, transform.Qh),
        )

        if print_tree:
            print(data.tree)
        return data

    if order != "hkl":
        raise ValueError(f"order must be 'native' or 'hkl', got: {order!r}")

    wants_roi = any(v is not None for v in (h, k, l))

    if not wants_roi:
        if cache_hkl:
            cache_path_final = _default_hkl_cache_path(path) if cache_path is None else cache_path
            if rebuild_cache or not os.path.exists(cache_path_final):
                build_transform_hkl_cache(
                    path,
                    cache_path=cache_path_final,
                    overwrite=True,
                    compression=cache_compression,
                    chunks=cache_chunks,
                )

            cached = nxload(cache_path_final).entry.transform
            if print_tree:
                print(cached.tree)
            return cached

        # Back-compat path: same output as upstream helper, but potentially slow.
        from nxs_analysis_tools.datareduction import load_transform
        return load_transform(path, print_tree=print_tree, use_nxlink=False)

    h_idx = _normalize_index(h)
    k_idx = _normalize_index(k)
    l_idx = _normalize_index(l)

    # Underlying dataset is in (L, K, H) axis order when using NXlink.
    # Read only the requested ROI, then transpose to (H, K, L).
    roi_lkh = transform.data.nxdata[l_idx, k_idx, h_idx]
    roi_hkl = np.transpose(roi_lkh, (2, 1, 0))

    qh = NXfield(transform.Qh.nxdata[h_idx], name=transform.Qh.nxname)
    qk = NXfield(transform.Qk.nxdata[k_idx], name=transform.Qk.nxname)
    ql = NXfield(transform.Ql.nxdata[l_idx], name=transform.Ql.nxname)

    data = NXdata(NXfield(roi_hkl, name="counts"), (qh, qk, ql))

    if print_tree:
        print(data.tree)

    return data
