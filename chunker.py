
from asyncio import subprocess
import itertools
import json
import math
import multivolumefile
import os
import py7zr
import random
import shutil
import subprocess

from datetime import time, timedelta,datetime

from joblib import delayed, Parallel


class Chunker:
    #Chunk Modes
    def __init__(self,total_nodes,survivor_percentage):
        self.allocation_LUT = {}
        self.allocation_min_total = 2
        self.allocation_max_total = 20
        self.allocation_min_survivors = 1
        self.allocation_max_survivors = 20

        self.total_nodes = total_nodes
        self.required_survivors_percentage = survivor_percentage

        self.chunk_split_count_limit = 20

        self.concurrency = 8

        pass
    def generateLUT(self,dest_dir):
        self.allocation_LUT = {}
        out_message = ''

        total_iterations = (self.allocation_max_total-self.allocation_min_total+1)*(self.allocation_max_survivors-self.allocation_min_survivors+1)
        iteration_count = 0
        start_time = datetime.now()
        for i in range(self.allocation_min_total,self.allocation_max_total+1,1):
            peers = i-1
            self.allocation_LUT[i] = {}
            for j in range(self.allocation_min_survivors,self.allocation_max_survivors+1,1):
                self.allocation_LUT[i][j] = {}
                combos = list(itertools.combinations(range(1,peers+2),j))
                combos_len = len(combos)
                random.shuffle(combos,lambda:0.5)

                def processSplits(node_count,survivor_count, k):
                    node_list = [[] for i in range(peers)]
                    
                    for _id,_combo in enumerate(combos):
                        passed = False
                        #print("Starting",str(_id+1)+'/'+str(combos_len),_combo)
                        while not passed:
                            out = []
                            for c in _combo:
                                out += node_list[c-2]
                            found=True
                            for chunk in range(k):
                                if not chunk in out:
                                    lengths = [len(n) for n in [node_list[m-2] for m in _combo]]
                                    min_node = min(lengths)
                                    min_index = lengths.index(min_node)
                                    node_list[_combo[min_index]-2].append(chunk)
                                    found = False
                                    break
                            if found:
                                passed = True
                        #print("Completed",str(_id+1)+'/'+str(combos_len))
                    return node_list

                iter_keys = [(i,j,k) for k in range(1,self.chunk_split_count_limit+1)]
                results = Parallel(self.concurrency)(delayed(processSplits)(k1,k2,k3) for k1,k2,k3 in iter_keys)
                
                for result_id, node_list in enumerate(results):
                    print('\nTotal Nodes:',i,' | Survivors:',j,' | Splits:',result_id+1)
                    for nid,node in enumerate(node_list):
                        print('Peer '+str(nid+1)+':',sorted(node),'len:',len(node))
                    print()
                    self.allocation_LUT[i][j][result_id+1] = node_list
                print('Progress:',iteration_count+1,'/',total_iterations)
                #out_message = '\b'*len(out_message)
                #out_message += 'Progress: '+str(iteration_count+1)+' / '+str(total_iterations)
                #print(out_message,end='')
                iteration_count += 1
        print()
        duration = datetime.now() - start_time
        print("Generating LUT took ", duration)
        if not os.path.isdir(dest_dir):
            os.makedirs(dest_dir)
        
        output_path = str(self.allocation_max_total)+'_'+str(self.allocation_max_survivors)+'_'+str(self.chunk_split_count_limit)+'.json'
        json.dump(self.allocation_LUT,open(os.path.join(dest_dir,output_path),'w'),sort_keys=True,indent=4)
        print('saved lut to',os.path.abspath(output_path))

    def loadLUTFromJson(self,src_dir):
        if not os.path.isdir(src_dir):
            print("Could not open LUT directory",src_dir)
            return False
        lut_name = str(self.allocation_max_total)+'_'+str(self.allocation_max_survivors)+'_'+str(self.chunk_split_count_limit)+'.json'
        if not os.path.isfile(os.path.join(src_dir,lut_name)):
            print("Could not locate LUT file",lut_name,'in',src_dir)
            return False
        else:
            self.allocation_LUT = json.load(open(os.path.join(src_dir,lut_name),'r'))
            print("Successfully Loaded Allocation LUT")
            return True
    
    def lookupLUT(self,total_nodes,survivors,splits):
        total_nodes = str(total_nodes)
        survivors = str(survivors)
        splits = str(splits)
        if (not total_nodes in self.allocation_LUT or
            not survivors in self.allocation_LUT[total_nodes] or
            not splits in self.allocation_LUT[total_nodes][survivors]):
                return []
        else:
            return self.allocation_LUT[total_nodes][survivors][splits]
    
    def lookupChunkAlloc(self,total_nodes,survivors,splits,chunk_index):
        node_list = self.lookupLUT(total_nodes,survivors,splits)
        if 0<=chunk_index<splits:
            return [i for i in range(len(node_list)) if chunk_index in node_list[i]]
        else:
            print("Invalid chunk index! (0<chunk_index<"+str(splits)+') Got:',chunk_index)
            return []

    def getFileSizeB(self,filepath):
        return os.path.getsize(filepath)
    
    def getDirectorySizeB(self,dirpath):
        total_size = 0
        for root,dirs,files in os.walk(dirpath):
            for f in files:
                path = os.path.join(root,f)
                if not os.path.islink(path):
                    total_size += os.path.getsize(path)
        return total_size

    def stageChunks(self,staging_dir,tracked_paths=[],name_prefix='',split_count=-1,use_subprocess=True):
        if split_count<0:
            split_count = self.chunk_split_count_limit
        if not os.path.isdir(staging_dir):
            os.makedirs(staging_dir)

        total_size = 0
        for path in tracked_paths:
            print(path)
            if os.path.isfile(path):
                total_size += self.getFileSizeB(path)
            elif os.path.isdir(path):
                total_size += self.getDirectorySizeB(path)
            else:
                print("Skipping size calculation of invalid path",path)
        
        chunk_size = total_size//split_count
        
        archive_name = name_prefix+str(datetime.now()).replace(' ','-').replace(':','_')+'.7z'

        #staging_dir = os.path.join(staging_dir,archive_name.replace('.7z',''))

        if os.path.isdir(staging_dir):
            shutil.rmtree(staging_dir)
            
        os.makedirs(staging_dir)        

        print("Total size in Bytes:",total_size)
        print("Chunk Size:",chunk_size)
        if not use_subprocess:
            archive_name.replace('.7z','.py7zr')
            with multivolumefile.open(os.path.join(staging_dir,archive_name),'ab',chunk_size) as archive:
                with py7zr.SevenZipFile(archive,'w') as f:
                    for i,p in enumerate(tracked_paths):
                        print("Storing path",i+1,'/',len(tracked_paths),':',p)
                        if os.path.isdir(p):
                            f.writeall(p)
                        elif os.path.isfile(p):
                            f.write(p)
                        else:
                            print("Skipping invalid path:",p)
        else:
            try:
                output = subprocess.run(['7z','a',os.path.join(staging_dir,archive_name),*tracked_paths,'-t7z','-v'+str(chunk_size)+'b','-mx=9','-mmt='+str(self.concurrency)],capture_output=True,text=True)
                print(output.stdout,output.stderr)
            except:
                print("Failed to open 7z CLI application. Falling back to Py7zr")
                self.stageChunks(staging_dir,tracked_paths,use_subprocess=False)
        
        return len(os.listdir(staging_dir))

