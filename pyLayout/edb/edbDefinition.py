#--- coding=utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 20250516

'''_summary_
Note: "This file defines a parent class, which cannot be used independently and must be implemented through a subclass." 
'''

import re

from ..common.complexDict import ComplexDict
from ..common.unit import Unit
from ..common.common import log,Iterable


class EdbDefinition(object):
    '''
    '''
    
    
    
    def __init__(self,obj,type,edbApp=None):
        '''Initialize Pin object
        Args:
            name (str): Via name in edbApp
            edbApp (PyedbApp): PyedbApp object, optional
        '''

        self.edbApp = edbApp
        self.obj = obj
        self.type = type
        
        self._info = ComplexDict()
        self.maps = {}
        self.parsed = False

    def __getitem__(self, key):
        """
        key: str
        """
        self.parse()
        
        #for multi-level key
        keyList = re.split(r"[\\/]", key,maxsplit = 1)
        keyList = list(filter(lambda k:k.strip(),keyList)) #filter empty key
        if len(keyList)>1:
            return self[keyList[0]][keyList[1]]

        if key in self._info:
            return self._info[key] 

        else:
            log.exception("key error for %s: %s"%(self.type,key))       
        

    def __setitem__(self, key,value):
        self.parse()
        
        #for multi-level key
        keyList = re.split(r"[\\/]", key,maxsplit = 1)
        keyList = list(filter(lambda k:k.strip(),keyList)) #filter empty key
        if len(keyList)>1:
            self[keyList[0]][keyList[1]] = value

            
        if key in self._info:
            self._info[key] = value

        else:
            log.exception("key error for %S: %s"%(self.type,key))       
        

    def __getattr__(self,key):

        if key in ["edbApp","obj","_info","parsed","type","maps"]:
            return object.__getattr__(self,key)
        elif key in self.Info:
            return self[key]
        elif key in dir(self.obj):
            return getattr(self.obj,key)
        else:
            log.info("__getattr__ from _dict: %s"%key)
    def __setattr__(self, key, value):
        if key in ["edbApp","obj","_info","parsed","type","maps"]:
            object.__setattr__(self,key,value)
        elif key in self.Info:
           self[key] = value
        else:
            log.info("__getattr__ from _dict: %s"%key)

    def __contains__(self,key):
        return key in self.Props

    def __repr__(self):
        return "%s Object: %s"%(self.__class__.__name__ ,self.name)
    
    def __dir__(self):
        return list(dir(self.__class__)) + list(self.__dict__.keys()) + list(self.Props)


    @property
    def Props(self):
        propKeys = list(self.Info.Keys)
        propKeys += list(dir(self.obj))
        if self.Info.maps:
            propKeys += self.Info.maps.keys()
    
        return propKeys

    @property
    def Info(self):
        self.parse()
        return self._info
    
        
    def parse(self,force = False):
        '''
        mapping key must not have same value with maped key.
        '''
        
        log.exception("DefinitionDict should be implemented by subclasses." )
        
#         if self.parsed and not force:
#             return
#         self._info.update("self", self)    
#         self._info.update("Name",self.name)
# 
#         self.maps = maps
#         self.parsed = True
    
    
    def update(self):
        self.oManager.Edit(self.Name,self.Array.Datas)
        self.parse()


    
class EdbDefinitions(object):

    def __init__(self,edbApp = None,type=None,definitionCalss = None):
        self.edbApp = edbApp
        self.definitionCalss = definitionCalss
        self.type = type
        self._definitionDict = None
            
    def __getitem__(self, key):
        
        if isinstance(key, int):
            return self.DefinitionDict[key]
        
        if isinstance(key, slice):
            return self.DefinitionDict[key]
        
        if isinstance(key, str):
            if key in self.DefinitionDict:
                return self.DefinitionDict[key]
            else:
                #find by 正则表达式
                lst = [name for name in self.DefinitionDict.Keys if re.match(r"^%s$"%key,name,re.I)]
                if not lst:
                    raise Exception("not found %s: %s"%(self.type,key))
                else:
                    #如果找到多个器件（正则表达式），返回列表
                    return self[lst]

        if isinstance(key, (list,tuple,Iterable)):
            return [self[i] for i in list(key)]
        
        raise Exception("not found %s: %s"%(self.type,key))
        
            
#     def __getattr__(self,key):
#         if key in ['__get__','__set__']:
#             #just for debug run
#             return None
# #         print("%s  __getattribute__ from _info: %s"%str(self.__class__.name,key))
#         try:
#             return super(self.__class__,self).__getattribute__(key)
#         except:
#             log.debug("%s  __getattribute__ from _info: %s"%(self.__class__.__name__,key))
#             return self[key]
            
    def __contains__(self,key):
        return key in self.DefinitionDict
    
    def __len__(self):
        return len(self.DefinitionDict)
    
    def __repr__(self):
        return "%s Definition Objects"%(self.type)
            

    @property
    def DefinitionDict(self):
        if self._definitionDict == None:
            log.exception("DefinitionDict should be implemented by subclasses." )
        return self._definitionDict
    
    @property
    def All(self):
        return self.DefinitionDict.Values
    
    @property
    def Count(self):
        return len(self)
    
    @property
    def Type(self):
        return self.type
    
    @property
    def NameList(self):
        return list(self.DefinitionDict.Keys)
    
    def filter(self, func):
        return dict(filter(func,self.ObjectDict.items()))
    
    def refresh(self):
        self._definitionDict  = None
        
    def push(self,name):
        self.DefinitionDict.update(name,self.definitionCalss(name,edbApp=self.edbApp))
    
    def pop(self,name):
        del self.DefinitionDict[name]
        
        
    def getByName(self,name):
        '''
        Args:
            name (str): component name in edbApp, ingor case
        Returns:
            (Component): Component object of name
             
        Raises:
            name not found on edbApp
        '''
        if name in self.DefinitionDict:
            return self.DefinitionDict[name]
        
        log.info("not found %s: %s"%(self.type,name))
        return None
    
    def getUniqueName(self,prefix=""):
        
        if prefix == None:
            prefix = "%s_"%self.type
            
        for i in range(1,100000):
            name = "%s%s"%(prefix,i)
            names = self.NameList
            if name in names:
                i += 1
            else:
                break
        return name
        