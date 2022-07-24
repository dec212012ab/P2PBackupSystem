import argparse

import json
from re import sub
import multivolumefile
import os
import platform
import psutil
import subprocess
import sys
import time

from pathlib import Path

from ipfs import IPFS, IPFSCluster
from geth_helper import GethHelper
from app_cli import CLIApp
from chunker import Chunker

import tkinter as tk
from tkinter import simpledialog, messagebox

import threading
from signers import SignerMonitor

def isWindows():
    return platform.system() == 'Windows'

def findProcsByName(name):
    "Return a list of processes matching 'name'."
    ls = []
    for p in psutil.process_iter(["name", "exe", "cmdline"]):
        if name == p.info['name'] or \
                p.info['exe'] and os.path.basename(p.info['exe']) == name or \
                p.info['cmdline'] and p.info['cmdline'][0] == name:
            ls.append(p)
    return ls

def stopDaemon(name):
    proc_list = findProcsByName(name)
    for proc in proc_list:
        print("Stopping "+ name +" process with PID",proc.pid)
        proc.kill()

def ensureDaemon(name,start_cmd,hide_output=True):
    if len(findProcsByName(start_cmd[0]))<1:
        print(name,"daemon is not running. Starting up the",name,"daemon...")
        if isWindows():
            subprocess.Popen(start_cmd,start_new_session=True,close_fds=True,creationflags=subprocess.DETACHED_PROCESS)
        else:
            if hide_output:
                subprocess.Popen(start_cmd,start_new_session=True,close_fds=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            else:
                subprocess.Popen(start_cmd,start_new_session=True,close_fds=True)
        while not findProcsByName(start_cmd[0]):
            print("Waiting for",name,"daemon...")
            time.sleep(1)
        print(name,"daemon started!")
    else:
        print(name,'daemon is running.')

def parseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stop_daemons',action='store_true',help='If set then the program stops any existing IPFS, IPFS-Cluster, or Geth daemons and exits.')
    parser.add_argument('--netrestrict',type=str,
        #default='192.168.3.0/24,192.168.2.0/24',
        default='192.168.29.0/24',
        help='Comma separated list of restricted subnets for Geth. Gets passed directly to the Geth daemon.')
    parser.add_argument('--contract_dir',type=str,default='./contracts',help='The directory with the .sol or .sc files with smart contract information.')
    return parser.parse_args()

def unlockCoinbase(geth):
    pswd = ''
    unlocked = False
    retry_count = 10
    while not unlocked:
        pswd = simpledialog.askstring('Unlock Ethereum Account [' + geth.session.geth.admin.datadir()+']','Password:',show='*')
        if not pswd:
            response = messagebox.askyesno("Abort?","There was no password entered into the prompt. Should the program quit?")
            if response:
                return False
            else:
                continue
        try:
            unlocked = geth.session.geth.personal.unlock_account(geth.session.eth.accounts[0],pswd,0)
        except:
            unlocked = False
        if not unlocked:
            if retry_count<=0:
                messagebox.showerror("Tries Expired",'Number of password tries exceeded! The program will now quit.')
                return False
            response = messagebox.askyesno("Incorrect Password","The entered password was incorrect. Try again? ("+str(retry_count-1)+' tries remaining)')
            if response:
                retry_count -= 1
                continue
            else:
                return False
    return unlocked

def scanForContracts(geth,contract_dir):
    for item in os.listdir(contract_dir):
        split_item = os.path.splitext(item)
        if split_item[-1] == '.sol':
            print(os.path.join(contract_dir,split_item[0]+'.sc'))
            if os.path.isfile(os.path.join(contract_dir,split_item[0]+'.sc')):
                geth.importContractArtifact(split_item[0],os.path.join(contract_dir,split_item[0]+'.sc'))
                print("Imported precompiled contract:",os.path.join(contract_dir,split_item[0]+'.sc'))
            elif not str(split_item[0]).lower() in geth.contract_registry:
                response = messagebox.askyesno("Discovered Contract Source",'Found contract ' + item + '. Should it be compiled and published?')
                if response:
                    geth.session.geth.miner.start()
                    geth.compileContractSource(split_item[0],os.path.join(contract_dir,item))
                    geth.publishContract(split_item[0])
                    geth.session.geth.miner.stop()

def main():
    root = tk.Tk()
    root.withdraw()
    '''c = Chunker(20,6)
    #c.generateLUT('.')
    paths = [os.path.abspath('.')]
    paths.append(os.path.abspath('../recovery_test.py'))
    staging_dir = os.path.abspath('../staging')
    c.stageChunks(staging_dir,paths,'asdf_')

    return'''

    args = parseArgs()

    if args.stop_daemons:
        print("Stopping existing daemons...")
        stopDaemon('ipfs')
        stopDaemon('ipfs-cluster-service')
        g = GethHelper()
        g.stopDaemon()
        exit(0)

    ensureDaemon('IPFS',['ipfs','daemon'])
    while True:
        output = subprocess.run(['ipfs','--version'],capture_output=True,text=True)
        if 'ipfs version ' in output.stdout:
            break
    ensureDaemon('IPFS-Cluster-Service',['ipfs-cluster-service','daemon'],True)
    while True:
        output = subprocess.run(['ipfs-cluster-service','--version'],capture_output=True,text=True)
        if 'ipfs-cluster-service version ' in output.stdout:
            break

    ipfs_helper = IPFS()
    ipfscl_helper = IPFSCluster()
    if isWindows():
        geth_helper = GethHelper("\\\\.\\pipe\\geth.ipc")
    else:
        geth_helper = GethHelper(str(Path.home()/'.eth'/'node0'/'geth.ipc'))

    geth_helper.startDaemon(netrestrict=args.netrestrict.split(','),hide_output=True)
    geth_helper.connect()

    if geth_helper.session.isConnected():
        print("Geth connected!")
    else:
        print("Could not start Geth. Quitting.")
        exit(1)

    if not unlockCoinbase(geth_helper):
        root.destroy()
        return

    if geth_helper.session.eth.coinbase.lower() in geth_helper.getSigners():
        geth_helper.session.geth.miner.start()
    root.destroy()
    scanForContracts(geth_helper,args.contract_dir)
    
    print(geth_helper.contract_registry['Contracts'])

    cli = CLIApp(ipfs_helper,ipfscl_helper,geth_helper)
    cli.construct()
    
    signer_monitor:SignerMonitor = SignerMonitor(geth_helper)
    monitor_thread = threading.Thread(target=signer_monitor.run)
    
    print("Starting monitor thread...")
    monitor_thread.start()
    
    cli.menu.show()

    signer_monitor.stopSignal()

    print("Waiting for monitor thread to exit")
    monitor_thread.join()

    pass

if __name__ == '__main__':
    main()