
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

class EdbLayer(EdbDefinition):
    def __init__(self,layer,edbApp=None):
        super(self.__class__,self).__init__(layer,type="EdbLayer",edbApp=edbApp)

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
        
        maps.update({"LayerId":{
            "Key":"self",
            "Get":lambda s:s.obj.GetLayerId()
            }})

        maps.update({"Color":{
            "Key":"self",
            "Get":lambda s:s.obj.GetColor()
            }})

        maps.update({"LayerType":{
            "Key":"self",
            "Get":lambda s:s.obj.GetLayerType().ToString()
            }})


        maps.update({"Locked":{
            "Key":"self",
            "Get":lambda s:s.obj.GetLocked()
            }})

        maps.update({"LowerElevation":{
            "Key":"self",
            "Get":lambda s:s.obj.GetLowerElevation()
            }})

        maps.update({"Material":{
            "Key":"self",
            "Get":lambda s:s.obj.GetMaterial()
            }})
        maps.update({"Thickness":{
            "Key":"self",
            "Get":lambda s:s.obj.GetThicknessValue()
            }})

        maps.update({"UpperElevation":{
            "Key":"self",
            "Get":lambda s:s.obj.GetUpperElevation()
            }})

        self._info.update("self", self)
        self._info.setMaps(maps)
#         self.maps = maps
        self.parsed = True
    


class EdbLayers(EdbDefinitions):

    def __init__(self,edbApp=None):
        '''
        from ansys.aedt.core import Edb
        edbApp = Edb(edbpath=".aedb")
        '''
        super(self.__class__,self).__init__(edbApp,type="EdbLayer",definitionCalss=EdbLayer)
        

    
    @property
    def DefinitionDict(self):
        if self._definitionDict == None:
            layers = self.edbApp.layout.GetLayerCollection().Layers(self.edbApp.Edb.Cell.LayerTypeSet.AllLayerSet)
            self._definitionDict  = ComplexDict(dict([(l.GetName(),self.definitionCalss(l,self.edbApp)) for l in layers]))
        return self._definitionDict