#coding:utf-8

"""
    Examples:
        >>> pin = Pin()
        >>> pin["A1"]
        返回U1的Component对象
        
        >>> cmp[["A1","A2"]]
        返回A1,A2的Pin对象List
        
        >>> pin["A\d+"]
        返回"A\d+"匹配命名的Pin对象List，匹配A1,A2,Axxx
        
        >>> for p in layout.Pins:
        >>>     log.debug(p.Name)
        打印Component上所有pin的名字     


get pin information from oEditor.GetComponentPinInfo API

"PinInfo":['PinName = UI-A1', 'Type=Pin, Padstack: C35', 'X=0.005647', 'Y=-0.023463', 
'ConnectionPoints= 0.005647 -0.023463 Dir:NONE Layer: TOP', 'NetName=ZQ_U1']

oEditor.GetProperties("BaseElementTab","U8-4")
['Type', 'LockPosition', 'Name', 'Net', 'Padstack Definition', 'Padstack Usage', 
'Start Layer', 'Stop Layer', 'Backdrill Top', 'Top Offset', 'Backdrill Bottom', 'Bottom Offset', 
'OverrideHoleDiameter', 'HoleDiameter', 'Location', 'Angle', 'Component Pin']

"""

import re
from ..common import hfss3DLParameters
from ..common.arrayStruct import ArrayStruct
from ..common.complexDict import ComplexDict
from ..common.unit import Unit
from ..common.common import log

from .geometry import Point
from .primitive import Primitive,Primitives

class Pin(Primitive):
    '''

    Args:
        object (_type_): _description_
        
    Examples:
        >>> pin = Pin()
        >>> pin["A1"]
        返回A1的Pin对象
        
        >>> pin[["A1","A2"]]
        返回A1,A2的Pin对象List
        
        >>> cmp["A\d+"]
        返回"A\d+"匹配命名的Pin对象List，匹配A1,A2,Axxx
        
        >>> for p in layout.Pins:
        >>>     log.debug(p.Name)
        打印Component上所有pin的名字  
        
    '''

    def __init__(self, name,layout=None):
        '''Initialize Pin object
        Args:
            pinName (str): pin name of the component, optinal
            compName (str): refdes of component in PCB, optional
            layout (PyLayout): PyLayout object, optional
        '''
        super(self.__class__,self).__init__(name,layout)
        
    def parse(self, force = False):
        if self.parsed and not force:
            return
        
        super(self.__class__,self).parse(force) #initial component properties
        
        name = self.name
        maps = self.maps
        names = re.split(r"[.-]+", name, maxsplit = 1)
        
        if "Component Pin" in self and len(names) >1:
            #in component
            self._info.update("CompName",names[0])
            self._info.update("pinName",names[-1]) #self["Component Pin"]
        else:
            log.debug("floating pin found: %s"%name)
            self._info.update("CompName",None)
            self._info.update("pinName",name)
        
#         if len(names) <2:
# #                 log.exception("pinName pattern error: %s, should be like: U1-A1 or U1.A1"%pinName) 
#             log.debug("floating pin found: %s"%name)
#             self._info.update("CompName",None)
#             self._info.update("pinName",name)
#         else:
#             self._info.update("CompName",names[0])
#             self._info.update("pinName",names[1])
            # get pin information from oEditor.GetComponentPinInfo API
            # 
            # "PinInfo":['PinName = UI-A1', 'Type=Pin, Padstack: C35', 'X=0.005647', 'Y=-0.023463', 
            # 'ConnectionPoints= 0.005647 -0.023463 Dir:NONE Layer: TOP', 'NetName=ZQ_U1']
            # 
            # oEditor.GetProperties("BaseElementTab","U8-4")
            # ['Type', 'LockPosition', 'Name', 'Net', 'Padstack Definition', 'Padstack Usage', 
            # 'Start Layer', 'Stop Layer', 'Backdrill Top', 'Top Offset', 'Backdrill Bottom', 'Bottom Offset', 
            # 'OverrideHoleDiameter', 'HoleDiameter', 'Location', 'Angle', 'Component Pin']
            comp = names[0]
            if comp in self.layout.Components:
                pinInfo = self.layout.oEditor.GetComponentPinInfo(comp, name)
                for k,v in filter(lambda x:len(x)==2,[i.split("=",1) for i in pinInfo]):
                    self._info.update(k,v)
            else:
                compObj = self.layout.Components.findComponentByPin(self.name)
                if compObj:
                    self._info.update("CompName",compObj.Name)
                    self._info.update("pinName",self.name)
                    pinInfo = self.layout.oEditor.GetComponentPinInfo(compObj.Name, name)
                    for k,v in filter(lambda x:len(x)==2,[i.split("=",1) for i in pinInfo]):
                        self._info.update(k,v)
                else:
                    log.error("component not found for pin %s"%self.name)
                    self._info.update("CompName",None)
                    self._info.update("pinName",self.name)

        maps.update({"X":{
            "Key":"self",
            "Get":lambda v:v.Location.xvalue
            }})
        maps.update({"Y":{
            "Key":"self",
            "Get":lambda v:v.Location.yvalue
            }})
#         # GetComponentPinInfo ConnectionPoints not right
#         self._info.update("X",self._info.Location.X)
#         self._info.update("Y",self._info.Location.Y)
            
        #pins information will update when they used by self[]
        maps.update({"IsSMTPad":{
            "Key":"self",
            "Get":lambda s: s.get("Start Layer") == s.get("Stop Layer")
            }})
        
        self._info.setMaps(maps)
                
    
    def getInscribedDiameter(self):
        '''
        内切圆
        '''
        pskName = self["Padstack Definition"]
        psk = self.layout.PadStacks[pskName]
        layerName = self.layout.Components[self.compName]["PlacementLayer"]
        
        shp = psk[layerName].pad.shp
        szs = psk[layerName].pad.Szs
        
        if shp == "Rct":
            return (Unit(szs[0])).V if (Unit(szs[0])).V< (Unit(szs[1])).V else (Unit(szs[1])).V
        elif  shp == "Cir":
            return (Unit(szs[0])).V
        elif  shp == "Sq":
            return (Unit(szs[0])).V
        else:
            return None
    


    def backdrill(self,stub = None):
        '''
        this function only support 2023.1 or later versions 
        '''
        
        if self.isSMTPad: 
            return
        
        if stub == None:
            stub = self.layout.options["H3DL_backdrillStub"]
        
        layers = []
        #for lines
        names = self.getConnectedObjs('line')
        for name in names:
            line = self.layout.lines[name]
            layers.append(line["PlacementLayer"])
        
        #for smt pad
#         names = self.getConnectedObjs('pin')
#         for name in names:
#             pin = self.layout.pins[name]
#             if pin.isSMTPad: layers.append(pin["Start Layer"])
        if self.CompName:
            layers.append(self.layout.Components[self.CompName].PlacementLayer)
        
        if len(layers)<2: #small then two layers
            log.info("small then two layers, skip backdrill")
            return
        
        layers.sort(key = lambda x: Unit(self.layout.layers[x].Lower).V,reverse = True)
        #---backdrill Top
        if layers[0] != self.layout.layers["C1"].Name:
            log.info("Backdrill vias : %s from Top to %s, stub:%s, net:%s"%(self.name,layers[0],stub,self.Net))
            self.BackdrillTop = layers[0]
            self.TopOffset = stub
            self.update()
        #---backdrill bottom
        if layers[-1] != self.layout.layers["CB1"].Name:
            log.info("Backdrill vias : %s from Bottom to %s, stub:%s, net:%s"%(self.name,layers[-1],stub,self.Net))
            self.BackdrillBottom = layers[-1]
            self.BottomOffset = stub
            self.update()

    def getNearestRefPin(self,PinList = None, net = None):
        '''
        get nearest pin to self
        '''
        if not PinList and net:
            # PinList = self.layout.Nets[net].getConnectedObjs("pin")
            PinList = [pin for pin in self.layout.Components[self.CompName].Pins if pin.Net == net]

        if not PinList:
            log.exception("PinList is empty. Please check Pinlist.")

        nearPin = None
        nearDis = 1e9
        for pin in PinList:
            if isinstance(pin,str):
                pin = self.layout.pins[pin]
            dis = abs((pin.Location - self.Location))
            if dis < nearDis:
                nearPin = pin
                nearDis = dis

        return nearPin

class Pins(Primitives):
    
    def __init__(self,layout=None):
        super(self.__class__,self).__init__(layout, type="pin",primitiveClass=Pin)
