from ipfs import IPFS, IPFSCluster
import json

a = IPFS()
b = IPFSCluster()

output = a.execute_cmd('pin/ls',{})
hashes = output.json()['Keys']

for k in hashes.keys():
    if hashes[k]['Type'] == 'recursive':
#        print(
        a.execute_cmd('pin/rm',{},k).text
#            )

output = a.execute_cmd('files/ls',{},'//').json()
if output['Entries']:
    for entry in output['Entries']:
        print(a.execute_cmd('files/rm',{},'//'+entry['Name'],force=True).text)

#print(
a.execute_cmd('repo/gc',{}).text
#    )

cl_hashes = [item.strip() for item in b.listPins().text.split('\n') if item.strip()]

for item in cl_hashes:
    json_item = json.loads(item)
    b.unpinCID(json_item['cid'])