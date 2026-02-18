
from .instruments.rga100.rga  import RGA100
from .instruments.get_instruments import get_rga
from .instruments.rga100.sicp import SICP, Packet

# RGA100 is available with other names
RGA200 = RGA100
RGA300 = RGA100

try:
    from .plots.analogscanplot    import AnalogScanPlot
    from .plots.histogramscanplot import HistogramScanPlot
    from .plots.timeplot          import TimePlot
except (ImportError, ModuleNotFoundError):
    # Without matplotlib package installed, importing plot classes will fail.
    pass

__version__ = "0.3.9"  # Global version number


