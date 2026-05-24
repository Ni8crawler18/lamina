// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./LaminaRWAToken.sol";
import "./AuditLog.sol";

/// @title LaminaFactory
/// @notice Deploy a new tokenized RWA (LaminaRWAToken + AuditLog topic) in a
///         single transaction.  Mirrors the combined HTS + HCS create flow on Hedera.
///
///         The factory owns the shared AuditLog contract.
///         Each asset gets its own LaminaRWAToken + a dedicated topic ID.
contract LaminaFactory {
    AuditLog public immutable auditLog;
    address  public immutable owner;

    struct AssetRecord {
        address tokenAddress;
        bytes32 topicId;
        string  name;
        string  symbol;
        address deployer;
        uint256 deployedAt;
    }

    AssetRecord[] public assets;
    mapping(address => AssetRecord) public assetByToken;

    event AssetDeployed(
        address indexed tokenAddress,
        bytes32 indexed topicId,
        string  name,
        string  symbol,
        address indexed deployer
    );

    constructor(address _auditLog) {
        auditLog = AuditLog(_auditLog);
        owner    = msg.sender;
    }

    /// @notice Deploy a new compliant RWA token + audit topic.
    /// @param name_         Full asset name, e.g. "US Treasury Bond 2031"
    /// @param symbol_       Token symbol, e.g. "UST31"
    /// @param totalSupply_  Total token supply in smallest units
    /// @param decimals_     Decimal places (2 for bonds priced to cents)
    /// @param assetType_    "bond" | "equity" | "fund" | "real_estate"
    /// @param jurisdiction_ "US" | "EU" | "UK" | "SG"
    /// @return tokenAddress  Deployed LaminaRWAToken address
    /// @return topicId       AuditLog topic ID (bytes32) for this asset
    function deployAsset(
        string  calldata name_,
        string  calldata symbol_,
        uint256          totalSupply_,
        uint8            decimals_,
        string  calldata assetType_,
        string  calldata jurisdiction_
    ) external returns (address tokenAddress, bytes32 topicId) {
        // 1. Deploy token — deployer (msg.sender) becomes treasury + compliance admin
        LaminaRWAToken token = new LaminaRWAToken(
            name_,
            symbol_,
            totalSupply_,
            decimals_,
            assetType_,
            jurisdiction_,
            msg.sender
        );
        tokenAddress = address(token);

        // 2. Create audit topic
        string memory memo = string.concat("Lamina audit: ", name_, " (", symbol_, ")");
        topicId = auditLog.createTopic(memo);

        // 3. Record
        AssetRecord memory record = AssetRecord({
            tokenAddress: tokenAddress,
            topicId:      topicId,
            name:         name_,
            symbol:       symbol_,
            deployer:     msg.sender,
            deployedAt:   block.timestamp
        });
        assets.push(record);
        assetByToken[tokenAddress] = record;

        emit AssetDeployed(tokenAddress, topicId, name_, symbol_, msg.sender);
    }

    /// @notice Total number of assets deployed via this factory.
    function assetCount() external view returns (uint256) {
        return assets.length;
    }
}
