// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Test} from "forge-std/Test.sol";
import {LaminaRWAToken} from "../src/LaminaRWAToken.sol";

contract LaminaRWATokenTest is Test {
    LaminaRWAToken token;
    address treasury = address(this); // holds DEFAULT_ADMIN + COMPLIANCE + MINTER
    address alice = makeAddr("alice");
    address bob = makeAddr("bob");

    function setUp() public {
        token = new LaminaRWAToken("US Treasury Bond", "USTB", 1_000_000, 2, "bond", "US", treasury);
    }

    function testTreasuryInitialSupplyAndKyc() public view {
        assertEq(token.balanceOf(treasury), 1_000_000);
        assertTrue(token.kycApproved(treasury));
        assertEq(token.decimals(), 2);
        assertEq(token.assetType(), "bond");
    }

    function testTransferRequiresReceiverKyc() public {
        vm.expectRevert(bytes("LaminaRWA: receiver not KYC approved"));
        token.transfer(alice, 100);

        token.grantKYC(alice);
        assertTrue(token.transfer(alice, 100));
        assertEq(token.balanceOf(alice), 100);
    }

    function testNonKycSenderCannotTransfer() public {
        token.grantKYC(alice); // alice can receive
        token.transfer(alice, 100);
        token.revokeKYC(alice); // now alice is not approved
        token.grantKYC(bob);
        vm.prank(alice);
        vm.expectRevert(bytes("LaminaRWA: sender not KYC approved"));
        token.transfer(bob, 10);
    }

    function testFrozenAccountCannotTransfer() public {
        token.grantKYC(alice);
        token.grantKYC(bob);
        token.transfer(alice, 100);
        token.freeze(alice);
        vm.prank(alice);
        vm.expectRevert(bytes("LaminaRWA: sender account is frozen"));
        token.transfer(bob, 10);
        token.unfreeze(alice);
        vm.prank(alice);
        assertTrue(token.transfer(bob, 10));
    }

    function testMintRequiresKyc() public {
        vm.expectRevert(bytes("LaminaRWA: mint recipient not KYC approved"));
        token.mint(alice, 500);

        token.grantKYC(alice);
        token.mint(alice, 500);
        assertEq(token.balanceOf(alice), 500);
    }

    function testForceBurnByCompliance() public {
        token.grantKYC(alice);
        token.transfer(alice, 1000);
        token.forceBurn(alice, 400, "maturity_settlement");
        assertEq(token.balanceOf(alice), 600);
    }

    function testOnlyComplianceCanGrantKyc() public {
        vm.prank(alice); // no role
        vm.expectRevert();
        token.grantKYC(bob);
    }

    function testOnlyMinterCanMint() public {
        token.grantKYC(alice);
        vm.prank(bob); // no role
        vm.expectRevert();
        token.mint(alice, 1);
    }

    function testGrantKycBatch() public {
        address[] memory accts = new address[](2);
        accts[0] = alice;
        accts[1] = bob;
        token.grantKYCBatch(accts);
        assertTrue(token.kycApproved(alice));
        assertTrue(token.kycApproved(bob));
    }
}
