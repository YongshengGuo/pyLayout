#--- coding=utf-8
#--- @Author: Yongsheng.Guo@ansys.com, Henry.he@ansys.com,Yang.zhao@ansys.com
#--- @Time: 20230410
"""
    Examples:
        >>> cmp = Component()
        >>> cmp["U1"]
        返回U1的Component对象
        
        >>> cmp[["U1","U2"]]
        返回U1,U2的Component对象List
        
        >>> cmp["U\d+"]
        返回"U\d+"匹配命名的Component对象List，匹配U1,U2,Uxxx
        
        >>> for c in layout.Components:
        >>>     log.debug(c.Name)
        打印PCB上所有的器件名字     


get component information from oEditor.GetComponentInfo API

"ComponentInfo":['ComponentName=U2', 'PartName=metal5_U2', 'ComponentType=Other', 'PlacementLayer=metal5', 
    "ComponentProp=ComponentProp(CompPropEnabled=true, Pid=-1, Pmo='0', CompPropType=2, 
    PinPairRLC(RLCModelType=0), SolderBallProp(sbsh='None', sbh='0', sbr='0', sb2='0', sbn=''), 
    PortProp(rh='0', rsa=true, rsx='0', rsy='0'))", 'LocationX=0', 'LocationY=0', 'BBoxLLx=0.002252728', 
    'BBoxLLy=0.00879525', 'BBoxURx=0.003799791', 'BBoxURy=0.0093079', 'Angle=0', 'Flip=false', 'Scale=1']
    
    BBox = (self._info["BBoxLLx"],self._info["BBoxLLy"],self._info["BBoxURx"],self._info["BBoxURy"])
"""


import re
import os
from itertools import groupby
from ..common import hfss3DLParameters
from ..common.arrayStruct import ArrayStruct
from ..common.complexDict import ComplexDict
from ..common.unit import Unit
from ..common.common import log
from ..definition.spiceModel import Subckt

from collections import Counter
from .primitive import Primitive,Primitives
from ..common.progressBar import ProgressBar

class Component(Primitive):
    '''

    Args:
        object (_type_): _description_
        
    Examples:
        >>> cmp = Component()
        >>> cmp["U1"]
        返回U1的Component对象
        
        >>> cmp[["U1","U2"]]
        返回U1,U2的Component对象List
        
        >>> cmp["U\d+"]
        返回"U\d+"匹配命名的Component对象List，匹配U1,U2,Uxxx
        
        >>> for c in layout.Components:
        >>>     log.debug(c.Name)
        打印PCB上所有的器件名字     
        
    '''

    def __init__(self,name = None,layout=None):
        '''Initialize Component object
        Args:
            compName (str): refdes of component in PCB, optional
            layout (PyLayout): PyLayout object, optional
        '''
        super(self.__class__,self).__init__(name,layout)




    def parse(self, force = False):
        if self.parsed and not force:
            return
        
        super(self.__class__,self).parse(force) #initial component properties
        
        comp = self.name
        componentInfo = self.layout.oEditor.GetComponentInfo(comp)
        maps = self.maps
        
        for k,v in filter(lambda x:len(x)==2,[i.split("=",1) for i in componentInfo]):
            self._info.update(k,v)
            
        self._info.update("BBox", (self._info["BBoxLLx"],self._info["BBoxLLy"],self._info["BBoxURx"],self._info["BBoxURy"]))
        
        
        #pins information will update when they used by self[]
        maps.update({"PinNames":{
            "Key":"self",
            "Get":lambda s:s.layout.oEditor.GetComponentPins(s.name)
            }})
        
        #pins 
        maps.update({"ShortPinNames":{
            "Key":"self",
            "Get":lambda s:[name.split("-")[-1] for name in s.layout.oEditor.GetComponentPins(s.name)]
            }})
        
        #pins objects
        maps.update({"Pins":{
            "Key":"self",
            "Get":lambda s:[s.layout.Pins[name] for name in s.layout.oEditor.GetComponentPins(s.name)]
            }})
        
        maps.update({"PinCount":{
            "Key":"self",
            "Get":lambda s:len(s.layout.oEditor.GetComponentPins(s.name))
            }})
        
        maps.update({"NetNames":{
            "Key":"self",
            "Get":lambda s: list(set([s.layout.Pins[p].Net for p in s.layout.oEditor.GetComponentPins(s.name)]))
            }})
        
        maps.update({"Nets":{
            "Key":"self",
            "Get":lambda s: [s.layout.Nets[name] for name in set([s.layout.Pins[p].Net for p in s.layout.oEditor.GetComponentPins(s.name)])]
            }})
        
        self._info.setMaps(maps)
        self.parsed = True


    def changePartType(self,type = "IO"):
        '''
        Args:
            typ (str, optional): Capacitor,Inductor,Resistor,IC,IO,Other . Defaults to "IO".
        '''

        self.layout.oEditor.ChangeProperty(
          [
            "NAME:AllTabs",
            [
              "NAME:BaseElementTab",
              [
                "NAME:PropServers"
              ]+[self.name],
              [
                "NAME:ChangedProps",
                [
                  "NAME:Part Type",
                  "Value:="    , type
                ]
              ]
            ]
          ])
        
        self.Info["ComponentType"] = type
        
    def createSolderBall(self,size = None ,solderMaterial = "solder", pecSize = ""):
        """
        size = Height,width,Mid
        size = ["14mil","14mil"] or [Auto,Auto]
        "SolderBallProp:=",["sbsh:=",typ,  "sbh:=",size[0],  "sbr:=",size[1],  "sb2:=",size[2],  "sbn:=",solderMaterial],
        
        """
        log.info("Create solderball on component: %s, size: %s"%(self.name,str(size)))
        
        #20250718
        if size==None or str(size[0]).lower()=="auto" or str(size[1]).lower()=="auto":
            bbox = self.Pins[0].BBox
            diameter = min(abs(bbox[1].X-bbox[0].X),abs(bbox[1].Y-bbox[0].Y))
            size2 = [(Unit(diameter)*self.layout.options["H3DL_solderBallHeightRatio"])["mm"],(Unit(diameter)*self.layout.options["H3DL_solderBallWidthRatio"])["mm"]] #Height 0.66x from solder, width 0.8x from aedt
            #20231106 for [Auto,Auto]

            if size==None:
                size = size2
                log.info("Create solderball on component: %s, size: %s"%(self.name,str(size)))
            elif isinstance(size,(list,tuple)):
                if size[0].lower()=="auto" :
                    size[0] = size2[0] 
                    
                if size[1].lower()=="auto" :
                    size[1] = size2[1] 
            else:
                log.info("solderball size error, Create solderball use default value: %s, size: %s"%(self.name,str(size)))
                size = size2
                
            log.info("Create solderball on component: %s, size: %s"%(self.name,str(size)))

#             pskNames = []
#             for pin in self.Pins: #[:20]
#                 pskNames.append(pin["Padstack Definition"])
            
#             count = Counter(pskNames)
#             pskName = count.most_common(1)[0][0] #find most padstack
#             psk = self.layout.PadStacks[pskName]
#             layerName = self["PlacementLayer"]
#             try:
#                 pskl = psk[layerName]
#             except:
#                 pskl = ArrayStruct(psk["psd/pds"][1])
                
#             shp = pskl.pad.shp
#             szs = pskl.pad.Szs

#             size1 = 0
#             if shp == "Rct":
#                 size1 = (Unit(szs[0])).V if (Unit(szs[0])).V< (Unit(szs[1])).V else (Unit(szs[1])).V
#             elif  shp == "Cir":
#                 size1 = (Unit(szs[0])).V
#             elif  shp == "Sq":
#                 size1 = (Unit(szs[0])).V
#             else:
#                 log.exception("pad shape unknown: %s"%shp)
            
            
# #             size2 = [(Unit(size1)*0.7)["mm"],(Unit(size1)*0.6)["mm"]] #Height 0.7x from solder, width 0.6x from aedt
#             size2 = [(Unit(size1)*self.layout.options["H3DL_solderBallHeightRatio"])["mm"],(Unit(size1)*self.layout.options["H3DL_solderBallWidthRatio"])["mm"]] #Height 0.7x from solder, width 0.6x from aedt
            
#             #20231106 for [Auto,Auto]
#             if size[0].lower()=="auto" :
#                 size[0] = size2[0] 
                
#             if size[1].lower()=="auto" :
#                 size[1] = size2[1] 
                
#             if size==None:
#                 size = size2
#                 log.info("Create solderball on component: %s, size: %s"%(self.name,str(size)))

        
        
        ary = ArrayStruct(hfss3DLParameters.solderBall).copy()
        solder = ary["BaseElementTab/ChangedProps/Model Info/Model/IOProp/SolderBallProp"]
        
        if len(size) == 2:
            solder["sbsh"] = "Cyl"
            solder["sbh"] = size[0]
            solder["sbr"] = size[1]
            solder["sb2"] = size[1]
            solder["sbn"] = solderMaterial
            ary["BaseElementTab/ChangedProps/Model Info/Model/IOProp/SolderBallProp/sbn"] = solderMaterial
            
        if len(size) == 3:
            solder["sbsh"] = "Sph"
            solder["sbh"] = size[0]
            solder["sbr"] = size[1]
            solder["sb2"] = size[2]
            solder["sbn"] = solderMaterial

        PropServers = ary["BaseElementTab/PropServers"]
        PropServers.Array[1] = self.name
        #change the type to IO
        self.changePartType("IO")
        self.layout.oEditor.ChangeProperty(ary.Array)

    
    def addSnpModel(self,path,pinMap=None):
        '''
        bug: model can't be update twice
        '''
        
        # model->ComponentDefs->Part
        log.info("Add touchstone model to component '%s': %s"%(self.name,path))
        modelName = self.part + "_" + os.path.basename(path)# + "_1"
        modelName = re.sub("[\.\s#]","_",modelName) #replace illegal character
        relPath = self.layout.getRelPath(path)
        nodes = []
        pinNames = []
        if pinMap:
            splits = pinMap.split(":")
            if len(splits) == 1:
                #only nodes given
                nodes = [s.strip() for s in splits[0].split()]
                pinNames = None
            elif len(splits) > 1:
                nodes = [s.strip() for s in splits[0].split()]
                pinNames = [s.strip() for s in splits[1].split()]
            else:
                log.error("Invalid pinMap %s"%pinMap)

            if not nodes:
                portCount = int(re.sub(r"[A-Za-z]","",path.split(".")[-1]))
                nodes = ["Port%s"%(n+1) for n in range(portCount) ]
            if not pinNames:
                pinNames = self.ShortPinNames

            if len(nodes) != len(pinNames):
                log.exception("pin count not match with subckt node.")
            
        self.changePartType(type="Capacitor") #must change to RLC for 2025R1 now
        self.layout.modelDefs.addSnpModel(relPath,name=modelName,pinMap=[nodes,pinNames])
        self.layout.ComponentDefs.addSNPDef(self.part,modelName,pinMap=[nodes,pinNames]) #Edit part model

        self.layout.oEditor.ChangeProperty(
            [
                "NAME:AllTabs",
                [
                    "NAME:BaseElementTab",
                    [
                        "NAME:PropServers",  self.name
                    ],
                    [
                        "NAME:ChangedProps",
                        [
                            "NAME:Model Info",
                            "ExtraText:=", "",
                            [
                                "NAME:Model",
                                "RLCProp:=", ["CompPropEnabled:=", True,"Pid:=", -1,"Pmo:=", "0","CompPropType:=", 0, 
                                "PinPairRLC:=", ["RLCModelType:=", 1,    "NetRef:=", "GND",    "CosimDefintion:=", modelName]],
                                "CompType:=", 3
                            ]
                        ]
                    ]
                ]
            ])
        
        
    def addSpiceModel(self,path,pinMap=None):
        '''_summary_

        Args:
            path (_type_): _description_
            pinMap: "nodes:pinNames"
        
        Note: must change component to RLC components before add spice model
        '''

        log.info("Add spice model to component '%s': %s"%(self.name,path))
        modelName = self.part + "_" + os.path.basename(path)
        modelName = re.sub("[\.\s#]","_",modelName) #replace illegal character
        
        relPath = self.layout.getRelPath(path)
        
        if not pinMap:
            nodes = None
            pinNames = None
        else:
            splits = pinMap.split(":")
            if len(splits) == 1:
                #only nodes given
                nodes = [s.strip() for s in splits[0].split()]
                pinNames = None
            elif len(splits) > 1:
                nodes = [s.strip() for s in splits[0].split()]
                pinNames = [s.strip() for s in splits[1].split()]
            else:
                log.error("Invalid pinMap %s"%pinMap)
        sp = Subckt(path)
        if not nodes:
            nodes = sp.nodes
        if not pinNames:
            pinNames = self.ShortPinNames

        if len(nodes) != len(pinNames):
            log.exception("pin count not match with subckt node.")

        #---add model
#         self.layout.modelDefs.addSpiceModel(relPath,name=modelName) #no need, will cause error
        self.changePartType(type="Capacitor")

    
        nodeArray = []
        for i in range(len(nodes)):
            nodeArray.append("%s:="%nodes[i])
            nodeArray.append(pinNames[i])

        self.layout.oEditor.UpdateModels(
            [
                "NAME:ModelChanges",
                [
                    "NAME:UpdateModel0",
                    [
                        "NAME:ComponentNames", self.name
                    ],
                    "Prop:=", ["CompPropEnabled:=", True,"Pid:=", -1,"Pmo:=", "0","CompPropType:=", 0,
                        "PinPairRLC:=", ["RLCModelType:=", 4,"SPICE_file_path:=", relPath,
                        "SPICE_model_name:=", modelName,"SPICE_subckt:=", sp.name,"terminal_pin_map:=", nodeArray]]
                ]
            ])
            
    def addModel(self,path=None,R=None,L=None,C=None,parallel=False,pinMap=None):
        
        if path:
            snp = path.split(".")[-1]
            if re.match(r"s\d+p", snp,re.IGNORECASE):
                self.addSnpModel(path,pinMap)
            else:
                self.addSpiceModel(path,pinMap)
        elif R or L or C:
            self.addRLCModel(R=R,L=L,C=C,parallel=parallel)
        else:
            log.exception("input model error for component: %s."%self.name)
    
    def addRLCModel(self,R=None,L=None,C=None,parallel=False):
        '''
        Args:
            rlc(list): RLC value [r,l,c]
            layerNum: the number of the component palcement layer (e.g. Top = 2 if slodermask exist)
        '''
        
        log.info("Add RLC model to component '%s': R:%s L:%s, C:%s"%(self.name,R,L,C))
        if len(self.PinNames) != 2:
            log.error("RLC Model only support two pins RLC Component: %s have %s pins, will skip."%(self.name,len(self.PinNames)))
            return
        
        if self.PartType not in ["Resistor","Inductor","Capacitor"]:
            log.error("RLC Model only support RLC Part Type: %s Part type is %s, will skip."%(self.name,len(self.PartType)))
            return
                    
        self.layout.oEditor.ChangeProperty(
            [
                "NAME:AllTabs",
                [
                    "NAME:BaseElementTab",
                    [
                        "NAME:PropServers", self.name
                    ],
                    [
                        "NAME:ChangedProps",
                        [
                            "NAME:Model Info",
                            [
                                "NAME:Model",
                                "RLCProp:=", ["CompPropEnabled:=", True,                            
                                "Pid:=", -1,                            
                                "Pmo:=", "0",                            
                                "CompPropType:=", 0,                            
                                "PinPairRLC:=", ["RLCModelType:=", 0,                                
                                 "ppr:="    , ["p1:=", "1","p2:=", "2","rlc:=", 
                                    ["r:=", str(R) if R else "0",                                        
                                     "re:=", True if R != None else False,
                                     "l:=", str(L) if L else "0",                                      
                                     "le:=", True if L != None else False,
                                     "c:=", str(C) if C else "0",                                    
                                     "ce:=", True if C != None else False,
                                     "p:=", parallel,                                        
                                     #"lyr:=", layerNum
                                    ]]]],
                                "CompType:="        , ["Resistor","Inductor","Capacitor"].index(self.PartType)+1
                            ]
                        ]
                    ]
                ]
            ])

    def addLibraryModel(self,vendor=None,series=None,libraryPart=None,path=None):
        
        if path:
            LibraryModelPath = path
            LibraryModelPart = os.path.splitext(os.path.basename(path))[0]
        elif vendor and  series and libraryPart:
            LibraryModelPath = os.path.join(self.layout.installDir,"complib","Locked",self.PartType,vendor,series,"sdata.bin")
            LibraryModelPart = libraryPart
        
        self.layout.oEditor.ChangeProperty(
            [
                "NAME:AllTabs",
                [
                    "NAME:BaseElementTab",
                    [
                        "NAME:PropServers", 
                        self.name
                    ],
                    [
                        "NAME:ChangedProps",
                        [
                            "NAME:Model Info",
                            [
                                "NAME:Model",
                                "RLCProp:="        , ["CompPropEnabled:="    , True,"Pid:=", -1,"Pmo:=", "0","CompPropType:="    , 0,
                                "PinPairRLC:="        , [    "RLCModelType:="    , 3,    "NetRef:="        , "GND",    
                                "LibraryModelPath:="    , LibraryModelPath,    
                                "LibraryModelPart:="    , LibraryModelPart,    "LibraryNominalValue:="    , 1E-12]],
                                "CompType:="        , 3
                            ]
                        ]
                    ]
                ]
            ])
        


    
    def createPinGroup(self,pinNames = None, net = None,groupName = None):
        '''
        pins(list)
        '''
        if not groupName:
            pin0 = self.layout.Pins[pinNames[0]]
            groupName = "PinGroup_%s_%s"%(pin0.Net,pinNames[0])

        if not pinNames: 
            if net:
                pinNames = [p.Name for p in self.Pins if p.Net.lower() == net.lower()]
            else:
                log.exception("pinNames or net can't be None")
            
        CompPinNames = self.PinNames
        pins2 = []
        for pin in pinNames:
            if pin in CompPinNames:
                pins2.append(pin)
            else:
                print("pin %s not found on component %s"%(pin,self.name))

        self.layout.oEditor.CreatePinGroups(
            [
                "NAME:PinGroupDatas",
                [
                    "NAME:%s"%groupName, 
                ] + pins2
            ])
        
        self.layout.PinGroups.push(groupName,self.layout.PinGroups.definitionCalss(groupName,pins2,self.layout))
        
    def _gridPins(self,pins,rows,cols):

        # 定义网格的列数和行数
#         cols = 20
#         rows = 20

        # 计算x和y的最小最大值
        x_values = [pin.X for pin in pins]
        y_values = [pin.Y for pin in pins]
        x_min, x_max = min(x_values), max(x_values)
        y_min, y_max = min(y_values), max(y_values)

        # 生成网格边界
        x_bins = [x_min + i * (x_max - x_min) / cols for i in range(cols + 1)]
        y_bins = [y_min + i * (y_max - y_min) / rows for i in range(rows + 1)]

        # 定义一个函数，计算某个值属于哪个网格
        def get_bin_index(value, bins):
            for i in range(len(bins) - 1):
                if bins[i] <= value < bins[i + 1]:
                    return i
            return len(bins) - 2  # 处理最大值的情况（右边界）

        # 分配每个坐标到网格
        grid_assignment = {}
        for pin in pins:
            col = get_bin_index(pin.X , x_bins)
            row = get_bin_index(pin.Y, y_bins)

            key = "%s_%s" % (col, row)  # 创建键
            if key in grid_assignment:
                grid_assignment[key].append(pin)
            else:
                grid_assignment[key] = [pin]
        return grid_assignment

    def createGridPinGroup(self,pinNames,nets=None,groupName = None,rows = 1,cols = 1):

        if isinstance(nets,str):
            nets = [nets]

        pinList = []
        if pinNames:
            for name in pinNames:
                if name in self.layout.Pins:
                    pinList.append(self.layout.Pins[name])
                else:
                    log.info("Pin %s not exist,skip"%name)
                    continue
      
        grid_assignment = self._gridPins(pinList,rows,cols)
        for k,v in grid_assignment.items():
            sorted_data = sorted(v, key=lambda x: x.Net)
            grouped_data = groupby(sorted_data, key=lambda x: x.Net) 
            for netName, netPins in grouped_data:
                log.info("Create PinGroup, component:%s Net:%s Grid:%s"%(self.name,netName,k))
                groupName = "PinGroup_%s_%s"%(netName,self.Name)
                pinNames = [p.Name for p in netPins]
                self.createPinGroup(pinNames,groupName = groupName+"_"+k)

    def createPinGroupByNets(self,nets,rows = 1,cols = 1):

        if isinstance(nets,str):
            nets = [nets]

        pinList = []
        for net in nets:
            pins = [p for p in self.Pins if p.Net.lower() == net.lower()]
            if pins:
                pinList.extend(pins)

        grid_assignment = self._gridPins(pinList,rows,cols)
        for k,v in grid_assignment.items():
            sorted_data = sorted(v, key=lambda x: x.Net)
            grouped_data = groupby(sorted_data, key=lambda x: x.Net) 
            for netName, netPins in grouped_data:
                log.info("Create PinGroup, component:%s Net:%s Grid:%s"%(self.name,netName,k))
                groupName = "PinGroup_%s_%s"%(netName,self.Name)
                pinNames = [p.Name for p in netPins]
                self.createPinGroup(pinNames,groupName=groupName+"_"+k)

              
    def createPinGroupOnNet(self,net, groupName=None):
        '''
        pins(list)
        '''
        return self.createPinGroup(net=net,groupName=groupName)

    
    def deletePinGroup(self,groupName):
        self.layout.oEditor.Delete([groupName])
        self.layout.PinGroups.pop(groupName)


    def createPinGroupPort(self,posGroup,refGroup,portZ0 = "0.1ohm"):
        '''
        posGroup is port Name
        return portName
        '''
        
        self.layout.oEditor.CreatePinGroupPort(
            [
                "NAME:elements",posGroup,
                [
                    "NAME:Boundary Types", 
                    "Port"
                ],
                [
                    "NAME:Magnitudes", 
                    str(portZ0)
                ]
            ])
        self.layout.oEditor.AddPinGroupRefPort([posGroup], [refGroup])
        return posGroup

    def createPinGroupPortByNet(self,posNet,refNet,portZ0 = "0.1ohm"):
        '''
        Port_posNet is port Name
        '''
        posGroup = self.createPinGroupOnNet(posNet,"Port_%s"%posNet)
        refGroup = self.createPinGroupOnNet(refNet,"Port_%s"%refNet)
        return self.createPinGroupPort(posGroup, refGroup, portZ0)

    def createPortOnNets(self,nets):
        '''
        create port on each pin of nets.
        '''
        if isinstance(nets, str):
            nets = [nets]
            
        self.layout.oEditor.CreatePortsOnComponentsByNet(
            ["NAME:Components",self.name],["NAME:Nets"]+nets, "Port", "0", "0", "0")

    def removeAllPorts(self):
        self.layout.oEditor.RemovePortsOnComponents(
            [
                "NAME:elements", 
                self.Name
            ])
    
    def exportPloc(self,path=None):
        #41963 -0.980560 3.153650 CHIP_LAYER VSS CCD_U0_CCD_VSS_41963
        #pinName X Y Layer NetName Group
        if not path:
            path = os.path.join(self.layout.ProjectDir,self.layout.DesignName+"_"+ self.Part + "_" + self.Name+".ploc")
        
        lines = []
        for pin in self.Pins:
#             print(pin.Name)
            pos = pin.Location
            lines.append(" ".join([pin.Name,str(pos.xvalue*1e6),str(pos.yvalue*1e6),self.PlacementLayer,pin.Net])) #PLOC default unit um
        txts = "# VERSION 1.0" + "\n"
        txts += "#This is generated by pyLayout.\n"
        txts += "#From 3D Layout Project: %s, Design: %s "%(
            self.layout.ProjectName,self.layout.DesignName)   + "\n"
        txts += "#Part: %s, Component: %s"%(self.Part,self.Name) + "\n"
        txts += "\n".join(lines)
        log.info("export %s ploc to %s"%(self.name,path))
        with open(path,"w") as f:
            f.write(txts)
            f.close()
            
    def hasPin(self,pinName):
        for pin in self.PinNames:
            if pin.lower() == pinName.lower():
                return True
        return False
    
    def dissolve(self):
        self.layout.oEditor.DissolveComponents(["NAME:elements",self.Name])
        self.layout.Components.pop(self.Name)
        
    def delete(self):
        self.layout.oEditor.Delete([self.Name])
        self.layout.Components.pop(self.Name)
        

#not use
class Components(Primitives):
#     layout=None
    
    def __init__(self,layout=None):
        super(self.__class__,self).__init__(layout, type="component",primitiveClass=Component)

        
    def importBOM(self,csvfile):
        pass
    
    
    def getComponentsByPart(self,part):
        '''
        Args:
            part (str): part name in PCB, ingor case, support regex
        Returns:
            (Component): Component object 
            
        Raises:
            part not found on PCB
        '''
        comps = []
        try:
            comps = [c for c in self.ObjectDict if re.match(part,c.Part,re.IGNORECASE)]
        except:
            log.debug("getComponentsByPart regex error: %s,try to get use string compare"%part)
            comps = [c for c in self.ObjectDict if c.Part.lower() == part.lower()]

        return comps
    

    def deleteInvalidRLC(self):
        '''
        if rlc have only one pin, will delete
        '''
        delComps = []
        for comp in self:
            if comp.PartType in ["Capacitor","Inductor","Resistor"] and len(comp.netnames)<2:
                log.info("Remove invalid RLC: %s, Pin Count %s"%(comp.Name,len(comp.PinNames)))
                #comp.delete()
                log.debug("delete invalid RLC: %s"%comp.Name)
                delComps.append(comp.Name)
            
        self.layout.oEditor.DissolveComponents(delComps)
        self.refresh()
        
    def deleteInvalidComponents(self,ConnectedNetsLessThen = 1):
        '''
        if component have only 1 pin, will delete
        '''
        delComps = []
        for comp in self:
            if len(comp.netnames)<=ConnectedNetsLessThen:
                log.info("Remove invalid Component: %s, Net Count %s"%(comp.Name,len(comp.netnames)))
                #comp.delete()
#                 log.debug("delete invalid RLC: %s"%comp.Name)
                delComps.append(comp.Name)
                
        if not delComps:
            return
        
#         self.layout.oEditor.DissolveComponents(delComps)
        self.layout.oEditor.Delete(delComps) #oEditor.Delete(["R440", "R442", "R443"])
        self.refresh()
        
        
    def getUniqueName(self,prefix="U"):
        for i in range(1,10000):
            name = "%s%s"%(prefix,i)
            names = self.NameList
            if name in names:
                i += 1
            else:
                break
        return name
    
    def createByPins(self,pinList,layerName=None,compName=None):
        if len(pinList)<1:
            return None
        
        if not layerName:
            layerName = self.layout.Pins[pinList[0]]["Start Layer"]
        else:
            layerName = self.layout.Layers[layerName].name
        
        if not compName:
            compName = self.getUniqueName()
            
        compDefName = '%s_%s'%(layerName,compName)
        log.info("Component '%s' will created on layer '%s', with pins %s"%(compName,layerName,len(pinList)))

        self.layout.oEditor.CreateComponent(
            [
                "NAME:Contents",
                "isRCS:="        , True,
                "definition_name:="    , compDefName,
                "type:="        , "Other",
                "ref_des:="        , compName,
                "placement_layer:="    , layerName,
                "elements:=", pinList
            ])        
        self.push(compName)
        return compName
    
    def createResistor(self,points,R=50,L=None,C=None,padR="1um"):
        pass
        
    
    def updateModels(self,models):
        #[{"RefDes":"","Part":"cap1","PartType":"Capacitor","FileName":null,"R":null,"L":null,"C":null,"Library":null}]
        
        modelList = []
        tempList = []
        for model in models:
            if not ( model["FileName"].strip() or model["R"].strip() or model["C"].strip() or model["L"].strip()):
                #if no model file, no R, no C, no L, will skip
                continue

            if model["RefDes"].strip(): 
                #if Refdes hass value, will add model
                refs = re.split("[\s,;]+",model["RefDes"])
                for ref in refs:
                    if not ref:
                        continue
                    if ref in tempList:
                        continue

                    model2 = model.copy()
                    model2["RefDes"] = ref
                    tempList.append(ref)
                    modelList.append(model2)
            elif model["Part"].strip():
                for ref in self.getComponentsByPart(model["Part"]):
                    if ref in tempList:
                        continue
                    model2 = model.copy()
                    model2["RefDes"] = ref
                    tempList.append(ref)
                    modelList.append(model2)
            else:
                log.warning("Component model has no RefDes or Part, will skip")                         

        #---model by refdes
        bar = ProgressBar(len(modelList),"Add component models:")
        for each in modelList:
            bar.showPercent()
            #{"RefDes":"","Part":"cap1","PartType":"Capacitor","FileName":null,"R":null,"L":null,"C":null,"Library":null}
            #RefDes,Part,PartType,FileName,Library,R,L,C
            # model>library>rlc
            model = ComplexDict(each)
            refdes = model.Refdes
            
            if refdes not in self:
                log.info("Component %s not in layout, skip."%refdes)
                continue
            
            comp = self[refdes]
            #change part type
            if model.PartType.lower() != comp.PartType.lower():
                comp.changePartType(model.PartType)
            
            if model.FileName:
                if not os.path.isabs(model.FileName):
                    model.FileName = os.path.join(self.layout.ProjectDir,"Model",model.FileName)
                comp.addModel(model.FileName)
                
            elif "Library" in model and model.Library:
                splits = re.split(r"[;,]", model.Library)
                if len(splits) == 1:
                    comp.addLibraryModel(path = splits[0])
                elif len(splits)>2:
                    comp.addLibraryModel(vendor = splits[0],series=splits[1],libraryPart=splits[2])
                else:
                    log.info("Library model error: %s"%model.Library)
                    continue                  
                
            elif model.R or model.L or model.C:
                comp.addModel(R=model.R,L=model.L,C=model.C)
                
            else:
                log.info("model error: %s"%str(model))
        
        bar.stop()

    def findComponentByPin(self,pinName):
        for component in self.All:
            if component.hasPin(pinName):
                return component
        return None