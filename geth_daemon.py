from geth_helper import * 

if platform.system() == 'Windows':
    g = GethHelper("\\\\.\\pipe\\geth.ipc")
else:
    g = GethHelper(str(Path.home()/'.eth'/'node0'/'geth.ipc'))
g.startDaemon(netrestrict=['192.168.3.0/24'])
g.connect()


print('CHECKSUM: ',Web3.toChecksumAddress(g.session.eth.coinbase))

duration_seconds = 300

time.sleep(duration_seconds)

print("Local Node Ether: ",g.session.eth.get_balance(g.session.eth.coinbase))

print("Daemon Exitting")
g.stopDaemon()