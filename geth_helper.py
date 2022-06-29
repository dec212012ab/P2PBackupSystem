from web3 import Web3
import web3
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
from enum import IntEnum
import configparser as cfgp


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
        self.address = ''
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
        if self.address:
            content['address'] = self.address
        out = open(os.path.join(dest_dir,self.name+'.sc'),'w')
        json.dump(content,out)
        out.close()
    
    def load(self,filepath:str)->bool:
        if not filepath:
            print("File path is empty or invalid!")
            return False
        if not os.path.isfile(filepath):
            print('Could not open',filepath)
            return False
        _in = open(filepath,'r')
        try:
            j = json.load(_in)
        except:
            print("JSON error loading contract artifact file at",filepath)
            if not _in.closed:
                _in.close()
            return False

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
        if 'address' in j:
            self.address = j['address']
        return True

class TxType(IntEnum):
    EXCHANGE=0
    CONTRACT=1

class Transaction:
    def __init__(self,txtype:TxType=TxType.EXCHANGE):
        self.txtype = txtype
        self.txhash = None
        self.txreceipt = None
        self.extra = {}

    def addTxInfo(self,tx_hash, tx_receipt,additional_info:dict[str,str] = {}):
        self.txhash = tx_hash
        self.txreceipt = tx_receipt
        if additional_info:
            self.extra = {**self.extra,**additional_info}

    def toJSON(self)->str:
        out = {}
        out['txtype'] = int(self.txtype)
        #print(json.dumps(out['txtype']))
        out['txhash'] = str(self.txhash)
        #print(json.dumps(out['txhash']))
        out['txreceipt'] = web3.Web3.toJSON(self.txreceipt)
        #print(json.dumps(out['txreceipt']))
        out['extra'] = self.extra
        #print(json.dumps(out['extra']))
        return json.dumps(out,indent=4,sort_keys=True)
    
    def fromJSON(self,json_str)->bool:
        try:
            _in = json.loads(json_str)
        except:
            print("Error when converting Transaction string to JSON")
            return False
        for k in ['txtype','txhash','txreceipt','extra']:
            if not k in _in:
                print("Incomplete transaction record. Key",k,'is not present')
                return False
        self.txtype = TxType(_in['txtype'])
        self.txhash = _in['txhash']
        self.txreceipt = _in['txreceipt']
        self.extra = _in['extra']
        return True
     
class LocalTxManifest:
    def __init__(self,path):
        self.path = path
        self.transactions:list[Transaction] = []
        self.unique_ids = set()
        self.dirty = False
        if os.path.isfile(path):
            self.load()
        pass
    
    def load(self,path:str=None,force=False)->bool:
        if self.dirty:
            print("Cannot overwrite pending changes! Save the current manifest first or set the force argument to True")
            return False
        if not path:
            path = self.path
        if not os.path.isfile(path):
            print("Could not load transaction manifest at",path)
            return False
        try:
            f = open(path,'r')
            manifest = json.load(f)
            f.close()
        except:
            print("Failed to open JSON content in",path)
            if not f.closed:
                f.close()
            return False
        self.transactions = []
        self.unique_ids.clear()
        for i,item_str in enumerate(manifest):
            t = Transaction()
            if not t.fromJSON(item_str):
                print('Failed to load transaction',i,'from',path)
                continue
            else:
                self.addTx(t)
        self.dirty = False
        return True

    def addTx(self,tx:Transaction)->bool:
        if not tx.txhash in self.unique_ids:
            self.transactions.append(tx)
            self.dirty = True
            return True
        else:
            print('Found duplicate transaction hash. Skipping...')
            return False
    
    def save(self,path:str=None)->bool:
        if not path:
            path = self.path
        if not os.path.isdir(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
        out = []
        for t in self.transactions:
            out.append(t.toJSON())
        fp = open(path,'w')
        try:
            json.dump(out,fp,indent=4,sort_keys=True)
        except:
            print("Failed to save manifest as JSON")
            if not fp.closed:
                fp.close()
            return False
        
        if not fp.closed:
            fp.close()
        self.dirty = False
        return True

#--http.api debug,eth,web3,personal,net,admin
class GethHelper:
    def __init__(self,host:str=None,
        local_tx_manifest_path=str(Path.home()/'.eth'/'tx.manifest'),
        contract_registry_path=str(Path.home()/'.eth'/'contracts.ini'),
        peer_coinbase_registry_path=str(Path.home()/'.eth'/'peers.ini')):

        self.contracts:dict[str,ContractArtifacts] = {}
        self.session = None

        self.transaction_manifest = LocalTxManifest(local_tx_manifest_path)
        self.contract_registry = cfgp.ConfigParser()
        self.contract_registry.optionxform = str
        self.contract_registry_path = contract_registry_path
        self.contract_registry.read(contract_registry_path)
        if not "Contracts" in self.contract_registry:
            self.contract_registry['Contracts'] = {}

        self.peer_coinbase_registry = cfgp.ConfigParser()
        self.peer_coinbase_registry.optionxform = str
        self.peer_coinbase_registry_path = peer_coinbase_registry_path
        self.peer_coinbase_registry.read(peer_coinbase_registry_path)
        if not 'Coinbase' in self.peer_coinbase_registry:
            self.peer_coinbase_registry['Coinbase'] = {}

        self.data_dir = ''
        self.networkid = 2022
        self.host = host
        
        self.http = self.host and len(self.host)>6 and 'http://' in self.host[:6]

        #Configuration
        self.netrestrict = []
        self.password_file = ''
    
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
        ip:str=getPrimaryIP(),
        netrestrict:list[str]=[],
        boot_file=str(Path.home()/'.eth'/'boot'),
        force=True
        ):
        if force:
            self.stopDaemon()
        
        self.data_dir = data_dir
        self.networkid=networkid

        cmd = ['geth','--datadir',data_dir,'--networkid',str(networkid),'--nat','extip:'+ip]
        if netrestrict:
            cmd.append('--netrestrict')
            cmd.append(','.join(netrestrict))
            self.netrestrict = netrestrict

        if os.path.isfile(boot_file):
            bootnodes = ''
            with open(boot_file,'r') as f:
                bootnodes = f.read().strip()
            if bootnodes:
                cmd += ['--bootnodes',bootnodes]

        if platform.system()=='Windows':
            subprocess.Popen(cmd,start_new_session=True,close_fds=True,creationflags=subprocess.DETACHED_PROCESS)
        else:
            subprocess.Popen(cmd,start_new_session=True,close_fds=True)
        while not self.checkDaemonRunning():
            print("Waiting for geth daemon...")
            time.sleep(1)
        #while True:
        if self.host:
            output = subprocess.run(['geth','attach',self.host,'--exec','admin.nodeInfo'],capture_output=True,text=True)
        else:
            time.sleep(5)
        #    print(output.stdout,output.stderr)
        #    break
        print(cmd)
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
    
    def getContractAddress(self,contract_name:str)->str:
        if not 'Contracts' in self.contract_registry:
            self.contract_registry['Contracts'] = {}
            return ''
        if not contract_name in self.contract_registry['Contracts']:
            return ''
        return self.contract_registry['Contracts'][contract_name]

    def connect(self):
        self.http = self.host and len(self.host)>6 and 'http://' in self.host[:6]
        if self.http:
            self.session = Web3(Web3.HTTPProvider(self.host))
        else:
            #if platform.system() == 'Windows':
            provider = Web3.IPCProvider()
            print("Overwriting default with",self.host)
            provider.ipc_path = self.host
            provider._socket.ipc_path = self.host
            #else:
                #provider = Web3.IPCProvider(self.host)
            #    provider = Web3.IPCProvider()
            #    provider.ipc_path = self.host
            #    provider._socket.ipc_path = self.host
            #Retry
            for _ in range(10):
                self.session = Web3(provider)
                if self.session.isConnected():
                    print('Connected!')
                    break
                else:
                    time.sleep(1)
        if self.session.isConnected():
            self.session.middleware_onion.inject(geth_poa.geth_poa_middleware,layer=0)
            #print(self.session.eth.accounts)
            self.session.eth.default_account = self.session.eth.accounts[0]
        else:
            print("Failed to connect to Geth client via IPC")

    def importContractArtifact(self,contract_name:str,filepath:str)->bool:
        artifacts = ContractArtifacts()
        if artifacts.load(filepath):
            self.contracts[contract_name] = artifacts
            return True
        return False

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

        self.contracts[contract_name] = artifacts

        print('Saving Contract Artifacts to',dest_dir)
        artifacts.save(dest_dir)

    def publishContract(self,contract_name:str,*args,**kwargs)->tuple[bool,str]:
        if not contract_name in self.contracts:
            print("Contract with name:",contract_name,"was not found!")
            return False,''
        else:
            #Otherwise publish the contract and note the transaction in the registry
            ca = self.contracts[contract_name]
            t = Transaction(TxType.CONTRACT)
            contract_obj = self.session.eth.contract(abi=ca.abi,bytecode=ca.bytecode)
            tx_hash = contract_obj.constructor(*args,**kwargs).transact()
            tx_receipt = self.session.eth.wait_for_transaction_receipt(tx_hash)

            print(tx_hash)
            print(tx_receipt)

            t.addTxInfo(tx_hash,tx_receipt,{'name':contract_name})
            self.contract_registry['Contracts'][contract_name] =  tx_receipt.contractAddress
            self.transaction_manifest.addTx(t)
            
            self.transaction_manifest.save()

            with open(self.contract_registry_path,'w') as f:
                self.contract_registry.write(f)
            
    def callContract(self,contract_name:str,func_name:str,localized:bool=True,tx={},*args,**kwargs)->bool:
        try:
        #if True:
            print(1)
            if not contract_name in self.contract_registry['Contracts']:
                print(2)
                if not contract_name in self.contracts:
                    print("Contract with name:",contract_name,"was not found!")
                    return False
                else:
                    print(3)
                    #Otherwise publish the contract and note the transaction in the registry
                    self.publishContract(contract_name)
            else:
                #Else interact with the live contract instance.
                #TODO: Need to setup ABI access over shared MFS or cluster pins
                #       For now assume the contract artifacts are already loaded
                print(4)
                contract_inst = self.session.eth.contract(address=self.contract_registry['Contracts'][contract_name],abi=self.contracts[contract_name].abi)
                if localized:
                    print(5)
                    cf = contract_inst.get_function_by_name(func_name)
                    output = cf(*args,**kwargs).call(tx)
                    return output
                else:
                    print(6)
                    tx_hash = contract_inst.functions[func_name](*args,**kwargs).transact(tx)
                    tx_receipt = self.session.eth.wait_for_transaction_receipt(tx_hash)
                    t = Transaction(txtype=TxType.CONTRACT)
                    t.addTxInfo(tx_hash,tx_receipt)
                    success = self.transaction_manifest.addTx(t)
                    if success:
                        print(7)
                        self.transaction_manifest.save()
                    else:
                        print("ERROR: Could not add transaction to manifest!")
                        print(t.toJSON())
                    
        except Exception as e:
            print(e)
            return False
        return True
    
    def sendEtherToPeer(self,recipient_address,amount_wei):
        tx = {
            'from': self.session.eth.coinbase,
            'to': recipient_address,
            'value': amount_wei
        }
        t = Transaction()
        tx_hash = self.session.eth.send_transaction(tx)
        tx_receipt = self.session.eth.wait_for_transaction_receipt(tx_hash)
        t.addTxInfo(tx_hash,tx_receipt)
        success = self.transaction_manifest.addTx(t)
        if success:
            self.transaction_manifest.save()
        else:
            print("ERROR: Could not add transaction to manifest!")
            print(t.toJSON())
        pass
    
    def getSigners(self):
        response = self.session.provider.make_request('clique_getSigners',[])
        if 'result' in response:
            return response['result']
        return []

    def inspectBlocksForTransactions(self,start_index:int,count:int,filter_local_node:bool=True):
        if count<1:
            count = 1
        if start_index <0:
            start_index = 0
        
        for i in range(start_index,start_index+count):
            #print(i)
            try:
                blk = self.session.eth.get_block(i,False)
                if blk['transactions']:
                    #print("\nBlock",i,blk['transactions'],'\n')
                    print("\nBlock",i,blk,'\n')
                    for j,tx in enumerate(blk['transactions']):
                        receipt = self.session.eth.get_transaction_receipt(tx)['logs']
                        print('Transaction',j,"Receipt:\n",receipt)
            except:
                #print("Failed to get block number",i)
                pass
        pass
    
    def proposeSigner(self):
        pass
    


