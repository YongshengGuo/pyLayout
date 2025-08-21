#--- coding=utf-8
#--- @Author: Yongsheng.Guo@ansys.com, Henry.he@ansys.com,Yang.zhao@ansys.com
#--- @Time: 20250403

import os,sys,re
# from ..common.common import readCfgFile,log
from ..common.common import *
from ..common.config import Config
from .edbSiwaveOption import EdbSIwaveOptions
from .edbPinGroup import EdbPinGroups
from .edbComponent import EdbComponents
from .edbLayer import EdbLayers

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
        self.layout = None
        
        self._siaveOptions = None
        self._pinGroups = None
        self._components = None
        self._layers = None
        self.pyEdb = None
        
        if edbpath:
            self.open(edbpath)
            
    def __del__(self):
        """
        destructor saves and closes active db if valid
        """
        #if self.saveEdb and self.db and not self.db.IsNull():
#         self.del2()
        try:
            if self.db and not self.db.IsNull():
                self.db.Save()
                self.db.Close()
        except:
            pass

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
            self._siaveOptions = EdbSIwaveOptions(self)
        return  self._siaveOptions
    
    @property
    def PinGroups(self):
        if self._pinGroups == None:
            if not self.cell:
                log.exception("cell is null, please open aedb file first.")
            self._pinGroups = EdbPinGroups(self)
        return  self._pinGroups

    @property
    def Components(self):
        if self._components == None:
            if not self.cell:
                log.exception("cell is null, please open aedb file first.")
            self._components = EdbComponents(self)
        return  self._components

    @property
    def Layers(self):
        if self._layers == None:
            if not self.cell:
                log.exception("cell is null, please open aedb file first.")
            self._layers = EdbLayers(self)
        return  self._layers

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

        self.layout = self.cell.GetLayout()

        return True  
    

    def attachEdb(self,hdb):
        '''
        not work @ list(self.db.TopCircuitCells) ...
        '''
        if is_linux:
            try:
                from ansys.aedt.core.generic.clr_module import _clr # @UnresolvedImport
            except:
                log.exception("pyaedt must be install on linux: pip install pyaedt")
        else:
            #for windows
            import clr as _clr # @UnresolvedImport
        
        from System import Convert

        try:
            self.Edb.Database.SetRunAsStandAlone(False)
            hdl = Convert.ToUInt64(hdb)
            self.db = self.Edb.Database.Attach(hdl)
        except:
            log.exception("attach edb error.")
            return False

        if self.db.IsNull():
            log.exception('Edb could not be opened')
            return False
        cells = list(self.db.TopCircuitCells)
        if cells:
            self.cell = cells[0]
        if self.cell and self.cell.IsNull():
            log.exception('TopCircuitCell could not be found')
            return False

        return True  



    def loadLayout(self,layoutPath ,edbOutPath = None,controlFile = "", layoutType = None, extractExePath = None):
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
        
        if extractExePath:
            if extractExePath[-4:].lower() == ".exe":
                extractExePath = os.path.dirname(extractExePath)
                
            if extractExePath not in os.environ['PATH']:
                os.environ['PATH'] = os.pathsep.join([extractExePath,os.environ['PATH']])
                log.debug(os.environ['PATH'])
        
        
        if layoutType.lower() == "aedt":
            self.open(layoutPath[:-4]+"aedb")
        elif layoutType.lower() == "edb":
            self.open(layoutPath)
        elif layoutType.lower() == "cadence":
            if not edbOutPath:
                edbOutPath = layoutPath[:-4] + ".aedb"
            if not controlFile:
                controlFile = ""
            # self.importBrd(layoutPath,edbOutPath,controlFile)
        elif layoutType.lower() == "odb++":
            if not edbOutPath:
                edbOutPath = layoutPath[:-4] + ".aedb"
            if not controlFile:
                controlFile = ""
            # self.importODB(layoutPath,edbOutPath,controlFile)

        elif layoutType.lower() == "siwave":
            self.importSIwave(layoutPath)

        else:
            raise Exception("Unknow layout type")
    
        
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
    

    def importSIwave(self,path,edbPath = None):
        if edbPath == None:
            edbPath = os.path.splitext(self.ProjectPath)[0]+"aedb"

        execPath = os.path.join(self.ProjectDir, "SaveSiw.exec") 
        with open(execPath,"w+") as f:
            f.write("SaveEdb %s"%edbPath)
            f.close()

        if self.installDir not in os.environ['PATH']:
            split = ";" if 'nt' in os.name else ":"
            os.environ['PATH'] = split.join([self.installDir,os.environ['PATH']])
            log.debug(os.environ['PATH'])

        cmd = '"{0}" {1} {2} -formatOutput'.format("siwave_ng",path,execPath)
        log.info("Import Siwave to Aedt: %s"%path)
        with os.popen(cmd,"r") as output:
            for line in output:
                log.info(line)
            output.close()
        self.open(edbPath)

    def exportSiwave(self,edbpath=None,path=None):
        edbpath = edbpath or self.edbpath
        return edbToSIwave(edbpath, path,self.installDir)
    

if __name__ == "__main__":
    from ansys.aedt.core import Edb
    edbapp = Edb(edbpath=r"C:\work\Project\AE\Script\PSI\PSI_automation_testCase\edb\SIWAVE_PDN_TEST_0716_group1.aedb", 
        edbversion="2024.2")
    siwave_id = edbapp.edb_api.ProductId.SIWave
    cell = edbapp.active_cell._active_cell
    cell.SetProductProperty(siwave_id, 515, '1')
    edbapp.save_edb()
    
    
#     self.cell.SetProductProperty(edb.ProductId.SIWave, kSIwaveProperties.PSI_SIMULATION_PREFERENCE, self.m_simConfig.m_simulationPreference)