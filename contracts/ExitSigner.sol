// SPDX-License-Identifier: GPL-3.0
pragma solidity >=0.4.16 <0.9.0;

contract ExitSigner{
    address owner;
    address[] internal exit_nodes;

    constructor(){
        owner = msg.sender;
    }

    function kill() public{
        if(msg.sender == owner) selfdestruct(payable(owner));
    }

    modifier restrictToUnique{
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
    }

    function signalExit() public restrictToUnique{
        exit_nodes.push(msg.sender);
    }

    function getExitingNodes() view public returns (address[] memory retVal){
        return exit_nodes;
    }

    function isExitingNode(address addr) view public returns(bool){
        bool found = false;
        
        for (uint256 index = 0; index < exit_nodes.length; index++) {
            if(addr == exit_nodes[index]){
                found = true;
                break;
            }
        }

        return found;
    }

    function finalizeExit() public restrictToPresent{
        for(uint256 index = 0; index<exit_nodes.length; index++){
            if (msg.sender == exit_nodes[index]){
                exit_nodes[index] = exit_nodes[exit_nodes.length-1];
                exit_nodes.pop();
                break;
            }
        }
    }
}