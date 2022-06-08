from web3 import Web3
from web3.middleware import geth_poa
from solcx import compile_source, compile_files
import json

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
    def __init__(self):
        self.contracts = {}
        self.host = None
        self.session = None
        self.transaction_manifest = None
        self.contract_manifest = None
        pass
    def connect(self,host):
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
    


