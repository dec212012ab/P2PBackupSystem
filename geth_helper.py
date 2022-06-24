from web3 import Web3
from web3.middleware import geth_poa
from solcx import compile_source, compile_files
import json
import socket
import os
from pathlib import Path
import platform
import psutil
import subprocess
import time

def getPrimaryIP():
    s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    s.settimeout(0)
    IP = None
    try:
        s.connect(('15.255.255.255',1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


class ContractArtifacts:
    def __init__(self):
        self.src = ''
        self.abi = ''
        self.bytecode = ''
        self.contract_id = ''
        self.name = ''
    
    def save(self,dest_dir):        
        if not os.path.isdir(dest_dir):
            print("Creating directory path:",dest_dir)
            os.makedirs(dest_dir)

        content = {}
        
        if self.src:
            content['src'] = self.src
        if self.abi:
            content['abi'] = self.abi
        if self.bytecode:
            content['bytecode'] = self.bytecode
        if self.contract_id:
            content['id'] = self.contract_id
        
        out = open(os.path.join(dest_dir,self.name+'.sc'),'w')
        json.dump(content,out)
        out.close()
    
    def load(self,filepath):
        if not filepath:
            print("File path is empty or invalid!")
            return
        if not os.path.isfile(filepath):
            print('Could not open',filepath)
            return
        _in = open(filepath,'r')
        j = json.load(_in)
        _in.close()

        self.name = os.path.splitext(os.path.basename(filepath))[0]
        if 'src' in j:
            self.src = j['src']
        if 'abi' in j:
            self.abi = j['abi']
        if 'bytecode' in j:
            self.bytecode = j['bytecode']
        if 'id' in j:
            self.contract_id = j['id']


class LocalTxManifest:
    def __init__(self,path):
        self.path = path
        pass
    def addTx(self,tx):
        pass
    def removeTx(self,tx):
        pass
    def save(self,path):
        pass


#--http.api debug,eth,web3,personal,net,admin
class GethHelper:
    def __init__(self,host:str=None):
        self.contracts = {}
        self.session = None
        self.transaction_manifest = None
        self.contract_manifest = None
        
        self.data_dir = ''
        self.networkid = 2022
        self.host = host
        self.http = self.host and len(self.host)>6 and 'http://' in self.host[:6]


        #Configuration
        self.netrestrict = []
        self.password_file = ''


        pass
    
    def checkDaemonRunning(self)->bool:
        ls = []
        for p in psutil.process_iter(["name", "exe", "cmdline"]):
            if 'geth' == p.info['name'] or \
                p.info['exe'] and os.path.basename(p.info['exe']) == 'geth' or \
                p.info['cmdline'] and p.info['cmdline'][0] == 'geth':
                ls.append(p)
        return len(ls)>0

    def startDaemon(self,
        data_dir:str=str(Path.home()/'.eth'/'node0'),
        networkid:int=2022,
        netrestrict:list[str]=[],
        force=True
        ):
        if force:
            self.stopDaemon()
        
        self.data_dir = data_dir
        self.networkid=networkid

        cmd = ['geth','--datadir',data_dir,'--networkid',str(networkid)]
        if netrestrict:
            cmd.append('--netrestrict')
            cmd.append(','.join(netrestrict))
            self.netrestrict = netrestrict

        if platform.system()=='Windows':
            subprocess.Popen(cmd,start_new_session=True,close_fds=True,creationflags=subprocess.DETACHED_PROCESS)
        else:
            subprocess.Popen(cmd,start_new_session=True,close_fds=True)
        while not self.checkDaemonRunning():
            print("Waiting for geth daemon...")
            time.sleep(1)
        #while True:
        output = subprocess.run(['geth','attach',self.host,'--exec','admin.nodeInfo'],capture_output=True,text=True)
        #    print(output.stdout,output.stderr)
        #    break
        print("Geth daemon started!")
        
    def stopDaemon(self):
        ls = []
        for p in psutil.process_iter(["name", "exe", "cmdline"]):
            if 'geth' == p.info['name'] or \
                p.info['exe'] and os.path.basename(p.info['exe']) == 'geth' or \
                p.info['cmdline'] and p.info['cmdline'][0] == 'geth':
                ls.append(p)
        
        for proc in ls:
            print("Stopping Geth process with PID",proc.pid)
            proc.kill()
        pass

    def connect(self):
        self.http = self.host and len(self.host)>6 and 'http://' in self.host[:6]
        if self.http:
            self.session = Web3(Web3.HTTPProvider(self.host))
        else:
            provider = Web3.IPCProvider()
            print("Overwriting default with",self.host)
            provider.ipc_path = self.host
            #Retry
            for _ in range(10):
                self.session = Web3(provider)
                if self.session.isConnected():
                    print('Connected!')
                    break
        if self.session.isConnected():
            self.session.middleware_onion.inject(geth_poa.geth_poa_middleware,layer=0)
            print(self.session.eth.accounts)
            self.session.eth.default_account = self.session.eth.accounts[0]
        else:
            print("Failed to connect to Geth client via IPC")
        pass

    def loadTransactionManifest(self,filepath):
        pass
    
    def importContractABI(self,contract_name,filepath):
        pass
    
    def loadContractSource(self,contract_name,filepath):
        pass
    
    def compileContractSource(self,contract_name,filepath=None):
        if not filepath:
            print('Path to contract source not provided!')
            return
        if not os.path.isfile(filepath):
            print("Invalid path to contract source:",filepath)
            return
        file_name = os.path.basename(filepath)
        file_name = os.path.splitext(file_name)[0]
        artifacts = ContractArtifacts()
        artifacts.name = contract_name

        with open(filepath,'r') as f:
            artifacts.src = f.read()
        dest_dir = os.path.dirname(filepath)
        print('Compiling contract file:',os.path.basename(filepath))

        compiled_sol = compile_source(artifacts.src,output_values=['abi','bin'])
        artifacts.contract_id, contract_interface = compiled_sol.popitem()
        artifacts.bytecode = contract_interface['bin']
        artifacts.abi = contract_interface['abi']

        print('Saving Contract Artifacts to',dest_dir)
        artifacts.save(dest_dir)

        #abi_path = os.path.join(dest_dir,file_name+'.json')
        #print('Saving ABI to',abi_path)
        #with open(abi_path,'w') as f:
        #    _abi = str(abi).replace('\'',"\"")
        #    f.write(_abi)
        
        #bytecode_path = os.path.join(dest_dir,file_name+'.bytecode')
        #print('Saving Bytecode to',bytecode_path)
        #with open(bytecode_path,'w') as f:
        #    f.write(byte_code)
        #pass

    def callContract(self,contract_name,localized=True,*args,**kwargs):
        pass
    
    def sendEtherToPeer(self,recipient,amount):
        pass
    
    def inspectBlocksForTransactions(self,start_index,end_index,filter_local_node=True):
        pass
    
    def proposeSigner(self):
        pass
    


