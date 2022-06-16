
import configparser
import json
import pathlib
import pickle
import os
from pyclbr import Function
import sys
import tkinter

from consolemenu import *
from consolemenu.items import *
from ipfs import IPFS, IPFSCluster, DotDict
from geth_helper import GethHelper

from chunker import Chunker
from pathlib import Path

from tkinter import filedialog


class CLIApp:
    def __init__(self,ipfs_obj:IPFS,ipfs_cluster_obj:IPFSCluster,geth_obj:GethHelper):
        self.title = "P2P Distributed Backup System"
        self.menu = ConsoleMenu(self.title,"Main Menu",clear_screen=False)
        self.menu_entries = DotDict()

        self.constructed = False

        self.ipfs = ipfs_obj
        self.ipfscl = ipfs_cluster_obj
        self.geth = geth_obj

        self.tracked_locations = set()
        self.loadTrackingManifest()

        self.chunker = Chunker(20,6)
        if not os.path.isfile('20_20_20.json'):
            print("Generating Allocation LUT...")
            self.chunker.generateLUT('.')
            print("Allocation LUT created successfully")
        else:
            print("Loading default LUT")
            success = self.chunker.loadLUTFromJson('.')
            if not success:
                print("Failed to load default Allocation LUT. Attempting to re-generate...")
                self.chunker.generateLUT('.')

        self.createBackupMenu()
    
    def loadTrackingManifest(self):
        if os.path.isfile(Path.home()/'.backup_manifest'):
            self.tracked_locations = set(json.load(open(str(Path.home()/'.backup_manifest'),'r')))
            print("Loaded last saved tracking state.")

    def construct(self):
        for k in self.menu_entries:
            self.menu.append_item(self.menu_entries[k])
        self.constructed = True

    def addSubMenu(self,key,menu,text):
        self.menu_entries[key] = SubmenuItem(text,menu,self.menu,False)
    
    def addFunctionItem(self,key,item):
        self.menu_entries[key] = item

    def createBackupMenu(self):
        backup_menu = ConsoleMenu(self.title,"Backup Menu",clear_screen=False)

        def listTrackedLocations():
            if not self.tracked_locations:
                print("No tracked locations")
            else:
                print('Tracked Locations:')
                for item in self.tracked_locations:
                    if os.path.isdir(item):
                        print('\t (DIR) '+item)
                    elif os.path.isfile(item):
                        print('\t(FILE) '+item)
                    else:
                        print('\t(????) '+item)
        
        def trackDirectory():
            selected = filedialog.askdirectory()
            if selected:
                self.tracked_locations.add(selected)

        def trackFile():
            selected = filedialog.askopenfilenames()
            if selected:
                self.tracked_locations.update(selected)
        
        def saveTracked():
            json.dump(list(self.tracked_locations),open(str(Path.home()/'.backup_manifest'),'w'))
            print("Saved to ",str(Path.home()/'.backup_manifest'))

        '''def multiSelectDeletion():
            m = MultiSelectMenu(self.title,'Select Items to Untrack',show_exit_option=False,clear_screen=False)
            
            def process_wrapper(menu):
                user_input = menu.screen.input()

                try:
                    indexes = menu.__parse_range_list(user_input)
                    # Subtract 1 from each number for its actual index number
                    indexes[:] = [x - 1 for x in indexes if 0 < x < len(menu.items) + 1]
                    for index in indexes:
                        if index == indexes[-1]:
                            menu.items[index].should_exit=True
                        menu.current_option = index
                        menu.select()
                except Exception as e:
                    return
                
            def _rem(_rempath):
                if _rempath in self.tracked_locations:
                    self.tracked_locations.remove(_rempath)
                #if item in menu.items:
                #    menu.items.pop(menu.index(item))
                print(m.selected_option)
                
            for item in self.tracked_locations:
                m.append_item(FunctionItem(item,lambda:_rem(item)))
            
            #m.process_user_input = process_wrapper
            bound_func = process_wrapper.__get__(m,m.__class__)
            setattr(m,m.process_user_input.__name__,bound_func)
            m.show()'''

        def showDeletionMenu():
            l = list(self.tracked_locations) + ['Cancel']
            index = SelectionMenu.get_selection(l,self.title,'Select Items to Untrack',show_exit_option=False)
            if index != len(l)-1:
                self.tracked_locations.remove(l[index])

        def runBackup():
            staging_dir = os.path.dirname(sys.argv[0])
            staging_dir = os.path.join(staging_dir,'.bckup_stage')

            #Get IPFS ID
            response = self.ipfs.execute_cmd('id',{})
            prefix = ''
            if response.status_code == 200:
                prefix = response.json()['ID']
                print("Using prefix",prefix)

            #Accumulate and generate staged chunks
            print("Staging chunks")
            self.chunker.stageChunks(staging_dir,self.tracked_locations,prefix)

            print('Posting to IPFS')
            #Post to IPFS 
            ids = []
            for item in os.listdir(staging_dir):
                print('Posting',item)
                response = self.ipfs.execute_cmd('add',{'file':open(os.path.join(staging_dir,item),'rb')})
                if response.status_code == 200:
                    jsonized = response.json()
                    ids.append((jsonized["Name"],jsonized["Hash"]))
                else:
                    print("Received response: ",response.text)
                    print("Aborting Backup")
                    return

            print(ids)

            #Add to MFS
            mfs_dir = '/backups/'+ids[0][0][:-7]
            response = self.ipfs.execute_cmd('files/mkdir',{},'/backups/'+ids[0][0][:-7],parents=True)
            print("Adding references to MFS")
            for id in ids:
                response = self.ipfs.execute_cmd('files/cp',{},'/ipfs/'+id[1],os.path.join(mfs_dir,id[0]))
                if response.status_code != 200:
                    print("Received response: ",response.text)
                    print("Aborting Backup")
                    return
                pass
            
            #Get peer count
            peer_count = 0
            response = self.ipfs.execute_cmd('swarm/peers',{})
            if response.status_code == 200:
                print(response.text)
                response = response.json()
                if response['Peers']:
                    peer_count = len(response.json()['Peers'])
            else:
                print("Received response: ",response.text)
                print("Aborting Backup")
                return

            print('Peer count',peer_count)

            cl_peers = 0
            response = self.ipfscl.peers()
            if response.status_code == 200:
                response = response.json()
                cl_peers = len([item for item in response['cluster_peers'] if item!=response['id']])
            print("Cluster Peer Count:",cl_peers)
            
            for id in ids:
                self.ipfs.execute_cmd('pin/rm',{},id[1])
            self.ipfs.execute_cmd('repo/gc',{})

            #alloc = self.chunker.lookupLUT()
            #Add to Cluster with replication factors
            


        options = [
            FunctionItem("List Tracked Locations",listTrackedLocations),
            FunctionItem("Add Directory to Tracking List",trackDirectory),
            FunctionItem("Add File to Tracking List",trackFile),
            FunctionItem("Save Tracking List",saveTracked),
            FunctionItem("Remove Tracked Item",showDeletionMenu),
            FunctionItem("Run Backup",runBackup)            
        ]
        for opt in options:
            backup_menu.append_item(opt)

        self.addSubMenu('backup_menu',backup_menu,'Backup Menu')

    