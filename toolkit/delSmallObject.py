#--- coding:utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 2024-01-18


import sys,os
appPath = os.path.realpath(__file__)
appDir = os.path.split(appPath)[0] 
sys.path.append(appDir)
sys.path.append(r"C:\work\Study\Script\Ansys\quickAnalyze\FastSim")
# MessageBox.Show(appDir)
try:
    import pyLayout
except:
    import clr
    layoutlib = os.path.join(appDir,'pyLayout.dll')
    if os.path.exists(layoutlib):
        print("import pyLayout.dll")
        clr.AddReferenceToFileAndPath(layoutlib)
        import pyLayout
        
from pyLayout import Layout
# pyLayout.log.setLogLevel(logLevel="DEBUG")

def main():
    layout = Layout()
    layout.initDesign()
    
    samllArea = 1e-3
    delObjs = []
    
    #for shapes
    for shape in layout.Shapes:
        if shape.Area<samllArea:
            print("%s with area %s, small then %s, will be remove from layout."%(shape.Name,shape.Area,samllArea))
            delObjs.append(shape.Name)
            
    if delObjs:
        layout.delete(delObjs)
        
    
#     layout.close()
    

    

if __name__ == '__main__':
#     test1()
    main()