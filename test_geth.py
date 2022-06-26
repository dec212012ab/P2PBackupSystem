
from geth_helper import *
from pathlib import Path
import platform

def main():
    #geth = GethHelper("http://localhost:8545",str(Path.home()/'.eth'/'node1'))
    if platform.system() == 'Windows':
        geth = GethHelper("\\\\.\\pipe\\geth.ipc")
    else:
        geth = GethHelper(str(Path.home()/'.eth'/'node0'/'geth.ipc'))
    geth.startDaemon(netrestrict=['192.168.2.0/24'])
    geth.connect()
    #print(geth.session.eth.get_balance(geth.session.eth.coinbase))
    if geth.session.isConnected():
        print(geth.session.isConnected())
        #print(geth.session.eth.get_balance(geth.session.eth.default_account))
        #print(geth.session.geth.admin.node_info())

        #geth.compileContractSource('Hello','./contracts/Hello.sol')
        hello_contract_artifacts = ContractArtifacts()
        hello_contract_artifacts.load('./contracts/Hello.sc')

        hello = geth.session.eth.contract(abi=hello_contract_artifacts.abi,bytecode=hello_contract_artifacts.bytecode)

        ether_amount = geth.session.fromWei(geth.session.eth.get_balance(geth.session.eth.default_account),'ether')
        print("Ether:",ether_amount)

        print(hello)
    
    print("Quitting")

    geth.stopDaemon()


if __name__ == '__main__':
    main()