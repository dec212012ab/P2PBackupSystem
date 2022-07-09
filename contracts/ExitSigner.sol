// SPDX-License-Identifier: GPL-3.0
pragma solidity >=0.4.16 <0.9.0;

contract ExitSigner{
    address owner;
    //address[] internal exit_nodes;
    address exiting_node;

    constructor(){
        owner = msg.sender;
    }

    function kill() public{
        if(msg.sender == owner) selfdestruct(payable(owner));
    }

    /*modifier restrictToUnique{
        bool found = false;
        
        for (uint256 index = 0; index < exit_nodes.length; index++) {
            if(msg.sender == exit_nodes[index]){
                found = true;
                break;
            }
        }
       
        require(!found ,"Exiting node already posted!");
        _;
    }

    modifier restrictToPresent{
        bool found = false;
        
        for (uint256 index = 0; index < exit_nodes.length; index++) {
            if(msg.sender == exit_nodes[index]){
                found = true;
                break;
            }
        }
       
        require(found ,"Exiting node not in list of exiting nodes!");
        _;
    }*/

    function isOwner(address addr) view public returns (bool retVal){
        return addr == owner;
    }

    function getOwner() view public returns (address retVal){
        return owner;
    }

    function canExit() view public returns (bool retVal){
        return msg.sender != owner && exiting_node==address(0);
    }

    function signalExit() public { //restrictToUnique{
        //exit_nodes.push(msg.sender);
        require(msg.sender != owner,"Initial node cannot be demoted!");
        require(exiting_node==address(0),"Another node is exiting!");
        exiting_node = msg.sender;
    }

    //function getExitingNodes() view public returns (address[] memory retVal){
    //    return exit_nodes;
    //}

    function getExitingNode() view public returns (address retVal){
        return exiting_node;
    }

    /*function isExitingNode(address addr) view public returns(bool){
        bool found = false;
        
        for (uint256 index = 0; index < exit_nodes.length; index++) {
            if(addr == exit_nodes[index]){
                found = true;
                break;
            }
        }

        return found;
    }*/

    function finalizeExit() public { //restrictToPresent{
        require(exiting_node!=address(0) && msg.sender==exiting_node,"Nothing to finalize!");
        exiting_node = address(0);
        /*for(uint256 index = 0; index<exit_nodes.length; index++){
            if (msg.sender == exit_nodes[index]){
                exit_nodes[index] = exit_nodes[exit_nodes.length-1];
                exit_nodes.pop();
                break;
            }
        }*/
    }
}