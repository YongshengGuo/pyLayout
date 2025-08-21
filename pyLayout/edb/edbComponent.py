
#--- coding:utf-8
#--- @Author: Yongsheng.Guo@ansys.com, Henry.he@ansys.com,Yang.zhao@ansys.com
#--- @Time: 2025-05-15

'''
pingroup for edb function
'''
import os,sys,re
from ..common.common import *
from ..common.complexDict import ComplexDict

from .edbDefinition import EdbDefinition,EdbDefinitions
from .edbPin import EdbPin

appPath = os.path.realpath(__file__)
appDir = os.path.split(appPath)[0] 
sys.path.append(appDir)

class EdbComponent(EdbDefinition):
    def __init__(self,pin,edbApp=None):
        super(self.__class__,self).__init__(pin,type="EdbPin",edbApp=edbApp)

    def parse(self,force = False):
        '''
        mapping key must not have same value with maped key.
        '''
        
        if self.parsed and not force:
            return
        maps = self.maps
        maps.update({"Name":{
            "Key":"self",
            "Get":lambda s:s.obj.GetName()
            }})
        
        maps.update({"NetName":{
            "Key":"self",
            "Get":lambda s:s.obj.GetNet().GetName()
            }})

        maps.update({"PlacementLayer":{
            "Key":"self",
            "Get":lambda s:s.obj.GetPlacementLayer()
            }})

        maps.update({"PlacementLayerName":{
            "Key":"self",
            "Get":lambda s:s.obj.GetPlacementLayer().GetName()
            }})

        maps.update({"Pins":{
            "Key":"self",
            "Get":lambda s:[EdbPin(p,self.edbApp) for p in s.obj.LayoutObjs]
            }})

        maps.update({"PinNames":{
            "Key":"self",
            "Get":lambda s:[p.GetName() for p in s.obj.LayoutObjs]
            }})

        maps.update({"PartName":{
            "Key":"self",
            "Get":lambda s:s.obj.GetComponentDef().GetName()
            }})

        maps.update({"PartType":{
            "Key":"self",
            "Get":lambda s:s.obj.GetComponentType().ToString()
            }})


# Other 0 Other component type.  
# Resistor 1 Resistor type.  
# Inductor 2 Inductor type.  
# Capacitor 3 Capacitor type.  
# IC 4 IC type.  
# IO 5 IO type.  

        # #---function
        # maps.update({"Ungroup":{
        #     "Key":"self",
        #     "Get":lambda s:s.obj.Ungroup
        #     }})

        # maps.update({"Delete":{
        #     "Key":"self",
        #     "Get":lambda s:s.obj.Delete
        #     }})

        # maps.update({"IsNull":{
        #     "Key":"self",
        #     "Get":lambda s:s.obj.IsNull
        #     }})

        # maps.update({"FindByName":{
        #     "Key":"self",
        #     "Get":lambda s:s.obj.FindByName
        #     }})


        self._info.update("self", self)
        self._info.setMaps(maps)
#         self.maps = maps
        self.parsed = True
    
    


class EdbComponents(EdbDefinitions):

    def __init__(self,edbApp=None):
        '''
        from ansys.aedt.core import Edb
        edbApp = Edb(edbpath=".aedb")
        '''
        super(EdbComponents,self).__init__(edbApp,type="EdbComponent",definitionCalss=EdbComponent)
        

    
    @property
    def DefinitionDict(self):
        if self._definitionDict == None:
            component = [g for g in list(self.edbApp.layout.Groups) if g.ToString() == "Ansys.Ansoft.Edb.Cell.Hierarchy.Component"]
            self._definitionDict  = ComplexDict(dict([(g.GetName(),self.definitionCalss(g,self.edbApp)) for g in component]))
        return self._definitionDict