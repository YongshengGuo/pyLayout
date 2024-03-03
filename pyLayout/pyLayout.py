#--- coding:utf-8
#--- @Author: Yongsheng.Guo@ansys.com
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

import clr
import os,sys,re
import shutil
import time

from .lib.desktop import initializeDesktop,releaseDesktop
# from .lib.translator import Translator
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
from .lib.shape import Shapes
from .lib.complexDict import ComplexDict
from .lib.geometry import Point,Polygen
from .lib.padStack import PadStacks
from .lib.layoutOptions import options

##log is a globle variable
from .lib.common import log

isIronpython = "IronPython" in sys.version

class Layout(object):
    '''
    classdocs
    '''
    maps = {
        "InstallPath":"InstallDir",
        "Path":"ProjectPath",
        "Name":"DesignName",
        "Ver":"Version",
        "Comps":"Components"
        }
    

    def __init__(self, version=None, installDir=None,usePyAedt=False):
        '''
        初始化PyLayout对象环境
        
        - version和installDir都为None，会尝试启动最新版本的AEDT
        - version和installDir都指定时， version优先级 高于 installDir
        Examples:
            >>> PyLayout()
            open least version AEDT, return PyLayout

            >>> PyLayout(version = "Ansoft.ElectronicsDesktop.2013.1")
            open AEDT 2013R1, return PyLayout
        
        '''
        self._info = ComplexDict({
            "Version":None,
            "InstallDir":None,
            "UsePyAedt":usePyAedt,
            "PyAedtApp":None,
            "pyAedt":None,
            "ProjectDir":None,
            "ProjectName":None,
            "DesignName":None,
            "ProjectPath":None,
            "EdbPath":None,
            "ResultsPath":None,
            
            "Components":None,
            "Pins":None,
            "Nets":None,
            "Layers":None,
            "Lines":None,
            "Vias":None,
            "Shapes":None,
            "Materials":None,
            "Variables":None,
            "Log":None,
            "Version":None,
            "Setups":None,
            "Ports":None,
            "Solutions":None,
            "Config":None
            },maps=self.__class__.maps)
        
        self._info.update("Version", version)
        self._info.update("InstallDir", installDir)
        self._info.update("Log", log)
        self._info.update("options",options)
        
        if not isIronpython and self._info["UsePyAedt"] == None:
            log.info("In cpython environment, UsePyAedt will set to True default. You could set it to False manually.")
            self._info.update("UsePyAedt", True)
        
        #----- 3D Layout object
        self._oDesktop = None
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
        
#        Process is terminated due to StackOverflowException.
#         if not self._oEditor:
#             log.info("Try to intial Project.")
#             self.initDesign()

        if not isinstance(key, str):
            log.exception("key for layout must be str: %s"%key)
        
        flag = False
        try:
            return self._info[key]
        except:
            
#             if not isinstance(key, str):
#                 log.exception("key for layout must be str: %s"%key)
            
            if not self._oDesign:
                log.exception("layout should be intial use 'Layouot.initDesign(projectName = None,designName = None)'")
#             self.initDesign()
            
            log.debug("try to get element type: %s"%key)
            for ele in ["Components","Ports","Nets","Layers","Materials","Pins","Setups","Lines","Vias","Shapes","Variables"]:
                if key in self[ele]:
                    log.debug("Try to return %s for key: %s"%(ele,key))
                    return self[ele][key]
            flag = True
            
        if flag:
            log.exception("not found element on layout: %s"%key)
        
        
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
        if key in ["_oDesktop","_oProject","_oDesign","_oEditor","_info"]:
            object.__setattr__(self,key,value)
        else:
            self[key] = value
        
    def __dir__(self):
#         return object.__dir__(self)  + self.Props
        return dir(self.__class__) + list(self.__dict__.keys()) + self.Props
    
    @property
    def Info(self):
        return self._info
    
    @property
    def Props(self):
        propKeys = list(self.Info.Keys)
        if self.maps:
            propKeys += list(self.maps.keys())
             
        return propKeys
        
    @property
    def oDesktop(self):
        if self.UsePyAedt and self._oDesktop == None: #use pyaedt lib
            if not self.PyAedt:
                log.debug("Try to load pyaedt.")
                try:
                    log.info("will initial oDesktop using PyLayout Lib... ")
                    self.pyAedt = __import__("pyaedt")
                    from pyaedt import launch_desktop
                    from pyaedt.desktop import release_desktop
                    self.PyAedtApp = launch_desktop(specified_version = self.version,new_desktop_session = False)
                    # app = Desktop(specified_version, non_graphical, new_desktop_session, close_on_exit, student_version, machine, port, aedt_process_id)
                except:
                    log.error("pyaedt lib must be installed, install command: pip install pyaedt")
                    log.error("if you don't want use pyaedt to intial pylayout, please set layout.usePyAedt = False before get oDesktop")
                    log.exception("pyaedt app intial error.")

            self._oDesktop == self.PyAedtApp.odesktop
            sys.modules["__main__"].oDesktop = self._oDesktop
        
        if self._oDesktop == None: 
            self._oDesktop = initializeDesktop(self.version,self.installDir)
            self.installDir = self._oDesktop.GetExeDir()
            sys.modules["__main__"].oDesktop = self._oDesktop
            
        return self._oDesktop
    
    
    @property
    def oProject(self):
        if not self._oProject:
            log.info("Try to intial Project to get oDesign.")
            self.initDesign()
#             self.initLayout()
        return self._oProject
    
    @property
    def oDesign(self):
        if not self._oDesign:
            log.info("Try to intial Project to get oDesign.")
            self.initDesign()
#             self.initLayout()
        return self._oDesign
    
    @property
    def oEditor(self):
        if not self._oEditor:
            self._oEditor = self.oDesign.SetActiveEditor("Layout") 
        return self._oEditor

    @property
    def Components(self):
        return self._info["Components"]
 
    @property
    def Pins(self):
        return self._info["Pins"]
 
    @property
    def Nets(self):
        return self._info["Nets"]

    @property
    def Layers(self):
        return self._info["Layers"]
     
    @property
    def Materials(self):
        return self._info["Materials"]
 
    @property
    def Variables(self):
        return self._info["Variables"]

    @property
    def Setups(self):
        return self._info["Setups"]

    @property
    def Solutions(self):
        return self._info["Solutions"]

    
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
        oDesktop = self.oDesktop
        
#         log.debug("AEDT:"+self.Version)
        projectList = oDesktop.GetProjects()
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
                    log.error("project not in aedt.%s"%projectName)
                    raise Exception("project not in aedt.%s"%projectName)
                self._oProject = oDesktop.SetActiveProject(projectName)
    
            else:
                self._oProject = oDesktop.GetActiveProject()
                
                if not self._oProject:
                    self._oProject = oDesktop.GetProjects()[0]
                
        if not self._oProject:
            log.error("Must have one project opened in aedt.")
            raise Exception("Must have one project opened in aedt.")
        
        designList = self.getDesignNames()
        if len(designList)<1:
#             log.error("Must have one design opened in project.")
#             raise Exception("Must have one design opened in project.")
            self._oProject.InsertDesign("HFSS 3D Layout Design", "Layout1", "", "")
            self._oDesign = self._oProject.SetActiveDesign(designName)
        else:
        
            if designName:
                if designName not in designList:
                    log.error("design not in project.%s"%designName)
                    raise Exception("design not in project.%s"%designName)
                self._oDesign = self._oProject.SetActiveDesign(designName)
            else:
                self._oDesign = self._oProject.GetActiveDesign()
                if not self._oDesign:
                    log.info("try to get the first design")
                    self._oDesign = self._oProject.SetActiveDesign(designList[0])
                    
        #make sure the design is 3DL
        designtype = self._oDesign.GetDesignType()
        if designtype != 'HFSS 3D Layout Design':
            log.error("design type error, not 3D layout design.")

            
#         self._oEditor = self._oDesign.SetActiveEditor("Layout") 
        self.projectName = self._oProject.GetName()
        self.projectDir = self._oProject.GetPath()
        self.designName = self.getDesignName(self._oDesign)
        
        log.info("init design: %s : %s"%(self.projectName,self.designName))
        
        #intial layout elements
        self.enableICMode(False)
        if initLayout:
            self.initLayout()

    def initLayout(self):
        
        info = self._info
        #intial log
        path = os.path.join(self.projectDir,"%s_%s.log"%(self.projectName,self.designName))
        log.setPath(path)
        log.info("Simulation log recorded in: %s"%path)

        #path
        info.update("ProjectPath", os.path.join(self.projectDir,self.projectName+".aedt"))
        info.update("EdbPath", os.path.join(self.projectDir,self.projectName+".aedb"))
        info.update("ResultsPath", os.path.join(self.projectDir,self.projectName+".aedtresults"))
        
        info.update("ProjectName", self.projectName)
        info.update("DesignName", self.designName)
        
        #Veraion C:\Program Files\AnsysEM\v231\Win64
        if self.version==None and self.installDir:
            splits = re.split(r"[\\/]+",self.installDir)
            ver1 = splits[-2] if splits[-1].strip() else splits[-3]
            ver2 = ver1.replace(".","")[-3:]
            self.version = "20%s.%s"%(ver2[0:2],ver2[2])
        
        info.update("oDesktop", self.oDesktop)
        info.update("oProject", self.oProject)
        info.update("oDesign", self.oDesign)
        info.update("oEditor", self.oEditor)
        info.update("Maps", self.maps)
        
        info.update("Components", Components(layout = self))
        info.update("Pins", Pins(layout = self))
        info.update("Nets", Nets(layout = self))
        info.update("Layers", Layers(layout = self))
        info.update("Materials", Materials(layout = self))
        info.update("Variables", Variables(layout = self))
        info.update("Lines", Lines(layout = self))
        info.update("Vias", Vias(layout = self))
        info.update("Shapes", Shapes(layout = self))
        info.update("Setups", Setups(layout = self))
        info.update("Ports", Ports(layout = self))
        info.update("Solutions", Solutions(layout = self))
        info.update("PadStacks", PadStacks(layout = self))
        
        info.update("unit",self.oEditor.GetActiveUnits())
        
        #intial geometry definition
        Polygen.layout = self
        Point.layout = self
        
    def getDesignName(self,oDesign):
        return oDesign.GetName().split(';')[-1]
    
    def getDesignNames(self):
        return [name.split(';')[-1] for name in self.oProject.GetTopDesignList()]  
                
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
        delNet = list(filter(lambda n:n not in kNets,self.Nets.NetNames))
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
            
            
    def enableAutosave(self,flag=True):
        Enabled = self.oDesktop.GetAutoSaveEnabled()
        
        if bool(flag) == Enabled:
            return Enabled
        
        if flag:
            oDesktop.EnableAutoSave(True)
        else:
            oDesktop.EnableAutoSave(False)
        
        return Enabled

    #--- objects
    
    def getObjects(self,type="*"):
        '''
        "Type" to search by object type.
        Valid <value> strings for this type include: 'pin', 'via', 'rect', 'arc', 'line', 'poly', 'plg', 'circle void', 
        'line void', 'rect void', 'poly void', 'plg void', 'text', 'cell', 'Measurement', 'Port', 'Port Instance', 
        'Port Instance Port', 'Edge Port', 'component', 'CS', 'S3D', 'ViaGroup'
        '''
        return self.layout.oEditor.FindObjects('Type',type)
        
    def setUnit(self, unit = "um"):
        #return old unit
        return self.oEditor.SetActiveUnits(unit)
    
    def getUnit(self):
        return self.oEditor.GetActiveUnits()
    #--functions

    
    #--- IO
    
    def newDesign(self,newDesignName,newPorjectName = None):
        if newPorjectName:
            oProject = oDesktop.NewProject()
            oProject.Rename(os.path.join(oProject.GetPath(),newPorjectName), True)
            oProject.InsertDesign("HFSS 3D Layout Design", newDesignName, "", "")
            self.initDesign(newPorjectName, newDesignName)
        else:
            self.oProject.InsertDesign("HFSS 3D Layout Design", newDesignName, "", "")
            self.initDesign(self.projectName, newDesignName)
    
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
        
#         if not layoutType:
#             if layoutPath[-4:].lower() in [".brd",".mcm",".sip"]:
#                 layoutType = "Cadence"
#             elif layoutPath[-4:].lower() in [".siw"]:
#                 layoutType = "SIwave"
#             elif layoutPath[-5:].lower() in [".aedt","aedtz"]:
#                 layoutType = "AEDT"
#             elif layoutPath[-5:].lower() in [".aedb"]:
#                 layoutType = "EDB"
#             elif layoutPath[-7:].lower() in ["edb.def"]:
#                 layoutType = "EDB"
                
#             elif layoutPath[-4:].lower() in [".tgz"]:
#                 layoutType = "ODB++"
#                 
#             elif layoutPath[-4:].lower() in [".gds"]:
#                 layoutType = "GDS"
#                 
#             else:
#                 raise Exception("Layout type must be specified")
        
#         if layoutType.lower() == "aedt":
#             self.layout.openAedt(layoutPath)
#         elif layoutType.lower() == "edb":
#             self.layout.importEBD(layoutPath)
#         elif layoutType.lower() == "cadence":
#             if not edbOutPath:
#                 edbOutPath = layoutPath[:-4] + ".aedb"
#             if not controlFile:
#                 controlFile = ""
#             cmd = "AnsTranslator {input} {output} -c={controlFileName}".format(input=layoutPath,output=edbOutPath,controlFileName=controlFile)
#             os.system(cmd)
# #             self.importBrd(layoutPath,edbOutPath,controlFile)
#         else:
#             raise Exception("Unknow layout type")
        
        if not edbOutPath:
            edbOutPath = layoutPath[:-4] + ".aedb"
        if not controlFile:
            controlFile = ""
        cmd = "AnsTranslator {input} {output} -c={controlFileName}".format(input=layoutPath,output=edbOutPath,controlFileName=controlFile)
        os.system(cmd)
        
        return edbOutPath
    
    def loadLayout(self,layoutPath ,edbOutPath = None,controlFile = "", layoutType = None):
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
        
        if layoutType.lower() == "aedt":
            self.layout.openAedt(layoutPath)
        elif layoutType.lower() == "edb":
            self.layout.importEBD(layoutPath)
        elif layoutType.lower() == "cadence":
            if not edbOutPath:
                edbOutPath = layoutPath[:-4] + ".aedb"
            if not controlFile:
                controlFile = ""
            self.importBrd(layoutPath,edbOutPath,controlFile)
        else:
            raise Exception("Unknow layout type")
    
    def importEBD(self,path):
        if path[-4:] == "aedb":
            path = os.path.join(path,"edb.def")
            
        aedtPath = os.path.dirname(path)[-5:] + ".aedt"
        if os.path.exists(aedtPath):
            self.openAedt(aedtPath)
            return
            
        log.info("load edb : %s"%path)
        oTool = self.oDesktop.GetTool("ImportExport")
        oTool.ImportEDB(path)
        self.initDesign()
        
    def importBrd(self,path,edbPath = None, controlFile = ""):
        '''
        Imports a Cadence Extracta file into a new project.
        '''
        
        if edbPath == None:
            edbPath = path[-3:]+"aedb"
            
        oTool = self.oDesktop.GetTool("ImportExport")
        oTool.ImportExtracta(path, edbPath, controlFile)
        self.initDesign()
        
    def openAedt(self,path):
        log.info("OpenProject : %s"%path)
        self.oDesktop.OpenProject(path)
        self.initDesign()
    
    def openArchive(self,archive,newPath):
        log.info("RestoreProjectArchive: %s"%archive)
        self.oDesktop.RestoreProjectArchive(archive, newPath, False, True) 
        self.initDesign()
    
    def reload(self):
        aedtPath = os.path.join(self.oProject.GetPath(),self.oProject.GetName()+".aedt")
        log.info("reload AEDT %s"%aedtPath)
        self.oProject.Save()
        self.oProject.Close()
        self.oDesktop.OpenProject(aedtPath)
        self.initDesign()


    def reloadEdb(self):
        
        aedtPath = os.path.join(self.oProject.GetPath(),self.oProject.GetName()+".aedt")
        edbPath = os.path.join(self.oProject.GetPath(),self.oProject.GetName()+".aedb")
        log.info("reload Edb %s"%edbPath)
        self.oProject.Save()
        self.oProject.Close()
        if os.path.exists(aedtPath):
            os.remove(aedtPath)
        self.importEBD(edbPath)
        self.initDesign()

    def saveAs(self,path,OverWrite=True):
        log.info("save As %s"%path)
        self.oProject.SaveAs(path, OverWrite)
        self.initDesign()

    def save(self):
        log.info("Save project: %s"%self.ProjectPath)
        self.oProject.Save()

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

    #---message and job   
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
        return jobId


    def message(self,msg,level = 0):
        global oDesktop
        log.debug(msg)
        self.oDesktop.AddMessage("","",0,msg)


    def release(self):
        
        releaseDesktop()
        try:
            self._oEditor = None
            self._oDesign = None
            self._oProject = None
            self._oDesktop = None
            import gc
            gc.collect()
        except AttributeError:
            pass

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