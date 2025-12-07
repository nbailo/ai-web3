## Strategy Agent

Autonomous quoting brain that takes maker-specified constraints, current pricing, and on-chain feasibility data to produce firm quote parameters—always deterministic per request and never returning something that would revert on-chain.

### Responsibilities
- **Quote Intent synthesis:** for each `QuoteRequest`, choose side-aware `amountIn/amountOut`, spread, `ttlSec`, `minOutNet`, select the right `strategyHash`, and allocate a fresh nonce.
- **Policy enforcement:** honor maker settings such as allowed pairs, max trade size, optional daily caps, and paused states before producing an intent.
- **On-chain feasibility gate:** ensure the referenced Aqua strategy is active (`rawBalances.tokensCount != 0 && != DOCKED`), holds sufficient `tokenOut` budget, and has the required allowances (`maker → Aqua`) before the intent leaves the service.
- **State management:** keep a per-maker monotonic nonce, cache issued quotes by `idempotencyKey`, track fills/reverts, and snapshot budgets for quick checks. Emit canonical reject reasons (`MAKER_PAUSED`, `INSUFFICIENT_BUDGET`, `STALE_PRICING`, `PAIR_NOT_ALLOWED`, etc.) when declining.

### Inputs
- `QuoteRequest` (chainId, side, tokenIn/out, amount, taker, optional recipient/idempotencyKey).
- `MakerConfig` mirror from the DB.
- `PricingSnapshot` from the pricing service for fair spreads.
- `ChainSnapshot` covering Aqua budgets and allowances.

### Outputs
- Deterministic `QuoteIntent` objects `{maker, tokenIn, tokenOut, amountIn, amountOut, strategyHash, nonce, expiry, minOutNet, reason?}`.
- Optional explainability payload for Maker Agent consumers (plain-language description / rationale).

### Definition of Done
- Replaying the same `idempotencyKey` before expiry yields the identical intent.
- Never emits an intent that would fail due to known budget/allowance/strategy issues—reject instead with a stable, documented reason.

