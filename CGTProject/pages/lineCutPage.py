# AP 2026
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QComboBox, QPushButton, QTableWidget, QTableWidgetItem
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.collections import QuadMesh
from CGTProject.models.temperatureDataModel import TemperatureDataModel
from CGTProject.widgets.analysisOptionsWidget import AnalysisOptionsWidget
from CGTProject.widgets.plottedLineCutGraphWidget import PlottedLineCutGraphWidget
from CGTProject.widgets.plottedGraphWidget import PlottedGraphWidget
from CGTProject.utilities.NXDataHandler import extractNDArrayFromNXdata, nxlabel, trimNXdataToAxisLimits
import numpy as np

from nexusformat.nexus import NXdata, NeXusError, nxsetmemory, NXfield
from nxs_analysis_tools.fitting import LinecutModel
from lmfit.models import GaussianModel, LinearModel
from lmfit.parameter import Parameter

class LineCutPage(QWidget):
    def __init__(self, extractedData : NXdata):
        super().__init__()
        layout = QVBoxLayout()
        
        # self.lineCutFigure = Figure(figsize=(8, 6), dpi=100)
        # self.lineCutCanvas = FigureCanvas(self.lineCutFigure)
        # self.lineCutAxes = self.lineCutFigure.add_subplot(111)
        # self.plotNXData(extractedData)
        self.extractedData = extractedData
        self.plottedLineCutWidget = PlottedLineCutGraphWidget()
        self.plottedLineCutWidget.lineCutModeActivated.connect(self.onLineCutModeActivated)
        
        #filter options toggle checkbox
        analysisOptionsLayout = QVBoxLayout() #sub layout for filter options toggle and filter options widget
        self.analysisOptionsToggle = QPushButton("▶ Show Filter Options")
        self.analysisOptionsToggle.setCheckable(True)
        self.analysisOptionsToggle.setEnabled(False)
        self.analysisOptionsToggle.clicked.connect(self.toggleFilterOptions)
        self.analysisOptionsWidget = AnalysisOptionsWidget()
        self.analysisOptionsWidget.fitLineCut.connect(lambda fitType, compositeModels: self.fitLineCut(fitType, compositeModels))
        self.analysisOptionsWidget.hide() #start hidden
    
        #lm.params gives a table of parameters
        self.LMParams = QTableWidget()
        self.LMParams.setRowCount(7)
        self.LMParams.setColumnCount(7)
        self.LMParams.setHorizontalHeaderLabels(["Name", "Value", "Initial Value", "Min", "Max", "Vary", "Expression"])
        self.LMParams.setVisible(False) #start hidden, only show when fit is performed
        
        analysisOptionsLayout.addWidget(self.analysisOptionsToggle)
        analysisOptionsLayout.addWidget(self.analysisOptionsWidget)
        analysisOptionsLayout.addWidget(self.LMParams)
        layout.addLayout(analysisOptionsLayout)
        
        self.redrawPlot()
        
        
        layout.addWidget(self.plottedLineCutWidget)
        self.setLayout(layout)
        
    def redrawPlot(self):
        if self.extractedData:
            self.plottedLineCutWidget.updateNXDataPlot(self.extractedData)
        
    def toggleFilterOptions(self):
        if self.analysisOptionsToggle.isChecked():
            self.analysisOptionsToggle.setText("▼ Hide Filter Options")
            # self.layoutCol2Row2.addWidget(self.lineCoords)
            self.analysisOptionsWidget.setVisible(True)
        else:
            self.analysisOptionsToggle.setText("▶ Show Filter Options")
            # self.layoutCol2Row2.removeWidget(self.lineCoords)
            self.analysisOptionsWidget.hide()
            
    def onLineCutModeActivated(self, enabled: bool):
        if enabled:
            print("Line cut mode activated - enable filter options")
            self.analysisOptionsToggle.setEnabled(True)
        else:
            print("Line cut mode deactivated - disable filter options")
            self.analysisOptionsToggle.setEnabled(False)
            
    def fitLineCut(self, fitType: str, compositeModels: list[str]):
        print(f"Fitting LineCut with FitType: {fitType}, CompositeModels: {compositeModels}")
        #get teh range of self.extractedData between the two vertical lines if in vertical line cut mode, otherwise use the whole range
        twoVertLines = self.plottedLineCutWidget.getTwoVertLines()
        
        
        # x1, x2 = twoVertLines
        # filtered_data = trimNXdataToAxisLimits(self.extractedData, axis_index=0, min_val=min(x1, x2), max_val=max(x1, x2))
        
        # Get full x, y for display
        _full_lm = LinecutModel(data=self.extractedData)
        x = _full_lm.x
        y = _full_lm.y

        # Create fitting model on the trimmed range if twoVertLines is set
        if twoVertLines is not None:
            x1, x2 = twoVertLines
            mask = (x >= min(x1, x2)) & (x <= max(x1, x2)) ##TODO : can i make this more modular instead of hard coding attrs
            x_fit, y_fit = x[mask], y[mask]
            signal_name = self.extractedData.attrs['signal']
            axes_attr = self.extractedData.attrs['axes']
            axis_name = axes_attr if isinstance(axes_attr, str) else list(axes_attr)[0]
            _fit_data = NXdata()
            _fit_data.attrs['axes'] = axis_name
            _fit_data.attrs['signal'] = signal_name
            _fit_data[axis_name] = NXfield(x_fit)
            _fit_data[signal_name] = NXfield(y_fit)
            lm = LinecutModel(data=_fit_data)
        else:
            lm = LinecutModel(data=self.extractedData)

        self.LMParams.setVisible(True)  # Show the parameters table when fit is performed

        #model: set_model_components(GaussianModel(prefix='peak'))
        #list of models: set_model_components(GaussianModel(prefix='peak'), LinearModel(prefix='background')])
        #composite: set_model_components(GaussianModel(prefix='peak') + LinearModel(prefix='background'))
        if fitType == "Model":
            model_name = compositeModels[0] if compositeModels else None
            if model_name == "Gaussian":
                model = GaussianModel(prefix='peak')
            elif model_name == "Linear":
                model = LinearModel(prefix='background')
            else:
                print(f"Unsupported model type: {model_name}")
                return
            lm.set_model_components(model)
        elif fitType == "Composite":
            model_components = []
            for modeli, model_name in enumerate(compositeModels):
                if model_name == "Gaussian":
                    model_components.append(GaussianModel(prefix=f'peak{modeli}'))
                elif model_name == "Linear":
                    model_components.append(LinearModel(prefix=f'background{modeli}'))
                else:
                    print(f"Unsupported model type: {model_name}")
                    return
            print(model_components)
            composite_model = model_components[0]
            for m in model_components[1:]:
                composite_model += m
            lm.set_model_components(composite_model)
        elif fitType == "List Of Models":
            model_components = []
            for modelj, model_name in enumerate(compositeModels):
                if model_name == "Gaussian":
                    model_components.append(GaussianModel(prefix=f'peak{modelj}'))
                elif model_name == "Linear":
                    model_components.append(LinearModel(prefix=f'background{modelj}'))
                else:
                    print(f"Unsupported model type: {model_name}")
                    return
            # lm.set_model_components(*model_components)
            lm.set_model_components(model_components)
        else:
            print(f"Unsupported FitType: {fitType}")
            return
        
        # trimmedX is the x range used for fitting (already trimmed to twoVertLines range if set)
        trimmedX = lm.x
        lm.guess()

        # # For multiple Gaussians, spread initial centers using peak detection
        # if fitType in ("Composite", "List Of Models"):
        #     from scipy.signal import find_peaks
        #     gaussian_indices = [i for i, m in enumerate(compositeModels) if m == "Gaussian"]
        #     if len(gaussian_indices) > 1:
        #         fy = lm.y
        #         fx = lm.x
        #         min_dist = max(1, len(fx) // (len(gaussian_indices) + 1))
        #         peaks_idx, _ = find_peaks(fy, distance=min_dist)
        #         if len(peaks_idx) >= len(gaussian_indices):
        #             # Pick the tallest N peaks, sorted by position
        #             top_n = np.argsort(fy[peaks_idx])[-len(gaussian_indices):]
        #             peak_positions = np.sort(fx[peaks_idx[np.sort(top_n)]])
        #         else:
        #             # Fall back: evenly space centers across the range
        #             peak_positions = np.linspace(fx.min(), fx.max(), len(gaussian_indices) + 2)[1:-1]
        #         for i, pos in zip(gaussian_indices, peak_positions):
        #             lm.params[f'peak{i}center'].set(value=pos)
        #             print(f"Initialized peak{i}center = {pos}")

        lmparams : Parameter = lm.params
        
        # lm.plot_initial_guess()
        lm.fit()
        # lm.plot_fit()
        
        # Update the table with parameter values
        # self.LMParams.setRowCount(len(lmparams))
        for i, (param_name, param) in enumerate(lmparams.items()):
            self.LMParams.setItem(i, 0, QTableWidgetItem(param_name))
            self.LMParams.setItem(i, 1, QTableWidgetItem(str(param.value)))
            self.LMParams.setItem(i, 2, QTableWidgetItem(str(param.init_value)))
            self.LMParams.setItem(i, 3, QTableWidgetItem(str(param.min)))
            self.LMParams.setItem(i, 4, QTableWidgetItem(str(param.max)))
            self.LMParams.setItem(i, 5, QTableWidgetItem(str(param.vary)))
            self.LMParams.setItem(i, 6, QTableWidgetItem(str(param.expr)))
        # if numpoints is None:
        #     numpoints = len(self.x)
        # self.x_eval = np.linspace(self.x.min(), self.x.max(), numpoints)
        # self.y_eval = self.modelresult.eval(x=self.x_eval)
        # self.y_eval_components = self.modelresult.eval_components(x=self.x_eval)
        # self.modelresult.plot(numpoints=numpoints, **kwargs)
        # ax = plt.gca()
        # for model_component, value in self.y_eval_components.items():
        #     ax.fill_between(self.x_eval, value, alpha=0.3, label=model_component)
        #     # ax.plot(self.x_eval, value, label=model_component)
        # plt.legend()
        # plt.show()
        # if fit_report:
        #     print(self.modelresult.fit_report())
        # return ax
        
        numpoints=None
        model = lm.model
        params = lm.params
        y_init_fit = model.eval(params=params, x=trimmedX)
        
        #open a new PlottedGraphWidget as a new window to show the initial fit guess
        self.initialFitPlot = PlottedGraphWidget()
        self.initialFitPlot.updateXYPlot(x, y, marker='o', label='data')
        # self.initialFitPlot.updateXYPlot(trimmedX, y_init_fit, linestyle='--', label='initial guess', holdprevious=True)
        # self.initialFitPlot.ax_main.legend()
        # plt.plot(x, y, 'o', label='data')
        # plt.plot(x, y_init_fit, '--', label='guess')

        # Plot the components of the model
        if numpoints is None:
            numpoints = len(lm.x)
        # x_eval = np.linspace(lm.x.min(), lm.x.max(), numpoints)
        x_eval = np.linspace(trimmedX.min(), trimmedX.max(), numpoints)
        y_init_fit_components = model.eval_components(params=params, x=x_eval)
        for component in y_init_fit_components.keys():
            print(f"Model component: {component}")
            self.initialFitPlot.updateXYPlot(x_eval, y_init_fit_components[component], linestyle='--', label=component+'fit', holdprevious=True)
        self.initialFitPlot.ax_main.legend()
        ax = self.initialFitPlot.ax_main
        for model_component, value in y_init_fit_components.items():
            ax.fill_between(x_eval, value, alpha=0.3, label=model_component)
            
        
        #show widget as new window
        self.initialFitPlot.show()
        ###TODO
        #make modelType and compositeModel in enums
        #fix why the data is getting changed when we plot the fit guess
        #do 3dpdf
        
    
        
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
        