#AP 2026
import json
import numpy as np
from nexusformat.nexus import NXdata, NeXusError, nxsetmemory, NXfield
def centers(axis, dimlen):
    """Return the centers of the axis bins.

    This works regardless of whether the axis consists of bin boundaries,
    i.e, `dimlen = len(axis) + 1``, or centers, i.e., `dimlen = len(axis)`.

    Parameters
    ----------
    axis : ndarray
        Array containing the axis values.
    dimlen : int
        Length of corresponding data dimension.

    Returns
    -------
    ndarray
        Array of bin centers with a size of dimlen.
    """
    ax = axis.astype(np.float64)
    if ax.shape[0] == dimlen+1:
        return (ax[:-1] + ax[1:])/2
    else:
        assert ax.shape[0] == dimlen
        return ax


def boundaries(axis, dimlen):
    """Return the axis bin boundaries.

    This works regardless of whether the axis consists of bin boundaries,
    i.e, dimlen = len(axis) + 1, or centers, i.e., dimlen = len(axis).

    Parameters
    ----------
    axis : ndarray
        Array containing the axis values.
    dimlen : int
        Length of corresponding data dimension.

    Returns
    -------
    ndarray
        Array of bin boundaries with a size of dimlen + 1.
    """
    ax = axis.astype(np.float64)
    if ax.shape[0] == dimlen:
        start = ax[0] - (ax[1] - ax[0])/2
        end = ax[-1] + (ax[-1] - ax[-2])/2
        return np.concatenate((np.atleast_1d(start),
                               (ax[:-1] + ax[1:])/2,
                               np.atleast_1d(end)))
    else:
        assert ax.shape[0] == dimlen + 1
        return ax


def nxlabel(field):
    """Return a label for a data field suitable for use on a graph axis.

    This returns the attribute 'long_name' if it exists, or the field name,
    followed by the units attribute if it exists.

    Parameters
    ----------
    field : NXfield
        NeXus field used to construct the label.

    Returns
    -------
    str
        Axis label.
    """
    if 'long_name' in field.attrs:
        return field.long_name
    elif 'units' in field.attrs:
        return f"{field.nxname} ({field.units})"
    else:
        return field.nxname
    
def extractNDArrayFromNXdata(extractedData : NXdata) -> tuple[np.ndarray, np.ndarray]:
    nxdata = extractedData
    # Get axis name(s) from @axes attribute
    axes_attr = nxdata.attrs['axes']
    if isinstance(axes_attr, str):
        axis_names = [axes_attr]  # Single axis
    else:
        axis_names = list(axes_attr)  # Multiple axes

    # Get signal name from @signal attribute
    signal_name = nxdata.attrs['signal']

    # Extract data as numpy arrays
    axes_data = [np.array(nxdata[name]) for name in axis_names]
    signal_data = np.array(nxdata[signal_name])

    # For single axis case:
    x_data = axes_data[0]
    y_data = signal_data
    
    # if 2D
    # axes_data[0] -> Qh, axes_data[1] -> Qk
    # X, Y = np.meshgrid(axes_data[0], axes_data[1])
    # plt.pcolormesh(X, Y, signal_data)
    return x_data, y_data

def trimNXdataToAxisLimits(nxdata : NXdata, axis_index: int, min_val: float, max_val: float) -> NXdata:
    """Trim the NXdata to the specified axis limits along the given axis index.

    Parameters
    ----------
    nxdata : NXdata
        The input NXdata object to be trimmed.
    axis_index : int
        The index of the axis to trim (0 for first axis, 1 for second, etc.).
    min_val : float
        The minimum value of the axis to keep.
    max_val : float
        The maximum value of the axis to keep.
    Returns
    -------
    NXdata
        A new NXdata object containing only the data within the specified axis limits.
    """
    
    axes_attr = nxdata.attrs['axes']
    axis_names = [axes_attr] if isinstance(axes_attr, str) else list(axes_attr)
    axis_name = axis_names[axis_index]

    axis_data = np.asarray(nxdata[axis_name])
    if min_val > max_val:
        min_val, max_val = max_val, min_val

    indices = np.where((axis_data >= min_val) & (axis_data <= max_val))[0]
    if indices.size == 0:
        return nxdata

    segments: list[tuple[int, int]] = []
    segment_start = int(indices[0])
    segment_end = int(indices[0])
    for index in indices[1:]:
        index = int(index)
        if index == segment_end + 1:
            segment_end = index
        else:
            segments.append((segment_start, segment_end))
            segment_start = index
            segment_end = index
    segments.append((segment_start, segment_end))

    return trimNXdataToAxisSegments(nxdata, axis_index, segments)


def trimNXdataToAxisSegments(nxdata: NXdata, axis_index: int, segments: list[tuple[int, int]]) -> NXdata:
    """Trim an NXdata object to one or more index ranges along a single axis.

    The kept ranges are concatenated in the order they are provided after sorting.
    Ranges are inclusive on both ends.
    """

    axes_attr = nxdata.attrs['axes']
    axis_names = [axes_attr] if isinstance(axes_attr, str) else list(axes_attr)
    axis_name = axis_names[axis_index]
    signal_name = nxdata.attrs['signal']

    axis_field = nxdata[axis_name]
    signal_field = nxdata[signal_name]
    axis_data = np.asarray(axis_field)

    if axis_data.size == 0:
        return nxdata

    normalized_segments: list[tuple[int, int]] = []
    axis_max_index = axis_data.shape[0] - 1
    for start, end in segments:
        start_index = max(0, min(int(start), axis_max_index))
        end_index = max(0, min(int(end), axis_max_index))
        if start_index > end_index:
            start_index, end_index = end_index, start_index
        normalized_segments.append((start_index, end_index))

    normalized_segments.sort(key=lambda pair: pair[0])

    trimmed_signal_chunks: list[np.ndarray] = []
    trimmed_axis_chunks: list[np.ndarray] = []

    for start_index, end_index in normalized_segments:
        slicer = [slice(None)] * signal_field.ndim
        slicer[axis_index] = slice(start_index, end_index + 1)
        trimmed_signal_chunks.append(np.asarray(signal_field[tuple(slicer)]))
        trimmed_axis_chunks.append(axis_data[start_index:end_index + 1])

    if not trimmed_signal_chunks:
        return nxdata

    if len(trimmed_signal_chunks) == 1:
        trimmed_signal = trimmed_signal_chunks[0]
        trimmed_axis = trimmed_axis_chunks[0]
    else:
        trimmed_signal = np.concatenate(trimmed_signal_chunks, axis=axis_index)
        trimmed_axis = np.concatenate(trimmed_axis_chunks, axis=0)

    segment_ranges: list[str] = []
    for start_index, end_index in normalized_segments:
        start_value = axis_data[start_index]
        end_value = axis_data[end_index]
        segment_ranges.append(f"{start_value:.6g}-{end_value:.6g}")

    trimmed_nxdata = NXdata()
    trimmed_nxdata.attrs['axes'] = axis_name if len(axis_names) == 1 else tuple(axis_names)
    trimmed_nxdata.attrs['signal'] = signal_name
    trimmed_nxdata.attrs['trim_axis_name'] = axis_name
    if axis_name.lower().startswith("q") and len(axis_name) > 1:
        axis_label = axis_name[1:].upper()
    else:
        axis_label = axis_name.upper()
    trimmed_nxdata.attrs['trim_axis_label'] = axis_label
    trimmed_nxdata.attrs['trim_ranges'] = ";".join(segment_ranges)

    existing_history = nxdata.attrs.get("trim_history_json", "")
    trim_history: list[dict[str, object]] = []
    if existing_history:
        try:
            parsed_history = json.loads(str(existing_history))
            if isinstance(parsed_history, list):
                trim_history = [entry for entry in parsed_history if isinstance(entry, dict)]
        except Exception:
            trim_history = []

    new_entry = {
        "axis_name": axis_name,
        "axis_label": axis_label,
        "ranges": [
            {
                "start": float(axis_data[start_index]),
                "end": float(axis_data[end_index]),
            }
            for start_index, end_index in normalized_segments
        ],
    }

    trim_history.append(new_entry)
    trimmed_nxdata.attrs['trim_history_json'] = json.dumps(trim_history)

    # Propagate bin history so saved filenames retain prior bin ops.
    for bin_attr in ("bin_history_json", "bin_factors", "bin_reduction"):
        if bin_attr in nxdata.attrs:
            trimmed_nxdata.attrs[bin_attr] = nxdata.attrs[bin_attr]

    for idx, name in enumerate(axis_names):
        if idx == axis_index:
            trimmed_nxdata[name] = NXfield(trimmed_axis, name=name)
        else:
            trimmed_nxdata[name] = NXfield(np.asarray(nxdata[name]), name=name)

    trimmed_nxdata[signal_name] = NXfield(trimmed_signal, name=signal_name)

    return trimmed_nxdata


def binNXdataByFactors(nxdata: NXdata, factors: list[int], reduction: str = "mean") -> NXdata:
    """Coarsen an NXdata object by integer factors along each axis.

    For each axis with factor f > 1, the signal is truncated to a length divisible by f
    along that axis, then grouped into bins of f and reduced. Axis values are reduced
    by mean over the same groups so they remain bin centers.
    """
    if reduction not in ("mean", "sum"):
        raise ValueError(f"reduction must be 'mean' or 'sum', got {reduction!r}")

    axes_attr = nxdata.attrs['axes']
    axis_names = [axes_attr] if isinstance(axes_attr, str) else list(axes_attr)
    signal_name = nxdata.attrs['signal']

    signal_field = nxdata[signal_name]
    if len(factors) != signal_field.ndim:
        raise ValueError(
            f"factors length ({len(factors)}) must match signal ndim ({signal_field.ndim})"
        )

    normalized_factors = [max(1, int(f)) for f in factors]

    # Truncate each axis to a length divisible by its factor so the reshape is exact.
    slicer = []
    for dim_size, factor in zip(signal_field.shape, normalized_factors):
        new_len = (dim_size // factor) * factor
        slicer.append(slice(0, new_len))
    signal_arr = np.asarray(signal_field[tuple(slicer)])

    # Reshape to expose the bin groups, then reduce.
    reshape_dims = []
    reduce_axes = []
    for axis_idx, (new_size, factor) in enumerate(
        zip(signal_arr.shape, normalized_factors)
    ):
        bins = new_size // factor
        reshape_dims.extend([bins, factor])
        reduce_axes.append(len(reshape_dims) - 1)
    reshaped = signal_arr.reshape(reshape_dims)
    reducer = np.mean if reduction == "mean" else np.sum
    binned_signal = reducer(reshaped, axis=tuple(reduce_axes))

    binned_nxdata = NXdata()
    binned_nxdata.attrs['axes'] = axis_names[0] if len(axis_names) == 1 else tuple(axis_names)
    binned_nxdata.attrs['signal'] = signal_name
    binned_nxdata.attrs['bin_factors'] = tuple(normalized_factors)
    binned_nxdata.attrs['bin_reduction'] = reduction

    # Propagate trim history so saved filenames retain prior trims.
    for trim_attr in ("trim_history_json", "trim_axis_name", "trim_axis_label", "trim_ranges"):
        if trim_attr in nxdata.attrs:
            binned_nxdata.attrs[trim_attr] = nxdata.attrs[trim_attr]

    existing_history = nxdata.attrs.get("bin_history_json", "")
    bin_history: list[dict[str, object]] = []
    if existing_history:
        try:
            parsed_history = json.loads(str(existing_history))
            if isinstance(parsed_history, list):
                bin_history = [entry for entry in parsed_history if isinstance(entry, dict)]
        except Exception:
            bin_history = []

    bin_history.append({
        "factors": [int(f) for f in normalized_factors],
        "reduction": reduction,
        "axis_names": list(axis_names),
    })
    binned_nxdata.attrs['bin_history_json'] = json.dumps(bin_history)

    for axis_idx, name in enumerate(axis_names):
        axis_arr = np.asarray(nxdata[name]).astype(np.float64)
        factor = normalized_factors[axis_idx]
        new_len = (axis_arr.shape[0] // factor) * factor
        axis_arr = axis_arr[:new_len]
        if factor > 1:
            axis_arr = axis_arr.reshape(-1, factor).mean(axis=1)
        binned_nxdata[name] = NXfield(axis_arr, name=name)

    binned_nxdata[signal_name] = NXfield(binned_signal, name=signal_name)
    return binned_nxdata