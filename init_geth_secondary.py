import sys
import os
from geth_helper import * 

if platform.system() == 'Windows':
    g = GethHelper("\\\\.\\pipe\\geth.ipc")
else:
    g = GethHelper(str(Path.home()/'.eth'/'node0'/'geth.ipc'))
g.startDaemon(netrestrict=['192.168.3.0/24','192.168.2.0/24'],hide_output=False)
g.connect()

peer_path = os.path.join(os.path.dirname(sys.argv[0]),'install/redist/geth/peers')

if not os.path.isdir(peer_path):
    os.makedirs(peer_path)

checksum_addr = Web3.toChecksumAddress(g.session.eth.coinbase)
print('ID:',g.session.geth.admin.node_info()['id'])
print('CHECKSUM: ',checksum_addr)
with open(os.path.join(peer_path,g.session.geth.admin.node_info()['id']),'w') as f:
    f.write(checksum_addr)

duration_seconds = 600

while g.session.eth.get_balance(g.session.eth.coinbase)<=0:
    time.sleep(10)
    duration_seconds -= 10
    if duration_seconds<=0:
        print("Funding timout triggered!")
        break

print("Local Node Ether: ",g.session.fromWei(g.session.eth.get_balance(g.session.eth.coinbase),'ether'))

print("Daemon Exitting")
g.stopDaemon()