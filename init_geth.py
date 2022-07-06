
import sys
import shutil
from geth_helper import *
from pathlib import Path
import platform
import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog

root = tk.Tk()
root.withdraw()
root.iconify()

transfer_to_contract = True
timeout = 10

def main():
    global transfer_to_contract, timeout
    if platform.system() == 'Windows':
        geth = GethHelper("\\\\.\\pipe\\geth.ipc")
    else:
        geth = GethHelper(str(Path.home()/'.eth'/'node0'/'geth.ipc'))
    geth.startDaemon(netrestrict=['192.168.3.0/24','192.168.2.0/24'],hide_output=False)
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
                        geth.session.geth.miner.start()
                        geth.compileContractSource(split_item[0],os.path.join('./contracts',item))
                        geth.publishContract(split_item[0])
                        geth.session.geth.miner.stop()

        #Reduce locktime for now
        print("Reducing lockout time")
        geth.session.geth.miner.start()
        response = geth.callContract('Faucet','setLockTimeSeconds',False,{},0)
        geth.session.geth.miner.stop()
        print('Lock time modified:',response)

        
        if transfer_to_contract:
            print('Donating 1000 ether to faucet...')
            geth.session.geth.miner.start()
            geth.callContract('Faucet','donateToFaucet',False,tx={'value':Web3.toWei(1000,'ether')})
            geth.session.geth.miner.stop()
            amount = geth.callContract('Faucet','getFaucetBalance',True)
            print('Contract has',Web3.fromWei(amount,'ether'),'ether')
        
        #Set up peer coinbase/checksum address. 
        # NOTE: In practice will use Remote MFS pinning
        print("Looking for peers...")
        while not geth.session.geth.admin.peers():
            time.sleep(1)
            timeout -= 1
            if timeout<=0:
                print("Peer search timed out...")
                break
        #print(geth.session.geth.admin.peers())

        peer_path = os.path.join(os.path.dirname(sys.argv[0]),'install/redist/geth/peers')
        
        for peer in geth.session.geth.admin.peers():
            if not str(peer['id']) in geth.peer_coinbase_registry['Coinbase'] or geth.session.eth.get_balance(geth.peer_coinbase_registry['Coinbase'][peer['id']])<Web3.toWei(10,'ether'):
                #response = messagebox.askyesno("Discovered New Peer",'Found new peer ' + peer['id'] + '. Do you want to enter its checksum address?')
                #if response:
                if peer['id'] in os.listdir(peer_path):
                    #addr = simpledialog.askstring("Checksum Address Entry",'Address:')
                    f = open(os.path.join(peer_path,peer['id']))
                    addr = f.read().strip()
                    f.close()
                    geth.peer_coinbase_registry['Coinbase'][str(peer['id'])] = addr
                    with open(geth.peer_coinbase_registry_path,'w') as f:
                        geth.peer_coinbase_registry.write(f)
                    print("Calling faucet contract for new peer",peer['id'])
                    geth.session.geth.miner.start()
                    while not geth.callContract('Faucet','requestFunds',False,{},Web3.toChecksumAddress(addr.lower())):
                        print("Faucet is still locked... Trying again after 30 seconds...")
                        time.sleep(30)
                    time.sleep(30)

                    print("Peer has",Web3.fromWei(geth.session.eth.get_balance(geth.peer_coinbase_registry['Coinbase'][peer['id']]),'ether'),'ether')
                    geth.session.geth.miner.stop()
        
        #Add self
        if not geth.session.geth.admin.node_info()['id'] in geth.peer_coinbase_registry['Coinbase']:
            geth.peer_coinbase_registry['Coinbase'][geth.session.geth.admin.node_info()['id']] = geth.session.eth.coinbase
            with open(geth.peer_coinbase_registry_path,'w') as f:
                geth.peer_coinbase_registry.write(f)


        shutil.copy(str(Path.home()/'.eth'/'contracts.ini'),str(os.path.join(os.path.dirname(sys.argv[0]),'install/redist/geth/')))
        shutil.copy(str(geth.peer_coinbase_registry_path),str(os.path.join(os.path.dirname(sys.argv[0]),'install/redist/geth/')))

        #Try to get signers with direct jsonrpc request
        print(geth.getSigners())
        print(geth.session.eth.coinbase)

        #print('Inspecting...')
        #geth.inspectBlocksForTransactions(0,1000)

        #geth.stopDaemon()
        geth.session.geth.miner.start()
        return

if __name__ == '__main__':
    main()
    root.destroy()