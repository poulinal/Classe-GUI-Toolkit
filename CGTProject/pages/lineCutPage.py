# AP 2026
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QComboBox, QPushButton
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.collections import QuadMesh
from CGTProject.models.classeDataModel import ClasseDataModel
from CGTProject.widgets.analysisOptionsWidget import AnalysisOptionsWidget
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


def label(field):
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

class LineCutPage(QWidget):
    def __init__(self, extractedData : NXdata):
        super().__init__()
        layout = QVBoxLayout()
        
        self.lineCutFigure = Figure(figsize=(8, 6), dpi=100)
        self.lineCutCanvas = FigureCanvas(self.lineCutFigure)
        self.lineCutAxes = self.lineCutFigure.add_subplot(111)
        self.plotNXData(extractedData)
        
        #filter options toggle checkbox
        analysisOptionsLayout = QVBoxLayout() #sub layout for filter options toggle and filter options widget
        self.analysisOptionsToggle = QPushButton("▶ Show Filter Options")
        self.analysisOptionsToggle.setCheckable(True)
        self.analysisOptionsToggle.clicked.connect(self.toggleFilterOptions)
        self.analysisOptionsWidget = AnalysisOptionsWidget()
        self.analysisOptionsWidget.hide() #start hidden
        # self.analysisOptionsWidget.gaussianFilter.connect(lambda state, sigma: self.setGaussianFilter(state, sigma))
        analysisOptionsLayout.addWidget(self.analysisOptionsToggle)
        analysisOptionsLayout.addWidget(self.analysisOptionsWidget)
        layout.addLayout(analysisOptionsLayout)
        
        
        layout.addWidget(self.lineCutCanvas)
        self.setLayout(layout)
        
    def toggleFilterOptions(self):
        if self.analysisOptionsToggle.isChecked():
            self.analysisOptionsToggle.setText("▼ Hide Filter Options")
            # self.layoutCol2Row2.addWidget(self.lineCoords)
            self.analysisOptionsWidget.setVisible(True)
        else:
            self.analysisOptionsToggle.setText("▶ Show Filter Options")
            # self.layoutCol2Row2.removeWidget(self.lineCoords)
            self.analysisOptionsWidget.hide()
            
    def extractNDArrayFromNXdata(self, extractedData : NXdata) -> tuple[np.ndarray, np.ndarray]:
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
        
    def plotNXData(self, extractedData : NXdata):
        x_data, y_data = self.extractNDArrayFromNXdata(extractedData)
        print(f"Plotting line cut with x_data: {x_data}, y_data: {y_data}, with lengths x: {len(x_data)}, y: {len(y_data)}")

        self.lineCutAxes.clear()
        self.lineCutAxes.plot(x_data, y_data)
        self.lineCutAxes.set_xlabel(label(extractedData.nxaxes[0]))
        self.lineCutAxes.set_ylabel(label(extractedData.nxsignal))
        self.lineCutAxes.set_title(extractedData.nxtitle)
        self.lineCutCanvas.draw()
        
    # def plotNXData(self, extractedData : NXdata, fmt=None, xmin=None, xmax=None,
    #          ymin=None, ymax=None, vmin=None, vmax=None, **kwargs):
    #     self.lineCutAxes.clear()
        
    #     over = kwargs.pop("over", False)
    #     image = kwargs.pop("image", False)
    #     log = kwargs.pop("log", False)
    #     logx = kwargs.pop("logx", False)
    #     logy = kwargs.pop("logy", False)
    #     origin = kwargs.pop("origin", "lower")
    #     aspect = kwargs.pop("aspect", "auto")
    #     regular = kwargs.pop("regular", False)
    #     cmap = kwargs.pop("cmap", "viridis")
    #     colorbar = kwargs.pop("colorbar", True)
    #     interpolation = kwargs.pop("interpolation", "nearest")
    #     bad = kwargs.pop("bad", "darkgray")
    #     weights = kwargs.pop("weights", False)
    #     ax = kwargs.pop("ax", None)

    #     signal = extractedData.nxsignal
    #     if signal.ndim > 2 and not image:
    #         raise NeXusError(
    #             "Can only plot 1D and 2D data - please select a slice")
    #     errors = extractedData.nxerrors
    #     title = extractedData.nxtitle

    #     # Provide a new view of the data if there is a dimension of length 1
    #     data, axes = (signal.nxdata.reshape(extractedData.plot_shape),
    #                   extractedData.plot_axes)
        
    #     if weights and extractedData.nxweights:
    #         with np.errstate(divide='ignore'):
    #             w = extractedData.nxweights.nxdata.reshape(extractedData.plot_shape)
    #             data = np.where(w > 0, data/w, 0.0)

    #     # isinteractive = plt.isinteractive()
    #     # plt.ioff()

    #     try:
    #         if over:
    #             # plt.autoscale(False)
    #             self.lineCutAxes.autoscale(False)
    #         else:
    #             # plt.autoscale(True)
    #             self.lineCutAxes.autoscale(True)
    #             if ax is None:
    #                 # plt.clf()
    #                 self.lineCutAxes.clear()
    #         if ax:
    #             # plt.sca(ax)
    #             self.lineCutAxes = ax
    #         else:
    #             ax = self.lineCutAxes

    #         # One-dimensional Plot
    #         if len(data.shape) == 1:
    #             if 'marker' in kwargs:
    #                 fmt = kwargs.pop('marker')
    #             else:
    #                 fmt = 'o'
    #             if 'units' in signal.attrs:
    #                 if not errors and signal.attrs['units'] == 'counts':
    #                     errors = NXfield(np.sqrt(data))
    #             if errors:
    #                 ebars = errors.nxdata
    #                 ax.errorbar(centers(axes[0], data.shape[0]), data, ebars,
    #                             fmt=fmt, **kwargs)
    #             else:
    #                 ax.plot(centers(axes[0], data.shape[0]), data, fmt,
    #                         **kwargs)
    #             if not over:
    #                 if xmin is not None:
    #                     ax.set_xlim(left=xmin)
    #                 if xmax is not None:
    #                     ax.set_xlim(right=xmax)
    #                 if ymin is not None:
    #                     ax.set_ylim(bottom=ymin)
    #                 if ymax is not None:
    #                     ax.set_ylim(top=ymax)
    #                 if logx:
    #                     ax.set_xscale('log')
    #                 if log or logy:
    #                     ax.set_yscale('log')
    #                 # plt.xlabel(label(axes[0]))
    #                 # plt.ylabel(label(signal))
    #                 # plt.title(title)
    #                 self.lineCutAxes.set_xlabel(label(axes[0]))
    #                 self.lineCutAxes.set_ylabel(label(signal))
    #                 self.lineCutAxes.set_title(title)
                    
    #         # Two dimensional plot
    #         else:
    #             from matplotlib.colors import LogNorm, Normalize

    #             if image:
    #                 x = boundaries(axes[-1], data.shape[-2])
    #                 y = boundaries(axes[-2], data.shape[-3])
    #                 xlabel, ylabel = label(axes[-1]), label(axes[-2])
    #             else:
    #                 x = boundaries(axes[-1], data.shape[-1])
    #                 y = boundaries(axes[-2], data.shape[-2])
    #                 xlabel, ylabel = label(axes[-1]), label(axes[-2])

    #             if not vmin:
    #                 vmin = np.nanmin(data[data > -np.inf])
    #             if not vmax:
    #                 vmax = np.nanmax(data[data < np.inf])

    #             if image:
    #                 im = ax.imshow(data, origin='upper', **kwargs)
    #                 ax.set_aspect('equal')
    #             else:
    #                 if log:
    #                     vmin = max(vmin, 0.01)
    #                     vmax = max(vmax, 0.01)
    #                     kwargs["norm"] = LogNorm(vmin, vmax)
    #                 else:
    #                     kwargs["norm"] = Normalize(vmin, vmax)

    #                 cm = plt.get_cmap(cmap).copy()
    #                 cm.set_bad(bad)
    #                 if regular:
    #                     extent = (x[0], x[-1], y[0], y[-1])
    #                     kwargs['interpolation'] = interpolation
    #                     im = ax.imshow(data, origin=origin, extent=extent,
    #                                    cmap=cm, **kwargs)
    #                 else:
    #                     im = ax.pcolormesh(x, y, data, cmap=cm, **kwargs)
    #                     ax.set_xlim(x[0], x[-1])
    #                     ax.set_ylim(y[0], y[-1])
    #                 if aspect == 'equal':
    #                     try:
    #                         if 'scaling_factor' in axes[-1].attrs:
    #                             _xscale = axes[-1].attrs['scaling_factor']
    #                         else:
    #                             _xscale = 1.0
    #                         if 'scaling_factor' in axes[-2].attrs:
    #                             _yscale = axes[-2].attrs['scaling_factor']
    #                         else:
    #                             _yscale = 1.0
    #                         aspect = float(_yscale / _xscale)
    #                     except Exception as error:
    #                         raise NeXusError(str(error))
    #                 ax.set_aspect(aspect)
    #                 if colorbar:
    #                     # cb = plt.colorbar(im)
    #                     cb = self.lineCutFigure.colorbar(im, ax=ax)
    #                     if cmap == 'tab10':
    #                         cmin, cmax = im.get_clim()
    #                         if cmax - cmin <= 9:
    #                             if cmin == 0:
    #                                 im.set_clim(-0.5, 9.5)
    #                             elif cmin == 1:
    #                                 im.set_clim(0.5, 10.5)
    #                             if Version(mplversion) >= Version('3.5.0'):
    #                                 cb.ax.set_ylim(cmin-0.5, cmax+0.5)
    #                                 cb.set_ticks(range(int(cmin), int(cmax)+1))

    #             if xmin is not None:
    #                 ax.set_xlim(left=xmin)
    #             if xmax is not None:
    #                 ax.set_xlim(right=xmax)
    #             if ymin is not None:
    #                 if image:
    #                     ax.set_ylim(top=ymin)
    #                 else:
    #                     ax.set_ylim(bottom=ymin)
    #             if ymax is not None:
    #                 if image:
    #                     ax.set_ylim(bottom=ymax)
    #                 else:
    #                     ax.set_ylim(top=ymax)

    #             # plt.xlabel(xlabel)
    #             # plt.ylabel(ylabel)
    #             # plt.title(title)
    #             self.lineCutAxes.set_xlabel(xlabel)
    #             self.lineCutAxes.set_ylabel(ylabel)
    #             self.lineCutAxes.set_title(title)

    #         # if isinteractive:
    #         #     plt.pause(0.001)
    #         #     plt.show(block=False)
    #         # else:
    #         #     plt.show()

    #     # finally:
    #     #     if isinteractive:
    #     #         plt.ion()
        
    #         self.lineCutCanvas.draw()
    #     except Exception as e:
    #         print(f"Error plotting NXdata: {e}")
            
    #         raise e
        