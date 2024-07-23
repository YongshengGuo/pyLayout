# pylayout简介
pylayout是在PyAedt基础上，针对3D Layout深度定制的python库，提供更加方便的layout属性访问和管理。

- 使用集合方式和名字直接访问layout上的图形物体
- 直接使用属性名字访问和修改属性，所见即所得
- 支持对layout进行遍历操作
- 提供了更简单的Stackup和layer属性修改接口
- 提供了对变量的快捷添加和访问
- 更方便的Setup/Sweep添加
- 方便的后处理（规划中）



# Layout对象初始化：
Layout对象代表了一块PCB Or Package设计，如果一个Project下有多个Design,可用多个Layout对象描述。  

```python
from pyLayout import Layout
layout = Layout("2023.2")
layout.initDesign()
```

>1. layout = Layout()不指定版本是，pyLayout会尝试启动最新版本的AEDT界面。
>2. 如果对应版本的AEDT是打开状态，默认使用当前AEDT窗口，不会打开新的AEDT界面。
>3. 通过AEDT调用时(Tools->Run Script), 会默认继承当前窗口的版本号，指定的版本号不起作用。
>4. layout.initDesign() 用于初始化Layout对象，初始化之后Layout对象的属性才有效。

在initDesign()调用之前，请确保AEDT中已经有一个打开的3DL Design。  
在python环境执行时，需要按照pyAedt. (本测试环境为python环境)




```python
#初始化pylayout
import sys
sys.path.append(r"C:\work\Study\Script\Ansys\quickAnalyze\FastSim") #添加pyaedt的路径
import pyLayout
pyLayout.log.setLogLevel("INFO")

from pyLayout import Layout
# layout = Layout("2022.2")
layout = Layout("2023.2") #2023.2 
# layout = Layout() #least version
# layout.openAedt(r"C:\work\Project\AE\Script\test_pcb\galileo.aedt")
layout.initDesign()
```

layout对象有元素集合，定义集合，仿真数据三大部分组成，通过集合可以索引对应的元素。  
- 元素集合：pins,vias,rects,circles,arcs,lines,polys,plgs,circleVoids,lineVoids,rectVoids,polyVoids,plgVoids,texts,cells,Measurements,Ports,components,CSs,S3Ds,ViaGroups 
-  定义集合： Materials,Padstacks,ComponentDefs,Layers,Variables,Setups,Sweeps
-  仿真数据集合： Solutions,Reports

# 一. Layout对象的访问（Components）
Layout由Component, Layer, Material, Net, Pin, Line, Via, shape, Setup, Solution, Variable等元素组成，这些元素可以通过没有元素的集合对象来访问。比如Layout.Components对象代表了Layout所有Component的集合，可以用于获取所有的Component对象。  
Component, Layer, Material, Net, Pin, Line, Via, shape, Setup, Solution, Variable的集合都支持类似调用方式。 
以上对象的访问不区分大小写。


```python
## 方法1：使用位号索引，访问Layout上的U2A5器件对象
U2A5_1 = layout.Components["U2A5"]  
```


```python
## 方法2：直接作为属性，访问Layout上的U2A5器件对象
U2A5_2 = layout.Components.U2A5 
```


```python
## 方法3: 直接访问Layout的U2A5对象，
# Layout会尝试U2A5的类型，返回Compoent对象或者其它对象，如果遍历未发下U2A5元素，则抛出异常。（有存在重名的可能性）
U2A5_3 = layout["U2A5"]  
U2A5_4 = layout.U2A5  
```


```python
## 除了以上方法，可以直接使用index对器件进行访问：
U_0 = layout.Components[0]
U_0_5 = layout.Components[0:5]
```


```python
## 使用for循环迭代对象
print("Total components on layout: %s"%len(layout.Components))
for comp in layout.Components: 
    print("Name:%s,  Part:%s,  PlacementLayer:%s"%(comp.Name,comp.Part,comp.placementLayer))

```


```python
print("Total Vias on layout: %s"%len(layout.Vias))
for via in layout.Vias: 
    print(via.Name,via.PadstackDefinition,
          via.Location,
          via.StartLayer,via.StopLayer)

```

# 二. 访问Component的属性


```python
U2A5 = layout.Components["U2A5"]
dir(U2A5)
```


```python
## 访问Component的pins
for name in U2A5.PinNames:
    pin = layout.pins[name]
    print(pin.name,pin.Location)
```

# 三. Layout.Layers 对象访问




```python
## 获取具体某层的layer对象
# layer对象可以通过层名索引，或者通过位置获取。

layout.layers["Top"] #使用名字获取
layout.layers["C1"] #获取第一个金属层，即Top层
layout.layers["CB1"] #反向获取第一个金属层，即BOTTOM层
layout.layers["D1"] #获取第一个介质层
layout.layers["DB1"] #反向第一个介质层
layout.layers["S1"] #获取叠层所有层的第一层
layout.layers["SB1"] #反向获取叠层所有层的第一层

layout.layers.Top #使用名字获取
layout.layers.C1 #使用名字获取
layout.layers.S1 #使用名字获取
```


```python
## 获取和设置Layer的属性

layout.layers["Top"]["Thickness"] #获取层厚度
print(layout.layers["Top"].Thickness) #获取层厚度

layout.layers["Top"].Thickness = "1.9mil" #设置层厚度

layout.layers["Top"].Thickness = "1.9mil" #设置层厚度

print(layout.layers["Top"].Material,
layout.layers["Top"].FillMaterial,
layout.layers["Top"].Height,
layout.layers["Top"].Lower)

```


```python
## 获取和设定粗糙度

layout.layers["Top"].Roughness = "0.5um"
```


```python
layout.layers["Top"].UseRoughness = True
layout.layers["Top"].Roughness = "0.5um"
layout.layers["Top"].Roughness
```

# 四. Variable 变量的增加和赋值


```python
layout.Variables.add("test1") #局部变量
layout.Variables.add("$test2") #全局变量

layout.Variables.test1 = "10mil"
layout.Variables["$test2"] = "20mil"

print(layout.Variables["test1"])
print(layout.Variables["$test2"])
```


```python
varss = layout.Variables
print(varss.All)
```

# 五. 访问和管理line,via,shape,pin,net的属性
在3D Layout UI中看到的物体属性，均可直接访问，不区分大小写，支持直接赋值。   
![image.png](image.png)



```python
via1 = layout.vias["via928"] #获取via对象
via2 = layout.vias.via928  #和via1为同一对象
print(via1 is via2)
```

## 对象属性的访问
可以通过key值访问，也可以作为属性访问，如果属性值有空格，允许去掉空格进行索引。不区分大小写。


```python
print(via1.name,via2.Net)
print(via1["Start Layer"]) #直接访问属性
print(via1["StartLayer"]) #属性可以去掉空格
print(via1.StartLayer) #和前面两种方法等同
```




```python
## I可见属性同Via案例

line1 = layout.lines["line_2333"]
pin1 = layout.pins["U2A5-AN11"]
p1 = layout.Shapes["poly_354"]
net1 = layout.nets["M_CAS_N"]

```

## 关于坐标点属性


```python
poly = layout.shapes.poly_1134
print(poly.Pt0)
print(poly.Pts)

print(poly.Pt0.X, poly.Pt0.Y)
print(poly.Pt0[0], poly.Pt0[1])

print(list(poly.Pt0))

print("Pt0 add ")
#mothod 1
temp = list(poly.Pt0)
poly.Pt0 += ["100um","200um"]
print(temp,"add 100um,200um->",poly.Pt0)

#mothod 2
temp = list(poly.Pt0)
poly.Pt0 += "100um,100um"
print(temp,"add 100um,200um->",poly.Pt0)
```

# 六. setup的管理
setup 添加，获取，删除setup


```python
layout.setups.add("hfss1",solutionType = "HFSS")
layout.setups.add("siwave1",solutionType = "SIwave")
```

## hfss setup属性访问和设定


```python
# dir(layout.setups["hfss1"])

layout.setups["hfss1"].AdaptiveFrequency = "10Ghz"
layout.setups["hfss1"].DeltaS = "0.01"
layout.setups["hfss1"].MaxPasses = 20

print(layout.setups["hfss1"].AdaptiveFrequency)
print(layout.setups["hfss1"].DeltaS)
print(layout.setups["hfss1"].Order)
print(layout.setups["hfss1"].MaxPasses)
```

sweep的添加和删除


```python
#添加HFSS Sweep
layout.setups["hfss1"].addSweep("swp1")
layout.setups["hfss1"].Sweeps["swp1"].SweepData = "LIN 0GHz 20GHz 0.01GHz"
layout.setups["hfss1"].Sweeps["swp1"].UseQ3D = True
layout.setups["hfss1"].Sweeps["swp1"].InterpolatingTolerance = 0.001 #0.1%
layout.setups["hfss1"].Sweeps["swp1"].SweepType = "interpolating" #default


#添加SIwave Sweep
layout.setups["siwave1"].addSweep("swp1")
layout.setups["siwave1"].Sweeps["swp1"].SweepData = "LIN 0GHz 20GHz 0.01GHz"
layout.setups["siwave1"].Sweeps["swp1"].UseQ3D = True
layout.setups["siwave1"].Sweeps["swp1"].InterpolatingTolerance = 0.001 #0.1%
layout.setups["siwave1"].Sweeps["swp1"].SweepType = "interpolating" #default

```

# 七. PadStack的访问
访问padstack数据  
![image.png](image.png)


```python
padStk1_name = layout.Vias.via1082["Padstack Definition"]
padStk1 = layout.PadStacks[padStk1_name]
print(padStk1.DrillSize)
print(padStk1["Top"].PadSize) 
print(padStk1["Top"].AntipadPadSize)
print(padStk1["Top"].ThermalPadSize)

# layerName Top可以使用C1进行索引，即Concudtor的第一层
print(padStk1["C1"].PadSize) 
print(padStk1["C1"].AntipadPadSize)
print(padStk1["C1"].ThermalPadSize)
print(padStk1["CB2"].PadSize) 
```

## 按照属性直接访问


```python
print(padStk1["Top"].pad.shp) 
print(padStk1["Top"].pad.Szs) 

print(padStk1["Top"].ant.shp) 
print(padStk1["Top"].ant.Szs) 

print(padStk1["Top"].thm.shp) 
print(padStk1["Top"].thm.Szs) 
```

# 八. Material属性访问
可以按照材料的属性名作为key值进行访问和赋值.  

```python
mat1 = layout.Materials["copper"]
# dir(mat1)

for prop in mat1.Props:
    print(prop,"->",mat1[prop])
```




```python
print(mat1["permittivity"])
print(mat1.DK) #同 permittivity

print(mat1["dielectric_loss_tangent"])
print(mat1.DF) #同 dielectric_loss_tangent

print(mat1["conductivity"])
print(mat1.Cond) #同 conductivity

print(mat1["Resistivity"]) # 1/conductivity
print(mat1.Resistivity) # 1/conductivity

print(mat1["permeability"])
print(mat1.ur) #同 permeability

```
