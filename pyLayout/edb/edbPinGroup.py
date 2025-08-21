
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

class EdbPinGroup(EdbDefinition):
    def __init__(self,pinGroup,edbApp=None):
        super(__class__,self).__init__(pinGroup,"EdbPinGroup",edbApp)


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

        maps.update({"PinGroupTerminal":{
            "Key":"self",
            "Get":lambda s:s.obj.GetPinGroupTerminal().GetName()
            }})

        maps.update({"Pins":{
            "Key":"self",
            "Get":lambda s:[EdbPin(p,self.edbApp) for p in  s.obj.GetPins()]
            }})

        maps.update({"PinNames":{
            "Key":"self",
            "Get":lambda s:["%s-%s"%(p.GetComponent().GetName(),p.GetName()) for p in  s.obj.GetPins()]
            }})

        # #---function

        # maps.update({"IsNull":{
        #     "Key":"self",
        #     "Get":lambda s:s.obj.IsNull()
        #     }})

        self._info.update("self", self)
        self._info.setMaps(maps)
#         self.maps = maps
        self.parsed = True
    


class EdbPinGroups(EdbDefinitions):

    def __init__(self,edbApp=None):
        '''
        from ansys.aedt.core import Edb
        edbApp = Edb(edbpath=".aedb")
        '''
        super(__class__,self).__init__(edbApp,type="EdbPinGroup",definitionCalss=EdbPinGroup)
        

    
    @property
    def DefinitionDict(self):
        if self._definitionDict == None:
            pingroups = list(self.edbApp.layout.PinGroups)
            self._definitionDict  = ComplexDict(dict([(g.GetName(),self.definitionCalss(g,self.edbApp)) for g in pingroups]))
        return self._definitionDict