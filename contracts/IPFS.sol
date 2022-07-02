// SPDX-License-Identifier: GPL-3.0
pragma solidity >=0.4.16 <0.9.0;

contract IPFS{
    address owner;

    constructor(){
        owner = msg.sender;
    }

    function kill() public{
        if(msg.sender == owner) selfdestruct(payable(owner));
    }

    function pinned(string memory filename, string memory hash) public{
        emit Pinned(msg.sender, filename, hash);
    }

    function unpinned(string memory filename, string memory hash) public{
        emit Unpinned(msg.sender, filename, hash);
    }

    function postBackup(string memory backup_name, string memory fragment_names) public{
        emit BackupPosted(msg.sender,backup_name,fragment_names);
    }

    event BackupPosted(address sender,string backup_name,string fragment_names);
    event Pinned(address sender, string filename, string hash);
    event Unpinned(address sender, string filename, string hash);

}