## Maker Agent (Chat Control Plane)

Conversational assistant that helps makers configure Aqua quoting safely. The agent translates natural-language intents into explicit `MakerConfig` updates and unsigned transaction payloads, enforcing a confirm-before-action workflow.

### Responsibilities
- **Chat → config:** capture allowed pairs, max trade size, daily caps, TTL ranges, spread presets, pause toggles, and strategy selection into structured `MakerConfig`.
- **Onboarding helper:** draft `strategyBytes`, compute `strategyHash`, and assemble payloads for `approve(AQUA, tokenOut)`, `AQUA.ship`, `AQUA.dock`, plus executor calls (`setPairAllowed`, `setPolicy`, `invalidateNoncesUpTo`).
- **Status & explainability:** surface active strategies, remaining budgets via `Aqua.rawBalances`, current executor policy, and any pending actions in plain language.
- **Safety:** require an explicit “confirm” message before emitting any state-changing transaction data; log who confirmed and when.

### Inputs
- Maker chat messages (primary interface).
- Maker state/config stored in the DB.
- On-chain reads: Aqua budgets, token allowances, executor policy state.
- Optional Strategy Agent summaries to enrich recommendations.

### Outputs
- Updated `MakerConfig` records written back to the DB.
- Prepared transaction payloads (ABI-encoded data + human-readable summary) awaiting maker signature.
- Append-only audit log capturing intent, payload, and confirmation metadata.

### Definition of Done
- No silent on-chain execution; everything is opt-in via signed transactions.
- Every chat intent maps to an explicit config field or payload step with zero ambiguity.
- Makers always see what a payload will do before confirming.

