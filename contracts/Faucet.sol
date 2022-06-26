// SPDX-License-Identifier: GPL-3.0
pragma solidity >=0.4.16 <0.9.0;

contract Mortal {
    address owner;
    address[] internal authorized;
    constructor(){
        owner = msg.sender;
        authorized = new address[](1);
    }

    function kill() public{
        if (msg.sender == owner) selfdestruct(payable(owner));
    }
}

contract Faucet is Mortal{
    
    mapping(address=>uint) public request_map;
    uint public distribution_amount = 10;

    constructor() payable{
        
    }

    modifier restrictToOwner{
        require(msg.sender == owner ,"This function is restricted to the contract owner!");
        _;
    }

    modifier restrictToAuthorized{
        bool found = false;
        for (uint256 index = 0; index < authorized.length; index++) {
            if(msg.sender == authorized[index]){
                found = true;
                break;
            }
        }
        require(found ,"This function is restricted to authorized users!");
        _;
    }

    function setOwner(address new_owner) public restrictToOwner {
        owner = new_owner;
    }


    
    
}