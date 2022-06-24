// SPDX-License-Identifier: GPL-3.0
pragma solidity >=0.4.16 <0.9.0;

contract Mortal {
    address owner;
    constructor(){
        owner = msg.sender;
    }

    function kill() public{
        if (msg.sender == owner) selfdestruct(payable(owner));
    }
}

contract Hello is Mortal{
    string greeting;

    constructor(string memory _greeting){
        greeting = _greeting;
    }

    function setGreeting(string memory _greeting) public{
        greeting=_greeting;
    }

    function greet() public view returns(string memory){
        return greeting;
    }
}