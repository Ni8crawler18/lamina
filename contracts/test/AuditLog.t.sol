// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Test} from "forge-std/Test.sol";
import {AuditLog} from "../src/AuditLog.sol";

contract AuditLogTest is Test {
    AuditLog auditLog;
    address operator = address(this); // deployer = owner + first writer
    address factory = makeAddr("factory");
    address attacker = makeAddr("attacker");

    function setUp() public {
        auditLog = new AuditLog();
    }

    function testDeployerIsOwnerAndWriter() public view {
        assertEq(auditLog.owner(), operator);
        assertTrue(auditLog.writers(operator));
    }

    function testNonWriterCannotCreateTopic() public {
        vm.prank(attacker);
        vm.expectRevert(bytes("AuditLog: not an authorized writer"));
        auditLog.createTopic("asset");
    }

    function testNonWriterCannotLog() public {
        bytes32 topic = auditLog.createTopic("asset");
        vm.prank(attacker);
        vm.expectRevert(bytes("AuditLog: not an authorized writer"));
        auditLog.log(topic, "agent", "action", "{}");
    }

    function testOnlyOwnerCanSetWriter() public {
        vm.prank(attacker);
        vm.expectRevert(bytes("AuditLog: not owner"));
        auditLog.setWriter(factory, true);
    }

    function testAuthorizedWriterCanCreateAndLog() public {
        auditLog.setWriter(factory, true);
        vm.prank(factory);
        bytes32 topic = auditLog.createTopic("asset");
        vm.prank(factory);
        uint256 seq = auditLog.log(topic, "lifecycle", "asset_issued", "{}");
        assertEq(seq, 0);
        assertEq(auditLog.messageCount(topic), 1);
    }

    function testLogRequiresExistingTopic() public {
        vm.expectRevert(bytes("AuditLog: topic does not exist"));
        auditLog.log(bytes32(uint256(123)), "a", "b", "c");
    }

    function testGetMessagesReturnsEntries() public {
        bytes32 topic = auditLog.createTopic("asset");
        auditLog.log(topic, "lifecycle", "asset_issued", "{\"x\":1}");
        auditLog.log(topic, "compliance", "whitelist_add", "{\"y\":2}");
        AuditLog.LogEntry[] memory entries = auditLog.getMessages(topic, 10);
        assertEq(entries.length, 2);
        assertEq(entries[0].action, "asset_issued");
        assertEq(entries[1].action, "whitelist_add");
    }

    function testRevokedWriterCannotCreate() public {
        auditLog.setWriter(factory, true);
        auditLog.setWriter(factory, false);
        vm.prank(factory);
        vm.expectRevert(bytes("AuditLog: not an authorized writer"));
        auditLog.createTopic("asset");
    }
}
