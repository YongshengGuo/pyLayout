#--- coding:utf-8
#--- @Author: Yongsheng.Guo@ansys.com, Henry.he@ansys.com,Yang.zhao@ansys.com
#--- @Time: 2023-04-09
'''
PyLayout对象代表AEDT中的一个Design对象，即一块PCB的对象，可以通过PyLayout对象对PCB上的器件，网络，图形，求解设定，结果数据进行访问。

相比AEDT的底层API,PyLayout提供了更加快捷和符合逻辑的访问方式。
```
PyLayout
|- Layers
|- Components
   |-pins
|- Nets
|- Variables
|- Lines
|- Vias
|- plane
|- log
```
所有的属性支持字典索引

- for Component, the key is refdes, support regular to match mutiple components
```
PyLayout.Components["U1"]  #获取U1器件的component对象
PyLayout.Components["U.*"]  #返回匹配以U开头器件的List
```
- for Nets, the key is netName, support regular to match mutiple nets
```
PyLayout.Nets["DDR3_A1"]  #获取DDR3_A1的Net对象
PyLayout.Nets["DDR3_A.*"]  #返回匹配DDR3_A.*的Net对象List
```
Examples：
    >>> PyLayout["Comp:U1"]  #获取U1器件的component对象
    >>> PyLayout["Net:A0"]  #获取U1器件的component对象
    >>> PyLayout["Pin:U1.A2"]  #获取U1器件的component对象
    >>> PyLayout["LC:0"]  #获取U1器件的component对象

'''

import os,sys,re
import shutil
import time
import math
from collections import Counter

from .desktop import initializeDesktop,releaseDesktop

#---Primitive
from .primitive.component import Components
from .primitive.pin import Pins
from .primitive.port import Ports
from .primitive.line import Lines
from .primitive.via import Vias
from .primitive.source import Sources

#---library
from .definition.padStack import PadStacks
from .definition.componentLib import ComponentDefs
from .definition.modelDef import ModelDefs
from .definition.material import Materials
#---natural
from .definition.layer import Layers
from .definition.setup import Setups
from .definition.net import Nets
from .definition.variable import Variables
from .definition.pinGroup import PinGroups

from .postData.solution import Solutions

from .common.complexDict import ComplexDict
from .common.arrayStruct import ArrayStruct

from .options import options

from .primitive.primitive import Primitives,Objects3DL
from .primitive.geometry import Polygen,Point

#log is a globle variable
from .common import common
from .common.common import *
# from .common.common import log,isIronpython
from .common.unit import Unit

from .common.common import DisableAutoSave,ProcessTime
from .common.licenseChecker import LicenseChecker
from .common.hfss3DLParameters import analysis_cfg

class Layout(object):
    '''
    classdocs
    '''
    #FindObjects 
    primitiveTypes = ['pin', 'via', 'rect','circle', 'arc', 'line', 'poly','plg', 'circle void','line void', 'rect void', 
           'poly void', 'plg void', 'text', 'cell','Measurement', 'Port', 'component', 'CS', 'S3D', 'ViaGroup']
    definitionTypes = ["Layer","Material","Setup","PadStack","ComponentDef","Variable","Net"]
    
    def __init__(self, version=None, installDir=None,nonGraphical=False,newDesktop=False,usePyAedt=False,oDesktop = None):
        '''
        初始化PyLayout对象环境
        
        - version和installDir都为None，会尝试启动最新版本的AEDT
        - version和installDir都指定时， version优先级 高于 installDir
        Examples:
            >>> PyLayout()
            open least version AEDT, return PyLayout

            >>> PyLayout(version = "2013.1")
            open AEDT 2013R1, return PyLayout
        
        '''
        self.maps = {
            "InstallPath":"InstallDir",
            "Path":"ProjectPath",
            "Name":"DesignName",
            "Ver":"Version",
            "Comps":"Components"
            }
        
        self._info = ComplexDict({
            "Version":None,
            "InstallDir":None,
            },maps=self.maps)
        
        self._info.update("Version", version)
        self._info.update("InstallDir", installDir)
        self._info.update("NonGraphical", nonGraphical)
        self._info.update("newDesktop", newDesktop)
        self._info.update("UsePyAedt", usePyAedt)
        self._info.update("PyAedtApp", None)
        self._info.update("Log", log)
        self._info.update("options",options)
#         self._info.update("Maps", self.maps)
        
        if not isIronpython:
            log.info("In cpython environment, pyaedt shold be installed, install command: pip install pyaedt")
#             self._info.update("UsePyAedt", True)
        
        #----- 3D Layout object
        self._oDesktop = oDesktop
        self._oProject = None
        self._oDesign = None
        self._oEditor = None
        

        
        
    def __del__(self):
#         self._oDesktop = None
#         self._info = None
#         self._components = None
#         self._setups = None
#         self._nets = None
#         self._layers = None
#         self._variables = None
#         self._ports = None
#         self._solutions = None
#         self._stackup = None
#         self._log = None
 
        releaseDesktop()
        
    def __getitem__(self, key):
        
        if not isinstance(key, str):
            log.exception("key for layout must be str: %s"%key)

        if key in self._info:
            return self._info[key]
        
        if not self._oDesign:
            log.exception("layout should be intial use method: 'Layout.initDesign(projectName = None,designName = None)'")
            return
        
        log.debug("try to get element type: %s"%key)
        
        for ele in self.primitiveTypes:
            collection = ele+"s"
            if key in self._info[collection]:
                log.debug("Try to return %s for key: %s"%(collection,key))
                return self._info[collection][key]
            
        log.exception("not found element on layout: %s"%key)
        return None
        
    def __setitem__(self, key,value):
        self._info[key] = value
        
        
    def __getattr__(self,key):
#         当调用一个不存在的属性时，就会触发__getattr__()
#         __getattribute__() 方法是无条件触发
        if key in ['__get__','__set__']:
            #just for debug run
            return None

        try:
            return super(self.__class__,self).__getattribute__(key)
        except:
            log.debug("Layout __getattribute__ from info: %s"%str(key))
            return self[key]
        
    def __setattr__(self, key, value):
        if key in ["_oDesktop","_oProject","_oDesign","_oEditor","_info","maps"]:
            object.__setattr__(self,key,value)
        else:
            self[key] = value
        
    def __dir__(self):
#         return object.__dir__(self)  + self.Props
        return dir(self.__class__) + list(self.__dict__.keys()) + self.Props
    
    def __repr__(self):
        
        temp = ""
        if "ProjectName" in self._info:
            temp += "Project: %s"%self._info["ProjectName" ]
        else:
            temp += "Project: %s"%"None"
            
        if "DesignName" in self._info:
            temp += "Design: %s"%self._info["DesignName" ]
        else:
            temp += "Design: %s"%"None"
        
        return "%s Object: %s"%(self.__class__.__name__,temp)
    
    @property
    def Info(self):
        return self._info
    
    @property
    def Props(self):
        propKeys = list(self.Info.Keys)
        if self.maps:
            propKeys += list(self.maps.keys())
             
        return propKeys
        
    def __initByPyaedt(self):    
        try:
            from pyaedt import launch_desktop
            log.info("try to initial oDesktop using pyaedt Lib... ")
            self.PyAedtApp = launch_desktop(version = self.version,non_graphical=self.NonGraphical,new_desktop = self.newDesktop,close_on_exit=False)
            self.UsePyAedt = True
            self._oDesktop = self.PyAedtApp.odesktop
            # sys.modules["__main__"].oDesktop = self._oDesktop
            log.logger = self.PyAedtApp.logger
#             self._info.update("Log", self.PyAedtApp._logger)
#             common.log = self.PyAedtApp._logger
        except:
            log.warning("pyaedt lib should be installed, install command: pip install pyaedt")
#             log.info("if you don't want use pyaedt to intial pylayout, please set layout.usePyAedt = False before get oDesktop")
            self.UsePyAedt = False
            log.warning("pyaedt app intial error.")
    
    def _AddKeepGUILicenseProject(self,oDesktop):
        
        if not self.options["AEDT_KeepGUILicense"]:
            return
            
        projectList = oDesktop.GetProjectList()
        #for COM Compatibility, yongsheng guo #20240422
        if "ComObject" in str(type(projectList)):
            projectList = [projectList[i] for i in range(projectList.count)]
        
        if len(projectList)>0:
            return
        
        if "AEDT_KeepGUILicense" in projectList:
            return
        
        oProject = oDesktop.NewProject()
        oProject.Rename("AEDT_KeepGUILicense.aedt", True)
        oProject.InsertDesign("HFSS", "UseForKeepGUILicense", "", "")
        
    def _DelKeepGUILicenseProject(self,oDesktop):
        
        
        if not self.options["AEDT_KeepGUILicense"]:
            return
            
        projectList = oDesktop.GetProjectList()
        #for COM Compatibility, yongsheng guo #20240422
        if "ComObject" in str(type(projectList)):
            projectList = [projectList[i] for i in range(projectList.count)]
        
        if not "AEDT_KeepGUILicense" in projectList:
            return
        
        oDesktop.DeleteProject("AEDT_KeepGUILicense")

    def waitForlicense(self,featureList,timeout = 100*60):
        if self.options["AEDT_LicenseServer"]:
            #set license server
            os.environ["ANSYSLMD_LICENSE_FILE"] = self.options["AEDT_LicenseServer"]

        if self.options["AEDT_LicenseServer"] and self.options["AEDT_WaitForLicense"]:
            licchk = LicenseChecker(os.environ["ANSYSLMD_LICENSE_FILE"])
            licchk.waitForlicense(featureList,timeout)

    @property
    def oDesktop(self):
        
        if self._oDesktop:
            return self._oDesktop
        
        #try to initial use pyaedt
        log.debug("Try to load pyaedt.")
        
        #try to get global oDesktop, for run script from aedt 
        Module = sys.modules['__main__']
        if hasattr(Module, "oDesktop"):
            oDesktop = getattr(Module, "oDesktop")
            if oDesktop:
                self._oDesktop = oDesktop
                self.UsePyAedt = bool(self.PyAedtApp) #may be lanuched from aedt internal
                if "ANSYSEM_ROOT" not in os.environ:
                    os.environ["ANSYSEM_ROOT"] = self._oDesktop.GetExeDir()
                return oDesktop
        
        if self.NonGraphical:
            log.info("Will be intial oDesktop in nonGraphical mode.")
        
        
        self.waitForlicense([{"module":"HFSSGUI"}])
        #try to intial by pyaedt
#         self.UsePyAedt = False
        if self.UsePyAedt:
            self.__initByPyaedt()

        #try to intial by internal method
        if self._oDesktop == None: 
            log.info("try to initial oDesktop using internal method... ")
            self._oDesktop = initializeDesktop(self.version,self.installDir,nonGraphical=self.NonGraphical,newDesktop=self.newDesktop)
            self.installDir = self._oDesktop.GetExeDir()
            self.UsePyAedt = False
            
        #intial error
        if self._oDesktop == None: 
            log.exception("Intial oDesktop error... ")
        
        print("Aedt Version: %s"%self._oDesktop.GetVersion())
        if "ANSYSEM_ROOT" not in os.environ:
            os.environ["ANSYSEM_ROOT"] = self._oDesktop.GetExeDir()

#         self._AddKeepGUILicenseProject(self._oDesktop)
        
        #do not set oDesktop to main modules, AEDT has a chance of crashing under certain circumstances.  
        # sys.modules["__main__"].oDesktop = self._oDesktop
        return self._oDesktop
    
     
    def initProject(self,projectName = None):
        #layout properties initial
        #----- 3D Layout object
#         self._oDesktop = None
        self._oProject = None
#         self._oDesign = None
#         self._oEditor = None
        oDesktop = self.oDesktop
         
#         log.debug("AEDT:"+self.Version)
        projectList = oDesktop.GetProjectList()
        #for COM Compatibility, yongsheng guo #20240422
        if "ComObject" in str(type(projectList)):
            projectList = [projectList[i] for i in range(projectList.count)]
             
        if len(projectList)<1:
#             log.error("Must have one project opened in aedt.")
#             exit()
#             log.error("Must have one project opened in aedt.")
            log.warning("not found opened projects, insert new one.")
            oProject = oDesktop.NewProject()
            oProject.InsertDesign("HFSS 3D Layout Design", "Layout1", "", "")
            self._oProject = oProject
         
        else:
         
            if projectName:
    #             messageBox("projectName&designName")
                if projectName not in projectList:
                    log.error("project not in aedt:%s"%projectName)
                    raise Exception("project not in aedt: %s"%projectName)
                self._oProject = oDesktop.SetActiveProject(projectName)
     
            else:
                self._oProject = oDesktop.GetActiveProject()
                 
                if not self._oProject:
                    self._oProject = oDesktop.GetProjects()[0]
                    oDesktop.SetActiveProject(self._oProject.GetName())
                 
        if not self._oProject:
            log.error("Must have one project opened in aedt.")
            raise Exception("Must have one project opened in aedt.")
         
        self._info.update("oProject",self._oProject)

        self._info.update("ProjectName", self._oProject.GetName())
        self._info.update("projectDir", self._oProject.GetPath())
         
        self._info.update("ProjectPath", os.path.join(self._info.projectDir,self._info.projectName+".aedt"))
        self._info.update("ResultsPath", os.path.join(self._info.projectDir,self._info.projectName+".aedtresults"))
        self._info.update("EdbPath", os.path.join(self._info.projectDir,self._info.projectName+".aedb"))
 
        self._info.update("Version", self.oDesktop.GetVersion())
        self._info.update("InstallDir", self.oDesktop.GetExeDir())
        self._info.update("InstallPath", self.oDesktop.GetExeDir())
    
    
    def initDesign(self,projectName = None,designName = None, initLayout = True):
        '''Try to intial project properties.
        
        AEDT must have on project and design opened.
        
        - if projectName give, will be initialize the given project.
        - if designName give and the projectName must give, will be initialize the given project and design
        - if projectName and designName not give, it will try to initialize the firt project or design in AEDT
        
        Args:
            projectName (str): projectName to be actived, default is first project in aedt
            designName (str): designName to be actived, default is first design in project
        
        Exceptions:
            Not have project or design in AEDT
        
        '''
        #layout properties initial
        #----- 3D Layout object
#         self._oDesktop = None
        self._oProject = None
        self._oDesign = None
        self._oEditor = None
        self.initProject(projectName)
 
        designList = self.getDesignNames()
        if len(designList)<1:
            log.error("Must have one design opened in project.")
            self._info.update("oDesign",None)
            self._info.update("oEditor",None)
            self._info.update("DesignName", "")
            
        else:
        
            if designName:
                if designName not in designList:
                    log.error("design not in project.%s"%designName)
                    raise Exception("design not in project.%s"%designName)
                self._oDesign = self._oProject.SetActiveDesign(designName)
            else:
                
                #update for 2025.1
                try:
                    self._oDesign = self._oProject.GetActiveDesign()
                except:
                    log.info("GetActiveDesign error.")
#                     log.info("try to get the first design")
#                     self._oDesign = self._oProject.SetActiveDesign(designList[0])
                
                #for 2024.2 GetActiveDesign() may return None
                if not self._oDesign:
                    log.info("try to get the first design")
                    self._oDesign = self._oProject.SetActiveDesign(designList[0])
                    
                    
                #make sure the design is 3DL
                designtype = self._oDesign.GetDesignType()
                if designtype != 'HFSS 3D Layout Design':
                    log.exception("design type error, not 3D layout design.")  #exception if not 3DL design
                    self._info.update("oDesign",None)
                    self._info.update("oEditor",None)
                    self._info.update("DesignName", "")
                    self._info.update("designtype", designtype)
                else:
                    self._info.update("oDesign",self._oDesign)
                    self._info.update("oEditor",self._oDesign.SetActiveEditor("Layout"))
                    self._info.update("DesignName", self.getDesignName(self._oDesign))
                    self._info.update("designtype", designtype)
                    
                #intial log with design
                path = os.path.join(self._info.projectDir,"%s_%s.log"%(self._info.projectName,self._info.designName))
                if self.UsePyAedt or "AedtLogger" in str(type(log.logger)):
                    import logging
                    
                    try:
                        logger1 = log.logger.logger
                    except:
                        logger1 = log.logger
                    
                    fileHandler = logger1.handlers[0]
                    fileHandler2 = logging.FileHandler(path)
                    fileHandler.stream = fileHandler2.stream
                    fileHandler.baseFilename = path
                    logger1.removeHandler(fileHandler)
                    logger1.addHandler(fileHandler)
                    del fileHandler2
                    del fileHandler
                    
                else:
                    log.setPath(path)
                    log.info("Simulation log recorded in: %s"%path)
                
                log.info("init design: %s : %s"%(self.projectName,self.designName))
                    

                #intial layout elements
                self.enableICMode(False)
                
                if initLayout and self._info.oEditor:
                    self.initObjects()

    def initObjects(self):
        
        info = self._info
        
        #for Primitives
        classDict = ComplexDict(dict([(name.lower(),obj) for name,obj in globals().items() if isinstance(obj,type)]))
        
        for obj in self.primitiveTypes:
            key = obj.lower()+"s"
            if key.replace(" ","") in classDict:
                info.update(key,classDict[key](layout = self))
            else:
                info.update(key,Primitives(layout = self,type=obj))
            
            if " " in key:
                self.maps.update({key.replace(" ",""):key})

        #for collections
        info.update("Objects", Objects3DL(layout = self,types=".*"))
        info.update("Traces", Objects3DL(layout = self,types=['arc', 'line']))
        info.update("Shapes", Objects3DL(layout = self,types=[ 'rect','poly','plg','circle']))
        info.update("Voids", Objects3DL(layout = self,types=['circle void', 'line void', 'rect void', 'poly void', 'plg void']))
        
        
        info.update("Layers", Layers(layout = self))
        info.update("Materials", Materials(layout = self))
        info.update("Variables", Variables(layout = self))
        info.update("Setups", Setups(layout = self))
        info.update("Nets", Nets(layout = self))
        info.update("Solutions", Solutions(layout = self))
        info.update("PadStacks", PadStacks(layout = self))
        info.update("ComponentDefs", ComponentDefs(layout = self))
        info.update("ModelDefs", ModelDefs(layout = self))
        info.update("PinGroups", PinGroups(layout = self))
        info.update("Sources", Sources(layout = self))
        
#         info.update("Primitives",Primitives(layout = self))
        info.update("unit",self.getUnit2())  #some bug exit in oEditor.GetActiveUnits()
        info.update("Version",self.oDesktop.GetVersion())
        info.update("layout",self)
        
        #intial geometry definition
#         Polygen.layout = self
#         Point.layout = self
        
        #When multiple layouts are open, there is a risk associated with the use of this statement here.
        sys.modules["__main__"].layout = self
        
    def getDesignName(self,oDesign):
        return oDesign.GetName().split(';')[-1]
    
    def getDesignNames(self):
        return [name.split(';')[-1] for name in self._oProject.GetTopDesignList()]  
                
    #--- design
        
    def clip(self,newDesignName, includeNetList, clipNetList, expansion = "2mm",InPlace=False):

        cutList = []
        for net in includeNetList:
            cutList.append("net:=")
            cutList.append([net,False])

        for net in clipNetList:
            cutList.append("net:=")
            cutList.append([net,True])
        
        #delete nets that not used
        kNets = includeNetList + clipNetList
        delNet = list(filter(lambda n:n not in kNets,self.Nets.NameList))
        log.debug("delete nets not used in cutout: %s"%",".join(delNet))
        self.Nets.deleteNets(delNet)
        
        log.info("Cut out layout by net: %s"%",".join(kNets))
        log.info("Cutout expansion: %s"%expansion)
        self.oEditor.CutOutSubDesign(
            [
                "NAME:Params",
                "Name:="        , newDesignName,
                "InPlace:="        , InPlace,
                "AutoGenExtent:="    , True,
                "Type:="        , "Conformal",
                "Expansion:="        , expansion,
                "RoundCorners:="    , True,
                "Increments:="        , 1,
                "UseSelection:="    , False,
                "ExtentSel:="        , [],
                [
                    "NAME:Nets",
#                     "net:="            , ["M_MA_4_",False],
#                     "net:="            , ["GND",True]
                ] + cutList
            ])
        
        
    def _merge(self,layout2,solderOnComponents = None,align = None,solderBallSize = "14mil,14mil", stackupReversed = False, prefix = ""):
        '''
            合并另外一个layout对象，叠层在Z轴叠加
        connect = [(pin1,pin2),(pin_1,pin_2)] #用于对齐
        solderOnComponents = {U1:(14mil,14mil),U2:None} #确定哪些位置长solderball
        次方法为完全实现，建议不要使用。
        '''
        log.info("Merge layers from {layout2} to {layout1}".format(layout1=self.designName,layout2=layout2.designName))
        layers2 = layout2.Layers
#         solderHeight = "14mil"
#         solderDiameter  = "14mil"
        solderHeight,solderDiameter = solderBallSize.split(",",1)
        
        #add solder ball
        self.Layers.S1.addLayerAbove(name = prefix + "SolderBall",typ = "dielectric", copy = None)
        self.Layers.S1.Material = "air"
        self.Layers.S1.Thickness = solderHeight
        
        #layers from layout2
        layers2 = layers2[::-1] if stackupReversed else layers2
        copyLayersDsp = []
        for layer2 in layers2:
            copyLayersDsp.append("%s:%s"%(layer2.Name,prefix + layer2.Name))
        #add solderball layers
        copyLayersDsp.append("0:%s"%(prefix + "SolderBall"))
        #add self layers
        for layer in self.Layers:
            copyLayersDsp.append("0:%s"%(layer.Name))
            
        
        #add from bottom layer
        for layer2 in layers2[::-1]:
            name2 = prefix + layer2.Name
            self.Layers.S1.addLayerAbove(name = name2, copy = layer2)
        
        #copy objs
        allObjs = layout2.oEditor.FindObjects('Type','*')
        layout2.oEditor.Copy(allObjs)
        self.oEditor.Paste(
            [
                "NAME:offset",
                "xy:="            , [0,0]
            ], 
            [
                "NAME:merge",
                "StackupLayers:="    , copyLayersDsp,
                "DrawLayers:="        , ["SIwave Regions:SIwave Regions","Measures:Measures","Outline:Outline","Rats:Rats","Errors:Errors","Symbols:Symbols","Postprocessing:Postprocessing"]
            ])
        log.info("Finished copy {0} object to {1}".format(len(allObjs),self.designName))

    def autoHFSSRegions(self):
        self.oEditor.GenerateSuggestedHFSSRegions()

    def enableICMode(self,flag=True):
        try:
            if flag:
                self.oDesign.DesignOptions(
                    [
                        "NAME:options",
                        "ModeOption:="        , "IC mode"
                    ], 0)
            else:
                self.oDesign.DesignOptions(
                    [
                        "NAME:options",
                        "ModeOption:="        , "General mode"
                    ], 0)
        except:
            log.error("enableICMode error: %s"%str(flag))

    def enableAutosave(self,flag=True):
        Enabled = self.oDesktop.GetAutoSaveEnabled()
        
        if bool(flag) == Enabled:
            return Enabled
        
        if flag:
            log.info("Enable autosave.")
            self.oDesktop.EnableAutoSave(True)
        else:
            log.info("Disenable autosave.")
            self.oDesktop.EnableAutoSave(False)
        
        return Enabled

    #--- objects
    def getPrimitiveObjects(self,types):
        '''
        type is list or regex
        '''
        return Objects3DL(layout = self,types=types)
    

    def getObjects(self,type="*"):
        '''
        "Type" to search by object type.
        Valid <value> strings for this type include: 'pin', 'via', 'rect', 'arc', 'line', 'poly', 'plg', 'circle void', 
        'line void', 'rect void', 'poly void', 'plg void', 'text', 'cell', 'Measurement', 'Port', 'Port Instance', 
        'Port Instance Port', 'Edge Port', 'component', 'CS', 'S3D', 'ViaGroup'
        '''
        if type.lower() == "all":
            type = "*"
            
        return self.layout.oEditor.FindObjects('Type',type)
    
    def getObjectsbyNet(self,net,type="*"):
        
        if type.lower() == "all":
            type = "*"
            
        return self.oEditor.FilterObjectList('Type', type, self.oEditor.FindObjects('Net',net))
        
    def getObjectsbyLayer(self,layer,type="*"):
        
        if type.lower() == "all":
            type = "*"
        return self.oEditor.FilterObjectList('Type', type, self.oEditor.FindObjects('Layer',layer))
    
    def getObjectsBySquare(self,center,layer="*",sideLength="1mil"):
        '''
        suggest to use getObjectByPoint
        '''
        return self.getObjectByPoint(center, layer, sideLength)
         
        
    def getObjectByPoint(self,point,layer="*",radius=0):
        
        if len(point)!=2:
            log.exception("center must be list with length 2")
            
        X,Y = [Unit(p).V for p in point]
        
        if radius == 0:
            posObj = self.oEditor.FindObjectsByPoint(self.oEditor.Point().Set(X, Y), layer)
            return list(posObj)
        
        else:
            l = Unit(radius).V
            p0 = self.oEditor.Point().Set(X-l/2, Y-l/2)
            p1 = self.oEditor.Point().Set(X+l/2, Y-l/2)
            p2 = self.oEditor.Point().Set(X+l/2, Y+l/2)
            p3 = self.oEditor.Point().Set(X-l/2, Y+l/2)
            box = self.oEditor.Polygon().AddPoint(p0).AddPoint(p1).AddPoint(p2).AddPoint(p3).SetClosed(True)
            posObj = self.oEditor.FindObjectsByPolygon(box, layer)
            return list(posObj)
        
    def setUnit(self, unit = "um"):
        #return old unit
        return self.oEditor.SetActiveUnits(unit)
    
    
    def getUnit2(self):
        
        unit1 = None
        unit2 = None
        #get via most unit 
        objs = self.oEditor.FindObjects('Type', "via")
        if len(objs)>5:
            lst = [re.sub(r"[\d\.]*","",self.oEditor.GetPropertyValue("BaseElementTab",obj,"HoleDiameter")) for obj in objs[:5]]
            count = Counter(lst)
            most_common = count.most_common(1)
            unit1 = most_common[0][0]
#             return unit
        
        #get line most unit  LineWidth
        objs = self.oEditor.FindObjects('Type', "line")
        if len(objs)>5:
            lst = [re.sub(r"[\d\.]*","",self.oEditor.GetPropertyValue("BaseElementTab",obj,"LineWidth")) for obj in objs[:5]]
            count = Counter(lst)
            most_common = count.most_common(1)
            unit2 = most_common[0][0]
#             return unit
            
        if unit1 and unit1 == unit2:
            return unit1
        
        elif unit2:
            return unit2
        else:
            #have bug in 2024R2
            return self.oEditor.GetActiveUnits()
    
    def getUnit(self):
        #have bug in 2024R2
        return self.oEditor.GetActiveUnits()
    
    
    def select(self,objs):
        '''
        objs: names of  objs
        '''
        if isinstance(objs, str):
            objs = [objs]
            
        self.oEditor.Select(objs)
        
    
    def delete(self,objs):
        '''
        objs: names of delete objs
        '''
        if isinstance(objs, str):
            objs = [objs]
            
        for name in objs:
            try:
                obj = self.Objects[name]
                self[obj.Type+"s"].pop(name)
            except:
                log.warning("%s: delete error from layout."%name)
                
        self.oEditor.Delete(objs)
        self.Objects.refresh()
        self.Traces.refresh()
        self.Shapes.refresh()
        self.Voids.refresh()

        

    
    #---functions
    
    #---Create objects
#     def addCircle(self,layer,location,r,name=None):
#         lay = self.Layers[layer].Name
#         loc = Point(location)
#         ra = str(r)
#         if not name:
#             name = self.Circles.getUniqueName("circle_")
#         log.info("Create Circle: %s"%name)
#         name = self.oEditor.addCircle(
#             [
#                 "NAME:Contents",
#                 "circleGeometry:="    , ["Name:=", name ,"LayerName:=", lay,"lw:=", "0","x:=", loc.x ,"y:=", loc.y ,"r:=",ra]
#             ])
#         
#         self.Circles.push(name)
#         self.Shapes.push(name)
#         
#         return name
    
    
    def addCircle(self,layer,location,r,net=None,name=None):
        lay = self.Layers[layer].Name
        loc = Point(location)
        ra = str(r)
        if not name:
            name = self.Circles.getUniqueName("circle_")
        log.info("Create Circle: %s"%(name))
#         log.info("Create Circle: %s  location:%s r: %s"%(name,str(location),str(r)))
        name = self.oEditor.CreateCircle(
            [
                "NAME:Contents",
                "circleGeometry:="    , ["Name:=", name ,"LayerName:=", lay,"lw:=", "0","x:=",0 ,"y:=", 0 ,"r:=", "1um"]
            ])
        
        self.Circles.push(name)
        obj = self.Circles[name]
        obj.Center = location #"%s,%s"%(loc.x,loc.y)
        obj.Radius = ra
        if net:
            obj.Net = net
        return obj
    
    def addLine(self,layerName,points,width="0.1mm",net=None,name=None):
        '''
        points:list,tuple, Point
        '''
        if not points or len(points)<2:
            log.exception("Points of line must have 2 points")
            
#         if not name:
#             name = self.getUniqueName()
            
        pts = [Point(p) for p in points]
        pUnit = self.layout.unit
        
        xyListTemp = []
        for i in range(len(pts)):
            xyListTemp.append("x:=")
            xyListTemp.append(0)
            xyListTemp.append("y:=")
            xyListTemp.append(0)
        
        if not name:
            name = self.Circles.getUniqueName("line_")
        log.info("Create Line: %s"%name)
        name = self.layout.oEditor.CreateLine(
            [
                "NAME:Contents",
                "lineGeometry:=", 
                ["Name:=", name, 
                "LayerName:=", self.layout.layers.getRealLayername(layerName),
                "lw:=", width,
                "endstyle:=", 0,
                "StartCap:=", 0,
                "n:=", len(xyListTemp),
                "U:=", pUnit] + xyListTemp
#                 "x:=", 17,"y:=", 28,
#                 "MR:=", "600mm"]
            ])
        
        self.Lines.push(name)
        obj = Lines[name]
        for i in range(len(pts)):
            obj["Pt%s"%i] = pts[i]
        
        if net:
            obj.Net = net
            
        return obj
    
    def addRectangle(self,layerName,ptA,ptB,net=None,name=None):
        if not name:
            name = self.Circles.getUniqueName("rect_")
        log.info("Create Rectangle: %s"%name)
        name = self.layout.oEditor.CreateRectangle(
            [
                "NAME:Contents",
                "rectGeometry:="    , 
                ["Name:=", "rect_0",
                 "LayerName:=", self.layout.Layers[layerName].Name,
                 "lw:=", "0",
                 "Ax:=", "0mm","Ay:=", "0mm",
                 "Bx:=", "0.1mm","By:=", "0.1mm",
                 "cr:=", "0mm","ang:=", "0deg"]
            ])
        
        self.rects.push(name)
        obj = self.Rects[name]
        obj.PtA = ptA 
        obj.PtB = ptB
        if net:
            obj.Net = net
        
        return obj
    
    def addpolygon(self,layerName,points,net=None,name=None):
        '''
        points:list,tuple, Point
        '''
        if not points or len(points)<3:
            log.exception("Points of polygon must have 3 points")
            
#         if not name:
#             name = self.getUniqueName()
            
        pts = [Point(p) for p in points]
        xyListTemp = []
        for i in range(len(pts)):
            xyListTemp.append("x:=")
            xyListTemp.append(0)
            xyListTemp.append("y:=")
            xyListTemp.append(0)
        if not name:
            name = self.Circles.getUniqueName("poly_")
        log.info("Create poly: %s"%name)
        
        name = self.layout.oEditor.CreatePolygon(
        [
            "NAME:Contents",
            "polyGeometry:=", 
            ["Name:=", "poly_0",     
            "LayerName:=", self.layout.Layers[layerName].Name,
            "lw:=", "0","n:=", 6,
            "U:=", self.layout.unit]  + xyListTemp
    #         "x:=", -1,"y:=", -25,"x:=", -11,"y:=", -41,"x:=", -4,"y:=", -49,"x:=", 37,"y:=", -50,"x:=", 24,"y:=", -21,"x:=", 11,"y:=", -29,"x:=", -1,"y:=", -25]
        ])
        
        self.Polys.push(name)
        obj = self.Polys[name]
        for i in range(len(pts)):
            obj["Pt%s"%i] = pts[i]
            
        if net:
            obj.Net = net
            
        return obj
    
    def addVia(self,position,padStack,hole="0mm",upperLayer=None,lowerLayer=None,isPin = False,net=None,name=None):
        
        if not name:
            name = self.Circles.getUniqueName("poly_")
        log.info("Create Via: %s"%name)
        
        if len(position)!=2:
            log.exception("Center must have length 2")
            
        if not lowerLayer:
            lowerLayer = upperLayer
        
        pos = Point(position)
        self.oEditor.CreateVia(
            [
                "NAME:Contents",
                "name:="        , name,
                "ReferencedPadstack:="    , padStack,
                "vposition:="        , ["x:=", "0mm","y:=", "0mm"],
                "vrotation:="        , ["0deg"],
                "overrides hole:="    , False,
                "hole diameter:="    , ["0.1mm"],
                "Pin:="            , isPin,
                "highest_layer:="    , upperLayer,
                "lowest_layer:="    , lowerLayer
            ])
        
        if isPin:
            
            self.Pins.push(name)
            obj = self.Pins[name]
#             self.Pins[name].Location = Point(position)
#             self.Pins[name].HoleDiameter = hole
#             if net:
#                 obj.Net = net
#             return self.Pins[name]
        else:
            self.Vias.push(name)
            obj = self.Vias[name]
            
        obj.Location = Point(position)
        obj.HoleDiameter = hole
        return obj
    
    def sanitize(self,nets):
        log.info("SanitizeLayout "+",".join(nets))
        self.oEditor.SanitizeLayout(["NAME:SanitizeList"]+list(nets))
    
    def healingVoid(self,smallArea="0.5mm2"):
        log.info("healing Void area small then %s"%smallArea)
        polys = self.Shapes.NameList
        self.oEditor.Heal(
            [
                "NAME:Feature",
                "Selection:="        , polys,
                "Type:="        , "Voids",
                "AntiPads:="        , False,
                "Tol:="            , smallArea
            ])
    
    #--- IO
    
    def newProject(self,projectName = None):
        oProject = self.oDesktop.NewProject()
        if projectName:
            oProject.Rename(projectName, True)
        self.initProject(projectName)
        return oProject
    
    
    def newDesign(self,newDesignName,projectName = None):
        if projectName:
            oProject = self.oDesktop.SetActiveProject(projectName)
            oProject.InsertDesign(self._toolType, newDesignName, "", "")
            self.initDesign(projectName, newDesignName)
        else:
            self.oProject.InsertDesign(self._toolType, newDesignName, "", "")
            self.initDesign(self.projectName, newDesignName)
            
        return self.oDesign
    
    def deleteProject(self):
        self.oDesktop.DeleteProject(self.ProjectName)
        self._oProject = None
        self._oDesign = None
        self._oEditor = None
    
    def deleteDesign(self):
        self.oProject.DeleteDesign(self.DesignName)
        self._oDesign = None
        self._oEditor = None
    
    
#     def newDesign(self,newDesignName,newPorjectName = None):
#         if newPorjectName:
#             oProject = oDesktop.NewProject()
#             oProject.Rename(os.path.join(oProject.GetPath(),newPorjectName), True)
#             oProject.InsertDesign("HFSS 3D Layout Design", newDesignName, "", "")
#             self.initDesign(newPorjectName, newDesignName)
#         else:
#             self.oProject.InsertDesign("HFSS 3D Layout Design", newDesignName, "", "")
#             self.initDesign(self.projectName, newDesignName)
    
    def translateLayout(self,layoutPath,edbOutPath = None, controlFile = "", extractExePath = None, layoutType = None):
        
        if extractExePath:
            if extractExePath[-4:].lower() == ".exe":
                extractExePath = os.path.dirname(extractExePath)
                
            if extractExePath not in os.environ['PATH']:
                split = ";" if 'nt' in os.name else ":"
                os.environ['PATH'] = split.join([extractExePath,os.environ['PATH']])
                log.debug(os.environ['PATH'])
                
        installPath = self.oDesktop.GetExeDir()
        if installPath not in os.environ['PATH']:
            split = ";" if 'nt' in os.name else ":"
            os.environ['PATH'] = split.join([installPath,os.environ['PATH']])
            log.debug(os.environ['PATH'])
        
        if not edbOutPath:
            edbOutPath = layoutPath[:-4] + ".aedb"
        if not controlFile:
            cmd = "anstranslator {input} {output}".format(input=layoutPath,output=edbOutPath)
        else:
            cmd = "anstranslator {input} {output} -c={controlFileName}".format(input=layoutPath,output=edbOutPath,controlFileName=controlFile)
        os.system(cmd)
        
        return edbOutPath
    
    def loadLayout(self,layoutPath ,edbOutPath = None,controlFile = "", layoutType = None, extractExePath = None):
        '''
        doc
        '''
   
        if not layoutType:
            if layoutPath[-4:].lower() in [".brd",".mcm",".sip"]:
                layoutType = "Cadence"
            elif layoutPath[-4:].lower() in [".siw"]:
                layoutType = "SIwave"
            elif layoutPath[-5:].lower() in [".aedt","aedtz"]:
                layoutType = "AEDT"
            elif layoutPath[-5:].lower() in [".aedb"]:
                layoutType = "EDB"
            elif layoutPath[-7:].lower() in ["edb.def"]:
                layoutType = "EDB"
                
            elif layoutPath[-4:].lower() in [".tgz"]:
                layoutType = "ODB++"
                
            elif layoutPath[-4:].lower() in [".gds"]:
                layoutType = "GDS"
                
            else:
                raise Exception("Layout type must be specified")
        
        if extractExePath:
            if extractExePath[-4:].lower() == ".exe":
                extractExePath = os.path.dirname(extractExePath)
                
            if extractExePath not in os.environ['PATH']:
                split = ";" if 'nt' in os.name else ":"
                os.environ['PATH'] = split.join([extractExePath,os.environ['PATH']])
                log.debug(os.environ['PATH'])
        
        
        if layoutType.lower() == "aedt":
            self.openAedt(layoutPath)
        elif layoutType.lower() == "edb":
            self.importEBD(layoutPath)
        elif layoutType.lower() == "cadence":
            if not edbOutPath:
                edbOutPath = layoutPath[:-4] + ".aedb"
            if not controlFile:
                controlFile = ""
            # self.importBrd(layoutPath,edbOutPath,controlFile)
            edbout = self.translateLayout(layoutPath,edbOutPath,controlFile)
            self.importEBD(edbout)
        elif layoutType.lower() == "odb++":
            if not edbOutPath:
                edbOutPath = layoutPath[:-4] + ".aedb"
            if not controlFile:
                controlFile = ""
            self.importODB(layoutPath,edbOutPath,controlFile)
        
        elif layoutType.lower() == "siwave":
            self.importSIwave(layoutPath)
            
        else:
            raise Exception("Unknow layout type")
    
    def importEBD(self,path):
        if path[-4:] == "aedb":
            path = os.path.join(path,"edb.def")
            
        if not os.path.exists(path):
            log.exception("EDB file not exist: %s"%path)
            
        aedtPath = os.path.dirname(path)[-5:] + ".aedt"
        if os.path.exists(aedtPath):
            os.remove(aedtPath)

        log.info("load edb : %s"%path)
        oTool = self.oDesktop.GetTool("ImportExport")
        oTool.ImportEDB(path)
        self.initDesign()
        
    def importBrd(self,path,edbPath = None, controlFile = ""):
        '''
        Imports a Cadence Extracta file into a new project.
        '''
        
        if edbPath == None:
            edbPath = path[:-3]+"aedb"
            
        if os.path.exists(edbPath[:-4]+"aedt"):
            log.info("Remove old edt file: %s"%edbPath[:-4]+"aedt")
            os.remove(edbPath[:-4]+"aedt")

        if os.path.exists(edbPath):
            log.info("Remove old edb file: %s"%edbPath)
            shutil.rmtree(edbPath)

        oTool = self.oDesktop.GetTool("ImportExport")
        oTool.ImportExtracta(path, edbPath, controlFile)
        self.initDesign()
#         self.initDesign(projectName=os.path.splitext(os.path.basename(path))[0])
        
    def importODB(self,path,edbPath = None, controlFile = ""):
        if edbPath == None:
            edbPath = path[:-3]+"aedb"
            
        if os.path.exists(edbPath[:-4]+"aedt"):
            log.info("Remove old edt file: %s"%edbPath[:-4]+"aedt")
            os.remove(edbPath[:-4]+"aedt")

        if os.path.exists(edbPath):
            log.info("Remove old edb file: %s"%edbPath)
            shutil.rmtree(edbPath)

        oTool = self.oDesktop.GetTool("ImportExport")
        oTool.ImportODB(path, edbPath, controlFile)
        self.initDesign()
#         self.initDesign(projectName=os.path.splitext(os.path.basename(path))[0])
        
    def importSIwave(self,path,edbPath = None):
        if edbPath == None:
            edbPath = os.path.splitext(self.ProjectPath)[0]+"aedb"

        execPath = os.path.join(self.ProjectDir, "SaveSiw.exec") 
        with open(execPath,"w+") as f:
            f.write("SaveEdb %s"%edbPath)
            f.close()

        if self.installDir not in os.environ['PATH']:
            split = ";" if 'nt' in os.name else ":"
            os.environ['PATH'] = split.join([self.installDir,os.environ['PATH']])
            log.debug(os.environ['PATH'])

        cmd = '"{0}" {1} {2} -formatOutput'.format("siwave_ng",path,execPath)
        log.info("Import Siwave to Aedt: %s"%path)
        with os.popen(cmd,"r") as output:
            for line in output:
                log.info(line)
            output.close()
        self.importEBD(edbPath)
         

    def exportGDS(self,path=None,outLayerMapPath = None):
        
        if path == None:
            path = self.ProjectPath+".gds"

        if not outLayerMapPath:
            outLayerMapPath = path+".layermap"
        
        log.info("Export layout to gds to %s"%path)

        LayerMap = []
        LayerMapTxts = []
        for i,name in enumerate(self.layers.ConductorLayerNames):
            LayerMap.append("entry:=")
            LayerMap.append([ "layer:=" , name, "id:=" , i*2, "include:=" , True])
            LayerMapTxts.append("%s %s"%(i*2,name))

        self.oEditor.ExportGDSII(
            [
                "NAME:options",
                "FileName:=" , path,
                "NumVertices:=" , 8191,
                "ArcTol:=" , 2E-06,
                "LayerMap:=" ,LayerMap
            ])
        writeData(LayerMapTxts,outLayerMapPath)

    def openAedt(self,path,unlock=False):
        
        if not os.path.exists(path):
            log.exception("Project Path not exist: %s"%path)
        
        if unlock:
            if os.path.exists(path+".lock"):
                os.remove(path+".lock")
        
        log.info("OpenProject : %s"%path)
        self.oDesktop.OpenProject(path)
        self.initDesign(projectName=os.path.splitext(os.path.basename(path))[0])
    
    def openArchive(self,archive,newPath):
        log.info("RestoreProjectArchive: %s"%archive)
        self.oDesktop.RestoreProjectArchive(archive, newPath, False, True) 
        self.initDesign(projectName=os.path.splitext(os.path.basename(newPath))[0])
    
    def reload(self):
        aedtPath = self.ProjectPath
        log.info("reload AEDT %s"%aedtPath)
        self.oProject.Save()
        self.oProject.Close()
        self.oDesktop.OpenProject(aedtPath)
        self.initDesign(projectName=os.path.splitext(os.path.basename(aedtPath))[0])


    def reloadEdb(self):
        
        aedtPath = os.path.join(self.oProject.GetPath(),self.oProject.GetName()+".aedt")
        edbPath = os.path.join(self.oProject.GetPath(),self.oProject.GetName()+".aedb")
        log.info("reload Edb %s"%edbPath)
        self.oProject.Save()
        self.oProject.Close()
        if os.path.exists(aedtPath):
            os.remove(aedtPath)
        self.importEBD(edbPath)
        self.initDesign(projectName=os.path.splitext(os.path.basename(aedtPath))[0])

    def saveAs(self,path,OverWrite=True):
        log.info("save As %s"%path)
        
        subDir = os.path.dirname(path)
        if not os.path.exists(subDir):
            os.makedirs(subDir)
        
        
        self.oProject.SaveAs(path, OverWrite)
#         self.close(save=True)
#         self.copyAEDT(self.projectPath,path)
#         self.openAedt(path)
        self.initDesign(projectName=os.path.splitext(os.path.basename(path))[0])

    def save(self):
        log.info("Save project: %s"%self.ProjectPath)
        self.oProject.Save()
    
    def exportSiwave(self,path=None):
        
        if not path:
            path = os.path.splitext(self.ProjectPath)[0]+".siw"
        
        execPath = os.path.join(self.ProjectDir, "SaveSiw.exec") 
        with open(execPath,"w+") as f:
            f.write("SaveSiw")
            f.close()
        cmd = '"{0}" {1} {2} -formatOutput'.format(os.path.join(self.InstallDir,"siwave_ng"),self.EdbPath,execPath)
        log.info("Save project to Siwave: %s"%path)
        with os.popen(cmd,"r") as output:
            for line in output:
                log.info(line)
            output.close()
        
        return path
    
    def close(self,save=True):
        if save:
            self.save()
        log.info("Close project: %s"%self.ProjectPath)
        self.oProject.Close()
            
    def deleteFromDisk(self):
        log.info("delete project from disk: %s"%self.ProjectPath)
        self.oDesktop.DeleteProject(self.projectName)
        if os.path.exists(self.resultsPath):
            log.info("delete project from disk: %s"%self.resultsPath)
            shutil.rmtree(self.resultsPath)
    
#     @classmethod
#     def quitAedt(cls):
#         Module = sys.modules['__main__']
#         if hasattr(Module, "oDesktop"):
#             oDesktop = getattr(Module, "oDesktop")
#             if oDesktop:
#                 log.info("QuitApplication.")
#                 oDesktop.QuitApplication()
#         releaseDesktop()
#         time.sleep(5) #wait for aedt quit

    def quitAedt(self,force=False):
        Module = sys.modules['__main__']
        if hasattr(Module, "oDesktop"):
            oDesktop = getattr(Module, "oDesktop")
        else:
            return
        
        if not oDesktop:
            return
         
        #nonGraphical will quit by AEDT
        # if self.nonGraphical:
        #     #quit aedt if in nonGraphical mode
        #     oDesktop.QuitApplication()
        #     releaseDesktop()

        if force:
#             self._DelKeepGUILicenseProject(oDesktop)
            oDesktop.QuitApplication()
            releaseDesktop()
            time.sleep(5)
        else:
            if self.options["AEDT_KeepGUILicense"]:
                log.info("KeepGUILicense have been set, Aedt will not quit without release license.")
            else:
#                 self._DelKeepGUILicenseProject(oDesktop)
                oDesktop.QuitApplication()
                releaseDesktop()
                time.sleep(5)
    
    @classmethod
    def copyAEDT(cls,source,target):
        '''
        copy aedb,aedt
        '''
        from shutil import copy
        #source = (source,source+".aedt")(".aedt" in source)
        if ".aedt" not in source:
            print("source must .aedt file: %s"%source)
            return
        if not os.path.exists(source):
            print("source file not found: %s"%source)
            return
        
        
        aedtTarget = (target+".aedt",target)[".aedt" in target]
        aedtTargetDir = os.path.dirname(aedtTarget)
        if not os.path.exists(aedtTargetDir):
            print("make dir: %s"%aedtTargetDir)
            os.mkdir(aedtTargetDir)
        
        copy(source,aedtTarget)
        
        edbSource = source[:-5]+".aedb" +"/edb.def"
        if os.path.exists(edbSource):
            edbTargetdir = aedtTarget[:-5]+".aedb"
            
            if not os.path.exists(edbTargetdir):
                print("make dir: %s"%edbTargetdir)
                os.mkdir(edbTargetdir)
            copy(edbSource,edbTargetdir)
        return aedtTarget

    #---analyze and job   

    def _getPackCount(self,cores):
        pack = 0
        if cores>8*4*4*4+4:
            pack = math.ceil(math.log((cores-4)/2) / math.log(4))
        elif cores>8*4*4+4:
            pack = 4
        elif cores>8*4+4:
            pack = 3
        elif cores>8+4:
            pack = 2
        elif cores>4:
            pack = 1
        else:
            pass
        return pack

    def analyze(self):

        if self.options["AEDT_WaitForLicense"]:
            if self.options["AEDT_HPC_NumCores"]:
                cores = self.options["AEDT_HPC_NumCores"]
                self.setCores(cores)
            else:
                oDesktop = self.oDesktop
                #worked, get core from ActiveDSOConfigurations/
                activeHPCOption = oDesktop.GetRegistryString("Desktop/ActiveDSOConfigurations/HFSS 3D Layout Design")
                log.info("ActiveDSOConfigurations: %s"%activeHPCOption)
                #oDesktop.SetRegistryString(r"Desktop/DSOConfigurationsEx/HFSS 3D Layout Design/%s/NumCores"%activeHPCOption)
                activeHpcStr = oDesktop.GetRegistryString("Desktop/DSOConfigurationsEx/HFSS 3D Layout Design/%s"%activeHPCOption)
                rst = re.findall(r"NumCores=(\d+)", activeHpcStr)
                if rst:
                    cores = int(rst[0])
                else:
                    cores = 0
            if cores:
                self.waitForlicense([{"module":"HFSSSolver"},{"feature":"anshpc_pack","count":self._getPackCount(cores)}])

        self.oDesign.AnalyzeAll()
    
    def submitJob(self,host="localhost",cores=20):
        installPath = self.oDesktop.GetExeDir()
        jobId = "RSM_{:.5f}".format(time.time()).replace(".","")
        cmd = '"{exePath}" -jobid {jobId} -distributed -machinelist list={host}:-1:{cores}:90%:1 -auto -monitor \
                -useelectronicsppe=1 -ng -batchoptions "" -batchsolve {aedtPath}'.format(
                    exePath = os.path.join(installPath,"ansysedt.exe"),
                    jobId = jobId,
                    host = host, cores = cores, aedtPath = self.ProjectPath
                    )
        log.info("Project will be closed to submit job.")
        log.info("submit job ID: %s"%jobId)
        self.close(save=True)
        log.info(cmd)
        os.system(cmd)
#         with os.popen(cmd,"r") as output:
#             for line in output:
#                 log.info(line)
#             output.close()
        
        return jobId
    
    def batchAnalysis(self,host="localhost",cores=20):
        installPath = self.oDesktop.GetExeDir()
        jobId = "RSM_{:.5f}".format(time.time()).replace(".","")
        cmd = '"{exePath}" -jobid {jobId} -distributed -machinelist list={host}:-1:{cores}:90%:1 -auto -monitor \
                -useelectronicsppe=1 -ng -batchoptions "" -batchsolve {aedtPath}'.format(
                    exePath = os.path.join(installPath,"ansysedt.exe"),
                    jobId = jobId,
                    host = host, cores = cores, aedtPath = self.ProjectPath
                    )
        log.info("Project will be closed to batch Analysis.")
        log.info("submit job ID: %s"%jobId)
        self.close(save=True)
        log.info(cmd)

        if self.options["AEDT_WaitForLicense"]:
            self.waitForlicense([{"module":"HFSSSolver"},{"feature":"anshpc_pack","count":self._getPackCount(cores)}])

        with os.popen(cmd,"r") as output:
            for line in output:
                log.info(line)
            output.close()

    def setCores(self,cores,hpcType = "Pack"):
        '''
        cores (int): 
        hpcType (str): Pack or Workgroup
        '''
        
        self.options["AEDT_HPC_NumCores"] = cores

        oDesktop = self.oDesktop
        ConfigName = "pyaedt_config"
        cfg = analysis_cfg.format(ConfigName ="pyaedt_config",DesignType = "HFSS 3D Layout Design",MachineName="localhost",NumCores = cores)
        pathScf = os.path.join(self.projectDir,"hpc.acf")
        writeData(cfg, pathScf)
        log.info('set Active HPC Configuration "%s":  NumCores=%s'%(ConfigName,cores))
        oDesktop.SetRegistryFromFile(pathScf)
        oDesktop.SetRegistryString(r"Desktop/ActiveDSOConfigurations/" + self.designtype, ConfigName)

        #worked
        # activeHPCOption = oDesktop.GetRegistryString("Desktop/ActiveDSOConfigurations/HFSS 3D Layout Design")
        # log.info("ActiveDSOConfigurations: %s"%activeHPCOption)
        # #oDesktop.SetRegistryString(r"Desktop/DSOConfigurationsEx/HFSS 3D Layout Design/%s/NumCores"%activeHPCOption)
        # activeHpcStr = oDesktop.GetRegistryString("Desktop/DSOConfigurationsEx/HFSS 3D Layout Design/%s"%activeHPCOption)
        
        # cores_old = re.findall(r"NumCores=(\d+)", activeHpcStr)
        
        # if cores_old and int(cores_old[0])!=int(cores):
        #     activeHpcStr = re.sub(r"NumCores=\d+","NumCores=%s"%int(cores), activeHpcStr)
            

        #     #workaround
        #     scfStr = "$begin 'Configs'\n$begin 'Configs'\n%s$end 'Configs'\n$end 'Configs'\n"%activeHpcStr
        #     pathScf = os.path.join(self.projectDir,"hpc.acf")
        #     writeData(scfStr, pathScf)
        #     log.info('set Active HPC Configuration "%s":  NumCores=%s'%(activeHPCOption,cores))
        #     self.oDesktop.SetRegistryFromFile(pathScf)
        # else:
        #     log.info("ActiveDSOConfigurations have the same cores as required")
        
        if hpcType:
            self.setHPCType(hpcType)

        
    def setHPCType(self,hpcType):
        '''
        hpcType (str): Pack or Workgroup
        '''
        if hpcType:
            #oDesktop.GetRegistryString("Desktop/Settings/ProjectOptions/HPCLicenseType")
            log.info('set HPCLicenseType: %s'%(hpcType))
            self.oDesktop.SetRegistryString("Desktop/Settings/ProjectOptions/HPCLicenseType",hpcType)
        
    @classmethod
    def isBatchMode(cls):
        Module = sys.modules['__main__']
        return hasattr(Module, "ScriptArgument")
    
    @classmethod
    def getScriptArgument(cls):
        Module = sys.modules['__main__']
        if hasattr(Module, "ScriptArgument"):
            return getattr(Module, "ScriptArgument")
        else:
            log.exception("Not running in batchmode")
    
    def getRelPath(self,path):
        
        try:
            relPath = os.path.relpath(path,self.ProjectDir)
            return os.path.join("$PROJECTDIR",relPath)
        except:
            return path

    #---message  

    def message(self,msg,level = 0):
        global oDesktop
        log.debug(msg)
        self.oDesktop.AddMessage("","",0,msg)


    def release(self):
        
        releaseDesktop()
        try:
            self._info = None
            self._oEditor = None
            self._oDesign = None
            self._oProject = None
            self._oDesktop = None
            import gc
            gc.collect()
        except AttributeError:
            pass

    @classmethod
    def setClr(cls):
        isIronpython = "IronPython" in sys.version
        is_linux = "posix" in os.name
        
        if is_linux and not isIronpython:
            try:
                from ansys.aedt.core.generic.clr_module import _clr
            except:
                log.exception("pyaedt must be install: pip3 install pyaedt")
        else:
            import clr as _clr
        return _clr

#for test
if __name__ == '__main__':
#     layout = Layout("2022.2")
    layout = Layout("2023.2")
    layout.initDesign()
    layout.via1062
    layout.port[0]
    U8 = layout["Component:U8"]
    U9 = layout["Component:U8"]
    a= layout.Copper
    a["Resistivity"]= 1.0e-08
    layout.Layers.addLayer("L0")
    pins = U8.Pins
    layout.Port1
    pin = layout["U8_1"]
    dir(U8)
    pin = layout["Pin:U8-1"]
#     top = layout["Layer:C:0"]
    fr4= layout.Materials["FR4_epoxy"]
#     rst = layout.Solutions.getAllSetupSolution()
#     layout.Variables.test
    layout.release()
#     rst[0].exportSNP("c:\work\1.txt")
    pass