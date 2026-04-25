#AP 2026
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

    axis_data = np.asarray(nxdata[axis_name])
    signal_data = np.asarray(nxdata[signal_name])

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
        slicer = [slice(None)] * signal_data.ndim
        slicer[axis_index] = slice(start_index, end_index + 1)
        trimmed_signal_chunks.append(signal_data[tuple(slicer)])
        trimmed_axis_chunks.append(axis_data[start_index:end_index + 1])

    if not trimmed_signal_chunks:
        return nxdata

    if len(trimmed_signal_chunks) == 1:
        trimmed_signal = trimmed_signal_chunks[0]
        trimmed_axis = trimmed_axis_chunks[0]
    else:
        trimmed_signal = np.concatenate(trimmed_signal_chunks, axis=axis_index)
        trimmed_axis = np.concatenate(trimmed_axis_chunks, axis=0)

    trimmed_nxdata = NXdata()
    trimmed_nxdata.attrs['axes'] = axis_name if len(axis_names) == 1 else tuple(axis_names)
    trimmed_nxdata.attrs['signal'] = signal_name

    for idx, name in enumerate(axis_names):
        if idx == axis_index:
            trimmed_nxdata[name] = NXfield(trimmed_axis, name=name)
        else:
            trimmed_nxdata[name] = NXfield(np.asarray(nxdata[name]), name=name)

    trimmed_nxdata[signal_name] = NXfield(trimmed_signal, name=signal_name)

    return trimmed_nxdata