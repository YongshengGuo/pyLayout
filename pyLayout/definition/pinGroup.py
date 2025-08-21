#--- coding=utf-8
#--- @Author: Yongsheng.Guo@ansys.com, Henry.he@ansys.com,Yang.zhao@ansys.com
#--- @Time: 20230410



'''Net Object quick access

Examples:
    Get Net using full Net Name
    
    >>> Net["DQ0"]
    Net object
    
    Get Net using regular
    
    >>> Net["DQ\d+"]
    Net object list

    
    Get Net using regular
    
    >>> Net["DQ\d+"]
    Net object list
    
    Get Net using bus
    
    >>> Net["DQ[7:0]"]
    Net object list
    
    Get Net using bus and regular
    
    >>> Net["CH\d+_DQ[7:0]"]
    Net object list
    
'''


import re
from ..common.common import log
from ..common.unit import Unit
from ..common.complexDict import ComplexDict
from ..common.arrayStruct import ArrayStruct
from .definition import Definitions,Definition

class PinGroup(Definition):
    '''_summary_
    '''
    def __init__(self, name = None,pinNames = None,layout = None):
        super(self.__class__,self).__init__(name,type="PinGroup",layout=layout)
        self._info.update("PinNames",pinNames)
    

    def parse(self,force = False):
        '''
        mapping key must not have same value with maped key.
        '''
        
        if self.parsed and not force:
            return
        maps = self.maps
        _array = ArrayStruct([])
        self._info.update("Name",self.name)
        self._info.update("Array", _array)
        maps.update({"PinCount":{
            "Key":"self",
            "Get":lambda s:len(s.PinNames)
            }})

        maps.update({"CompName":{
            "Key":"self",
            "Get":lambda s:s.layout.Pins[s.PinNames[0]].CompName
            }})

        self._info.setMaps(maps)
        self._info.update("self", self)
        self.parsed = True
    
    def hasPin(self,pinName):
        for pin in self.PinNames:
            if pin.lower() == pinName.lower():
                return True
        return False
        

class PinGroups(Definitions):

    def __init__(self,layout=None):
        super(self.__class__,self).__init__(layout, type="PinGroup",definitionCalss=PinGroup)

#     def _getDefinitionDict(self):
#         return  ComplexDict(dict([(name,Net(name,self.layout)) for name in self.layout.oEditor.GetNetClassNets('<All>')]))

    @property
    def DefinitionDict(self):
        if self._definitionDict == None:
            groupDict = self.getExistGroupInfoFromEdb()
            self._definitionDict  = ComplexDict(dict([(name,self.definitionCalss(name,groupDict[name],self.layout)) for name in groupDict]))
#             self._definitionDict  = self._getDefinitionDict()
        return self._definitionDict

    def getExistGroupInfoFromEdb(self):
        from ..edb.edbApp import EdbApp
        edbApp = EdbApp(edbpath= self.layout.edbPath ,installDir=self.layout.installDir)
        groupDict = {}
        for group in edbApp.PinGroups.All:
            groupDict[group.Name] = group.PinNames
        edbApp.close()
        return groupDict
    
    def findPinGroupByPin(self,pinName):
        for group in self.All:
            if group.hasPin(pinName):
                return group
        return None

    def createByPins(self,pinList=None,compName=None,groupName = None):
        
        if not pinList:
            log.info("pinList is empty,skip")
            return ""

        if compName and compName not in pinList[0]:
            # short Pin Name
            pinList = ["%s-%s"%(compName,p) for p in pinList]
        else:
            # full Pin Name
            pass

        if not groupName:
            pin0 = self.layout.Pins[pinNames[0]]
            groupName = "PinGroup_%s_%s"%(pin0.Net,pinNames[0])

        self.layout.oEditor.CreatePinGroups(
                [
                    "NAME:PinGroupDatas",
                    [
                        "NAME:%s"%groupName, 
                    ] + pinList
                ])
            
        self.push(groupName,self.definitionCalss(groupName,pinList,self.layout))


    def createByGrid(self,pinList,compName,nets=None,groupName = None,rows = 1,cols = 1):
        
        if not compName:
            log.exception("CompName must definition before create pingroup.")
        
        if isinstance(nets,str):
            nets = [nets]

        pinList = []
        Pins = self.layout.Components[compName].Pins
        for net in nets:
            pins = [p for p in Pins if p.Net.lower() == net.lower()]
            if pins:
                pinList.extend(pins)
        grid_assignment = self.layout.Components[compName]._gridPins(pinList,rows,cols)

        for k,v in grid_assignment.items():
            sorted_data = sorted(v, key=lambda x: x.Net)
            grouped_data = groupby(sorted_data, key=lambda x: x.Net) 
            for netName, netPins in grouped_data:
                log.info("Create PinGroup, component:%s Net:%s Grid:%s"%(self.name,netName,k))
                groupName = "PinGroup_%s_%s"%(netName,self.Name)
                pinNames = [p.Name for p in netPins]
                self.createPinGroup(pinNames,groupName = groupName+"_"+k)
        

    def deletePinGroup(self,groupName):
        self.layout.oEditor.Delete([groupName])

    def createByDict(self,gDict):
        '''_summary_

        Args:
            gDict (_type_): {"Name":"","Component":"","Pins":[],"Net":"","Rows":1,"Cols":1}]
        '''

        if not ("Component" in gDict and gDict["Component"]):
            log.error("Component name is required")
            return

        pinList = None
        if "Pins" in gDict and gDict["Pins"]:
            pinList = ["%s-%s"%(gDict["Component"],p) for p in gDict["Pins"]]
        elif "Net" in gDict and gDict["Net"]:
             pinList = [pin.Name for pin in self.layout.Components[gDict["Component"]].Pins if pin.Net.lower() == gDict["Net"].lower()]
        else:
            log.exception("Pins or Net is required")

        if not pinList: 
            log.info("No pins found to create pinGroup, skip.")
            return

        if "Rows" in gDict and gDict["Rows"]:
            Rows = int(gDict["Rows"])
        else:
            Rows = 1
        if "Cols" in gDict and gDict["Cols"]:
            Cols = int(gDict["Cols"])
        else:
            Cols = 1
        
        if "Net" not in gDict or not gDict["Net"]: 
            gDict["Net"] = self.layout.Pins[pinList[0]].Net

        if Rows>1 or Cols>1:
            pass
        else:
            if "Name" not in gDict or gDict["Name"]=="":
                gDict["Name"] = "PinGroup_%s_%s"%(gDict["Net"],pinList[0])
            self.layout.Components[gDict["Component"]].createPinGroup(gDict["Name"],pinList)
