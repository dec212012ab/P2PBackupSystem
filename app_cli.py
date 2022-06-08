from consolemenu import *
from consolemenu.items import *
from ipfs import IPFS, IPFSCluster, DotDict
from geth_helper import GethHelper
import json
import pickle
import configparser

class CLIHelper:
    def __init__(self,ipfs_obj:IPFS,ipfs_cluster_obj:IPFSCluster,geth_obj:GethHelper):
        self.title = "P2P Distributed Backup System"
        self.menu = ConsoleMenu(self.title,"Main Menu",clear_screen=False)
        self.menu_entries = DotDict()

        self.constructed = False

        self.ipfs = ipfs_obj
        self.ipfscl = ipfs_cluster_obj
        self.geth = geth_obj

        self.createBackupMenu()
        


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
            response = self.ipfs.execute_cmd('id',{})
            if response.status_code == 200:
                print(json.dumps(json.loads(response.text),indent=2,sort_keys=True))
            else:
                print(response.text)

        options = [
            FunctionItem("List Tracked Locations",listTrackedLocations),
        ]
        for opt in options:
            backup_menu.append_item(opt)

        self.addSubMenu('backup_menu',backup_menu,'Backup Menu')

    