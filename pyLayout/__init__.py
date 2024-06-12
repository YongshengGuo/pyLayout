
from .lib.desktop import initializeDesktop,releaseDesktop
from .lib.Primitives.component import Components
from .lib.Primitives.pin import Pins
from .lib.net import Nets
from .lib.layer import Layers
from .lib.library.material import Materials
from .lib.variable import Variables
from .lib.setup import Setups
from .lib.post.solution import Solutions
from .lib.Primitives.port import Ports
from .lib.Primitives.line import Lines
from .lib.Primitives.via import Vias
from .lib.library.padStack import PadStacks
from .lib.common.complexDict import ComplexDict
from .lib.common.arrayStruct import ArrayStruct
from .lib.common.common import *
from .lib.library.componentLib import ComponentDef
from .lib.layoutOptions import options

from .lib.Model3D.HFSS import HFSS

##log is a globle variable
from .lib.common.common import log

from .pyLayout import Layout

# version = "V0.62 20240314"
version = "V0.80 20240511"
log.info("pyLayout Version: %s"%version)
log.setLogLevel(logLevel="INFO")
# log.setLogLevel(logLevel="DEBUG")