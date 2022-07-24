from web3 import Web3
from geth_helper import GethHelper
import time
import logging
from pathlib import Path
import random


logging.basicConfig(filename=str(Path.home()/'.eth'/'signers.log'),encoding='utf-8',level=logging.INFO)

class SignerMonitor:
    def __init__(self,geth:GethHelper):
        self.signer_target_count = 2
        self.sleep_interval_s = 5
        self.count_check_interval_s = 15
        self.rotation_interval_s = 60
        self.exit_interval_s = 20
        self.geth = geth
        self._thread_exit = False
        self.top_off_threshold_ether = 5
        self.donate_threshold_ether = 12
        self.donate_lower_limit = 10

        self.use_fifo_rotation:bool = True
        self.signer_fifo:dict[str,int] = {}

    def stopSignal(self):
        self._thread_exit = True
    
    def exitFromSignerList(self):
        if not self.geth.callContract('ExitSigner','isOwner',True,{},self.geth.session.eth.coinbase):
            exit_node = self.geth.callContract('ExitSigner','getExitingNode')
            timeout_limit_s = 62
            timeout_triggered = False
            exit_start = time.time()
            while str(exit_node).lower() != self.geth.session.eth.coinbase.lower():
                logging.info('My coinbase: ' + self.geth.session.eth.coinbase.lower())
                logging.info('Exit node: ' + str(exit_node))
                self.geth.callContract('ExitSigner','signalExit',False)
                time.sleep(1)
                #timeout_limit_s -= 1
                if time.time() - exit_start >= timeout_limit_s: #timeout_limit_s<=0:
                    timeout_triggered = True
                    logging.info("Exit timeout triggered. Skipping self-removal of signer status.")
                    break
                exit_node = self.geth.callContract('ExitSigner','getExitingNode')
            if not timeout_triggered:
                demotion_start = time.time()
                while self.geth.session.eth.coinbase.lower() in self.geth.getSigners():
                    logging.info('Waiting for demotion...')
                    self.geth.demoteSigner(self.geth.session.eth.coinbase)
                    time.sleep(1)
                    #timeout_limit_s -= 1
                    if time.time()-demotion_start >= timeout_limit_s: #timeout_limit_s<=0:
                        logging.warn("Timeout triggered. Skipping demotion pass.")
                        break
                    pass
                self.geth.callContract('ExitSigner','finalizeExit',False)
            return not timeout_triggered
        return False

    def run(self):
        t0_count = time.time()
        t0_rot = t0_count
        t0_exit = t0_count

        self.geth.session.geth.miner.start()

        exiting_node = self.geth.callContract('ExitSigner','getExitingNode')

        if str(exiting_node).lower() == self.geth.session.eth.coinbase.lower():
            self.geth.callContract('ExitSigner','finalizeExit',False)

        if str(exiting_node).lower() == self.geth.session.eth.coinbase.lower():
            logging.error('Signer quorum may not be present!')
            print('ERROR: Signer quorum may not be present!')
            
        #if type(exiting_node) == list and self.geth.session.eth.coinbase in exiting_nodes:
        #    self.geth.callContract('ExitSigner','finalizeExit',False)
        #else:
        #    print(exiting_nodes)
        signers = self.geth.getSigners()
        for s in signers:
            if not self.signer_fifo.get(s,None):
                self.signer_fifo[s]=0
            else:
                self.signer_fifo[s]+=1
        for s in self.signer_fifo.keys():
            if not s in signers:
                self.signer_fifo[s] = -1
            if self.geth.callContract('ExitSigner','isOwner',True,{},Web3.toChecksumAddress(s)):
                self.signer_fifo[s] = -2

        while not self._thread_exit:
            t1 = time.time()

            if not self.geth.session.eth.mining:
                logging.info("Starting miner")
                self.geth.session.geth.miner.start()
            
            #Request from faucet
            local_balance_wei = self.geth.session.eth.get_balance(self.geth.session.eth.coinbase)
            if Web3.fromWei(local_balance_wei,'ether') <= self.top_off_threshold_ether:
                logging.info("Requesting funds from faucet")
                self.geth.callContract('Faucet','requestFunds',False,{},self.geth.session.eth.coinbase)
            
            #Donate to the faucet
            if Web3.fromWei(local_balance_wei,'ether') >= self.donate_threshold_ether:
                logging.info('Donating excess to faucet')
                donate_amount = local_balance_wei - Web3.toWei(self.donate_lower_limit,'ether')
                self.geth.callContract('Faucet','donateToFaucet',False,tx={'value':donate_amount})
            
            #Check exiting node
            if t1-t0_exit>=self.exit_interval_s:
                exiting_node = self.geth.callContract('ExitSigner','getExitingNode')
                logging.info('Exiting Nodes: ' + str(exiting_node))
                t0_exit = time.time()

            #Check signer count
            if t1-t0_count >= self.count_check_interval_s:
                signers = self.geth.getSigners()
                signer_count = len(signers)
                logging.info('Count: Signers: ' + str(signer_count))
                logging.info(str(signers) + ' ' + str(type(signers)))
                if signer_count <1:
                    print("Error: No Signer Nodes Present!!!!!")
                elif signer_count<self.signer_target_count:
                    peers = self.geth.session.geth.admin.peers()
                    logging.info('Peer Count: '+str(len(peers)))
                    logging.info('Signer Count: '+str(signer_count))
                    if len(peers)>=signer_count:
                        logging.info('Can add signer')
                        logging.info('I am ' + str(self.geth.session.eth.coinbase))
                        #logging.info('Am I signer? ' + str(str(self.geth.session.eth.coinbase) in signers))
                        if str(self.geth.session.eth.coinbase).lower() in signers:
                            logging.info('I am a signer')
                            random.shuffle(peers)
                            for peer in peers:
                                logging.info('Looking at peer '+peer['id'])
                                if peer['id'] in self.geth.peer_coinbase_registry['Coinbase']:
                                    cb_addr = self.geth.peer_coinbase_registry['Coinbase'][peer['id']].lower()
                                    if not cb_addr in signers and cb_addr != exiting_node:
                                        if self.signer_fifo.get(cb_addr,None) is None:
                                            logging.info(str(self.signer_fifo))
                                            self.signer_fifo[cb_addr] = 0
                                        elif self.signer_fifo.get(cb_addr,None) == -2:
                                            logging.info('is owner')
                                            continue
                                        elif self.signer_fifo.get(cb_addr,None) == -1:
                                            logging.info('adding to life count')
                                            self.signer_fifo[cb_addr]+=1
                                        elif self.signer_fifo.get(cb_addr,None) == 0:
                                            logging.info('Proposing signer: '+cb_addr)
                                            self.geth.proposeSigner(cb_addr)
                                            break
                                        else:
                                            logging.info('What is going on?')                                        
                                    else:
                                        logging.info('Signers? '+str(signers))
                                else:
                                    logging.info(str(peer['id'] + ' not in '+str(list(self.geth.peer_coinbase_registry.keys()))))
                
                t0_count = time.time()
            
            #Signer Rotation
            if t1-t0_rot >= self.rotation_interval_s:
                if self.use_fifo_rotation:
                    signers = self.geth.getSigners()
                    for s in signers:
                        s = str(s).lower()
                        if not self.signer_fifo.get(s.lower(),None):
                            self.signer_fifo[s]=1
                        else:
                            self.signer_fifo[s]+=1
                    for s in self.signer_fifo.keys():
                        s = s.lower()
                        if not s in signers:
                            self.signer_fifo[s] = -1
                        if self.geth.callContract('ExitSigner','isOwner',True,{},Web3.toChecksumAddress(s)):
                            self.signer_fifo[s] = -2
                    demote_target = max(self.signer_fifo,key=self.signer_fifo.get)
                    logging.info("Demote target: " + str(demote_target))
                    is_owner = self.geth.callContract('ExitSigner','isOwner',True,{},Web3.toChecksumAddress(demote_target))
                    owner = self.geth.callContract('ExitSigner','getOwner',True)
                    logging.info('Owner: ' + str(owner))
                    logging.info("Is Demotion Target the initial node? " + str(is_owner))
                    logging.info("Signer FIFO: "+str(self.signer_fifo))
                    if self.signer_fifo[demote_target]<=0 or is_owner:
                        t0_rot = time.time()
                    else:
                        logging.info("Attempting to demote "+str(demote_target))
                        self.geth.demoteSigner(demote_target)
                    pass
                else:
                    if not self.geth.callContract('ExitSigner','isOwner',True,{},Web3.toChecksumAddress(self.geth.session.eth.coinbase)):
                        logging.info("Rotation triggered.")
                        self.exitFromSignerList()
                        t0_rot = time.time()
            
            if exiting_node != '0x0000000000000000000000000000000000000000':
                self.geth.demoteSigner(exiting_node)
                logging.info("Voting to demote: " + str(exiting_node))
            
            #Call faucet for poor peers
            for peer in self.geth.session.geth.admin.peers():
                if str(peer['id']) in self.geth.peer_coinbase_registry['Coinbase'] and self.geth.session.eth.get_balance(self.geth.peer_coinbase_registry['Coinbase'][peer['id']])<Web3.toWei(1,'ether'):
                    logging.info("Calling faucet for poor peer: "+str(self.geth.peer_coinbase_registry['Coinbase'][peer['id']]))
                    self.geth.callContract('Faucet','requestFunds',False,{},Web3.toChecksumAddress(self.geth.peer_coinbase_registry['Coinbase'][peer['id']].lower()))
                        
            
            time.sleep(self.sleep_interval_s)

        self.exitFromSignerList()
        self.geth.stopDaemon()

        self._thread_exit = False
        
