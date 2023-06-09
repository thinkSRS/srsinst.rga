
from .instruments.rga100.rga  import RGA100
from .instruments.get_instruments import get_rga
from .instruments.rga100.sicp import SICP, Packet
from .plots.analogscanplot    import AnalogScanPlot
from .plots.histogramscanplot import HistogramScanPlot
from .plots.timeplot import TimePlot
from .version import VERSION

__version__ = VERSION  # Global version number
