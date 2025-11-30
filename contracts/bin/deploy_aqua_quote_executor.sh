#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

ENV_FILE="$PROJECT_ROOT/.env"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing .env at $ENV_FILE" >&2
  exit 1
fi

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

required_vars=(
  RPC_URL
  PRIVATE_KEY
  AQUA
  FEE_COLLECTOR
  FEE_BPS
  ETHERSCAN_API_KEY
)
for var in "${required_vars[@]}"; do
  if [[ -z "${!var:-}" ]]; then
    echo "Missing $var in .env" >&2
    exit 1
  fi
done

CHAIN_ID="${CHAIN_ID:-}"
if [[ -z "$CHAIN_ID" ]]; then
  CHAIN_ID="$(cast chain-id --rpc-url "$RPC_URL")"
fi

forge script script/AquaQuoteExecutor.s.sol:AquaQuoteExecutorScript \
  --rpc-url "$RPC_URL" \
  --broadcast \
  --verify \
  --chain-id "$CHAIN_ID" \
  --etherscan-api-key "$ETHERSCAN_API_KEY" \
  "$@"

