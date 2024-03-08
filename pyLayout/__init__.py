
from .lib.desktop import initializeDesktop,releaseDesktop
from .lib.component import Components
from .lib.pin import Pins
from .lib.net import Nets
from .lib.layer import Layers
from .lib.material import Materials
from .lib.variable import Variables
from .lib.setup import Setups
from .lib.solution import Solutions
from .lib.port import Ports
from .lib.line import Lines
from .lib.via import Vias
from .lib.padStack import PadStacks
from .lib.shape import Shapes
from .lib.complexDict import ComplexDict
from .lib.arrayStruct import ArrayStruct
from .lib.unit import Unit
from .lib.common import *
from .lib.layoutOptions import options

##log is a globle variable
# from .lib.common import log
from .pyLayout import Layout

version = "V0.61 20240308"
log.info("pyLayout Version: %s"%version)
log.setLogLevel(logLevel="INFO")
# log.setLogLevel(logLevel="DEBUG")