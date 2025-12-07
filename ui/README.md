# RFQ Swap UI (MVP)

A minimal RFQ swap workstation that talks to the Nest API in `api/`. The interface connects to MetaMask, requests `POST /price` and `POST /quote`, visualises every field, and can instantly push the returned `tx` back to the wallet for execution.

## Features

- MetaMask connect/disconnect with automatic chain-id detection (no manual chain field).
- Quick presets for the Base WETH ↔ USDC pair plus token dropdowns instead of address inputs.
- `/price` → `/quote` workflow with JSON payload previews and basic validation messaging.
- "Aurora pulse" confidence indicator that animates according to `confidenceScore` and snapshot freshness.

## Quick start

```bash
cd ui
cp env.example .env     # adjust VITE_API_URL if your API runs elsewhere
npm install
npm run dev             # http://localhost:5173
```

Environment variables:

- `VITE_API_URL` (default `http://localhost:3000`) — points the UI to your running API service.

## API flow

1. `POST /price` — requires `chainId`, `sellToken`, `buyToken`, `sellAmount`. Response is shown in the `/price` card along with confidence metadata.
2. `POST /quote` — uses the same payload plus `taker` (from MetaMask) and optional `recipient`. The response (signed RFQ, calldata, fee details) renders in the `/quote` card and powers the "Send tx to MetaMask" button.

This UI stores nothing server-side and is meant to be a fast RFQ test desk while iterating on the maker backend.
