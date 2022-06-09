
import argparse
import os
import pathlib
from pathlib import Path
import platform
from re import sub
import requests
import shutil
import signal
import socket
import subprocess
import sys
from zipfile import ZipFile

from versions import go_version, ipfs_version, ipfs_cluster_version

tmp_dir = os.path.join(os.path.dirname(os.path.normpath(sys.argv[0])),'.tmp')

sys.path.append(os.path.abspath(os.path.join(tmp_dir,'../..')))

from ipfs import IPFS

def downloadFile(url,dest_dir):
    if not os.path.isdir(dest_dir):
        os.makedirs(dest_dir)
    url_base = os.path.dirname(url)
    url_fname = os.path.basename(url)
    if not os.path.isfile(os.path.join(dest_dir,url_fname)):
        r = requests.get(url_base+'/'+url_fname)
        if r.status_code != 200:
            print("Error downloading",url_fname,'from',url_base+'/'+url_fname)
            print(r.status_code,r.text)
            exit(1)
        with open(os.path.join(dest_dir,url_fname),'wb') as f:
            f.write(r.content)
    else:
        print("Artifact already present in cache. Skipping download.")
    return url_fname

def getPrimaryIP():
    s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    s.settimeout(0)
    IP = None
    try:
        s.connect(('15.255.255.255',1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

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
    print("GoLang Installation Step Complete")

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
            #Download IPFS Zip File
            print("Acquiring IPFS...")
            ipfs_fname = downloadFile(ipfs_url+ipfs_fname,tmp_dir)
            print("Extracting contents to",Path.home()/'Apps'/os.path.splitext(ipfs_fname)[0])
            with ZipFile(os.path.join(tmp_dir,ipfs_fname),'r') as zf:
                zf.extractall(Path.home()/'Apps'/os.path.splitext(ipfs_fname)[0])
            
            #Add path to extracted folder to $PATH
            print("Updating path...")
            p = str(Path.home()/'Apps'/os.path.splitext(ipfs_fname)[0]/'go-ipfs')
            user_path = subprocess.run(["powershell", "-Command","[Environment]::GetEnvironmentVariable('Path','User')"], capture_output=True,text=True).stdout
            
            found = False
            for tmp_path in user_path.strip().split(';'):
                if not tmp_path.strip():
                    continue
                if p == tmp_path:
                    found = True
                    break

            if found:
                print("IPFS location already in PATH!")
            else:
                output = subprocess.run(['setx','PATH',user_path.strip()+p+';']).stdout
                
            
            #Generate Swarm Key for Private IPFS Network
            if args.generate_swarm_key:
                print("Acquiring swarm key generator...")
                subprocess.run(['go','install', 'github.com/Kubuxu/go-ipfs-swarm-key-gen/ipfs-swarm-key-gen@latest'])
                if os.path.isfile(Path.home()/'.ipfs'/'swarm.key'):
                    print("Another swarm key already exists!")
                else:
                    print('Generating swarm key to',Path.home()/'.ipfs'/'swarm.key')
                    if not os.path.isdir(Path.home()/'.ipfs'):
                        os.makedirs(Path.home()/'.ipfs')
                    output = subprocess.run(['ipfs-swarm-key-gen'],capture_output=True,text=True).stdout
                    with open(Path.home()/'.ipfs'/'swarm.key','w') as f:
                        f.write(output)
                    print("NOTE: The Swarm key must be copied to all new nodes joining the private network.")
            
            #Force Private Network with Environment Variable
            print("Setting LIBP2P environment flag to force private IPFS networking...")
            output = subprocess.run(['setx','LIBP2P_FORCE_PNET','1']).stdout
            print(output)

            #Initialize IPFS
            print("Initializing IPFS...")
            output = subprocess.run(['ipfs','init'],capture_output=True,text=True)
            print(output.stdout)
            print(output.stderr)

            #Generate bootstrap
            if args.ipfs_bootstrap_id:
                bootstrap_addr = '/ip4/'+getPrimaryIP()+'/tcp/4001/ipfs/'
                ipfs_ = IPFS()
                proc = subprocess.Popen(['ipfs','daemon'])
                node_id = ipfs_.execute_cmd('id',{}).json()['ID']
                proc.send_signal(signal.CTRL_C_EVENT)
                proc.send_signal(signal.CTRL_C_EVENT)
                bootstrap_addr+=node_id
                print("Saving textual copy of bootstrap address at",str(Path.home()/'.ipfs'/'bootstrap_id.txt'))
                with open(Path.home()/'.ipfs'/'bootstrap_id.txt','w') as f:
                    f.write(bootstrap_addr)
                print('Removing current bootstrap targets')
                output = subprocess.run(['ipfs','bootstrap','rm','--all'],capture_output=True,text=True)
                print(output)

                print('Adding private bootstrap node target')
                output = subprocess.run(['ipfs','bootstrap','add',bootstrap_addr],capture_output=True,text=True)
                print(output)
                pass
    
    print("IPFS Installation Step Complete")

def installIPFSClusterService(args):
    global tmp_dir
    ipfscluster_url = 'https://dist.ipfs.io/ipfs-cluster-service/v'+ipfs_cluster_version+'/'
    ipfscluster_fname = 'ipfs-cluster-service_v'+ipfs_cluster_version+'_windows-amd64.zip'

    tmp_out = None
    try:
        tmp_out = subprocess.run(['ipfs-cluster-service','version'],capture_output=True,text=True)
        assert not 'command not found' in tmp_out, "There appears to be an issue retrieving the IPFS-Cluster-Service version..."
    except:
        print("IPFS-Cluster-Service installation not found")
    
    if not tmp_out: #TODO: Remove not
        print("IPFS-Cluster-Service already installed: ", tmp_out)
    else:
        if not args.noinstall:
            #Download IPFS Zip File
            print("Acquiring IPFS-Cluster-Service...")
            ipfscluster_fname = downloadFile(ipfscluster_url+ipfscluster_fname,tmp_dir)
            print("Extracting contents to",Path.home()/'Apps'/os.path.splitext(ipfscluster_fname)[0])
            with ZipFile(os.path.join(tmp_dir,ipfscluster_fname),'r') as zf:
                zf.extractall(Path.home()/'Apps'/os.path.splitext(ipfscluster_fname)[0])
            
            #Add path to extracted folder to $PATH
            print("Updating path...")
            p = str(Path.home()/'Apps'/os.path.splitext(ipfscluster_fname)[0]/'ipfs-cluster-service')
            user_path = subprocess.run(["powershell", "-Command","[Environment]::GetEnvironmentVariable('Path','User')"], capture_output=True,text=True).stdout
            
            found = False
            for tmp_path in user_path.strip().split(';'):
                if not tmp_path.strip():
                    continue
                if p == tmp_path:
                    found = True
                    break

            if found:
                print("IPFS-Cluster-Service location already in PATH!")
            else:
                output = subprocess.run(['setx','PATH',user_path.strip()+p+';']).stdout
            
            #Initialize Cluster Service
            print("Initializing IPFS-Cluster-Service...")
            if not os.path.isfile(Path.home()/'.ipfs-cluster'/'service.json'):
                output = subprocess.run(['ipfs-cluster-service','init'])
                print('Defaults generated to',str(Path.home()/'.ipfs-cluster'))
            else:
                print("Service configuration already exists! Skipping.")

        print('NOTE: Other IPFS-Cluster Nodes must have the same value for "secret" in service.json!')
        print('IPFS-Cluster-Service Installation Step Complete')
            
    pass

def parseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument('--noinstall',action='store_true',help='Prevents download and installation of packages')
    parser.add_argument('--clean',action='store_true',help='Removes any preexisting installation artifacts before checking and installing packages')
    parser.add_argument('--generate_swarm_key',action='store_true',help='Should be set for the first node in the network installing the software to generate a shared IPFS swarm key')
    parser.add_argument('--ipfs_bootstrap_id',action='store_true',help='If set, will generate a bootstrap_id.txt file in the .ipfs folder to use with other node installations.')
    parser.add_argument('--ipfs_bootstrap_file',type=str,help='Path to file with bootstrap ids to add to the current node. WILL OVERWRITE EXISTING BOOTSTRAP NODE DATA!')
    return parser.parse_args()

def main():
    global tmp_dir
    args = parseArgs()
    if args.clean:
        if os.path.isdir(tmp_dir):
            shutil.rmtree(tmp_dir)
    
    os.makedirs(tmp_dir,exist_ok=True)
    
    if platform.system() == 'Windows':
        #installGoLang(args)
        #installIPFS(args)
        installIPFSClusterService(args)
        

        pass
    else: #NOTE: Currently not handling MacOS, just linux
        pass

if __name__ == '__main__':
    main()
