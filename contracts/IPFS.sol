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

    function pinned(string memory hash) public{
        emit Pinned(msg.sender, hash);
    }

    function unpinned(string memory hash) public{
        emit Unpinned(msg.sender, hash);
    }

    event Pinned(address sender, string hash);
    event Unpinned(address sender, string hash);

}