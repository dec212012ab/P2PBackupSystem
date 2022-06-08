
import argparse
import os
import pathlib
from pathlib import Path
import platform
from re import sub
import requests
import sys
import shutil
import subprocess
from zipfile import ZipFile

from versions import go_version, ipfs_version


tmp_dir = os.path.join(os.path.dirname(os.path.normpath(sys.argv[0])),'.tmp')

def downloadFile(url,dest_dir):
    if not os.path.isdir(dest_dir):
        os.makedirs(dest_dir)
    url_base = os.path.dirname(url)
    url_fname = os.path.basename(url)
    if not os.path.isfile(os.path.join(dest_dir,url_fname)):
        r = requests.get(url_base+url_fname)
        if r.status_code != 200:
            print("Error downloading",url_fname,'from',url_base+url_fname)
            print(r.status_code,r.text)
            exit(1)
        with open(os.path.join(dest_dir,url_fname),'wb') as f:
            f.write(r.content)
    return url_fname

def installGoLang(args):
    global tmp_dir
    tmp_out = None
    go_url = 'https://go.dev/dl/'
    go_fname = 'go'+go_version+'.windows-amd64.msi'

    try:
        tmp_out = subprocess.run(['go','version'],capture_output=True,text=True).stdout
        assert tmp_out[:10] == 'go version','There appears to be an issue retrieving the Go version...'
    except FileNotFoundError:
        print("Go installation not found")
    if tmp_out:
        print("Go already installed: ",tmp_out)
    else:
        if not args.noinstall:
            print("Acquiring Go installer...")
            go_fname = downloadFile(go_url+go_fname,tmp_dir)
            subprocess.run([
                "msiexec","/i",os.path.join(tmp_dir,go_fname)
            ])

def installIPFS(args):
    global tmp_dir
    ipfs_url = 'https://github.com/ipfs/go-ipfs/releases/download/v'+ipfs_version+'/'
    ipfs_fname = 'go-ipfs_v'+ipfs_version+'_windows-amd64.zip'
    
    tmp_out = None
    try:
        tmp_out = subprocess.run(['ipfs','version'],capture_output=True,text=True).stdout
        assert tmp_out[:12] == 'ipfs version','There appears to be an issue retrieving the IPFS version...'
    except:
        print("IPFS installation not found")
    if tmp_out:
        print("IPFS already installed: ",tmp_out)
    else:
        if not args.noinstall:
            print("Acquiring IPFS...")
            ipfs_fname = downloadFile(ipfs_url+ipfs_fname,tmp_dir)


def parseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument('--noinstall',action='store_true',help='Prevents download and installation of packages')
    parser.add_argument('--clean',action='store_true',help='Removes any preexisting installation artifacts before checking and installing packages')
    parser.add_argument('--ipfs_first_node',action='store_true',help='Should be set for the first node in the network installing the software to generate a shared IPFS swarm key')
    return parser.parse_args()

def main():
    global tmp_dir
    args = parseArgs()
    if args.clean:
        if os.path.isdir(tmp_dir):
            shutil.rmtree(tmp_dir)
    
    os.makedirs(tmp_dir,exist_ok=True)
    
    if platform.system() == 'Windows':
        #installGoLang()
        installIPFS(args)

        pass
    else: #NOTE: Currently not handling MacOS, just linux
        pass

if __name__ == '__main__':
    main()
