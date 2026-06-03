// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Test} from "forge-std/Test.sol";
import {AuditLog} from "../src/AuditLog.sol";
import {LaminaFactory} from "../src/LaminaFactory.sol";
import {LaminaRWAToken} from "../src/LaminaRWAToken.sol";

contract LaminaFactoryTest is Test {
    AuditLog auditLog;
    LaminaFactory factory;
    address operator = address(this); // deployer/operator + treasury

    function setUp() public {
        auditLog = new AuditLog();
        factory = new LaminaFactory(address(auditLog));
        auditLog.setWriter(address(factory), true); // factory may create topics
    }

    function testDeployAssetCreatesTokenAndTopic() public {
        (address tokenAddr, bytes32 topic) =
            factory.deployAsset("US Treasury Bond", "USTB", 1_000_000, 2, "bond", "US");

        assertTrue(tokenAddr != address(0));
        assertTrue(auditLog.topics(topic));
        assertEq(factory.assetCount(), 1);

        // Deployer is the treasury and is KYC-approved with the full supply.
        LaminaRWAToken token = LaminaRWAToken(tokenAddr);
        assertEq(token.balanceOf(operator), 1_000_000);
        assertTrue(token.kycApproved(operator));

        // Operator (a writer) can append to the factory-created topic.
        uint256 seq = auditLog.log(topic, "lifecycle", "asset_issued", "{}");
        assertEq(seq, 0);
    }

    function testUnauthorizedFactoryCannotCreateTopic() public {
        // A factory that was never authorized cannot create topics.
        LaminaFactory rogue = new LaminaFactory(address(auditLog));
        vm.expectRevert(bytes("AuditLog: not an authorized writer"));
        rogue.deployAsset("X", "X", 1, 2, "bond", "US");
    }
}
