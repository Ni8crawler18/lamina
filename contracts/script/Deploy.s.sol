// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Script, console} from "forge-std/Script.sol";
import {AuditLog}       from "../src/AuditLog.sol";
import {LaminaFactory}  from "../src/LaminaFactory.sol";

/// @notice Deploy AuditLog + LaminaFactory to Robinhood Chain testnet.
///         Run with:
///           forge script script/Deploy.s.sol \
///             --rpc-url robinhood_testnet \
///             --private-key $PRIVATE_KEY \
///             --broadcast \
///             --verify (optional, if blockscout supports it)
contract DeployLamina is Script {
    function run() external {
        uint256 deployerKey = vm.envUint("PRIVATE_KEY");
        address deployer    = vm.addr(deployerKey);

        console.log("Deployer :", deployer);
        console.log("Chain ID :", block.chainid);
        console.log("Balance  :", deployer.balance);

        vm.startBroadcast(deployerKey);

        // 1. Deploy AuditLog (deployer is owner + first writer == agent operator)
        AuditLog auditLog = new AuditLog();
        console.log("AuditLog deployed     :", address(auditLog));

        // 2. Deploy LaminaFactory (references AuditLog)
        LaminaFactory factory = new LaminaFactory(address(auditLog));
        console.log("LaminaFactory deployed:", address(factory));

        // 3. Authorize the factory to create audit topics during deployAsset()
        auditLog.setWriter(address(factory), true);
        console.log("Factory authorized as AuditLog writer");

        vm.stopBroadcast();

        // Print .env lines for easy copy-paste
        console.log("\n--- Copy these into server/.env ---");
        console.log("AUDIT_LOG_ADDRESS=%s", address(auditLog));
        console.log("FACTORY_ADDRESS=%s",   address(factory));
    }
}
