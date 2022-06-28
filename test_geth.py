
from geth_helper import *
from pathlib import Path
import platform
import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog

root = tk.Tk()
root.withdraw()
root.iconify()

transfer_to_contract = False

def main():
    if platform.system() == 'Windows':
        geth = GethHelper("\\\\.\\pipe\\geth.ipc")
    else:
        geth = GethHelper(str(Path.home()/'.eth'/'node0'/'geth.ipc'))
    geth.startDaemon(netrestrict=['192.168.3.0/24'])
    geth.connect()
    
    if geth.session.isConnected():
        #Unlock account for mining
        pswd = ''
        unlocked = False
        retry_count = 10
        while not unlocked:
            pswd = simpledialog.askstring('Unlock Ethereum Miner [' + geth.session.geth.admin.datadir()+']','Password:',show='*')
            if not pswd:
                response = messagebox.askyesno("Abort?","There was no password entered into the prompt. Should the program quit?")
                if response:
                    return
                else:
                    continue
            try:
                unlocked = geth.session.geth.personal.unlock_account(geth.session.eth.accounts[0],pswd,0)
            except:
                unlocked = False
            if not unlocked:
                if retry_count<=0:
                    messagebox.showerror("Tries Expired",'Number of password tries exceeded! The program will now quit.')
                    return
                response = messagebox.askyesno("Incorrect Password","The entered password was incorrect. Try again? ("+str(retry_count-1)+' tries remaining)')
                if response:
                    retry_count -= 1
                    continue
                else:
                    return
        
        geth.session.geth.miner.start()

        #Scan for new contracts
        for item in os.listdir('./contracts'):
            split_item = os.path.splitext(item)
            if split_item[-1] == '.sol':
                print(os.path.join('./contracts',split_item[0]+'.sc'))
                if os.path.isfile(os.path.join('./contracts',split_item[0]+'.sc')):
                    geth.importContractArtifact(split_item[0],os.path.join('./contracts',split_item[0]+'.sc'))
                    print("Imported precompiled contract:",os.path.join('./contracts',split_item[0]+'.sc'))
                elif not str(split_item[0]).lower() in geth.contract_registry:
                    response = messagebox.askyesno("Discovered Contract Source",'Found contract ' + item + '. Should it be compiled and published?')
                    if response:
                        geth.compileContractSource(split_item[0],os.path.join('./contracts',item))
                        geth.publishContract(split_item[0])
        
        if transfer_to_contract:
            print('Donating 100 ether to faucet...')
            geth.callContract('Faucet','donateToFaucet',False,tx={'value':Web3.toWei(100,'ether')})
            amount = geth.callContract('Faucet','getFaucetBalance',True)
            print('Contract has',Web3.fromWei(amount,'ether'),'ether')
        
        #Set up peer coinbase/checksum address. 
        # NOTE: In practice will use Remote MFS pinning
        print("Looking for peers...")
        timeout = 1
        while not geth.session.geth.admin.peers():
            time.sleep(1)
            timeout -= 1
            if timeout<=0:
                print("Peer search timed out...")
                break
        #print(geth.session.geth.admin.peers())
        
        for peer in geth.session.geth.admin.peers():
            if not str(peer['id']) in geth.peer_coinbase_registry['Coinbase']:
                response = messagebox.askyesno("Discovered New Peer",'Found new peer ' + peer['id'] + '. Do you want to enter its checksum address?')
                if response:
                    addr = simpledialog.askstring("Checksum Address Entry",'Address:')                    
                    geth.peer_coinbase_registry['Coinbase'][str(peer['id'])] = addr
                    with open(geth.peer_coinbase_registry_path,'w') as f:
                        geth.peer_coinbase_registry.write(f)
                    print("Calling faucet contract for new peer",peer['id'])
                    geth.callContract('Faucet','requestFunds',False,{},addr)


        #Try to get signers with direct jsonrpc request
        print(geth.getSigners())
        geth.inspectBlocksForTransactions(0,1000)

        geth.stopDaemon()
        return

        #geth.compileContractSource('Faucet','./contracts/Faucet.sol')
        
        #geth.publishContract('Faucet')

        #print(geth.session.geth.admin.peers()[0]['enode'])

        geth.importContractArtifact('Faucet','contracts/Faucet.sc')
        time.sleep(10)
        #tx = {
        #    'from':geth.session.eth.coinbase,
        #    'to':Web3.toChecksumAddress('0xc7bc027fed2af16947258afa42c30446bd5bb7e0'),
        #    'value': Web3.toWei(5,'ether')
        #}

        #tx = geth.session.eth.contract(address=geth.getContractAddress('Faucet'),abi=geth.contracts['Faucet'].abi).functions
        #tx['donateToFaucet']().transact({
            #'value': Web3.toWei(geth.session.eth.get_balance(geth.session.eth.coinbase),'Wei'),
        #    Web3.toWei(5,'ether'),
        #})


        #geth.session.eth.send_transaction(tx)


        time.sleep(15)

        result = geth.callContract(
            'Faucet',
            'getFaucetBalance',
        #    'requestFunds',
            True,
        #    geth.session.eth.coinbase
        )

        print(result)

        print('I have',geth.session.eth.get_balance(geth.session.eth.coinbase))
        print("Quitting")

        geth.stopDaemon()

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
    
    


if __name__ == '__main__':
    main()
    root.destroy()