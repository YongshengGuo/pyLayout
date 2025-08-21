
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

appPath = os.path.realpath(__file__)
appDir = os.path.split(appPath)[0] 
sys.path.append(appDir)

class EdbPin(EdbDefinition):
    def __init__(self,pin,edbApp=None):
        super(__class__,self).__init__(pin,type="EdbPin",edbApp=edbApp)

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

        maps.update({"Group":{
            "Key":"self",
            "Get":lambda s:s.obj.GetGroup()
            }})


        maps.update({"GroupName":{
            "Key":"self",
            "Get":lambda s:s.obj.GetGroup().GetName()
            }})

        maps.update({"PinGroups":{
            "Key":"self",
            "Get":lambda s:s.obj.GetPinGroups()
            }})


        maps.update({"PinGroups":{
            "Key":"self",
            "Get":lambda s:[g.GetName() for g in s.obj.GetPinGroups()]
            }})

        maps.update({"Component":{
            "Key":"self",
            "Get":lambda s:s.obj.GetComponent()
            }})


        maps.update({"ComponentName":{
            "Key":"self",
            "Get":lambda s:s.obj.GetComponent().GetName()
            }})


        # #---function
        # maps.update({"IsInPinGroup":{
        #     "Key":"self",
        #     "Get":lambda s:s.obj.IsInPinGroup
        #     }})

        # maps.update({"IsNull":{
        #     "Key":"self",
        #     "Get":lambda s:s.obj.IsNull
        #     }})


        self._info.update("self", self)
        self._info.setMaps(maps)
#         self.maps = maps
        self.parsed = True
    
    


# class EdbPins(EdbDefinitions):

#     def __init__(self,edbApp=None):
#         '''
#         from ansys.aedt.core import Edb
#         edbApp = Edb(edbpath=".aedb")
#         '''
#         super(EdbPinGroups,self).__init__(edbApp,type="EdbPin",definitionCalss=EdbPin)
        

    
#     @property
#     def DefinitionDict(self):
#         if self._definitionDict == None:
#             pingroups = list(self.layout.PinGroups)
#             self._definitionDict  = ComplexDict(dict([(g.GetName(),self.definitionCalss(g,self.edbApp)) for g in pingroups]))
#         return self._definitionDict