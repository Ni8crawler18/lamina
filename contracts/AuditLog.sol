// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title AuditLog
/// @notice Immutable per-asset audit trail on Robinhood Chain / Arbitrum.
///         Replaces Hedera Consensus Service (HCS) topics.
///         Every Lamina agent action is written here permanently.
contract AuditLog {
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

    event TopicCreated(
        bytes32 indexed topicId,
        string  memo,
        address indexed creator
    );

    event ActionLogged(
        bytes32 indexed topicId,
        uint256 indexed sequenceNumber,
        string  agent,
        string  action,
        uint256 timestamp
    );

    /// @notice Create a new audit topic for an asset. Returns topic ID (bytes32).
    function createTopic(string calldata memo) external returns (bytes32 topicId) {
        topicId = keccak256(abi.encodePacked(msg.sender, memo, block.timestamp, block.number));
        require(!topics[topicId], "Topic already exists");
        topics[topicId]    = true;
        topicMemos[topicId] = memo;
        emit TopicCreated(topicId, memo, msg.sender);
    }

    /// @notice Append an agent action to an existing topic.
    function log(
        bytes32        topicId,
        string calldata agent,
        string calldata action,
        string calldata details
    ) external returns (uint256 sequenceNumber) {
        require(topics[topicId], "Topic does not exist");
        sequenceNumber = _logs[topicId].length;
        _logs[topicId].push(LogEntry({
            timestamp: block.timestamp,
            caller:    msg.sender,
            agent:     agent,
            action:    action,
            details:   details
        }));
        emit ActionLogged(topicId, sequenceNumber, agent, action, block.timestamp);
    }

    /// @notice Read the most recent `limit` entries for a topic (newest last).
    function getMessages(bytes32 topicId, uint256 limit)
        external view returns (LogEntry[] memory result)
    {
        LogEntry[] storage all = _logs[topicId];
        uint256 total = all.length;
        uint256 count = limit == 0 || limit > total ? total : limit;
        result = new LogEntry[](count);
        uint256 start = total - count;
        for (uint256 i = 0; i < count; i++) {
            result[i] = all[start + i];
        }
    }

    /// @notice Total number of log entries for a topic.
    function messageCount(bytes32 topicId) external view returns (uint256) {
        return _logs[topicId].length;
    }
}
