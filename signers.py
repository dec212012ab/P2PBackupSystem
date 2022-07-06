from geth_helper import GethHelper
import time
import logging
from pathlib import Path

logging.basicConfig(filename=str(Path.home()/'.eth'/'signers.log'),encoding='utf-8',level=logging.INFO)

class SignerMonitor:
    def __init__(self,geth:GethHelper):
        self.signer_target_count = 7
        self.sleep_interval_s = 5
        self.count_check_interval_s = 15
        self.rotation_interval_s = 60
        self.exit_interval_s = 20
        self.geth = geth
        self._thread_exit = False

    def stopSignal(self):
        self._thread_exit = True

    def run(self):
        t0_count = time.time()
        t0_rot = t0_count
        t0_exit = t0_count

        exiting_nodes = self.geth.callContract('ExitSigner','getExitingNodes')
        if self.geth.session.eth.coinbase in exiting_nodes:
            self.geth.callContract('ExitSigner','finalizeExit',False)
        

        while not self._thread_exit:
            t1 = time.time()

            #Check exiting nodes
            if t1-t0_exit>=self.exit_interval_s:
                exiting_nodes = self.geth.callContract('ExitSigner','getExitingNodes')
                logging.info('Exiting Nodes: ' + str(exiting_nodes))

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
                            for peer in sorted(peers,key=lambda d: d['id']):
                                logging.info('Looking at peer '+peer['id'])
                                if peer['id'] in self.geth.peer_coinbase_registry['Coinbase']:
                                    cb_addr = self.geth.peer_coinbase_registry['Coinbase'][peer['id']]
                                    if not cb_addr in signers and not cb_addr in exiting_nodes:
                                        logging.info('Proposing signer: '+cb_addr)
                                        self.geth.proposeSigner(cb_addr)
                                        break
                
                t0_count = time.time()
            
            #Prune offline signers
            if t1-t0_rot >= self.rotation_interval_s:
                signers = self.geth.getSigners()
                if len(signers)>1:
                   if self.geth.session.eth.coinbase.lower() in signers:
                        peers = [self.geth.peer_coinbase_registry['Coinbase'][p['id']].lower() for p in self.geth.session.geth.admin.peers() if p['id'] in self.geth.peer_coinbase_registry['Coinbase']]
                        for signer in signers:
                            if not signer in peers:
                                logging.info("Demoting offline signer")
                                self.geth.demoteSigner(signer)
                            pass
                            
                        '''peers = sorted([p['id'] for p in self.geth.session.geth.admin.peers()])
                        for peer in peers:
                            logging.info('Checking peer '+peer+' for rotation')
                            if peer in self.geth.peer_coinbase_registry['Coinbase']:
                                logging.info("Peer in coinbase")
                                cb_addr = self.geth.peer_coinbase_registry['Coinbase'][peer]
                                if str(cb_addr).lower() in signers:
                                    logging.info('Demoting '+cb_addr)
                                    self.geth.demoteSigner(cb_addr)
                                    break
                        '''
            #            logging.info('Demoting '+signers[0]+' for rotation')
            #            self.geth.demoteSigner(signers[0])

            #    logging.info('Rotation end: ' + str(self.geth.getSigners()))
            #    t0_rot = time.time()
            
            #Check if signer is signing
            #signers = self.geth.getSigners()
            if not self.geth.session.eth.mining:
                logging.info("Starting miner")
                self.geth.session.geth.miner.start()
            
            #Check pending proposals
            #logging.info(str(self.geth.getProposals()))
            for node in exiting_nodes:
                self.geth.demoteSigner(node)
            

            time.sleep(self.sleep_interval_s)

        '''if len(self.geth.getSigners()) > 1:
            print('Removing self from signer list...')
            self.geth.callContract('ExitSigner','signalExit',False)
            timeout = 62
            while self.geth.session.eth.coinbase.lower() in self.geth.getSigners():
                if timeout < 1:
                    break
                if len(self.geth.getSigners())>1:
                    self.geth.demoteSigner(self.geth.session.eth.coinbase)
                else:
                    self.geth.discardProposal(self.geth.session.eth.coinbase)
                    break
                timeout -= 1
                time.sleep(1)
            
            self.geth.session.geth.miner.stop()
            self.geth.callContract('ExitSigner','finalizeExit',False)
            '''
        self.geth.stopDaemon()

        self._thread_exit = False
        
