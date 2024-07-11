// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title SimpleWallet
 * @dev A simple wallet that allows the owner to deposit and withdraw Ether.
 */
contract SimpleWallet {
    address public owner;

    /**
     * @dev Initializes the contract setting the deployer as the initial owner.
     */
    constructor() {
        owner = msg.sender;
    }

    /**
     * @dev Modifier to check if the caller is the owner.
     */
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can execute this.");
        _;
    }

    /**
     * @dev Allows the owner to deposit Ether into the contract.
     */
    function deposit() external payable onlyOwner {}

    /**
     * @dev Allows the owner to withdraw a specified amount of Ether from the contract.
     * @param amount The amount of Ether to withdraw.
     */
    function withdraw(uint256 amount) external onlyOwner {
        require(address(this).balance >= amount, "Insufficient balance.");
        payable(owner).transfer(amount);
    }

    /**
     * @dev Returns the balance of Ether held by the contract.
     * @return The balance of Ether held by the contract.
     */
    function getBalance() external view returns (uint256) {
        return address(this).balance;
    }

    /**
     * @dev Rejects any anonymous Ether transfers.
     */
    receive() external payable {
        revert("Please use the deposit function to fund this wallet.");
    }

    /**
     * @dev Allow contract owner to change owner address.
     * @param newOwner The address of the new owner.
     */
    function changeOwner(address newOwner) external onlyOwner {
        require(newOwner != address(0), "New owner cannot be zero address.");
        owner = newOwner;
    }
}