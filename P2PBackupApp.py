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


from ipfs import IPFS, IPFSCluster
from geth_helper import GethHelper
from app_cli import CLIApp
from chunker import Chunker


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
        print("Stopping IPFS process with PID",proc.pid)
        proc.kill()

def ensureDaemon(name,start_cmd):
    if len(findProcsByName(start_cmd[0]))<1:
        print(name,"daemon is not running. Starting up the",name,"daemon...")
        if isWindows():
            subprocess.Popen(start_cmd,start_new_session=True,close_fds=True,creationflags=subprocess.DETACHED_PROCESS)
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
    return parser.parse_args()

def main():

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
        stopDaemon('geth')
        exit(0)

    ensureDaemon('IPFS',['ipfs','daemon'])
    while True:
        output = subprocess.run(['ipfs','--version'],capture_output=True,text=True)
        if 'ipfs version ' in output.stdout:
            break
    ensureDaemon('IPFS-Cluster-Service',['ipfs-cluster-service','daemon'])
    while True:
        output = subprocess.run(['ipfs-cluster-service','--version'],capture_output=True,text=True)
        if 'ipfs-cluster-service version ' in output.stdout:
            break

    ipfs_helper = IPFS()
    ipfscl_helper = IPFSCluster()
    geth_helper = GethHelper()

    cli = CLIApp(ipfs_helper,ipfscl_helper,geth_helper)
    cli.construct()
    
    cli.menu.show()

    pass

if __name__ == '__main__':
    main()