// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";

/// @title LaminaRWAToken
/// @notice Compliance-enforced ERC-20 for tokenized real-world assets on Robinhood Chain.
///         Mirrors Hedera Token Service (HTS) behaviour:
///           - KYC whitelist enforced on every transfer (= HTS KYC key)
///           - Account freeze / unfreeze           (= HTS freeze key)
///           - Force-burn on maturity              (= HTS wipe key)
///           - Mint / burn by compliance role      (= HTS supply key)
///
///         Compliant with ERC-3643 intent: only KYC-approved, non-frozen
///         addresses can send or receive tokens.
contract LaminaRWAToken is ERC20, ERC20Burnable, AccessControl {
    // ─── Roles ───────────────────────────────────────────────────────────────
    bytes32 public constant COMPLIANCE_ROLE = keccak256("COMPLIANCE_ROLE");
    bytes32 public constant MINTER_ROLE     = keccak256("MINTER_ROLE");

    // ─── Compliance state ────────────────────────────────────────────────────
    mapping(address => bool) public kycApproved;
    mapping(address => bool) public frozen;

    // ─── Metadata ────────────────────────────────────────────────────────────
    uint8  private _decimals;
    string public  assetType;   // "bond" | "equity" | "fund" | "real_estate"
    string public  jurisdiction; // "US" | "EU" | "UK" | "SG"

    // ─── Events ──────────────────────────────────────────────────────────────
    event KYCGranted(address indexed account);
    event KYCRevoked(address indexed account);
    event AccountFrozen(address indexed account);
    event AccountUnfrozen(address indexed account);
    event ForceBurned(address indexed from, uint256 amount, string reason);

    // ─── Constructor ─────────────────────────────────────────────────────────
    constructor(
        string memory name_,
        string memory symbol_,
        uint256       initialSupply_,
        uint8         decimals_,
        string memory assetType_,
        string memory jurisdiction_,
        address       treasury_
    ) ERC20(name_, symbol_) {
        _decimals    = decimals_;
        assetType    = assetType_;
        jurisdiction = jurisdiction_;

        _grantRole(DEFAULT_ADMIN_ROLE, treasury_);
        _grantRole(COMPLIANCE_ROLE,    treasury_);
        _grantRole(MINTER_ROLE,        treasury_);

        // Treasury is auto-approved for KYC (distributes tokens to investors)
        kycApproved[treasury_] = true;

        if (initialSupply_ > 0) {
            _mint(treasury_, initialSupply_);
        }
    }

    // ─── Decimals override ───────────────────────────────────────────────────
    function decimals() public view override returns (uint8) { return _decimals; }

    // ─── Compliance hooks on every transfer ──────────────────────────────────
    function _update(address from, address to, uint256 amount)
        internal override
    {
        // Minting (from == address(0)) and burning (to == address(0)) bypass
        // KYC checks — only real wallet-to-wallet transfers are gated.
        if (from != address(0) && to != address(0)) {
            require(kycApproved[from], "LaminaRWA: sender not KYC approved");
            require(kycApproved[to],   "LaminaRWA: receiver not KYC approved");
            require(!frozen[from],     "LaminaRWA: sender account is frozen");
            require(!frozen[to],       "LaminaRWA: receiver account is frozen");
        }
        super._update(from, to, amount);
    }

    // ─── KYC management (= HTS grant/revoke KYC) ────────────────────────────
    function grantKYC(address account) external onlyRole(COMPLIANCE_ROLE) {
        kycApproved[account] = true;
        emit KYCGranted(account);
    }

    function revokeKYC(address account) external onlyRole(COMPLIANCE_ROLE) {
        kycApproved[account] = false;
        emit KYCRevoked(account);
    }

    // ─── Freeze / unfreeze (= HTS freeze key) ────────────────────────────────
    function freeze(address account) external onlyRole(COMPLIANCE_ROLE) {
        frozen[account] = true;
        emit AccountFrozen(account);
    }

    function unfreeze(address account) external onlyRole(COMPLIANCE_ROLE) {
        frozen[account] = false;
        emit AccountUnfrozen(account);
    }

    // ─── Mint (= HTS mint) ────────────────────────────────────────────────────
    function mint(address to, uint256 amount) external onlyRole(MINTER_ROLE) {
        _mint(to, amount);
    }

    // ─── Force-burn on maturity (= HTS wipe key) ─────────────────────────────
    /// @notice Burn tokens from any holder at maturity — compliance-authorised only.
    function forceBurn(address from, uint256 amount, string calldata reason)
        external onlyRole(COMPLIANCE_ROLE)
    {
        _burn(from, amount);
        emit ForceBurned(from, amount, reason);
    }

    // ─── Batch KYC (gas efficiency for large issuances) ──────────────────────
    function grantKYCBatch(address[] calldata accounts) external onlyRole(COMPLIANCE_ROLE) {
        for (uint256 i = 0; i < accounts.length; i++) {
            kycApproved[accounts[i]] = true;
            emit KYCGranted(accounts[i]);
        }
    }
}
