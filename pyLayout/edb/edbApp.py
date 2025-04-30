#--- coding=utf-8
#--- @Author: Yongsheng.Guo@ansys.com, Henry.he@ansys.com,Yang.zhao@ansys.com
#--- @Time: 20250403

import os,sys,re
# from ..common.common import readCfgFile,log
from ..common.common import *
from ..common.config import Config

appPath = os.path.realpath(__file__)
appDir = os.path.split(appPath)[0] 
sys.path.append(appDir)


def edbToSIwave(edbPath,siwPath=None,installDir=None):
#     log.info(str(installDir)) #for debug
#     log.info(str(edbPath)) #for debug
#     log.info(str(siwPath)) #for debug
    
    if not siwPath:
        siwPath = os.path.splitext(edbPath)[0]+".siw"
    
    if not installDir:
        if 'Ansys.Ansoft.Edb' in sys.modules:
            installDir = os.path.dirname(sys.modules['Ansys.Ansoft.Edb'].__file__)
        elif "ANSYSEM_ROOT" not in os.environ:
            installDir = os.environ["ANSYSEM_ROOT"]
        else:
            log.exception("Aedt installDir must set before translate edb to siwave.")
    
    execPath = os.path.join(os.path.dirname(siwPath), "SaveSiw.exec") 
    with open(execPath,"w+") as f:
        f.write("SaveSiw %s"%siwPath)
        f.close()
    cmd = '"{0}" {1} {2} -formatOutput'.format(os.path.join(installDir,"siwave_ng"),edbPath,execPath)
    log.info("Save project to Siwave: %s"%siwPath)
    with os.popen(cmd,"r") as output:
        for line in output:
            log.info(line)
        output.close()
    
    return siwPath


class EdbSIwaveOptions(object):

    def __init__(self,edbapp=None,cell=None):
        '''
        from ansys.aedt.core import Edb
        edbapp = Edb(edbpath=".aedb")
        '''
        self._config = None
        self.edbapp = edbapp
        self.cell = cell
        self.loadOptions()

    def __getitem__(self, key):
        """
        key: str
        """
        return self.get(key)


    def __setitem__(self,key,value):
        self.set(key,value)

    def __getattr__(self,key):

        if key in ["edbapp","_config","maps","cell"]:
            return object.__getattr__(self,key)
        else:
            log.debug("__getattr__ from _dict: %s"%key)
            return self[key]
        

    def __setattr__(self, key, value):
        if key in ["edbapp","_config","maps","cell"]:
            object.__setattr__(self,key,value)
        else:
            log.debug("get property '%s' from dict."%key)
            self[key] = value

    def __repr__(self):
        return "%s Object: %s"%(self.__class__.__name__,self.Name)
    
    def __contains__(self,key):
        return key in self.Config
    
    def __dir__(self):
        return list(dir(self.__class__)) + list(self.__dict__.keys()) + list(self.Props)

    @property
    def Config(self):
        if not self._config:
            self.loadOptions()
            
        return self._config

    @property
    def Props(self):
        propKeys = list(self.Config.Keys)
        if self.Config.maps:
            propKeys += list(self.Config.maps.keys())
        
        return propKeys
    

    def get(self,key):
        '''
        mapping key must not have same value with maped key.
        '''
        
        if not self._config:
            self.loadOptions()
  
        
        if key in self._config and self._config[key] != None: # Map value or already have value
            siwave_id = self.edbapp.Edb.ProductId.SIWave
            cell = self.cell 
            val= cell.GetProductProperty(siwave_id, int(self._config[key]))
            if val[0]:
                return val[1]
            else:
                log.error("Get Property error: %s"%(self.key))
#             cell.SetProductProperty(siwave_id, 515, '1')
        
        if not isinstance(key, str): #key must string
            log.exception("Property error: %s"%(self.key))
        
        
    
    def set(self,key,value):
        '''
        mapping key must not have same value with maped key.
        '''
        
        if not self._config:
            self.loadOptions()
  
        
        if key in self._config and self._config[key] != None: # Map value or already have value
            siwave_id = self.edbapp.Edb.ProductId.SIWave
            cell = self.cell
            rst = cell.SetProductProperty(siwave_id,int(self._config[key]), str(value))
            if not rst:
                log.error("Get Property error: %s"%(self.key))

        if not isinstance(key, str): #key must string
            log.exception("Property error: %s"%(str(key)))



    def loadOptions(self):
        cfgPath = os.path.join(appDir,"SIwaveProductProperties.cfg")
        cfgDict = readCfgFile(cfgPath)
        maps = {}
        for key,value in cfgDict.items():
            key2 = key.replace("_","") ##remove -  
            if key2 != key:
                key3 = key.title().replace("_","")
                maps[key3] = key
        self._config = Config(cfgDict)
        self._config.setMaps(maps)



def initEdb(version=None, installDir=None):

    aedtInstallDir = None
    if installDir:
        aedtInstallDir = installDir.strip("/").strip("\\")
    else:
        if version:
            ver = version.replace(".", "")[-3:]
            verEnv = "ANSYSEM_ROOT%s" % ver
            
            if verEnv in os.environ:
                aedtInstallDir = os.environ[verEnv] 
        
        if aedtInstallDir:
            pass
        elif "ANSYSEM_ROOT" in os.environ:
            aedtInstallDir = os.environ["ANSYSEM_ROOT"]
        else:
            ANSYSEM_ROOTs = list(
                filter(lambda x: "ANSYSEM_ROOT" in x, os.environ))
            if ANSYSEM_ROOTs:
                log.debug("Try to initialize Desktop in latest version")
                ANSYSEM_ROOTs.sort(key=lambda x: x[-3:])
                aedtInstallDir = os.environ[ANSYSEM_ROOTs[-1]]

    # set version from aedtInstallDir
    if version == None:
        ver1 = re.split(r"[\\/]+", aedtInstallDir)[-2]
        ver2 = ver1.replace(".", "")[-3:]
        version = "Ansoft.ElectronicsDesktop.20%s.%s" % (ver2[0:2],ver2[2])
    else:
        if "Ansoft.ElectronicsDesktop" not in version:
            version = "Ansoft.ElectronicsDesktop." + version

    #for python
    # if not isPython or is_linux:
    if is_linux:
        try:
            from ansys.aedt.core.generic.clr_module import _clr # @UnresolvedImport
        except:
            log.exception("pyaedt must be install on linux: pip install pyaedt")
    else:
        #for windows
        import clr as _clr # @UnresolvedImport
        
        
    if aedtInstallDir: 
        
        print("AEDT InstallDir: %s"%aedtInstallDir)

#         from System import Environment
#         from System.IO import Path, File, Directory
        
#         oaDir = Path.Combine(aedtInstallDir, os.path.join('common','oa'))
#         Environment.SetEnvironmentVariable("ANSYS_OADIR", oaDir)
        if "ANSYSEM_ROOT" not in os.environ:
            os.environ["ANSYSEM_ROOT"] = aedtInstallDir
        os.environ["ANSYS_OADIR"] = os.path.join(aedtInstallDir,'common','oa')
        sys.path.append(aedtInstallDir) # configure sys.path to see the assembly
#         Environment.SetEnvironmentVariable("PATH", aedtInstallDir + ";" + Environment.GetEnvironmentVariable("PATH")) # configure PATH env to so assembly can see shared dll's
        os.environ["PATH"] = aedtInstallDir + os.pathsep + os.environ["PATH"] 

    else:
        log.exception("please set environ ANSYSEM_ROOT=Ansys EM install path...")
    
    if isPython:
    
#         _clr.AddReference("System.Core")
        _clr.AddReference('Ansys.Ansoft.CoreDotNet')
        _clr.AddReference("Ansys.Ansoft.Edb")
        _clr.AddReference("Ansys.Ansoft.EdbBuilderUtils")
        _clr.AddReference("Ansys.Ansoft.SimSetupData")
    else:
#         import clr
        # Configure EDB path information
#         oaDir = Path.Combine(aedtInstallDir, os.path.join('common','oa'))
#         Environment.SetEnvironmentVariable("ANSYS_OADIR", oaDir)
#         sys.path.append(aedtInstallDir) # configure sys.path to see the assembly
#         Environment.SetEnvironmentVariable("PATH", aedtInstallDir + ";" + Environment.GetEnvironmentVariable("PATH")) # configure PATH env to so assembly can see shared dll's
        _clr.AddReference('Ansys.Ansoft.CoreDotNet.dll')
        _clr.AddReference('Ansys.Ansoft.PluginCoreDotNet.dll')
        _clr.AddReference('Ansys.Ansoft.Edb.dll')
        _clr.AddReference('Ansys.Ansoft.SimSetupData.dll')

    import Ansys.Ansoft.Edb as Edb
#     Edb = __import__("Ansys.Ansoft.Edb")
    
    if Edb:
        Edb.Database.SetRunAsStandAlone(True)
        return Edb
    else:
        log.exception("load edb module failed")
    # self._edb = edb.Ansoft.Edb
    # edbbuilder = __import__("Ansys.Ansoft.EdbBuilderUtils")
    # self.edbutils = edbbuilder.Ansoft.EdbBuilderUtils
    # self.simSetup = __import__("Ansys.Ansoft.SimSetupData")
    # self.simsetupdata = self.simSetup.Ansoft.SimSetupData.Data



class EdbApp(object):
    
    def __init__(self,edbpath=None,version=None,installDir=None):
        self.edbpath = edbpath
        self.version = version
        self.installDir=installDir
        self._edb = None
        self.db = None
        self.cell = None
        
        self._siaveOptions = None
        self.pyEdb = None
        
        if edbpath:
            self.open(edbpath)
            
    def __del__(self):
        """
        destructor saves and closes active db if valid
        """
        #if self.saveEdb and self.db and not self.db.IsNull():
#         self.del2()
        if self.db and not self.db.IsNull():
            self.db.Save()
            self.db.Close()


    def del2(self):
        if self.db and not self.db.IsNull():
            self.db.Save()
            self.db.Close()

    def initPyEdb(self):
        try:
            from ansys.aedt.core import Edb  # @UnresolvedImport
            edbapp = Edb( edbversion=self.version)
            self.pyEdb = edbapp
            self._edb = edbapp._edb
#                 os.environ["ANSYSEM_ROOT"] = edbapp.base_path
            self.installDir = os.path.dirname(self._edb.__file__)
            if "ANSYSEM_ROOT" not in os.environ:
                os.environ["ANSYSEM_ROOT"] = self.installDir
                
            return self._edb
        except:
            log.error("init edb error form ansys pyedb ... ")

    @property
    def Edb(self):
        
        if self._edb:
            return self._edb
        
        if 'Ansys.Ansoft.Edb' in sys.modules:
            self._edb = sys.modules['Ansys.Ansoft.Edb']
            self.installDir = os.path.dirname(self._edb.__file__)
            if "ANSYSEM_ROOT" not in os.environ:
                os.environ["ANSYSEM_ROOT"] = self.installDir
                
            return self._edb

            
        try:
            self._edb = initEdb(self.version,installDir=None)
#                 self.installDir = os.environ["ANSYSEM_ROOT"]
            self.installDir = os.path.dirname(self._edb.__file__)
            if "ANSYSEM_ROOT" not in os.environ:
                os.environ["ANSYSEM_ROOT"] = self.installDir
            return self._edb
        except:
            log.error("init edb error , try to init using pyedb mathod.")

        self.initPyEdb()
    
        if not self._edb:
            log.exception("init edb error ... ")
                
        return self._edb
        
    @property
    def SIwaveOptions(self):
        if self._siaveOptions == None:
            if not self.cell:
                log.exception("cell is null, please open aedb file first.")
            self._siaveOptions = EdbSIwaveOptions(self,self.cell)
        return  self._siaveOptions
        
        
    def open(self,edbpath=None):

        """
        Open and initialize from edbFN.
        First of db.TopCircuitCells is set active in this object
        """
        if not edbpath:
            edbpath = self.edbpath
        else:
            self.edbpath = edbpath

        if not os.path.exists(edbpath):
            log.exception('Edb could not be found at "{0}"'.format(edbpath))
            return False
        log.info("Open Edb: %s"%edbpath)
        self.Edb.Database.SetRunAsStandAlone(True)
        self.db = self.Edb.Database.Open(edbpath, False)
        if self.db.IsNull():
            log.exception('Edb could not be opened at "{0}"'.format(edbpath))
            return False
        cells = list(self.db.TopCircuitCells)
        if cells:
            self.cell = cells[0]
        if self.cell and self.cell.IsNull():
            log.exception('TopCircuitCell could not be found'.format(edbpath))
            return False

        return True  
    
    def save(self):
        if self.db and not self.db.IsNull():
            self.db.Save()
        else:
            log.error("Database not valid.")
    
    def close(self):
        if self.db and not self.db.IsNull():
            self.db.Close()
        else:
            log.error("Database not valid.")
    
    def exportSiwave(self,edbpath=None,path=None):
        edbpath = edbpath or self.edbpath
        return edbToSIwave(edbpath, path,self.installDir)
    

if __name__ == "__main__":
    from ansys.aedt.core import Edb
    edbapp = Edb(edbpath=r"C:\work\Project\AE\Script\PSI\PSI_automation_testCase\edb\SIWAVE_PDN_TEST_0716_group1.aedb", edbversion="2024.2")
    siwave_id = edbapp.edb_api.ProductId.SIWave
    cell = edbapp.active_cell._active_cell
    cell.SetProductProperty(siwave_id, 515, '1')
    edbapp.save_edb()
    
    
#     self.cell.SetProductProperty(edb.ProductId.SIWave, kSIwaveProperties.PSI_SIMULATION_PREFERENCE, self.m_simConfig.m_simulationPreference)