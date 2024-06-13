
from .desktop import initializeDesktop,releaseDesktop
from .Primitives.component import Components
from .Primitives.pin import Pins
from .definition.net import Nets
from .definition.layer import Layers
from .definition.material import Materials
from .definition.variable import Variables
from .definition.setup import Setups
from .post.solution import Solutions
from .Primitives.port import Ports
from .Primitives.line import Lines
from .Primitives.via import Vias
from .Primitives.primitive import Objects3DL
from .definition.padStack import PadStacks
from .common.complexDict import ComplexDict
from .common.arrayStruct import ArrayStruct
from .common.common import *
from .definition.componentLib import ComponentDef
from .layoutOptions import options

from .Model3D.HFSS import HFSS

##log is a globle variable
from .common.common import log

from .pyLayout import Layout

# version = "V0.62 20240314"
version = "V0.9.0 20240613"
log.info("pyLayout Version: %s"%version)
log.setLogLevel(logLevel="INFO")
# log.setLogLevel(logLevel="DEBUG")