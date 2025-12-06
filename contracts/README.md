## Contracts

These contracts host `AquaQuoteExecutor`, an RFQ fulfillment helper tightly integrated with Aqua strategies. Makers configure on-chain limits/pairs, takers submit signed quotes, and the executor handles `push/pull` settlement plus optional fee skim for the treasury.

### Deploy
1. Fill `contracts/.env` with `RPC_URL`, `PRIVATE_KEY`, `AQUA`, `FEE_COLLECTOR`, `FEE_BPS`, `ETHERSCAN_API_KEY` (and optional `CHAIN_ID`).
2. From `contracts/`, run `bash bin/deploy_aqua_quote_executor.sh`. It builds, broadcasts through `script/AquaQuoteExecutor.s.sol`, and verifies automatically.
3. Pass extra flags (e.g., `--legacy`) at the end of the command if needed; they are forwarded to `forge script`.

### Addresses
- Base Mainnet (chain 8453): `AquaQuoteExecutor` – `0x9F8F059A900A9Ce823C7C8eD19d66b32cC6505E7`
- BNB Smart Chain (chain 56): `AquaQuoteExecutor` – `0x0B9Ec798B4Ea766d8c5C2b995aD37FedB858200a`
