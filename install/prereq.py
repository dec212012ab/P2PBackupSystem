
import argparse
import ctypes
import json
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
import tarfile
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from zipfile import ZipFile

from versions import go_version, ipfs_version, ipfs_cluster_version,geth_version

tmp_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.normpath(sys.argv[0])),'.tmp'))

sys.path.append(os.path.abspath(os.path.join(tmp_dir,'../..')))

from ipfs import IPFS
import time

tkroot = tk.Tk()
tkroot.withdraw()
#TODO: Bug when using messagebox calls on Ubuntu: Windows don't close after user clicks a button

lPATH = os.getenv('PATH')
home_dir = None #TODO: No longer necessary since sudo is not needed on Ubuntu

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

def isAdmin():
    if platform.system() == 'Windows':
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    else:
        #Assume Ubuntu for now
        return os.getuid()==0

def isWindows():
    return platform.system() == 'Windows'

def installGoLang(args):
    global tmp_dir,lPATH
    tmp_out = None
    go_url = 'https://go.dev/dl/'
    if isWindows():
        go_fname = 'go'+go_version+'.windows-amd64.zip'
    else:
        go_fname = 'go'+go_version+'.linux-amd64.tar.gz'

    try:
        tmp_out = subprocess.run(['go','version'],capture_output=True,text=True).stdout
        assert tmp_out[:10] == 'go version','There appears to be an issue retrieving the Go version...'
    except FileNotFoundError:
        print("Go installation not found")
    if tmp_out and not args.force:
        print("Go already installed: ",tmp_out)
    else:
        if not args.noinstall:
            print("Acquiring Go installer...")
            go_fname = downloadFile(go_url+go_fname,tmp_dir)
            print(os.path.join(tmp_dir,go_fname))
            if isWindows():
                #subprocess.run([
                #    "msiexec","/i",os.path.join(tmp_dir,go_fname)
                #],capture_output=True)
                #messagebox.showinfo('Select Go bin Directory','Please select the bin folder of the Go installation used with the Go installer.',parent=tkroot)
                #go_path = filedialog.askdirectory()
                #if not go_path:
                #    print("Cannot proceed without the bin directory location of the Go installation.")
                #    exit(1)
                with ZipFile(os.path.join(tmp_dir,go_fname),'r') as zf:
                    zf.extractall(str(Path.home()/'Apps'))
            else:
                f = tarfile.open(os.path.join(tmp_dir,go_fname))
                f.extractall(Path.home()/'Apps')
                f.close()
            
            go_path = str(Path.home()/'Apps'/'go')
            print("Extracted go installation to",go_path)
                       
            
            print("Updating path...")
            if isWindows():
                user_path = subprocess.run(["powershell", "-Command","[Environment]::GetEnvironmentVariable('Path','User')"], capture_output=True,text=True).stdout
                
                found = False
                for tmp_path in user_path.strip().split(';'):
                    if not tmp_path.strip():
                        continue
                    if go_path == tmp_path:
                        found = True
                        break

                if found:
                    print("Go location already in PATH!")
                else:
                    output = subprocess.run(['setx','PATH',user_path.strip()+go_path+';'],capture_output=True,text=True)
                    print(output.stdout,output.stderr)
                
                lPATH += ';'+os.path.join(go_path,'bin')+';'+str(Path.home()/'go'/'bin')
                os.environ['PATH'] = lPATH

                output = subprocess.run(['setx','GOROOT',os.path.join(go_path,'bin')],capture_output=True,text=True)
                print(output.stdout,output.stderr)

                output = subprocess.run(['setx','GOPATH',str(Path.home()/'go')],capture_output=True,text=True)
                print(output.stdout,output.stderr)
            else:
                found = False
                for tmp_path in os.environ['PATH'].split(':'):
                    if not tmp_path.strip():
                        continue
                    if os.path.normpath(go_path) == os.path.normpath(tmp_path):
                        found=True
                        break
                
                if found:
                    print("Go location already in PATH!")
                else:
                    with open(os.path.join(home_dir,'.bashrc'),'a') as f:
                        f.write('\nexport GOROOT='+go_path+'\n')
                        f.write('export GOPATH='+os.path.join(home_dir,'go')+'\n')
                        f.write('export PATH=$PATH:$GOROOT/bin:$GOPATH/bin\n')
                    os.environ["GOROOT"] = go_path
                    os.environ['GOPATH'] = os.path.join(home_dir,'go')
                    os.environ["PATH"] +=':'+os.path.join(go_path,'bin')
                    os.environ["PATH"] +=':'+os.path.join(home_dir,'go/bin')
                    print(os.environ['PATH'])
                pass
    print("GoLang Installation Step Complete")

def installIPFS(args):
    global tmp_dir,lPATH
    ipfs_url = 'https://github.com/ipfs/go-ipfs/releases/download/v'+ipfs_version+'/'
    if isWindows():
        ipfs_fname = 'go-ipfs_v'+ipfs_version+'_windows-amd64.zip'
    else:
        ipfs_fname = 'go-ipfs_v'+ipfs_version+'_linux-amd64.tar.gz'

    tmp_out = None
    try:
        tmp_out = subprocess.run(['ipfs','version'],capture_output=True,text=True).stdout
        assert tmp_out[:12] == 'ipfs version','There appears to be an issue retrieving the IPFS version...'
    except:
        print("IPFS installation not found")
    if tmp_out and args.force:
        print("IPFS already installed: ",tmp_out)
    else:
        if not args.noinstall:
            #Download IPFS Zip File
            print("Acquiring IPFS...")
            ipfs_fname = downloadFile(ipfs_url+ipfs_fname,tmp_dir)
            if isWindows():
                print("Extracting contents to",Path.home()/'Apps'/os.path.splitext(ipfs_fname)[0])
                with ZipFile(os.path.join(tmp_dir,ipfs_fname),'r') as zf:
                    zf.extractall(Path.home()/'Apps'/os.path.splitext(ipfs_fname)[0])
            else:
                print("Extracting to"+str(Path.home()/'Apps'/ipfs_fname).replace('.tar.gz',''))
                f = tarfile.open(os.path.join(tmp_dir,ipfs_fname))
                f.extractall(Path.home()/'Apps')
                f.close()
            
            #Add path to extracted folder to $PATH
            print("Updating path...")
            if isWindows():
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
                    user_path = user_path.strip()
                    if not user_path[-1] == ';':
                        user_path+=';'
                    output = subprocess.run(['setx','PATH',user_path+p+';']).stdout
                    lPATH += ';'+p
                    os.environ['PATH'] = lPATH
            else:
                p = str(Path.home()/'Apps'/'go-ipfs') #'/usr/local/go-ipfs'
                found = False
                for tmp_path in os.environ['PATH'].split(':'):
                    if not tmp_path.strip():
                        continue
                    if os.path.normpath(p) == os.path.normpath(tmp_path):
                        found=True
                        break

                if found:
                    print("IPFS location already in PATH!")
                else:
                    with open(os.path.join(home_dir,'.bashrc'),'a') as f:
                        f.write('\nexport PATH=$PATH:'+p+'\n')
                    #if isWindows():
                    #    os.environ['PATH']+=';'+p
                    #else:
                    os.environ['PATH']+=':'+p
                        
            #Generate Swarm Key for Private IPFS Network
            if args.generate_swarm_key:
                print("Acquiring swarm key generator...")
                print(subprocess.run(['go','install', 'github.com/Kubuxu/go-ipfs-swarm-key-gen/ipfs-swarm-key-gen@latest']).stdout)
                if os.path.isfile(Path.home()/'.ipfs'/'swarm.key'):
                    print("Another swarm key already exists!")
                else:
                    dest = os.path.join(args.redist_path,'ipfs')
                    if not os.path.isdir(dest):
                        os.makedirs(dest)
                    dest = os.path.join(dest,'swarm.key')

                    if isWindows():
                        print('Generating swarm key to',Path.home()/'.ipfs'/'swarm.key')
                        if not os.path.isdir(Path.home()/'.ipfs'):
                            os.makedirs(Path.home()/'.ipfs')
                        output = subprocess.run(['ipfs-swarm-key-gen'],capture_output=True,text=True).stdout
                        with open(Path.home()/'.ipfs'/'swarm.key','w') as f:
                            f.write(output)
                    else:
                        swarm_key_path = os.path.join(home_dir,'.ipfs','swarm.key')
                        print("Generating swarm key to",swarm_key_path)
                        if not os.path.isdir(os.path.join(home_dir,'.ipfs')):
                            os.makedirs(os.path.join(home_dir,'.ipfs'))
                        print(subprocess.run(['env'],capture_output=True,text=True).stdout)
                        output = subprocess.run(['ipfs-swarm-key-gen'],capture_output=True,text=True).stdout
                        with open(swarm_key_path,'w') as f:
                            f.write(output)
                    
                    print("Writing to redistributable folder at",args.redist_path)
                    with open(dest,'w') as f:
                        f.write(output)
                    print("NOTE: The Swarm key must be copied to all new nodes joining the private network.")
            
            if args.swarm_key_file:
                dest = str(Path.home()/'.ipfs')
                print('Attempting to copy provided swarm key')
                if not os.path.isdir(dest):
                    os.makedirs(dest)
                if os.path.isfile(args.swarm_key_file):
                    shutil.copy2(args.swarm_key_file,dest)
                
            
            #Force Private Network with Environment Variable
            if isWindows():
                print("Setting LIBP2P environment flag to force private IPFS networking...")
                output = subprocess.run(['setx','LIBP2P_FORCE_PNET','1']).stdout
                print(output)
            else:
                with open(os.path.join(home_dir,'.bashrc'),'a') as f:
                    f.write('\nexport LIBP2P_FORCE_PNET=1\n')
                os.environ['LIBP2P_FORCE_PNET']='1'

            #Initialize IPFS
            print('PATH:',os.environ['PATH'])
            print("Initializing IPFS...")
            output = subprocess.run(['ipfs','init'],capture_output=True,text=True)
            print(output.stdout,output.stderr)

            #Generate bootstrap
            if args.ipfs_bootstrap_id:
                dest = os.path.join(args.redist_path,'ipfs')
                if not os.path.isdir(dest):
                    os.makedirs(dest)
                dest = os.path.join(dest,'bootstrap_id.txt')
                bootstrap_addr = '/ip4/'+getPrimaryIP()+'/tcp/4001/ipfs/'
                ipfs_ = IPFS()
                proc = subprocess.Popen(['ipfs','daemon'])
                node_id = None
                while True:
                    result = ipfs_.execute_cmd('id',{})
                    if result.status_code == 200:
                        node_id = result.json()['ID']
                        break
                proc.terminate()
                bootstrap_addr+=node_id
                
                print('Removing current bootstrap targets')
                output = subprocess.run(['ipfs','bootstrap','rm','--all'],capture_output=True,text=True)
                print(output.stdout,output.stderr)

                #TODO: Modify to prevent duplicate entries being written
                if not args.ipfs_bootstrap_file:
                    print('Adding private bootstrap node target')
                    output = subprocess.run(['ipfs','bootstrap','add',bootstrap_addr],capture_output=True,text=True)
                    print(output.stdout,output.stderr)
                    print("Saving textual copy of bootstrap address at",dest)
                    with open(dest,'a') as f:
                        f.write(bootstrap_addr+"\n")
                else:
                    if not os.path.isfile(args.ipfs_bootstrap_file):
                        print("ERROR: Bootstrap file could not be found at",args.ipfs_bootstrap_file)
                        print("Reverting to adding current node to bootstrap list.")
                        output = subprocess.run(['ipfs','bootstrap','add',bootstrap_addr],capture_output=True,text=True)
                        print(output.stdout,output.stderr)
                        print("Saving textual copy of bootstrap address at",dest)
                        with open(dest,'a') as f:
                            f.write(bootstrap_addr+"\n")
                    else:
                        with open(args.ipfs_bootstrap_file,'r') as f:
                            entries = f.readlines()
                            for item in entries:
                                item = item.strip()
                                if not item:
                                    continue
                                print("Adding bootstrap address:",item)
                                output = subprocess.run(['ipfs','bootstrap','add',item],capture_output=True,text=True)
                                print(output.stdout,output.stderr)
    
    print("IPFS Installation Step Complete")

def installIPFSClusterService(args):
    global tmp_dir,lPATH
    ipfscluster_url = 'https://dist.ipfs.io/ipfs-cluster-service/v'+ipfs_cluster_version+'/'
    if isWindows():
        ipfscluster_fname = 'ipfs-cluster-service_v'+ipfs_cluster_version+'_windows-amd64.zip'
    else:
        ipfscluster_fname = 'ipfs-cluster-service_v'+ipfs_cluster_version+'_linux-amd64.tar.gz'

    tmp_out = None
    try:
        tmp_out = subprocess.run(['ipfs-cluster-service','--version'],capture_output=True,text=True)
        assert 'ipfs-cluster-service' in tmp_out.stdout[:20], "There appears to be an issue retrieving the IPFS-Cluster-Service version..."
        tmp_out=tmp_out.stdout
    except:
        print("IPFS-Cluster-Service installation not found")
    
    if tmp_out and not args.force: 
        print("IPFS-Cluster-Service already installed: ", tmp_out)
    else:
        if not args.noinstall:
            #Download IPFS Zip File
            print("Acquiring IPFS-Cluster-Service...")
            ipfscluster_fname = downloadFile(ipfscluster_url+ipfscluster_fname,tmp_dir)
            print("Extracting contents to",Path.home()/'Apps'/os.path.splitext(ipfscluster_fname)[0])
            if isWindows():
                with ZipFile(os.path.join(tmp_dir,ipfscluster_fname),'r') as zf:
                    zf.extractall(Path.home()/'Apps'/os.path.splitext(ipfscluster_fname)[0])
            else:
                with tarfile.open(os.path.join(tmp_dir,ipfscluster_fname)) as f:
                    f.extractall(Path.home()/'Apps'/str(ipfscluster_fname).replace('.tar.gz',''))


            #Add path to extracted folder to $PATH
            print("Updating path...")
            if isWindows():
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
                    output = subprocess.run(['setx','PATH',user_path.strip()+p+';'],capture_output=True,text=True)
                    print(output.stdout,output.stderr)
                
                lPATH += ';'+p
                os.environ['PATH'] = lPATH
            else:
                p = str(Path.home()/'Apps'/str(ipfscluster_fname).replace('.tar.gz',''))
                found = False
                for tmp_path in os.environ['PATH'].strip().split(':'):
                    if not tmp_path.strip():
                        continue
                    if os.path.normpath(p) == os.path.normpath(tmp_path):
                        found=True
                        break
                if found:
                    print('IPFS-Cluster-Service location already in PATH!')
                else:
                    with open(os.path.join(home_dir,'.bashrc'),'a') as f:
                        f.write('\nexport PATH=$PATH:'+os.path.join(p,'ipfs-cluster-service')+'\n')
                    os.environ['PATH']+=':'+os.path.join(p,'ipfs-cluster-service')

            #Initialize Cluster Service
            print("Initializing IPFS-Cluster-Service...")
            if not os.path.isfile(Path.home()/'.ipfs-cluster'/'service.json'):
                output = subprocess.run(['ipfs-cluster-service','init'])
                print('Defaults generated to',str(Path.home()/'.ipfs-cluster'))
            else:
                print("Service configuration already exists! Skipping.")
            
            if args.cluster_secret_file and os.path.isfile(args.cluster_secret_file):
                secret = open(args.cluster_secret_file,'r').read().strip()
                f = json.load(open(Path.home()/'.ipfs-cluster'/'service.json'))
                f['cluster']['secret'] = secret
                json.dump(f,open(Path.home()/'.ipfs-cluster'/'service.json','w'))
                print("Wrote secret from",args.cluster_secret_file,'to',str(Path.home()/'.ipfs-cluster'/'service.json'))
            else:
                #NOTE: For actual deployment, generate new cluster secret. For now use the default
                pass

            #Store Cluster Secret
            cluster_secret = json.load(open(Path.home()/'.ipfs-cluster'/'service.json'))["cluster"]["secret"]
            dest = os.path.join(args.redist_path,'ipfs-cluster')
            if not os.path.isdir(dest):
                os.makedirs(dest)
            dest = os.path.join(dest,'cluster_secret')
            with open(dest,'w') as f:
                f.write(cluster_secret.strip())

        print('NOTE: Other IPFS-Cluster Nodes must have the same value for "secret" in service.json!')
        print('NOTE: Bootstrapping may be necessary depending on network topology. If so, start the daemon with ipfs-cluster-service --bootstrap <ClusterPeerMultiAddress1,...>')
        print('IPFS-Cluster-Service Installation Step Complete')
   
    pass

def installIPFSClusterControl(args):
    global tmp_dir
    ipfscluster_url = 'https://dist.ipfs.io/ipfs-cluster-ctl/v'+ipfs_cluster_version+'/'
    if isWindows():
        ipfscluster_fname = 'ipfs-cluster-ctl_v'+ipfs_cluster_version+'_windows-amd64.zip'
    else:
        ipfscluster_fname = 'ipfs-cluster-ctl_v'+ipfs_cluster_version+'_linux-amd64.tar.gz'

    tmp_out = None
    try:
        tmp_out = subprocess.run(['ipfs-cluster-ctl','--version'],capture_output=True,text=True)
        assert 'ipfs-cluster-ctl' in tmp_out[:16], "There appears to be an issue retrieving the IPFS-Cluster-Service version..."
    except:
        print("IPFS-Cluster-Ctl installation not found")
    
    if tmp_out and not args.force:
        print("IPFS-Cluster-Ctl already installed: ", tmp_out)
    else:
        if not args.noinstall:
            #Download IPFS Zip File
            print("Acquiring IPFS-Cluster-Ctl...")
            ipfscluster_fname = downloadFile(ipfscluster_url+ipfscluster_fname,tmp_dir)
            print("Extracting contents to",Path.home()/'Apps'/os.path.splitext(ipfscluster_fname)[0])
            if isWindows():
                with ZipFile(os.path.join(tmp_dir,ipfscluster_fname),'r') as zf:
                    zf.extractall(Path.home()/'Apps'/os.path.splitext(ipfscluster_fname)[0])
            else:
                with tarfile.open(os.path.join(tmp_dir,ipfscluster_fname)) as f:
                    f.extractall(Path.home()/'Apps'/str(ipfscluster_fname).replace('.tar.gz',''))
                        
            #Add path to extracted folder to $PATH
            print("Updating path...")
            if isWindows():
                p = str(Path.home()/'Apps'/os.path.splitext(ipfscluster_fname)[0]/'ipfs-cluster-ctl')
                user_path = subprocess.run(["powershell", "-Command","[Environment]::GetEnvironmentVariable('Path','User')"], capture_output=True,text=True).stdout
                
                found = False
                for tmp_path in user_path.strip().split(';'):
                    if not tmp_path.strip():
                        continue
                    if p == tmp_path:
                        found = True
                        break

                if found:
                    print("IPFS-Cluster-Ctl location already in PATH!")
                else:
                    output = subprocess.run(['setx','PATH',user_path.strip()+p+';']).stdout
            else:
                p = str(Path.home()/'Apps'/str(ipfscluster_fname).replace('.tar.gz',''))
                found = False
                for tmp_path in os.environ['PATH'].strip().split(':'):
                    if not tmp_path.strip():
                        continue
                    if os.path.normpath(p) == os.path.normpath(tmp_path):
                        found=True
                        break
                if found:
                    print('IPFS-Cluster-Ctl location already in PATH!')
                else:
                    with open(os.path.join(home_dir,'.bashrc'),'a') as f:
                        f.write('\nexport PATH=$PATH:'+os.path.join(p,'ipfs-cluster-ctl')+'\n')
                    os.environ['PATH']+=':'+os.path.join(p,'ipfs-cluster-ctl')

        print('IPFS-Cluster-Ctl Installation Step Complete')
   
    pass

def installGeth(args):
    global tmp_dir, lPATH
    geth_url = 'https://gethstore.blob.core.windows.net/builds/'
    if isWindows():
        #geth_fname = 'geth-windows-amd64-'+geth_version+'.exe'
        geth_fname = 'geth-windows-amd64-'+geth_version+'.zip'
    else:
        geth_fname = 'geth-linux-amd64-'+geth_version+'.tar.gz'
    
    tmp_out = None
    try:
        tmp_out = subprocess.run(['geth','version'],capture_output=True,text=True).stdout
        assert tmp_out[:4] == 'Geth', "There appears to be an issue retrieving the Geth version..."
    except:
        print("Geth installation not found")
    
    if tmp_out and not args.force:
        print('Geth already installed: ',tmp_out)
    else:
        if not args.noinstall:
            print("Acquiring Geth Installer...")
            geth_fname = downloadFile(geth_url+geth_fname,tmp_dir)

            print("Extracting contents to",str(Path.home()/'Apps'/geth_fname.replace('.tar.gz','')))
            if isWindows():
                with ZipFile(os.path.join(tmp_dir,geth_fname),'r') as zf:
                    zf.extractall(Path.home()/'Apps')
            else:
                with tarfile.open(os.path.join(tmp_dir,geth_fname)) as f:
                    f.extractall(Path.home()/'Apps')

            #Update Local Process Path

            #messagebox.showinfo('Select Geth Directory','Please select the folder containing geth.exe.',parent=tkroot)
            #geth_path = filedialog.askdirectory()
            #if not geth_path:
            #    print("Cannot proceed without the bin directory location of the geth executable.")
            #    exit(1)
            
            print("Updating path...")
            if isWindows():
                geth_path = str(Path.home()/'Apps'/geth_fname.replace('.zip',''))
                user_path = subprocess.run(["powershell", "-Command","[Environment]::GetEnvironmentVariable('Path','User')"], capture_output=True,text=True).stdout
                
                found = False
                for tmp_path in user_path.strip().split(';'):
                    if not tmp_path.strip():
                        continue
                    if geth_path == tmp_path:
                        found = True
                        break

                if found:
                    print("Geth location already in PATH!")
                else:
                    output = subprocess.run(['setx','PATH',user_path.strip()+geth_path+';'],capture_output=True,text=True)
                    print(output.stdout,output.stderr)
                
                lPATH += ';'+geth_path+';'+str(Path.home()/'go'/'bin')
                os.environ['PATH'] = lPATH
            else:
                p = str(Path.home()/'Apps'/str(geth_fname).replace('.tar.gz',''))
                found = False
                for tmp_path in os.environ['PATH'].strip().split(':'):
                    if not tmp_path.strip():
                        continue
                    if os.path.normpath(p) == os.path.normpath(tmp_path):
                        found=True
                        break
                if found:
                    print('Geth location already in PATH!')
                else:
                    with open(os.path.join(home_dir,'.bashrc'),'a') as f:
                        f.write('\nexport PATH=$PATH:'+p+'\n')
                    os.environ['PATH']+=':'+p

            #Create ethereum base directory
            eth_path = str(Path.home()/'.eth')
            if not os.path.isdir(eth_path):
                os.makedirs(eth_path)
            
            data_dir = os.path.join(eth_path,'node')

            if not args.skip_geth_user_creation:
                #Check for pswd file to use for account creation else generate a new one.
                acct_name = None
                while True:
                    acct_name = simpledialog.askstring("Create New Geth Account",'Enter New Geth Account Name')
                    
                    if not acct_name is None and not acct_name:
                        messagebox.showerror("Geth Account Name",'Account name cannot be empty!')
                    elif acct_name is None:
                        response = messagebox.askyesno("Geth Account Name",'Cannot create local Geth installation without an account name. Abort installation?')
                        if response:
                            exit(0)
                    else:
                        acct_name=acct_name.strip()
                        forbidden_chars = '< > : " / \\ | ? *'.split(' ')
                        forbidden_chars += [chr(i) for i in range(31)]
                        reserved_names = 'CON, PRN, AUX, NUL, COM0, COM1, COM2, COM3, COM4, COM5, COM6, COM7, COM8, COM9, LPT0, LPT1, LPT2, LPT3, LPT4, LPT5, LPT6, LPT7, LPT8, LPT9'.replace(',','').split(' ')
                        if acct_name in reserved_names:
                            messagebox.showerror("Name Error",'Cannot use reserved name ' + acct_name + '!')
                            continue
                        valid = True
                        for c in forbidden_chars:
                            if c in acct_name:
                                messagebox.showerror("Name Error","File name uses illegal characters!")
                                valid = False
                                break
                        if not valid:
                            continue
                        break
                data_dir = os.path.join(eth_path,acct_name)
                pswd = None
                while True:
                    pswd = simpledialog.askstring("Create New Geth Account Password",'Enter New Geth Account Password',show='*')
                    if not pswd is None and not pswd:
                        messagebox.showerror("Geth Password",'Password cannot be empty!')
                    elif pswd is None:
                        response = messagebox.askyesno("Geth Password",'Cannot create local Geth installation without an account password. Abort installation?')
                        if response:
                            exit(0)
                    else:
                        break
                
                with open('./.tmp/'+acct_name,'w') as f:
                    f.write(pswd)

                if args.save_geth_password:
                    with open(args.save_geth_password,'w') as f:
                        f.write(acct_name+' - '+pswd)

                #Create Account
                output = subprocess.run(['geth','account','new','--datadir',data_dir,'--password','./.tmp/'+acct_name],capture_output=True,text=True)
                print(output.stdout,output.stderr)
                os.remove('./.tmp/'+acct_name)

                args.geth_init_data_dir = data_dir

            #Genesis block creation
            if args.geth_generate_genesis_block:
                #Get account identity
                output = subprocess.run(['geth','account','list','--keystore',os.path.join(data_dir,'keystore')],capture_output=True,text=True)
                output_lines = [line for line in output.stdout.splitlines() if 'Account #' in line]
                output_lines = [line[13:53] for line in output_lines]

                signer_ids = '0x'+str('0'*64)+''.join(output_lines)+str('0'*130)
                genesis_json = {
                    "config": {
                        "chainId": args.geth_network_id,
                        "homesteadBlock": 0,
                        "eip150Block": 0,
                        "eip155Block": 0,
                        "eip158Block": 0,
                        "byzantiumBlock": 0,
                        "constantinopleBlock": 0,
                        "petersburgBlock": 0,
                        "istanbulBlock":0,
                        "clique": {
                            "period": 5,
                            "epoch": 30000
                        }
                    },
                    "difficulty": "1",
                    "gasLimit": "8000000",
                    "alloc": {}
                }
                genesis_json['extradata'] = signer_ids
                for signer in output_lines:
                    genesis_json['alloc'][signer] = {'balance':str(int(10**18)*int(10**9))}
                    
                json.dump(genesis_json,open(os.path.join(eth_path,'genesis.json'),'w'),sort_keys=True,indent=4)

                if not os.path.isdir('./redist/geth'):
                    os.makedirs('./redist/geth')
                shutil.copy2(os.path.join(eth_path,'genesis.json'),'./redist/geth/genesis.json')
        
            if args.genesis_block_file:
                print("Copying genesis block to geth folder...")
                shutil.copy2(args.genesis_block_file,os.path.join(eth_path,'genesis.json'))


            #Init Geth Database
            if args.geth_init_data_dir:
                if os.path.isdir(args.geth_init_data_dir):
                    output = subprocess.run(['geth','init','--datadir',data_dir,os.path.join(eth_path,'genesis.json')],capture_output=True,text=True)
                    print(output.stdout,output.stderr)
                    print("Genesis Block created and deployed")
                else:
                    print("Provided path,",args.geth_init_data_dir,'is not a valid geth account data directory! Skipping init step')

            sp = subprocess.Popen(['geth','--datadir',data_dir,'--networkid','2022','--http','--http.api','debug,eth,web3,personal,net,admin','--nat','extip:'+getPrimaryIP()])

            if args.geth_generate_bootstrap_record:
                if not os.path.isdir('./redist/geth'):
                    os.makedirs('./redist/geth')
                records = []
                if os.path.isfile('./redist/geth/boot'):
                    with open('./redist/geth/boot','r') as f:
                        records = f.read().split(',')
                if not os.path.isdir(data_dir):
                    data_dir = [os.path.join(eth_path,d) for d in os.listdir(eth_path) if os.path.isdir(os.path.join(eth_path,d))][0]
                    print("Using data dir = ",data_dir)
                output = None
                #time.sleep(5)
                while not output or not 'enode' in output[0:5]:
                    output = subprocess.run(['geth','attach','http://localhost:8545','--exec','admin.nodeInfo.enode'],capture_output=True,text=True).stdout[1:-2]
                    print(output[1:-2])
                #print(output.stdout,output.stderr)
                if not output in records:
                    records.append(output)
                with open('./redist/geth/boot','w') as f:
                    f.write(','.join(records))
                shutil.copy2('./redist/geth/boot',str(Path.home()/'.eth'/'boot'))
            
            if args.geth_generate_static_node_list:
                if not os.path.isdir('./redist/geth'):
                    os.makedirs('./redist/geth')
                static_nodes = []
                if os.path.isfile('./redist/geth/static-nodes.json'):
                    static_nodes = json.load(open('./redist/geth/static-nodes.json','r'))
                if not os.path.isdir(data_dir):
                    data_dir = [os.path.join(eth_path,d) for d in os.listdir(eth_path) if os.path.isdir(os.path.join(eth_path,d))][0]
                    print("Using data dir = ",data_dir)
                #sp = subprocess.Popen(['geth','--datadir',data_dir,'--networkid','2022','--http','--http.api','debug,eth,web3,personal,net,admin'])
                output = None
                #time.sleep(5)
                while not output or not '"enode' in output[0:7]:
                    output = subprocess.run(['geth','attach','http://localhost:8545','--exec','admin.nodeInfo.enode'],capture_output=True,text=True).stdout
                    print(output)
                output = output.replace('\"','').strip()
                #sp.terminate()
                #print(output.stdout,output.stderr)
                if not output in static_nodes:
                    static_nodes.append(output)
                json.dump(static_nodes,open('./redist/geth/static-nodes.json','w'))

                account_dirs = [os.path.join(eth_path,d) for d in os.listdir(eth_path) if os.path.isdir(os.path.join(eth_path,d))]

                for d in account_dirs:
                    shutil.copy2('./redist/geth/static-nodes.json',os.path.join(d,'static-nodes.json'))
                
            sp.terminate()

            #Install py-solc-x
            try:
                import web3
            except ImportError:
                print('Installing python package \'web3\'')
                output = subprocess.run([sys.executable,'-m','pip','install','web3','--upgrade'],capture_output=True,text=True)
                print(output.stdout,output.stderr)
            try:
                import solcx
            except ImportError:
                print('Installing python package \'py-solc-x\'')
                output = subprocess.run([sys.executable,'-m','pip','install','py-solc-x','--upgrade'],capture_output=True,text=True)
                print(output.stdout,output.stderr)
            
            print('Installing Solidity Compiler')
            from solcx import install_solc
            print(install_solc())
    
    print("Geth Installation Complete")

def parseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument('--redist_path',type=str,default='./redist',help='Path to folder which will contain files intended to be used for installations on other peer nodes.')
    parser.add_argument('--noinstall',action='store_true',help='Prevents download and installation of packages')
    parser.add_argument('--clean',action='store_true',help='Removes any preexisting installation artifacts before checking and installing packages')
    parser.add_argument('--generate_swarm_key',action='store_true',help='Should be set for the first node in the network installing the software to generate a shared IPFS swarm key')
    parser.add_argument('--swarm_key_file',type=str,default='',help='If set will copy the specified swarm.key file to the .ipfs directory.')
    parser.add_argument('--ipfs_bootstrap_id',action='store_true',help='If set, will generate a bootstrap_id.txt file in the redist folder to use with other node installations.')
    parser.add_argument('--ipfs_bootstrap_file',type=str,default='',help='Path to file with bootstrap ids to add to the current node. WILL OVERWRITE EXISTING BOOTSTRAP NODE DATA!')
    parser.add_argument('--cluster_secret_file',type=str,default='',help='If provided, the system will use the cluster secret value from the file instead of generating a new value when configuring IPFS-Cluster')
    parser.add_argument('--geth_network_id',type=int,default=2022,help='The network id to use when setting up the private ethereum network.')
    parser.add_argument('--geth_generate_genesis_block',action='store_true',help='If set, creates the genesis.json file for the Clique. This will also add the node as a signer.')
    parser.add_argument('--genesis_block_file',type=str,default='',help='If set, will copy the specified genesis file to the .eth folder')
    parser.add_argument('--save_geth_password',type=str,default='',help='If non-empty, the password used for the new account is written to the specified file path.')
    parser.add_argument('--skip_geth_user_creation',action='store_true',help='If set, skip the user creation steps when installing Geth')
    parser.add_argument('--skip_golang',action='store_true',help='If set will skip the Go installation step')
    parser.add_argument('--skip_ipfs',action='store_true',help='If set will skip the IPFS installation step')
    parser.add_argument('--skip_ipfs_cluster_service',action='store_true',help='If set will skip the IPFS-Cluster-Service installation step')
    parser.add_argument('--skip_ipfs_cluster_ctl',action='store_true',help='If set will skip the IPFS-Cluster-Ctl installation step')
    parser.add_argument('--skip_geth',action='store_true',help='If set will skip the go-ethereum (Geth) client installation step')
    parser.add_argument('--geth_init_data_dir',type=str,default='',help='If provided with a valid directory, will initialize the account with the genesis block file.')
    parser.add_argument('--geth_generate_bootstrap_record',action='store_true',help='If set, will add the newly created node\'s bootstrap-node-record for use by other nodes.')
    parser.add_argument('--geth_generate_static_node_list',action='store_true',help='If set, will append the new account id to static-nodes.json file for every account found in the ~/.eth folder to allow for sid in peer discovery')
    parser.add_argument('--force',action='store_true',help='If set will force selected components to reinstall')
    return parser.parse_args()

def main():
    global tmp_dir, home_dir
    args = parseArgs()
    if args.clean:
        if os.path.isdir(tmp_dir):
            shutil.rmtree(tmp_dir)
    
    os.makedirs(tmp_dir,exist_ok=True)
    
    if platform.system() == 'Windows':
        if not isAdmin():
            if not args.skip_golang:
                installGoLang(args)
            if not args.skip_ipfs:
                installIPFS(args)
            if not args.skip_ipfs_cluster_service:
                installIPFSClusterService(args)
            if not args.skip_ipfs_cluster_ctl:
                installIPFSClusterControl(args)
            if not args.skip_geth:
                installGeth(args)
        else:
            print("Relaunching as admin")
            a = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
            if a != 32:
                print('Elevation attempt yielded code',a)
    else: #NOTE: Currently not handling MacOS, just linux, more specifically just Ubuntu for now
        #TODO: Add platform-specific install steps as branches within the install functions
        
        if not isAdmin() and False: #No longer require sudo
            print("Please re-run installer with sudo.")
            exit(0)
        else:
            home_dir = str(Path.home())
            if not args.skip_golang:
                installGoLang(args)
            if not args.skip_ipfs:
                installIPFS(args)
            if not args.skip_ipfs_cluster_service:
                installIPFSClusterService(args)
            if not args.skip_ipfs_cluster_ctl:
                installIPFSClusterControl(args)
            if not args.skip_geth:
                installGeth(args)
            pass
        pass

if __name__ == '__main__':
    main()
