// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

/// @notice Interface matching the provided Aqua contract.
interface IAqua {
    function rawBalances(
        address maker,
        address app,
        bytes32 strategyHash,
        address token
    ) external view returns (uint248 balance, uint8 tokensCount);

    function ship(
        address app,
        bytes calldata strategy,
        address[] calldata tokens,
        uint256[] calldata amounts
    ) external returns (bytes32 strategyHash);

    function dock(
        address app,
        bytes32 strategyHash,
        address[] calldata tokens
    ) external;

    /// @dev msg.sender must be the app that was used in ship().
    function pull(
        address maker,
        bytes32 strategyHash,
        address token,
        uint256 amount,
        address to
    ) external;

    function push(
        address maker,
        address app,
        bytes32 strategyHash,
        address token,
        uint256 amount
    ) external;
}