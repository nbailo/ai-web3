# Aqua Maker API

NestJS + TypeORM service that manages public quote issuance and hackathon-grade admin flows for Aqua.

## Getting started

```bash
cd api
cp env.example .env
npm install
npm run build
npm run start:dev
```

### Required environment

| Variable | Description |
| --- | --- |
| `DATABASE_URL` | Postgres connection string (set `connection_limit=5` for Cloud SQL) |
| `CHAINS_CONFIG_PATH` | Path to the chains config JSON file (defaults to `chains.config.json`) |
| `SIGNING_KEY_<chainId>` | Per-chain maker signing key (referenced via `signingKeyEnv` in chains config) |
| `REQUEST_TIMEOUT_MS` | HTTP timeout for downstream services |
| `GLOBAL_TIMEOUT_MS` | API timeout guard |
| `QUOTE_EXPIRY_SECONDS` | Default expiry horizon for firm quotes |

### Database / migrations

```bash
# Generate
npm run migration:generate -- src/migrations/<Name>

# Run
npm run migration:run
```

See `src/migrations/1711770000000-InitSchema.ts` for the initial schema (tokens, pairs, strategies, quotes, nonce_state, app_config).

## Project layout

```
src/
  config/         -> env validation + chains registry
  db/             -> TypeORM entities + DatabaseModule (legacy filename prisma.*)
  common/         -> DTOs, filters, interceptors, utils
  pricing/        -> HTTP client wrapper for Pricing service
  strategy/       -> HTTP client wrapper for Strategy service
  signer/         -> EIP-712 signing
  tokens/         -> Token cache + decimals fetcher
  pairs/          -> Canonical pair enforcement
  strategies/     -> Strategy catalogue + app config
  quotes/         -> Price + quote orchestration (nonce allocation, signing, persistence)
  admin/          -> Pause / strategy admin endpoints
```

## HTTP surface

Public:

- `GET /v1/health`
- `GET /v1/chains`
- `GET /v1/metadata?chainId=8453`
- `POST /v1/price`
- `POST /v1/quote`
- `GET /v1/quotes/:quoteId`

Admin (no auth for hackathon; served under `/v1/admin/*`):

- `GET/POST /v1/admin/pairs`
- `GET/POST /v1/admin/strategies`
- `POST /v1/admin/strategies/:id/activate`
- `PUT /v1/admin/config`
- `GET /v1/admin/tokens`

OpenAPI docs are available at `/docs` (JSON at `/docs-json`) when `SWAGGER_ENABLED=true`.

## Docker / Cloud Run

`Dockerfile` follows a two-stage Node 20 build. For Cloud Run:

- `max-instances=3`
- `concurrency=30`
- `DATABASE_URL` should include `connection_limit=5`
- Pricing + strategy services can remain internal-only; only expose this API.