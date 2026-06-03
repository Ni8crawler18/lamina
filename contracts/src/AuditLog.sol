// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title AuditLog
/// @notice Immutable, append-only per-asset audit trail on Robinhood Chain / Arbitrum.
///         Replaces Hedera Consensus Service (HCS) topics.
///
/// @dev    Integrity model: only *authorized writers* may create topics or append
///         entries. The deployer is the owner and the first writer; the owner
///         authorizes the LaminaFactory and the off-chain agent operator. This
///         prevents anyone from forging or spamming the compliance audit trail —
///         entries can only originate from Lamina's own components.
contract AuditLog {
    string public constant VERSION = "1.1.0";

    struct LogEntry {
        uint256 timestamp;
        address caller;
        string  agent;
        string  action;
        string  details; // JSON-encoded string
    }

    mapping(bytes32 => LogEntry[]) private _logs;
    mapping(bytes32 => bool)       public  topics;
    mapping(bytes32 => string)     public  topicMemos;

    address public owner;
    mapping(address => bool) public writers;

    event TopicCreated(bytes32 indexed topicId, string memo, address indexed creator);
    event ActionLogged(
        bytes32 indexed topicId, uint256 indexed sequenceNumber,
        string agent, string action, uint256 timestamp
    );
    event WriterUpdated(address indexed writer, bool authorized);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    modifier onlyOwner() {
        require(msg.sender == owner, "AuditLog: not owner");
        _;
    }

    modifier onlyWriter() {
        require(writers[msg.sender], "AuditLog: not an authorized writer");
        _;
    }

    constructor() {
        owner = msg.sender;
        writers[msg.sender] = true; // deployer (== agent operator) can write
        emit OwnershipTransferred(address(0), msg.sender);
        emit WriterUpdated(msg.sender, true);
    }

    // ─── Access control ───────────────────────────────────────────────────────
    /// @notice Authorize or revoke an address (e.g. the LaminaFactory) as a writer.
    function setWriter(address writer, bool authorized) external onlyOwner {
        require(writer != address(0), "AuditLog: zero address");
        writers[writer] = authorized;
        emit WriterUpdated(writer, authorized);
    }

    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "AuditLog: zero address");
        emit OwnershipTransferred(owner, newOwner);
        owner = newOwner;
    }

    // ─── Topics & entries (writers only) ───────────────────────────────────────
    /// @notice Create a new audit topic for an asset. Returns topic ID (bytes32).
    function createTopic(string calldata memo) external onlyWriter returns (bytes32 topicId) {
        topicId = keccak256(abi.encodePacked(msg.sender, memo, block.timestamp, block.number, _nonce++));
        require(!topics[topicId], "AuditLog: topic already exists");
        topics[topicId]     = true;
        topicMemos[topicId] = memo;
        emit TopicCreated(topicId, memo, msg.sender);
    }

    /// @notice Append an agent action to an existing topic.
    function log(bytes32 topicId, string calldata agent, string calldata action, string calldata details)
        external onlyWriter returns (uint256 sequenceNumber)
    {
        require(topics[topicId], "AuditLog: topic does not exist");
        sequenceNumber = _logs[topicId].length;
        _logs[topicId].push(LogEntry({
            timestamp: block.timestamp, caller: msg.sender,
            agent: agent, action: action, details: details
        }));
        emit ActionLogged(topicId, sequenceNumber, agent, action, block.timestamp);
    }

    // ─── Reads ──────────────────────────────────────────────────────────────────
    /// @notice Read up to `limit` most-recent entries for a topic (newest last).
    function getMessages(bytes32 topicId, uint256 limit)
        external view returns (LogEntry[] memory result)
    {
        LogEntry[] storage all = _logs[topicId];
        uint256 total = all.length;
        uint256 count = (limit == 0 || limit > total) ? total : limit;
        result = new LogEntry[](count);
        uint256 start = total - count;
        for (uint256 i = 0; i < count; i++) {
            result[i] = all[start + i];
        }
    }

    function messageCount(bytes32 topicId) external view returns (uint256) {
        return _logs[topicId].length;
    }

    // Monotonic nonce makes topic IDs unique even within the same block.
    uint256 private _nonce;
}
