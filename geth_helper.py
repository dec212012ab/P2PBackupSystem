from web3 import Web3
from web3.middleware import geth_poa
from solcx import compile_source, compile_files
import json
import socket

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
        self.src = None
        self.abi = None
        self.bytecode = None
    def save(self,save_src=False,save_abi=True,save_bytecode=False):
        pass

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

class GethHelper:
    def __init__(self,host,data_dir,is_signer=False,is_bootstrap=False):
        self.contracts = {}
        self.host = host
        self.session = None
        self.transaction_manifest = None
        self.contract_manifest = None
        self.data_dir = data_dir
        self.is_signer = is_signer
        pass
    def connect(self):
        self.session = Web3(Web3.HTTPProvider(self.host))
        self.session.middleware_onion.inject(geth_poa.geth_poa_middleware,layer=0)
        self.session.eth.default_account = self.session.eth.accounts[0]
        pass
    def loadTransactionManifest(self,filepath):
        pass
    def importContractABI(self,contract_name,filepath):
        pass
    def loadContractSource(self,contract_name,filepath):
        pass
    def compileContractSource(self,contract_name,filepath=None):
        pass
    def callContract(self,contract_name,localized=True,*args,**kwargs):
        pass
    def sendEtherToPeer(self,recipient,amount):
        pass
    def inspectBlocksForTransactions(self,start_index,end_index,filter_local_node=True):
        pass
    


