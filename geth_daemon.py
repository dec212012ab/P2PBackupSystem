from geth_helper import * 

if platform.system() == 'Windows':
    g = GethHelper("\\\\.\\pipe\\geth.ipc")
else:
    g = GethHelper(str(Path.home()/'.eth'/'node0'/'geth.ipc'))
g.startDaemon(netrestrict=['192.168.3.0/24'])
g.connect()


print('CHECKSUM: ',Web3.toChecksumAddress(g.session.eth.coinbase))

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