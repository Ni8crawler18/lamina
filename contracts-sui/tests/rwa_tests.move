#[test_only]
module lamina_rwa::rwa_tests;

use sui::test_scenario as ts;
use sui::token::{TokenPolicy, TokenPolicyCap};
use std::string;
use lamina_rwa::rwa::{Self, OperatorCap, Asset};

const OP: address = @0xA;
const ALICE: address = @0xA11CE;
const MALLORY: address = @0xBAD;

fun s(b: vector<u8>): string::String { string::utf8(b) }

fun issue(sc: &mut ts::Scenario) {
    let cap = sc.take_from_sender<OperatorCap>();
    rwa::issue_asset(
        &cap, s(b"US Treasury Bill"), s(b"USTB"), 6, 1_000_000,
        s(b"bond"), s(b"US"), s(b"Laminaa SPV LLC"), sc.ctx(),
    );
    sc.return_to_sender(cap);
}

#[test]
fun full_lifecycle() {
    let mut sc = ts::begin(OP);
    rwa::init_for_testing(sc.ctx());

    sc.next_tx(OP);
    issue(&mut sc);

    sc.next_tx(OP);
    {
        let cap = sc.take_from_sender<OperatorCap>();
        let mut policy = sc.take_shared<TokenPolicy<rwa::RWA>>();
        let policy_cap = sc.take_from_sender<TokenPolicyCap<rwa::RWA>>();
        let mut asset = sc.take_shared<Asset>();

        rwa::grant_kyc(&cap, &mut policy, &policy_cap, ALICE);
        rwa::transfer(&cap, &policy, &mut asset, ALICE, 500);
        assert!(rwa::balance_of(&asset, ALICE) == 500, 0);
        assert!(rwa::treasury_of(&asset) == 999_500, 1);

        // freeze blocks a subsequent transfer; claw back works regardless
        rwa::force_redeem(&cap, &mut asset, ALICE, 200);
        assert!(rwa::balance_of(&asset, ALICE) == 300, 2);
        assert!(rwa::treasury_of(&asset) == 999_700, 3);

        sc.return_to_sender(cap);
        sc.return_to_sender(policy_cap);
        ts::return_shared(policy);
        ts::return_shared(asset);
    };
    ts::end(sc);
}

#[test]
#[expected_failure(abort_code = rwa::EKyc)]
fun transfer_to_non_kyc_aborts() {
    let mut sc = ts::begin(OP);
    rwa::init_for_testing(sc.ctx());
    sc.next_tx(OP);
    issue(&mut sc);

    sc.next_tx(OP);
    {
        let cap = sc.take_from_sender<OperatorCap>();
        let policy = sc.take_shared<TokenPolicy<rwa::RWA>>();
        let mut asset = sc.take_shared<Asset>();

        rwa::transfer(&cap, &policy, &mut asset, MALLORY, 100); // never KYC'd → abort
        abort 99
    }
}
