    #coding:utf-8
    #--- coding=utf-8
    #--- @author: yongsheng.guo@ansys.com
    #--- @Time: 20230410
    #--- @update 20230618

'''
通过仿真配置文件(json)驱动HFSS 3D Layout进行S参数的提取。

# workflow:

laod PCB -> load stackup -> configComponents -> ConfigNets -> Cutout -> Port -> solveSetup -> Solve -> datas -> Post

Eaxmples:

    configPath = os.path.join(r"config\galileo_pcie_snpExtract.json")
    sim = ExtractLayout(configPath)
    sim.run()


'''

import sys,os,re

from ..pyLayout import Layout
from ..definition.path import Path,Node
from ..common.common import log,writeJson,getParent,readData,writeData
from ..common.complexDict import ComplexDict
from .simConfig import SimConfig
log.info("Start ExtractLayout analyse, this progrom powered by Ansys AE.")

appPath = os.path.realpath(__file__)
appDir = os.path.split(appPath)[0] 
sys.path.append(appDir)

class ExtractBase(object):
    '''
    classdocs
    '''

    def __init__(self, simConfig, oDesktop = None):
        '''
        Constructor
        '''
        self._config = None
        self.layout = None
        self._config = SimConfig(simConfig)
        self.xmlPsiConfOut = None
        self.oDesktop = oDesktop
        
                
    @property
    def Config(self):
        return self._config

    def loadLayout(self):
        
        if "Import" not in self.Config:
            return
        
        Import = self.Config["Import"]

        if not Import["Enable"]:
            log.info("Import not enable.")
            return
  
        layoutPath = Import["LayoutPath"]
        edbOutPath = Import["EdbOutPath"]
        controlFile = Import["ControlFile"]
        layoutType = Import["LayoutType"]
        extractExePath = Import["extractExePath"]
        
        
        if layoutPath.lower().endswith(".aedt") and Import["SaveAs"]:
            #for multi-process, avoid aedt lock
            Layout.copyAEDT(layoutPath,Import["SaveAs"])
            self.layout.openAedt(Import["SaveAs"],unlock=True) #try to open with lock file
        else:
            #for brd, odb ... import
            self.layout.loadLayout(layoutPath, edbOutPath, controlFile, layoutType,extractExePath)
            if Import["SaveAs"]:
                self.layout.saveAs(Import["SaveAs"])

    def preConfig(self):

        #PortbyPins, {"PosPins":[],"NegPins":[],"CompName":null,"PosNet":null,"NegNet":null,"Name":null,"PortZ0":0.1}
        PortbyPins = self.Config["Ports"]["PortbyPins"]
        for group in PortbyPins:
            if not group["PosPins"]:
                if group["CompName"] and group["PosNet"]: 
                    group["PosPins"] = [pin.Name for pin in self.layout.Components[group["CompName"]].Pins if pin.Net.lower() == group["PosNet"].lower()]
                # else:
                #     log.exception("posPins or compName,posNet should be specified one")
            if not group["NegPins"]:
                if group["CompName"] and group["NegNet"]: 
                    group["NegPins"] = [pin.Name for pin in self.layout.Components[group["CompName"]].Pins if pin.Net.lower() == group["NegNet"].lower()]
                # else:
                #     log.exception("posPins or compName,posNet should be specified one")


    def loadStackup(self):
        '''
        - {Name: SURFACE,Type: signal, Material: copper, FillMaterial: M4 ,Thickness: 3.556e-05, Roughness: 0.5um,2.9 ,DK: 4,DF: 0.02, Cond: 5.8e7, EtchFactor: 2.5}
        - {Name: SURFACE,Type: dielectric, Material: M4 ,Thickness: 3.556e-05,DK: 4,DF: 0.02}
        '''
        if "Stackup" not in self.Config:
            return
        
        Stackup = self.Config["Stackup"]
        if not Stackup["Enable"]:
            log.info("Stackup not enable.")
            return
        
        materials = self.Config["Stackup/Matrials"]
        for name in materials.Keys:
            material = materials[name]
            material.update("Name",name)
            self.layout.Materials.add(material)
        
        if Stackup["Layers"]:
            self.layout.Layers.loadFromDict(Stackup["Layers"])
        else:
            log.info("Stackup layers is empty, skip.")

    def configComponents(self):
        
        if "Component" not in self.Config:
            return
        
        Component = self.Config["Component"]
        
        if not Component["Enable"]:
            log.info("Component not enable.")
            return
        
        models = Component["Models"]
        if not models:
            log.info("Component models is empty, skip.")
            return
        
        self.layout.Components.updateModels(models)
        

        
    def configNets(self):
        pass
    
    def cutoutDesign(self):
        '''
        Cutout:
          # NetInclude for net must be full included
          # PowerNet and GNDNet will be included and cut at boundary
          NetInclude: []
          NetClip: []
          KeepPowerNet: Yes
          Enable: True
          CutExpansion: 10mm

        '''

        if "Cutout" not in self.Config:
            return

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
            NetClip += [net for net in self.layout.Nets.PowerNetList if net not in NetInclude]
            
        if cutout["KeepOtherNets"]:
            NetClip += [net for net in self.layout.Nets.NameList if net not in NetInclude and net not in NetClip]
            
        if cutout["SubProjectName"]:
            newAedtPath = os.path.join(self.layout.projectDir,cutout["SubProjectName"])
            self.layout.saveAs(newAedtPath, True)
            
        self.layout.clip(self.layout.designName, NetInclude, NetClip, cutout["CutExpansion"], InPlace = True)

    def backdrill(self):
        if "Backdrill" not in self.Config:
            return
        if not self.Config["Backdrill"]["Enable"]:
            log.info("Backdrill not enable.")
            return
        if not self.Config["Backdrill"]["Nets"]:
            log.info("No backdrill nets set, PortOnNets value will be used.")
            self.Config["Backdrill"]["Nets"] = self.Config["Ports/PortOnNets"]

        Nets = self.layout.Nets.getRegularNets(self.Config["Backdrill"]["Nets"])
        stub = self.Config["Backdrill"]["Stub"]
        for net in Nets:
            self.layout.nets[net].backdrill(stub=stub)

    def clearLayout(self):
        if "ClearLayout" not in self.Config:
            return

        clearLayout = self.Config["ClearLayout"]  #return as ComplexDict()
        if not clearLayout["Enable"]:
            log.info("cutout not enable.")
            return
        
        # Net include
        KeepNet  = clearLayout["KeepNet"]
        if not KeepNet:  
            KeepNet = []

        if clearLayout["KeepNetWithPort"]:
            ports = self.Config["Ports"]
            #---PortOnNets
            if ports["PortOnNets"]:
            #create port on nets
                nets  = self.layout.Nets.getRegularNets(ports["PortOnNets"]) + self.layout.Nets.getRegularNets(ports["RefNets"]) 
                KeepNet += nets


            if ports["PortbyPins"]:
                pinNets = []
                startNode = None
                endNodes = []
                excludedNets = []
                
                for p in ports["PortbyPins"]:
                    #{"PosPins":[],"NegPins":[],"CompName":null,"PosNet":null,"NegNet":null,"Name":null,"PortZ0":0.1}{"PosPins":[],
                    # "NegPins":[],"CompName":null,"PosNet":null,"NegNet":null,"Name":null,"PortZ0":0.1}
                    for posPin in p["PosPins"]:
                        #PosPins and NegPins are preConfig
                        if not p["PosPins"] or not p["NegPins"]:
                            continue

                        if posPin not in self.layout.Pins:
                            continue
                        net = self.layout.Pins[posPin].Net
                        comp = self.layout.Pins[posPin].CompName
                        if net not in pinNets:
                            pinNets.append(net)
                        
                        if "Type"in p and "vrm" in p["Type"].lower():
                            startNode = [comp,net]
                            
                        if "Type"in  p and "sink" in p["Type"].lower():
                            endNodes.append([comp,net])
                        break
                            
                    for negPin in p["NegPins"]:
                        if negPin not in self.layout.Pins:
                            continue
                         
                        net = self.layout.Pins[negPin].Net
                        if net not in pinNets:
                            pinNets.append(net)
                            excludedNets.append(net)
                        break
                            
                KeepNet += pinNets

                #search other nets, just for PI 
                if startNode and endNodes:
                    path = Path(layout=self.layout)
                    path.startNode = startNode
                    path.endNodes = endNodes
                    path.excludedNets = excludedNets
                    path.search()
                    path.printTree()
                    KeepNet += path.nets
        
        
        KeepNet = list(set(KeepNet)) 
        RemoveNet = clearLayout["RemoveNet"]
        if RemoveNet:
            for net in RemoveNet:
                if net in KeepNet:
                    KeepNet.remove(net)
        removeNets = [net for net in self.layout.Nets.NameList if net not in KeepNet]
        log.info("Remove nets: %s"%removeNets)
        self.layout.Nets.deleteNets(removeNets)
    
    
        if "RemoveComponentConnectedNetsLessThen" in clearLayout:
            count =  int(clearLayout["RemoveComponentConnectedNetsLessThen"])
            if count>0:
                self.layout.Components.deleteInvalidComponents(clearLayout["RemoveComponentConnectedNetsLessThen"])
        self.layout.initDesign()
        
    def setPorts(self):
        
        if "Ports" not in self.Config:
            return
        
        ports = self.Config["Ports"]
        solderComps = []
        
        if not ports["Enable"]:
            log.info("ports not enable.")
            return
        
        #---solderBall befor port
        solderBall = ports["SolderBall"]
        if solderBall["Enable"]:
        #set solderball ratio
            ratio = solderBall["Ratio"]
            if ratio[0] !=None:
                self.layout.options["H3DL_solderBallHeightRatio"] = ratio[0]
            if ratio[1] !=None:
                self.layout.options["H3DL_solderBallWidthRatio"] = ratio[1]
                   
            nets  = self.layout.Nets.getRegularNets(ports["PortOnNets"])
            compNames = self.layout.Nets.getComponentsOnNets(nets, ignorRLC = not ports["PortOnRLC"])
            solderComps += compNames
            #---create solderball on components
            for name in solderComps:
                if name in solderBall:
                    size = solderBall[name]
                else:
                    size = solderBall["Default"][:] #copy to avoid modify self.Config
                    
                self.layout.Components[name].createSolderBall(size)
        
        
        #---PortOnNets
        if ports["PortOnNets"]:
        #create port on nets
            nets  = self.layout.Nets.getRegularNets(ports["PortOnNets"])
            compNames = self.layout.Nets.getComponentsOnNets(nets, ignorRLC = not ports["PortOnRLC"])
            self.layout.Nets.createPortsOnNets(nets, compNames)
#             solderComps += compNames
            
        #---PortbyPins
        if ports["PortbyPins"]:
            for p in ports["PortbyPins"]:
                #{"PosPins":[],"NegPins":[],"CompName":null,"PosNet":null,"NegNet":null,"Name":null,"PortZ0":0.1}{"PosPins":[],
                # "NegPins":[],"CompName":null,"PosNet":null,"NegNet":null,"Name":null,"PortZ0":0.1}
                #PosPins and NegPins are preConfig
                if not p["PosPins"] or not p["NegPins"]:
                    continue

                #posPins=None,refPins=None,compName=None,posNet=None,negNet=None,name=None,portZ0=0.1)
                temp = {"PosPins":[],"NegPins":[],"CompName":None,"PosNet":None,"NegNet":None,"Name":None,"PortZ0":0.1}
                temp.update(p)
                self.layout.Ports.addPinGroupPort(posPins=temp["PosPins"],refPins=temp["NegPins"],
                    compName=temp["CompName"],posNet=temp["PosNet"],negNet=temp["NegNet"],
                    name=temp["Name"],portZ0=temp["PortZ0"]) 
    
        #---PortbyPins
        portOrder = ports["OrderPorts"]
        if portOrder["Enable"]:
            self.layout.ports.reorder(compOrder=portOrder["CompOrder"],netOrder=portOrder["NetOrder"],portOrder = portOrder["PortOrder"])
        
    def createPinGroup(self):
        if "PinGroup" not in self.Config:
            return
        PinGroup = self.Config["PinGroup"]

        if not PinGroup["Enable"]: 
            log.info("PinGroup is disabled,skip.")
            return
        
        if not PinGroup["Groups"]:
            return

        for group in PinGroup["Groups"]:
            self.layout.PinGroups.createByGrid(group["Pins"],group["Name"],group["Rows"],group["Cols"])
            createByGrid(self,compName,shortPinList,groupName = None,rows = 1,cols = 1)

    def solveSetup(self):


        if "Setup" not in self.Config:
            return
        
        Setup = self.Config["Setup"]
        
        if not Setup["Enable"]:
            log.info("Setup not enable.")
            return

        setup1 = self.layout.Setups.add(Setup["Name"], Setup["SolutionType"])
#         datas = setup1.getData()
        for k,v in Setup["Options"].Dict.items():
            try:
                val = setup1[k]
            except:
                log.warning("key %s not found in %s"%(k,Setup["Name"]))
            else:
                setup1[k] = val.__class__(v)

        #for sweep datas
        if "Sweep" not in Setup:
            return
        
        Sweep = Setup["Sweep"]
        if not Sweep["Enable"]:
            log.info("Sweep not enable.")
            return
        
        sweep1 = setup1.addSweep(Sweep["Name"],sweepData=Sweep["Options"]["SweepData"]) #fix 3DL-siwave bug
#         datas = sweep1.getData()
        for k,v in Sweep["Options"].Dict.items():
            try:
                val = sweep1[k]
            except:
                log.warning("Sweep option %s not found."%k)
            else:
                sweep1[k] = val.__class__(v)

    def analyze(self):
#         tempPath = self.layout.ProjectPath
#         self.layout.submitJob(cores=20)
#         self.layout.openAedt(tempPath)
        
        if "Analysis" not in self.Config:
            return
        
        Analysis = self.Config["Analysis"]
        if not Analysis["Enable"]:
            log.info("Analysis not enable.")
            return
        
        setup = self.Config["Setup"] 
        if setup["Enable"]:
            setupName = setup["Name"] 
            sweepName = setup["Sweep/Name"]
        else:
            setups = self.layout.Setups
            if len(setups)<1:
                log.exception("layout don't have any analysis setup ...")
            
            setup = setups[0]
            setupName = setup.name
            sweepName = setup.Sweeps[0].name
        
        if "Cores" in Analysis and Analysis["Cores"]:
            self.layout.setCores(cores=Analysis["Cores"], hpcType=Analysis["HPCType"])
        
        log.info("Starting analysis for setup %s ..."%setupName)       
        self.layout.Setups[setupName].analyze()
        
        
        solution = self.layout.Solutions["%s:%s"%(setupName,sweepName)]
        if Analysis["ExportSNP"]:
            if not Analysis["SnpPath"] and self.Config["Header"]["Name"]:
                Analysis["SnpPath"] = os.path.join(self.layout.ProjectDir,self.Config["Header"]["Name"])
            solution.exportSNP(Analysis["SnpPath"])
            
    def run(self):
        '''
        workflow:
        
        laod PCB -> load stackup -> configComponents -> ConfigNets -> Cutout -> Port -> solveSetup -> Solve -> datas -> Post
        '''
        #write config file for debug
        layoutPath = self.Config["Import/LayoutPath"]
        configPath = layoutPath + ".json"
        self._config.writeJosn(configPath)

        #initial layout
#         self.layout = Layout("2022.2")
        version = self.Config["AEDT/Version"]
        installPath = self.Config["AEDT/InstallPath"]
        nonGraphical = self.Config["AEDT/NonGraphical"]
        UsePyaedt  = self.Config["AEDT/UsePyaedt"]
        NewSession  = self.Config["AEDT/NewSession"]

        #if version and installPath are null, least version will be initialized
        self.layout = Layout(version=version, installDir=installPath,nonGraphical=nonGraphical,newDesktop=NewSession,usePyAedt=UsePyaedt,oDesktop=self.oDesktop)
        self.layout.options["AEDT_WaitForLicense"] = self.Config["AEDT/WaitForLicense"]
        self.layout.options["AEDT_LicenseServer"] = self.Config["AEDT/LicenseServer"]
        self.layout.options["AEDT_KeepGUILicense"] = self.Config["AEDT/KeepGUILicense"]
        
        #---load layout file
        log.info("load layout file")
        self.loadLayout()
        self.layout.save()
        
        if not version:
            self.Config["AEDT/Version"] = self.layout.Version
            
        if not installPath:
            self.Config["AEDT/InstallPath"] = self.layout.InstallPath
        
        #---disable autoSave
        autoSave = self.layout.enableAutosave(False) 
        
        #---preConfig
        self.preConfig()

        #---load stackup
        log.info("load stackup file")
        self.loadStackup()
        self.layout.save()
        
        #ConfigNets
#         layout.configNets()
        #---cutout pcb to reduced simulaiton time
        log.info("cutout Design")
        self.cutoutDesign()
        self.layout.save()

        #---clear layout befor analysis
        log.info("clearLayout")
        self.clearLayout()
        self.layout.save()

        #---Component models
        log.info("configComponents")
        self.configComponents()
        self.layout.save()

        #---backdrill
        log.info("backdrill")
        self.backdrill()
        self.layout.save()

        #---create ports
        log.info("Create ports")
        self.setPorts()
        self.layout.save()

        #---solve frequency, sweep scope
        log.info("Add setup and sweep")
        self.solveSetup()
        self.layout.save()

        #---run the simution
        log.info("Run the simution")
        self.analyze()
        self.layout.save()
        
        #---quit Aedt
        self.layout.enableAutosave(autoSave)
        self.layout.close()
        self.layout.quitAedt()
        
#for test
if __name__ == '__main__':
    
#     configPath = os.path.join(appDir,r"snpExtract_galileo_brd.json")
    configPath = r"C:\work\Project\AE\Script\snp_extraction\test_from_users\test_004ED0_PCB.json"
    layout = Layout()
    layout.initDesign() #use exist aedt 
    sim = ExtractBase()
    sim.layout = layout
    sim.solveSetup()

    print("finished.")
    pass        
