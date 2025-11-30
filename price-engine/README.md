## Price Engine

Market-data microservice that returns consistent mid prices and liquidity curves (plus data-quality metadata) for the quoting stack.

### Responsibilities
- **Mid price synthesis:** evaluate prioritized feeds (DEX quoters, aggregators, on-chain oracles, TWAP fallback) to produce a mid price per pair/chain.
- **Depth sampling:** probe a configurable size grid (5–10 points) to return expected `amountOut` for sells or required `amountIn` for buys, with implied price/impact.
- **Quality signals:** attach `timestamp`, `stale` flag, `confidenceScore`, `sourceBreakdown`, `latencyMs`.
- **Operational safeguards:** cache/coalesce identical requests within a short window, enforce per-source timeouts, and gracefully fall through the priority stack before erroring.

### Inputs
- `{chainId, tokenIn, tokenOut, side (sell|buy), amountGrid[]}` in base units.
- Optional knobs: `maxLatencyMs`, `preferredSources[]`.

### Outputs
- `midPrice` (rational or decimal string).
- `depthPoints[]` entries `{amount, expectedOutOrIn, impliedPrice, impactBps}`.
- `confidenceScore (0..1)`, `stale`, `sourcesUsed[]`, `asOf`.

### Definition of Done
- Identical inputs within the cache TTL return deterministic responses.
- If every source is stale/unavailable, reject with a clear error instead of fabricating data.

