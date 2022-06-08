import sys
import os
import json
import argparse

import multivolumefile
import py7zr

from ipfs import IPFS, IPFSCluster
from geth_helper import GethHelper
from app_cli import CLIHelper
#from app_cli_linux import CLIHelper


def parseArgs():
    pass

def main():
    ipfs_helper = IPFS()
    ipfscl_helper = IPFSCluster()
    geth_helper = GethHelper()

    cli = CLIHelper(ipfs_helper,ipfscl_helper,geth_helper)
    cli.construct()
    
    cli.menu.show()

    pass

if __name__ == '__main__':
    main()