
from geth_helper import *
from pathlib import Path
import platform

def main():
    #geth = GethHelper("http://localhost:8545",str(Path.home()/'.eth'/'node1'))
    if platform.system() == 'Windows':
        geth = GethHelper("\\\\.\\pipe\\geth.ipc")
    else:
        geth = GethHelper(str(Path.home()/'.eth'/'node0'/'geth.ipc'))
    geth.startDaemon(netrestrict=['192.168.3.0/24'])
    geth.connect()
    #print(geth.session.eth.get_balance(geth.session.eth.coinbase))
    if geth.session.isConnected():
        print(geth.session.isConnected())
        geth.session.geth.personal.unlock_account(geth.session.eth.accounts[0],'eth')
        geth.session.geth.miner.start()

        #geth.compileContractSource('Faucet','./contracts/Faucet.sol')
        
        #geth.publishContract('Faucet')

        print(geth.session.geth.admin.peers()[0]['enode'])

        geth.importContractArtifact('Faucet','contracts/Faucet.sc')
        time.sleep(10)
        #tx = {
        #    'from':geth.session.eth.coinbase,
        #    'to':Web3.toChecksumAddress('0xc7bc027fed2af16947258afa42c30446bd5bb7e0'),
        #    'value': Web3.toWei(5,'ether')
        #}

        tx = geth.session.eth.contract(address=geth.getContractAddress('Faucet'),abi=geth.contracts['Faucet'].abi).functions
        tx['donateToFaucet']().transact({
            'value': Web3.toWei(5,'ether')
        })


        #geth.session.eth.send_transaction(tx)

        result = geth.callContract(
            'Faucet',
            'getFaucetBalance',
            True
        )

        print(result)

        return 

        geth.callContract(
            'Faucet',
            'donateToFaucet',
            False
        )


        geth.callContract(
            contract_name='Faucet',
            func_name='requestFunds',
            localized=False,
            func_args=[geth.session.eth.accounts[0]]
            )
        
        #faucet = geth.session.eth.contract(address=geth.contracts['Faucet'].address,abi=geth.contracts['Faucet'].abi)

        print(geth.session.eth.get_balance(geth.session.eth.coinbase))



        #geth.importContractArtifact('Faucet','./contracts/Faucet.sc')
        #

        #time.sleep(5)

        #geth.session.geth.miner.stop()


        #faucet_ca = ContractArtifacts()
        
        

        #print(geth.contracts)


        #hello_contract_artifacts = ContractArtifacts()
        #hello_contract_artifacts.load('./contracts/Hello.sc')

        #hello = geth.session.eth.contract(abi=hello_contract_artifacts.abi,bytecode=hello_contract_artifacts.bytecode)

        #ether_amount = geth.session.fromWei(geth.session.eth.get_balance(geth.session.eth.default_account),'ether')
        #print("Ether:",ether_amount)

        #print(hello)
    
    print("Quitting")

    geth.stopDaemon()


if __name__ == '__main__':
    main()