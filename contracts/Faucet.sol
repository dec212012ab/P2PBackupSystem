// SPDX-License-Identifier: GPL-3.0
pragma solidity >=0.4.16 <0.9.0;

/*contract Mortal {
    address owner;
    address[] internal authorized;
    constructor(){
        owner = msg.sender;
        authorized = new address[](1);
    }

    function kill() public{
        if (msg.sender == owner) selfdestruct(payable(owner));
    }
}*/

contract Faucet{
    address owner;
    address[] internal authorized;

    mapping(address=>uint) public request_map;
    uint public distribution_amount = 3 * (10**18);

    constructor() payable{
        owner = msg.sender;
        authorized = new address[](1);
    }

    function kill() public{
        if (msg.sender == owner) selfdestruct(payable(owner));
    }

    modifier restrictToOwner{
        require(msg.sender == owner ,"This function is restricted to the contract owner!");
        _;
    }

    modifier restrictToAuthorized{
        bool found = false;
        if(msg.sender != owner){
            for (uint256 index = 0; index < authorized.length; index++) {
                if(msg.sender == authorized[index]){
                    found = true;
                    break;
                }
            }
        }
        else found = true;
        require(found ,"This function is restricted to authorized users!");
        _;
    }

    function addAuthorized(address new_authorized) public restrictToAuthorized{
        bool found = false;
        for(uint i = 0; i<authorized.length; i++){
            if(authorized[i] == new_authorized){
                found = true;
                break;
            }
        }
        if(!found){
            authorized.push(new_authorized);
        }
    }


    function setOwner(address new_owner) public restrictToOwner {
        owner = new_owner;
    }

    function setDistributionAmount(uint new_amount) public restrictToOwner{
        distribution_amount = new_amount;
    }

    function donateToFaucet() public payable{

    }

    function getFaucetBalance() view public returns (uint256 retVal){
        return address(this).balance;
    }

    function requestFunds(address payable _dest/*, bool owner_force*/) public payable {
        uint top_off_amount = 0;
        //if(msg.sender != owner || owner_force){
            require(block.timestamp > request_map[msg.sender],"Requesting account is still locked from previous faucet request.");
            require(address(this).balance > distribution_amount,"Not enough funds in faucet for distribution. Authorized nodes should donate.");
            require(_dest.balance<distribution_amount,"Destination node already has at least 10 Ether!");
            top_off_amount = distribution_amount - _dest.balance;
        //}
        /*else{
            if(address(this).balance < distribution_amount){
                top_off_amount = address(this).balance;
            }
            else{
                top_off_amount = distribution_amount - _dest.balance;
            }
        }*/
        

        _dest.transfer(top_off_amount);
        //Lock for some time since we can't request if we have more than 10 ether
        request_map[msg.sender] = block.timestamp + 5 minutes;
    }

}