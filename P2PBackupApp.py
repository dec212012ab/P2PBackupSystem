import argparse

import json
from re import sub
import multivolumefile
import os
import psutil
import py7zr
import subprocess
import sys
import time


from ipfs import IPFS, IPFSCluster
from geth_helper import GethHelper
from app_cli import CLIHelper


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
    if not findProcsByName(name):
        print(name,"daemon is not running. Starting up the",name,"daemon...")
        subprocess.Popen(start_cmd,start_new_session=True,close_fds=True,creationflags=subprocess.DETACHED_PROCESS)
        while not findProcsByName('ipfs'):
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

    args = parseArgs()

    if args.stop_daemons:
        stopDaemon('ipfs')
        stopDaemon('ipfs-cluster-service')
        stopDaemon('geth')
        exit(0)

    ensureDaemon('IPFS',['ipfs','daemon'])
    ensureDaemon('IPFS-Cluster-Service',['ipfs-cluster-service','daemon'])
    return

    ipfs_helper = IPFS()
    ipfscl_helper = IPFSCluster()
    geth_helper = GethHelper()

    cli = CLIHelper(ipfs_helper,ipfscl_helper,geth_helper)
    cli.construct()
    
    cli.menu.show()

    pass

if __name__ == '__main__':
    main()