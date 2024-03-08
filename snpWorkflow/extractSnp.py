    #coding:utf-8
    #--- coding=utf-8
    #--- @author: yongsheng.guo@ansys.com
    #--- @Time: 20230410

'''
通过仿真配置文件(json)驱动HFSS 3D Layout进行S参数的提取。

# workflow:

laod PCB -> load stackup -> configComponents -> ConfigNets -> Cutout -> Port -> solveSetup -> Solve -> datas -> Post

Eaxmples:

    configPath = os.path.join(r"config\galileo_pcie_snpExtract.json")
    sim = ExtractSNP(configPath)
    sim.run()


'''

import sys,os
appPath = os.path.realpath(__file__)
appDir = os.path.split(appPath)[0] 
sys.path.append(appDir)

try:
    sys.path.append(r"C:\work\Study\Script\Ansys\quickAnalyze\FastSim")
    import pyLayout
except:
    import clr
    clr.AddReference(pyLayout)
    import pyLayout


from pyLayout import Layout,log,ComplexDict
from pyLayout import writeJson# from layout.lib.common import log
# from layout.lib.complexDict import ComplexDict
# complexDictayout.pyLayout import log

log.info("Start ExtractSNP analyse, this progrom powered by Ansys.")

class ExtractSNP(object):
    '''
    classdocs
    '''

    def __init__(self, simConfigPath = None, defaultConfigPath = None):
        '''
        Constructor
        '''
        self._config = None
        self.layout = None
        
        if not defaultConfigPath:
            defaultConfig = os.path.join(appDir,"snpExtract_default.json")
            self.loadConfig(defaultConfig)
        
        
        if simConfigPath:
#             conf = ComplexDict.loadConfig(simConfigPath)
            self.updateConfig(simConfigPath)
#             self.setConfigFile(simConfig)

    @property
    def Config(self):
        return self._config
    
    def setConfigFile(self,path):
        if not os.path.exists(path):
            log.warning("Configuration Path not found %s"%path)
            return
        conf = ComplexDict.loadConfig(path)
        self.updateConfig(conf)
#         self._config = path
        
        
    #--- workflow for Extract 3D Layout design

    def loadConfig(self,config):
        if isinstance(config, str):
            #config path
            self._config = ComplexDict(path = config)
        elif isinstance(config, dict):
            #dict options
            self._config = ComplexDict(options = config)
            
        elif isinstance(config, ComplexDict):
            self._config = config
        
        else:
            log.exception("loadConfig: config must be path,dict or ComplexDict. %s"%str(config))
    
    def updateConfig(self,config):
        '''
        Agrs:
            config(dict,jsonPath,ComplexDict):  update analyze config infomation to layout
        '''
        
        if self._config == None:
            self._config = ComplexDict()
        
        options = ComplexDict.loadConfig(config)
        self._config.updates(options)


    def loadLayout(self):
        
        pcb = self.Config["Import"]
        log.info("translateLayout : %s"%pcb["LayoutPath"])

        edbPath = self.layout.translateLayout(
            layoutPath = pcb["LayoutPath"],
            edbOutPath = pcb["EdbOutPath"],
            controlFile = pcb["ControlFile"],
            extractExePath = pcb["extractExePath"], 
            layoutType = pcb["LayoutType"])
        self.layout.importEBD(edbPath)
        #return edbpath

    def loadStackup(self):
        '''
        - {Name: SURFACE,Type: signal, Material: copper, FillMaterial: M4 ,Thickness: 3.556e-05, Roughness: 0.5um,2.9 ,DK: 4,DF: 0.02, Cond: 5.8e7, EtchFactor: 2.5}
        - {Name: SURFACE,Type: dielectric, Material: M4 ,Thickness: 3.556e-05,DK: 4,DF: 0.02}
        '''
        
        materials = self.Config["Stackup/Matrials"]
        for name in materials.Keys:
            material = materials[name]
            material.update("Name",name)
            self.layout.Materials.add(material)
        
        config = self.Config["Stackup/Layers"]
#         self.layout.Layers.setLayerDatas(config,mode="force")
        self.layout.Layers.loadFromDict(config)
    
    
    def configComponents(self):
        config = self.Config["BOM"]
        self.Components.updateBom(config)
        
#         delete "A36096-030" first
#         oEditor.CreateComponent(
#             [
#                 "NAME:Contents",
#                 "isRCS:="        , True,
#                 "definition_name:="    , "A36096-030",
#                 "type:="        , "Capacitor",
#                 "ref_des:="        , "C1-2",
#                 "placement_layer:="    , "TOP",
#                 "elements:="        , ["C1-1","C1-2"]
#             ])
        
    
    def configNets(self):
        pass
    
    def cutoutDesign(self):
#         Cutout:
#           # NetInclude for net must be full included
#           # PowerNet and GNDNet will be included and cut at boundary
#           NetInclude: []
#           NetClip： []
#           KeepPowerNet: Yes
#           Enable: True
#           CutExpansion: 10mm
        cutout = self.Config["Cutout"]  #return as ComplexDict()
        if not cutout["Enable"]:
            log.info("cutout not enable.")
            return
        
        # Net include
        NetInclude = cutout["NetInclude"]
        if not NetInclude:
            NetInclude = self.Config["Ports/PortOnNets"]
            
        NetInclude = self.layout.Nets.getRegularNets(NetInclude)
            
        if not NetInclude:
            log.info("No Net include, cutout skip")
            return
        
        # Net cutout
        NetClip = cutout["NetClip"]
        
        if not NetClip:
            NetClip = []
        
        NetClip = self.layout.Nets.getRegularNets(NetClip)
        
        if cutout["KeepPowerNet"]:
            NetClip += self.layout.Nets.PowerNetList
            
        if cutout["SubProjectName"]:
            newAedtPath = os.path.join(self.layout.projectDir,cutout["SubProjectName"])
            self.layout.saveAs(newAedtPath, True)
            
        self.layout.clip(self.layout.designName, NetInclude, NetClip, cutout["CutExpansion"], InPlace = True)

    
    def setPorts(self):
        ports = self.Config["Ports"]
        
        nets  = self.layout.Nets.getRegularNets(ports["PortOnNets"])
        solderBall = ports["SolderBall"]
        
        #set solderball ratio
        ratio = solderBall["Ratio"]
        if ratio[0] !=None:
            self.layout.options["H3DL_solderBallHeightRatio"] = ratio[0]
        if ratio[1] !=None:
            self.layout.options["H3DL_solderBallWidthRatio"] = ratio[1]
        
        ignoreComponent = ports["IgnoreComponent"]
        ignorePart  = ports["IgnorePart"]
        
        #Get all components on nets
        compNames = self.layout.Nets.getComponentsOnNets(nets, ignorRLC = not ports["PortOnRLC"])
        
        #create solderball on components
        for name in compNames:
            if name in solderBall:
                size = solderBall[name]
            else:
                size = solderBall["Default"][:] #copy to avoid modify self.Config
                
            self.layout.Components[name].createSolderBall(size)
        
        #create port on nets
        self.layout.Nets.createPortsOnNets(nets, compNames)
        portOrder = ports["OrderPorts"]
        self.layout.ports.reorder(compOrder=portOrder["CompOrder"],netOrder=portOrder["NetOrder"],portOrder = portOrder["PortOrder"])
        
    
    def solveSetup(self):

        Anslysis = self.Config["Analysis"]
        Setup = Anslysis["Setup"]
            
        Options = Setup.get("Options",default = {})


        setupName = Setup["Name"]
        solutionType = Setup["SolutionType"]
        setup1 = self.layout.Setups.add(setupName, solutionType)
#         datas = setup1.getData()
        for k,v in Options.items():
            setup1[k] = v
#         setup1.setData(arrayDatas = datas.Array)
        
        
        #for sweep datas
        Sweep = Setup["Sweep"]
        Options = Sweep.get("Options",default = {})          
        sweepName = Sweep["Name"]
        sweep1 = setup1.addSweep(sweepName)
#         datas = sweep1.getData()
        
        for k,v in Options.items():
            sweep1[k] = v
#         sweep1.setData(arrayDatas = datas.Array)
            

    def solve(self):
#         tempPath = self.layout.ProjectPath
#         self.layout.submitJob(cores=20)
#         self.layout.openAedt(tempPath)
        
        setup = self.Config["Analysis/Setup"]
        setupName = setup["Name"]
        self.layout.Setups[setupName].analyze()

    
    def exportDatas(self):
        setup = self.Config["Analysis/Setup"]
        setupName = setup["Name"] 
        sweepName = setup["Sweep/Name"]
        solution = self.layout.Solutions["%s:%s"%(setupName,sweepName)]
        solution.exportSNP()        
        
        
    def run(self):
        '''
        workflow:
        
        laod PCB -> load stackup -> configComponents -> ConfigNets -> Cutout -> Port -> solveSetup -> Solve -> datas -> Post
        '''
        #write config file for debug
        layoutPath = self.Config["Import/LayoutPath"]
        configPath = layoutPath + ".json"
        writeJson(configPath,self.Config._dict)
        
        #initial layout
#         self.layout = Layout("2022.2")
        version = self.Config["AEDT/Version"]
        installPath = self.Config["AEDT/InstallPath"]
        #if version and installPath are null, least version will be initialized
        self.layout = Layout(version=version, installDir=installPath)
        
#         self.layout.initDesign()
        log.info("load layout file")
        self.loadLayout()
        self.layout.save()
        #load stackup
        log.info("load stackup file")
        self.loadStackup()
        self.layout.save()
        #configComponents
#         layout.configComponents()
        #ConfigNets
#         layout.configNets()
        #cutout pcb to reduced simulaiton time
        log.info("Cutout layout")
        self.cutoutDesign()
        self.layout.save()
        #create ports
        log.info("Create ports")
        self.setPorts()
        self.layout.save()
        #solve frequency, sweep scope
        log.info("Add setup and sweep")
        self.solveSetup()
        self.layout.save()
        #run the simution
        log.info("Run the simution")
        self.solve()
        self.layout.save()
        #get simution data
        log.info("Export simution data")
        self.exportDatas()
        self.layout.release()

#for test
if __name__ == '__main__':
    
    configPath = os.path.join(appDir,r"snpExtract_galileo_brd.json")
    sim = ExtractSNP(configPath)
    sim.run()
    pass        
