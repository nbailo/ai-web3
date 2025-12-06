// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

import {EIP712} from "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import {ECDSA} from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

import {IAqua} from "./interfaces/IAqua.sol";

/// @notice RFQ executor integrated with Aqua as an "app".
/// @dev Maker must ship(strategy) with app = address(this).
contract AquaQuoteExecutor is EIP712, ReentrancyGuard, Ownable {
    using SafeERC20 for IERC20;
    using ECDSA for bytes32;

    struct Quote {
        address maker;
        address tokenIn;
        address tokenOut;
        uint256 amountIn;
        uint256 amountOut;     // Gross output (before optional fee-on-output)
        bytes32 strategyHash;  // keccak256(strategyBytes) from Aqua.ship()
        uint256 nonce;
        uint256 expiry;
    }

    struct Policy {
        bool paused;
        uint256 maxAmountInPerTrade; // 0 = no limit
    }

    // EIP-712
    bytes32 private constant QUOTE_TYPEHASH =
        keccak256(
            "Quote(address maker,address tokenIn,address tokenOut,uint256 amountIn,uint256 amountOut,bytes32 strategyHash,uint256 nonce,uint256 expiry)"
        );

    IAqua public immutable AQUA;

    // maker => policy
    mapping(address => Policy) public policy;

    // maker => tokenIn => tokenOut => allowed
    mapping(address => mapping(address => mapping(address => bool))) public pairAllowed;

    // maker => nonce used
    mapping(address => mapping(uint256 => bool)) public usedNonce;

    // maker => invalidate all nonces <= threshold
    mapping(address => uint256) public nonceInvalidBefore;

    // Optional fee (charged in tokenOut by default)
    address public feeCollector;
    uint256 public feeBps; // 0..10000

    // Aqua uses tokensCount == 0xff to mark DOCKED.
    uint8 private constant DOCKED = 0xff;

    event PolicyUpdated(address indexed maker, bool paused, uint256 maxAmountInPerTrade);
    event PairAllowed(address indexed maker, address indexed tokenIn, address indexed tokenOut, bool allowed);
    event NoncesInvalidatedUpTo(address indexed maker, uint256 newNonceInvalidBefore);

    event Filled(
        address indexed maker,
        address indexed taker,
        address indexed tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 amountOutGross,
        uint256 amountOutNet,
        bytes32 strategyHash,
        uint256 nonce
    );

    event FeeUpdated(address indexed feeCollector, uint256 feeBps);

    constructor(IAqua aqua, address _feeCollector, uint256 _feeBps)
        EIP712("AquaQuoteExecutor", "1")
        Ownable(msg.sender)
    {
        require(address(aqua) != address(0), "AQUA=0");
        require(_feeBps <= 10_000, "FEE_BPS");
        AQUA = aqua;
        feeCollector = _feeCollector;
        feeBps = _feeBps;
        emit FeeUpdated(_feeCollector, _feeBps);
    }

    // ----------------------------
    // Maker config (on-chain)
    // ----------------------------

    function setPolicy(bool paused_, uint256 maxAmountInPerTrade_) external {
        policy[msg.sender] = Policy({paused: paused_, maxAmountInPerTrade: maxAmountInPerTrade_});
        emit PolicyUpdated(msg.sender, paused_, maxAmountInPerTrade_);
    }

    function setPairAllowed(address tokenIn, address tokenOut, bool allowed) external {
        require(tokenIn != address(0) && tokenOut != address(0), "TOKEN=0");
        pairAllowed[msg.sender][tokenIn][tokenOut] = allowed;
        emit PairAllowed(msg.sender, tokenIn, tokenOut, allowed);
    }

    function invalidateNoncesUpTo(uint256 newNonceInvalidBefore) external {
        require(newNonceInvalidBefore > nonceInvalidBefore[msg.sender], "NOOP");
        nonceInvalidBefore[msg.sender] = newNonceInvalidBefore;
        emit NoncesInvalidatedUpTo(msg.sender, newNonceInvalidBefore);
    }

    // ----------------------------
    // Admin fee (optional)
    // ----------------------------

    function setFee(address _feeCollector, uint256 _feeBps) external onlyOwner {
        require(_feeBps <= 10_000, "FEE_BPS");
        feeCollector = _feeCollector;
        feeBps = _feeBps;
        emit FeeUpdated(_feeCollector, _feeBps);
    }

    // ----------------------------
    // Helpers
    // ----------------------------

    function computeStrategyHash(bytes calldata strategyBytes) external pure returns (bytes32) {
        return keccak256(strategyBytes);
    }

    // ----------------------------
    // Fill (taker)
    // ----------------------------

    /// @param minAmountOutNet Taker protection on the net output (after fee-on-output).
    function fill(Quote calldata q, bytes calldata sig, uint256 minAmountOutNet) external nonReentrant {
        _validateQuote(q, sig);

        require(pairAllowed[q.maker][q.tokenIn][q.tokenOut], "PAIR_NOT_ALLOWED");

        Policy memory p = policy[q.maker];
        require(!p.paused, "MAKER_PAUSED");
        if (p.maxAmountInPerTrade != 0) require(q.amountIn <= p.maxAmountInPerTrade, "MAX_TRADE");

        // Ensure strategy is active and has enough tokenOut budget for this app (msg.sender == app).
        _requireActiveAndSufficient(q.maker, q.strategyHash, q.tokenIn, 1); // tokenIn just needs to be active
        _requireActiveAndSufficient(q.maker, q.strategyHash, q.tokenOut, q.amountOut);

        usedNonce[q.maker][q.nonce] = true;

        // 1) Collect tokenIn from taker into this contract.
        IERC20(q.tokenIn).safeTransferFrom(msg.sender, address(this), q.amountIn);

        // 2) Push tokenIn to maker via Aqua (Aqua will transferFrom(this -> maker)).
        IERC20(q.tokenIn).forceApprove(address(AQUA), 0);
        IERC20(q.tokenIn).forceApprove(address(AQUA), q.amountIn);
        AQUA.push(q.maker, address(this), q.strategyHash, q.tokenIn, q.amountIn);

        // 3) Pull tokenOut from maker to this contract via Aqua (Aqua will transferFrom(maker -> this)).
        AQUA.pull(q.maker, q.strategyHash, q.tokenOut, q.amountOut, address(this));

        // 4) Apply optional fee on output, then pay taker.
        uint256 fee = 0;
        if (feeBps != 0 && feeCollector != address(0)) {
            fee = (q.amountOut * feeBps) / 10_000;
        }
        uint256 netOut = q.amountOut - fee;
        require(netOut >= minAmountOutNet, "MIN_OUT");

        if (fee != 0) IERC20(q.tokenOut).safeTransfer(feeCollector, fee);
        IERC20(q.tokenOut).safeTransfer(msg.sender, netOut);

        emit Filled(
            q.maker,
            msg.sender,
            q.tokenIn,
            q.tokenOut,
            q.amountIn,
            q.amountOut,
            netOut,
            q.strategyHash,
            q.nonce
        );
    }

    // ----------------------------
    // Internals
    // ----------------------------

    function _requireActiveAndSufficient(
        address maker,
        bytes32 strategyHash,
        address token,
        uint256 required
    ) internal view {
        (uint248 bal, uint8 tokensCount) = AQUA.rawBalances(maker, address(this), strategyHash, token);

        // Active strategy token must have tokensCount != 0 and != DOCKED.
        require(tokensCount != 0 && tokensCount != DOCKED, "STRATEGY_NOT_ACTIVE");

        // For tokenOut we require enough budget. For tokenIn we pass required=1 just to ensure active.
        if (required > 1) require(uint256(bal) >= required, "INSUFFICIENT_BUDGET");
    }

    function _validateQuote(Quote calldata q, bytes calldata sig) internal view {
        require(q.maker != address(0), "MAKER=0");
        require(q.tokenIn != address(0) && q.tokenOut != address(0), "TOKEN=0");
        require(q.amountIn != 0 && q.amountOut != 0, "AMOUNT=0");
        require(block.timestamp <= q.expiry, "EXPIRED");
        require(q.nonce > nonceInvalidBefore[q.maker], "NONCE_INVALIDATED");
        require(!usedNonce[q.maker][q.nonce], "NONCE_USED");

        bytes32 digest = _hashTypedDataV4(
            keccak256(
                abi.encode(
                    QUOTE_TYPEHASH,
                    q.maker,
                    q.tokenIn,
                    q.tokenOut,
                    q.amountIn,
                    q.amountOut,
                    q.strategyHash,
                    q.nonce,
                    q.expiry
                )
            )
        );

        address recovered = digest.recover(sig);
        require(recovered == q.maker, "BAD_SIG");
    }
}