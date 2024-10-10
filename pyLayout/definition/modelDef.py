#--- coding=utf-8
#--- @Author: Yongsheng.Guo@ansys.com, Henry.he@ansys.com,Yang.zhao@ansys.com
#--- @Time: 20230828


'''
used to get padstak information

'''
import os
import re

from ..common import hfss3DLParameters
from ..common.arrayStruct import ArrayStruct
from ..common.complexDict import ComplexDict
from ..common.unit import Unit
from ..common.common import log,tuple2list
from .definition import Definitions,Definition

class ModelDef(Definition):
    '''

    Args:
    '''
    
    def __init__(self, name = None,array = None,layout = None):
        super(self.__class__,self).__init__(name,type="Model",layout=layout)
    


class ModelDefs(Definitions):
    

    def __init__(self,layout=None):
        super(self.__class__,self).__init__(layout, type="Model",definitionCalss=ModelDef)

        

    def addSnpModel(self,path,name=None):
#         try:
#             portCount = float(re.sub(r"[A-Za-z]","",path.split(".")[-1]))
#         except:
#             log.exception(r"not a vaild snp file: %s"%path)
            
        if not name:
            name = os.path.split(path)[-1] 
        name = re.sub("[\.\s#]","_",name)
        
        oDefinitionManager = self.layout.oProject.GetDefinitionManager()
        oModelManager = oDefinitionManager.GetManager("Model")
        
        if name in self:
            oModelManager.EditWithComps (["NAME:%s"%name,"Name:=", name,"ModelType:=", "nport",
                               "filename:=", path,"numberofports:=", ])
            self[name].refresh()
            return self[name]
        else:
            oModelManager.Add(["NAME:%s"%name,"Name:=", name,"ModelType:=", "nport",
                               "filename:=", path,"numberofports:=", ])
            
            self.push(name)
            return self[name]
        
    def addSpiceModel(self,path,name=None):
        
        if not name:
            name = os.path.split(path)[-1] 
        name = re.sub("[\.\s#]","_",name)
        
        oDefinitionManager = self.layout.oProject.GetDefinitionManager()
        oModelManager = oDefinitionManager.GetManager("Model")
        
        if name in self:
            oModelManager.EditWithComps(["NAME:%s"%name,"Name:=", name,"ModelType:=", "dcirspice",
                               "filename:=", path,"modelname:=", name]) 
            
            self[name].refresh()
            return self[name]
        else:
            oModelManager.Add(["NAME:%s"%name,"Name:=", name,"ModelType:=", "dcirspice",
                               "filename:=", path,"modelname:=", name]) 
            
            self.push(name)
            return self[name]
