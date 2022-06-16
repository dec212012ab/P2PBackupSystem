
import configparser
import json
import pathlib
import pickle
import os
import tkinter

from consolemenu import *
from consolemenu.items import *
from ipfs import IPFS, IPFSCluster, DotDict
from geth_helper import GethHelper

from chunker import Chunker
from pathlib import Path

from tkinter import filedialog

root = tkinter.Tk()
root.withdraw()

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
            #response = self.ipfs.execute_cmd('id',{})
            #if response.status_code == 200:
            #    print(json.dumps(json.loads(response.text),indent=2,sort_keys=True))
            #else:
            #    print(response.text)
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
            l = list(self.tracked_locations)
            index = SelectionMenu.get_selection(l,self.title,'Select Items to Untrack',show_exit_option=False)
            self.tracked_locations.remove(l[index])                

        options = [
            FunctionItem("List Tracked Locations",listTrackedLocations),
            FunctionItem("Add Directory to Tracking List",trackDirectory),
            FunctionItem("Add File to Tracking List",trackFile),
            FunctionItem("Save Tracking List",saveTracked),
            FunctionItem("Remove Tracked Item",showDeletionMenu)
        ]
        for opt in options:
            backup_menu.append_item(opt)

        self.addSubMenu('backup_menu',backup_menu,'Backup Menu')

    