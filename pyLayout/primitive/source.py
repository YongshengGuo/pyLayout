#--- coding:utf-8
#--- @Author: Yongsheng.Guo@ansys.com, Henry.he@ansys.com,Yang.zhao@ansys.com
#--- @Time: 2023-04-24

'''
Ports manager module
'''

import re
from ..common import hfss3DLParameters
from ..common.arrayStruct import ArrayStruct
from ..common.complexDict import ComplexDict
from .geometry import Point
from ..common.unit import Unit
from ..common.common import log

from .primitive import Primitive,Primitives
from .geometry import Point


class Source(Primitive):

        
    def parse(self, force = False):
        if self.parsed and not force:
            return
        
        super(self.__class__,self).parse(force) #initial component properties
        
        maps = self.maps
        EMProperties = self.layout.oEditor.GetProperties("EM Design","Sources:%s"%self.Name)
        self._info.update("EMProperties",EMProperties)
        for prop in EMProperties:
            self._info.update(prop,None) #here give None value. get property value when used to improve running speed
            maps.update({prop.replace(" ",""):prop}) #map property with space characters

        #---prot infomation
        for item in self.layout.oEditor.GetPortInfo(self.name):
            splits = item.split("=",1)
            if len(splits) == 2:
                self._info.update(splits[0].strip(),splits[1].strip())
            else:
                log.debug("ignor port information: %s"%item)
        
        self._info.setMaps(maps)
        
    def get(self, key):
        
        if not self.parsed:
            self.parse()
        
        realKey = key
        
        if realKey in self._info.EMProperties:  #value is None
            self._info.update(realKey, self.layout.oEditor.GetPropertyValue("EM Design","Sources:%s"%self.Name,realKey))
            return self._info[realKey]
        
        return super(self.__class__,self).get(realKey)
    
    
    
    def set(self,key,value):
        '''
        mapping key must not have same value with maped key.
        '''
        
        
        if not self.parsed:
            self.parse()
        
        realKey = self._info.getReallyKey(key)
            
        if realKey in self._info.EMProperties: 
            self.layout.oEditor.SetPropertyValue("EM Design", "Sources:" + self.Name, realKey, value)
            self._info[realKey] = value
            if realKey == "Source": #Remane port name
                self.layout.Sources.refresh()
            return 1
#             self.parsed = False #refresh

        return super(self.__class__,self).set(key,value)
     
    def setPortImpedance(self,value):
        self.set("Impedance", str(value))
        try:
            self.set("Renormalize Impedence", str(value))
        except:
            self.set("Renormalize Impedance", str(value))
        
    def setSIwavePortRefNet(self,value):
        self.set("Reference Net", str(value))
        
        
    def autoRename(self):
        if "." in self.Name:
            log.info("skip port: %s"%self.Name)
            return
            
        ConnectionPoints = self.ConnectionPoints #0.000400 0.073049 Dir:270.000000 Layer: BOTTOM    
        if not ConnectionPoints or ConnectionPoints=='NONE':
            log.info("Port %s not a 3DL port, skip."%self.Name)
            return 
        
        splits = ConnectionPoints.split() #['0.000400', '0.073049', 'Dir:270.000000', 'Layer:', 'BOTTOM']
        X = float(splits[0])
        Y = float(splits[1])
        layer = splits[-1]
        posObjs = list(self.layout.getObjectByPoint([X,Y],layer = layer,radius="2mil"))
#         print(self.Name,posObjs,layer)
        
        if not posObjs:
            log.info("Not found objects on port '%s' position, skip."%self.Name)
            return

        if self.Name in posObjs:
            posObjs.remove(self.Name)
            
        if not posObjs:
            log.info("Not found objects on port '%s' position, skip."%self.Name)
            return
#             
#         posObj = posObjs[0]
        posObj = None
        for obj in posObjs:
            if obj in self.layout.Pins:
                posObj = obj
                break
            
        if not posObj:
            posObj = posObjs[0]
            
        if posObj in self.layout.Pins:   
            tempList = list(posObj.split("-"))+[self.layout.Pins[posObj].Net]
            newName = ".".join(tempList)
    #         print(newName,port)
            log.info("Rename %s to %s"%(self.Name,newName))
            self.Port = newName
        else:
            newName = self.layout[posObj].Net
            log.info("Rename %s to %s"%(self.Name,newName))
            self.Port = newName
        
        
    
class Sources(Primitives):
    
    def __init__(self,layout=None):
        super(self.__class__,self).__init__(layout, type="port",primitiveClass=Source) #port not get by FindObjects

    @property
    def ObjectDict(self):
        '''
        get all port by oDesign.GetModule("Excitations").GetAllPortsList()
        '''
        
        if self._objectDict is None:
            sources = list(self.layout.oEditor.FindObjects('Type','Point Port')) #onle non-group soucre
            pinGroupSources = [pin.Name for pin in self.layout.Pins if "NegativePinGroup" in pin]
            self._objectDict = ComplexDict(dict([(source,Source(source,layout=self.layout)) for source in sources + pinGroupSources]))
        return self._objectDict 


    def addCurrentSource(self,pt0,layer0,pt1,layer1=None,name=None,magnitude="1A",resistance=50000000):
        p0 =   Point(pt0,layout = self.layout)
        p1 =   Point(pt1,layout = self.layout)
        if not layer1: 
            layer1 = layer0
        temps = self.layout.oEditor.FindObjects('Type','Point Port')
        self.layout.oEditor.CreateCurrentSourcePort(
            [
                "NAME:Location",
                "PosLayer:="	, layer0,
                "X0:="			, p0.xvalue,
                "Y0:="			, p0.yvalue,
                "NegLayer:="	, layer1,
                "X1:="			, p1.xvalue,
                "Y1:="			, p1.yvalue
            ])
        temp2 = self.layout.oEditor.FindObjects('Type','Point Port')
        temp3 = set(temp2) - set(temps)
        nameNew = ""
        if temp3:
            nameNew = [p for p in list(temp3) if "InternalPort" not in p][0]
        else:
            log.exception("Can not find new source.")
        self.layout.oEditor.SetPropertyValue("EM Design", "Sources:" + nameNew, "Magnitude", str(magnitude))
        self.layout.oEditor.SetPropertyValue("EM Design", "Sources:" + nameNew, "Resistance", str(resistance))

        if name:
            self.layout.oEditor.SetPropertyValue("EM Design", "Sources:" + nameNew, "Source", name)
        else:
            name = nameNew
        log.info("Current Souce %s has been created."%name)
        self.layout.Sources.push(name)
        return  self[name]
    
    def addVoltageSource(self,pt0,layer0,pt1,layer1=None,name=None,magnitude="1V",resistance=1e-06):
        p0 =   Point(pt0,layout = self.layout)
        p1 =   Point(pt1,layout = self.layout)
        if not layer1: 
            layer1 = layer0
        temps = self.layout.oEditor.FindObjects('Type','Point Port')
        self.layout.oEditor.CreateVoltageSourcePort(
            [
                "NAME:Location",
                "PosLayer:="	, layer0,
                "X0:="			, p0.xvalue,
                "Y0:="			, p0.yvalue,
                "NegLayer:="    , layer1,
                "X1:="			, p1.xvalue,
                "Y1:="			, p1.yvalue
            ])
        temp2 = self.layout.oEditor.FindObjects('Type','Point Port')
        temp3 = set(temp2) - set(temps)
        nameNew = ""
        if temp3:
            nameNew = list(temp3)[0]
        else:
            log.exception("Can not find new source.")

        self.layout.oEditor.SetPropertyValue("EM Design", "Sources:" + nameNew, "Magnitude", str(magnitude))
        self.layout.oEditor.SetPropertyValue("EM Design", "Sources:" + nameNew, "Resistance", str(resistance))

        if name:
            self.layout.oEditor.SetPropertyValue("EM Design", "Sources:" + nameNew, "Source", name)
        else:
            name = nameNew
        log.info("Voltage Souce %s has been created."%name)
        self.layout.Sources.push(name)
        return  self[name]

    def addPinGroupVoltageSource(self,posPins,negPins,magnitude="1V",resistance=1e-6,name=None):

        if not posPins:
            log.exception("PosPin must give for DCVoltageSource")
        
        if not negPins: 
            log.exception("NegPin must give for DCVoltageSource")
        
        if isinstance(posPins,str): 
            posPins = [posPins]
        if isinstance(negPins,str): 
            negPins = [negPins] 

        if not name: 
            name = "DCVoltageSource_"+posPins[0]+"_"+negPins[0]
        
        temps = self.layout.oEditor.FindObjects('Type','*')
        self.layout.oEditor.CreateDCIRTerms(
        [
            "NAME:Args",
            [
                "NAME:CreateTerm",
                "btype:="		, "Interface Ground",
                "mag:="			, str(magnitude),
                [
                    "NAME:PosTerm",
                    "name:="		, "PinGroup_" + posPins[0],
                    "pins:="		, posPins
                ],
                [
                    "NAME:NegTerm",
                    "name:="		, "PinGroup_" + negPins[0],
                    "pins:="		, negPins
                ]
            ]
        ]) 
        
        temp2 = self.layout.oEditor.FindObjects('Type','*')
        temp3 = set(temp2) - set(temps)
        nameNew = ""
        if temp3:
            temp4 = list(temp3)
            temp4.sort(key=len,reverse=True)
            nameNew = temp4[0]
        else:
            log.exception("Can not find new source.")
        
        self.layout.oEditor.SetPropertyValue("EM Design", "Sources:" + nameNew, "Magnitude", str(magnitude))
        self.layout.oEditor.SetPropertyValue("EM Design", "Sources:" + nameNew, "Resistance", str(resistance))
        if name:
            self.layout.oEditor.SetPropertyValue("EM Design", "Sources:" + nameNew, "Source", name)
        else:
            name = nameNew
        log.info("PinGroup Voltage Souce %s has been created."%name)
        self.layout.Sources.push(name)
        return  self[name]

    def addPinGroupCurrentSource(self,posPins,negPins,magnitude="1A",resistance=1e6,name=None):

        if not posPins:
            log.exception("PosPin must give for DCurrentSource")
        
        if not negPins: 
            log.exception("NegPin must give for DCurrentSource")
        
        if isinstance(posPins,str): 
            posPins = [posPins]
        if isinstance(negPins,str): 
            negPins = [negPins] 

        if not name: 
            name = "DCurrentSource_"+posPins[0]+"_"+negPins[0]

        temps = self.layout.oEditor.FindObjects('Type','*')
        self.layout.oEditor.CreateDCIRTerms(
        [
            "NAME:Args",
            [
                "NAME:CreateTerm",
                "btype:="        , "Voltage Source",
                "mag:="            , str(magnitude),
                [
                    "NAME:PosTerm",
                    "name:="        , "PinGroup_" + posPins[0],
                    "pins:="        , posPins
                ],
                [
                    "NAME:NegTerm",
                    "name:="        , "PinGroup_" + negPins[0],
                    "pins:="        , negPins
                ]
            ]
        ]) 
        
        temp2 = self.layout.oEditor.FindObjects('Type','*')
        temp3 = set(temp2) - set(temps)
        nameNew = ""
        if temp3:
            temp4 = list(temp3)
            temp4.sort(key=len,reverse=True)
            nameNew = temp4[0]
        else:
            log.exception("Can not find new source.")
        
        self.layout.oEditor.SetPropertyValue("EM Design", "Sources:" + nameNew, "Magnitude", str(magnitude))
        self.layout.oEditor.SetPropertyValue("EM Design", "Sources:" + nameNew, "Resistance", str(resistance))
        if name:
            self.layout.oEditor.SetPropertyValue("EM Design", "Sources:" + nameNew, "Source", name)
        else:
            name = nameNew
        log.info("PinGroup Current Souce %s has been created."%name)
        self.layout.Sources.push(name)
        return  self[name]


    def addSourceByPin(self,type,posPin,negPin,negNet=None,name=None,magnitude=None,resistance=None):
        pt0 = self.layout.Pins[posPin].Location
        pt1 = self.layout.Pins[negPin].Location
        layer0 = self.layout.Pins[posPin].StartLayer
        layer1 = self.layout.Pins[negPin].StartLayer
        if type.lower() == "voltage":
            if not magnitude:
                magnitude = "1V"
            if not resistance:
                resistance = "1e-6"
            self.addVoltageSource(pt0,layer0,pt1,layer1,name=name,magnitude=magnitude,resistance=resistance)
        elif type.lower() == "current":
            if not magnitude:
                magnitude = "1A"
            if not resistance:
                resistance = "1e-6"
            self.addCurrentSource(pt0,layer0,pt1,layer1,name=name,magnitude=magnitude,resistance=resistance)
        else:
            log.exception("type must be Voltage or Current, input type is %s"%type)
        
        


    def addDCSource(self,type,pt0=None,pt1=None,layer=None,posPins=None,refPins=None,compName=None,posNet=None,negNet=None,name=None,magnitude=None,resistance=None):
        '''_summary_

        Args:
            type (_type_): Voltage/Current
            Pt0 (_type_, optional): _description_. Defaults to None.
            Pt1 (_type_, optional): _description_. Defaults to None.
            posPins (_type_, optional): _description_. Defaults to None.
            negPins (_type_, optional): _description_. Defaults to None.
            PosNet (_type_, optional): _description_. Defaults to None.
            NegNet (_type_, optional): _description_. Defaults to None.
            mag (str, optional): _description_. Defaults to "1A".
            name (_type_, optional): _description_. Defaults to None.
        '''
        if not posPins:
            if compName and posNet: 
                posPins = [pin.Name for pin in self.layout.Components[compName].Pins if pin.Net.lower() == posNet.lower()]
            else:
                log.exception("posPins or compName,posNet should be specified one")
        else:
            #remove pins not in layout
            posPins = [pin for pin in posPins if pin in self.layout.Pins]

        if not refPins:
            if compName and negNet: 
                posPins = [pin.Name for pin in self.layout.Components[compName].Pins if pin.Net.lower() == negNet.lower()]
            else:
                log.exception("refPins or compName,negNet should be specified one")
        else:
            #remove pins not in layout
            refPins = [pin for pin in refPins if pin in self.layout.Pins]
        
        if len(posPins)<1:
            log.info("PinGroup posPins have no pin. skip.")
            return
            
        if len(refPins)<1:
            log.info("PinGroup refPins have no pin. skip.")
            return


        if type.lower() == "voltage":
            if not magnitude:
                magnitude = "1V"
            if not resistance:
                resistance = "1e-6"

            if pt0 and pt1 and layer:
                self.addVoltageSource(pt0,layer,pt1,layer,name,magnitude,resistance)
            elif posPins and refPins:
                if len(posPins)==1 and len(refPins) == 1:
                    pt0 = self.layout.Pins[posPins[0]].Location
                    pt1 = self.layout.Pins[refPins[0]].Location
                    layer = self.layout.Pins[pt0].StartLayer
                    self.addVoltageSource(pt0,layer,pt1,layer,name,magnitude,resistance)
                else:
                    self.addPinGroupVoltageSource(posPins,refPins,magnitude=magnitude,resistance=resistance,name=name)
            else:
                log.exception("pt0,pt1,layer or  posPins,refPins or compName=None,posNet,negNet should set one.")
        elif type.lower() == "current": 
            if not magnitude:
                magnitude = "1A"
            if not resistance:
                resistance = 50000000

            if pt0 and pt1 and layer:
                self.addCurrentSource(pt0,layer,pt1,layer,name,magnitude,resistance)
            elif posPins and refPins:
                if len(posPins)==1 and len(refPins) == 1:
                    pt0 = self.layout.Pins[posPins[0]].Location
                    pt1 = self.layout.Pins[refPins[0]].Location
                    layer = self.layout.Pins[pt0].StartLayer
                    self.addCurrentSource(pt0,layer,pt1,layer,name,magnitude,resistance)
                else:
                    self.addPinGroupCurrentSource(posPins,refPins,magnitude=magnitude,resistance=resistance,name=name)
            else:
                log.exception("pt0,pt1,layer or  posPins,refPins or compName=None,posNet,negNet should set one.")
        else:
            log.exception("type must be Voltage or Current, input type is %s"%type)