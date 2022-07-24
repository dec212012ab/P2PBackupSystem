import os
from attr import field
import requests

class DotDict(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

class IPFS:
    def __init__(self,host='localhost',port='5001'):
        self.host = host
        self.port = port
        self.session = requests.Session()

        
    def execute_cmd(self,cmd,files,*args,**kwargs):
        cmd_str = "http://"+self.host+':'+self.port
        cmd_str += os.path.join(cmd_str,'/api/v0',cmd).replace('\\','/')

        if len(args)>0 or len(kwargs)>0:
            cmd_str+='?'
        
        args_added = False
        if len(args)>0:
            args_added = True
            for i,item in enumerate(args):
                if i == 0:
                    cmd_str+='arg='+str(item)
                else:
                    cmd_str+='&arg='+str(item)
        if len(kwargs)>0:
            for i,item in enumerate(kwargs):
                if i==0 and not args_added:
                    cmd_str+=str(item)+'='+str(kwargs[item])
                else:
                    cmd_str+='&'+str(item)+'='+str(kwargs[item])

        #print('Assembled',cmd_str)
        #try:
        return self.session.post(cmd_str,files=files)
        #except:
        #    tmp = DotDict()
        #    tmp.status_code = 404
        #    tmp.text = "Connection to http://"+str(self.host)+':'+str(self.port)+' failed. Is the IPFS Daemon running?'
        #    return tmp

class ClusterPin:
    def __init__(self):
        self.cid:str = ''
        self.name:str = ''
        self.pin_state:str = ''
        self.min_replication:int = 0
        self.max_replication:int = 0
        self.allocations:list[str] = []
        self.pin_type:str = ''
        self.metadata:str = ''
        self.expiry:str = ''
        self.timestamp:str = ''
        pass        

    def loadFromString(self,s:str):
        fields = s.split('|')
        
        self.cid = fields[0].strip()
        self.name = fields[1].strip()
        self.pin_state = fields[2].strip()
        fields[3] = fields[3].replace('Repl. Factor:','').strip()
        if '--' in fields[3]:
            fields[3] = fields[3].split('--')
            self.min_replication = int(fields[3][0])
            self.max_replication = int(fields[3][1])
        else:
            self.min_replication = int(fields[3])
            self.max_replication = self.min_replication
        fields[4] = fields[4].replace('Allocations:','').strip()
        self.allocations = fields[4][1:-1].split(' ')
        self.pin_type = fields[5].strip()
        self.metadata = fields[6].replace('Metadata:','').strip()
        self.expiry = fields[7].replace('Exp:','').strip()
        self.timestamp = fields[8].replace('Added:','').strip()
        pass

class IPFSCluster:
    def __init__(self,host_ip='localhost',port='9094'):
        self.host = host_ip
        self.port = port
        self.session = requests.Session()

    def getCMDBase(self,cmd,*args,**kwargs):
        base = 'http://'+self.host+':'+self.port
        cmd_str = os.path.join(base,cmd).replace('\\','/')
        
        if len(args)>0 or len(kwargs)>0:
            cmd_str+='?'
        
        args_added = False
        if len(args)>0:
            args_added = True
            for i,item in enumerate(args):
                if i == 0:
                    cmd_str+='arg='+str(item)
                else:
                    cmd_str+='&arg='+str(item)
        if len(kwargs)>0:
            for i,item in enumerate(kwargs):
                if i==0 and not args_added:
                    cmd_str+=str(item)+'='+str(kwargs[item])
                else:
                    cmd_str+='&'+str(item)+'='+str(kwargs[item])

        print('Cluster CMD Assembled',cmd_str)
        return cmd_str

    def _execute_get(self,cmd,*args,**kwargs):
        print(*args,**kwargs)
        return self.session.get(self.getCMDBase(cmd,*args,**kwargs))
    
    def _execute_del(self,cmd,*args,**kwargs):
        return self.session.delete(self.getCMDBase(cmd,*args,**kwargs))
    
    def _execute_post(self,cmd,files={},*args,**kwargs):
        return self.session.post(self.getCMDBase(cmd,*args,**kwargs),files=files)

    def id(self,*args,**kwargs):
        return self._execute_get('id',*args,**kwargs)
    
    def version(self,*args,**kwargs):
        return self._execute_get('version',*args,**kwargs)
    
    def peers(self,*args,**kwargs):
        return self._execute_get('peers',*args,**kwargs)

    def removePeer(self,peer_id,*args,**kwargs):
        return self._execute_del('peers/'+peer_id,*args,**kwargs)
    
    def addFile(self,filepath,*args,**kwargs):
        return self._execute_post('add',{'file':open(filepath,'rb')},*args,**kwargs)

    def listAllocations(self,*args,**kwargs):
        return self._execute_get('allocations',*args,**kwargs)

    def showAllocation(self,cid,*args,**kwargs):
        return self._execute_get('allocations/'+cid,*args,**kwargs)

    def listPins(self,*args,**kwargs):
        return self._execute_get('pins',*args,**kwargs)
    
    def showPin(self,cid,*args,**kwargs):
        return self._execute_get('pins/'+cid,*args,**kwargs)

    def pinCID(self,cid,*args,**kwargs):
        return self._execute_post('pins/'+cid,*args,**kwargs)

    def unpinCID(self,cid,*args,**kwargs):
        return self._execute_del('pins/'+cid,*args,**kwargs)
