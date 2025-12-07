import os
import requests
import time
import hashlib
import json
from web3 import Web3
from flask import Flask, jsonify, request
from flasgger import Swagger
from decimal import Decimal, ROUND_DOWN
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from dataclasses import dataclass
from typing import Optional
import dotenv

dotenv.load_dotenv()

app = Flask(__name__)
app.config['SWAGGER'] = {
    'title': 'Price Engine API',
    'uiversion': 3
}

swagger_template = {
    'info': {
        'title': 'Price Engine API',
        'description': 'Consistent mid prices, liquidity curves, and quality signals for quoting.',
        'version': '1.0.0'
    },
    'basePath': '/',
    'schemes': ['http', 'https'],
    'tags': [
        {'name': 'Pricing', 'description': 'Depth sampling and price synthesis'},
        {'name': 'Health', 'description': 'Operational status of upstream RPCs'}
    ],
    'definitions': {
        'PriceRequest': {
            'type': 'object',
            'required': ['chainId', 'tokenIn', 'tokenOut'],
            'properties': {
                'chainId': {'type': 'integer', 'example': 8453},
                'tokenIn': {'type': 'string', 'example': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'},
                'tokenOut': {'type': 'string', 'example': '0x4200000000000000000000000000000000000006'},
                'amountGrid': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': 'Amounts in base units (ints). If omitted, defaults to preset human-size grid.',
                    'example': ['100000000', '500000000']
                },
                'maxLatencyMs': {'type': 'integer', 'example': 10000},
                'preferredSources': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'example': ['uniswap', '1inch']
                }
            }
        },
        'PricingDepthRequest': {
            'type': 'object',
            'required': ['chainId', 'sellToken', 'buyToken', 'sellAmount'],
            'properties': {
                'chainId': {'type': 'integer', 'example': 8453},
                'sellToken': {'type': 'string', 'example': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'},
                'buyToken': {'type': 'string', 'example': '0x4200000000000000000000000000000000000006'},
                'sellAmount': {'type': 'string', 'example': '100000000'},
                'amountGrid': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': 'Optional override grid in base units',
                    'example': ['100000000', '250000000']
                },
                'maxLatencyMs': {'type': 'integer', 'example': 10000},
                'preferredSources': {
                    'type': 'array',
                    'items': {'type': 'string'}
                }
            }
        },
        'DepthPoint': {
            'type': 'object',
            'properties': {
                'amountInRaw': {'type': 'string', 'example': '100000000'},
                'amountOutRaw': {'type': 'string', 'example': '53210000000000000'},
                'price': {'type': 'string', 'example': '0.00053'},
                'impactBps': {'type': 'number', 'example': 12.34},
                'provenance': {
                    'type': 'object',
                    'properties': {
                        'venue': {'type': 'string', 'example': 'uniswap_v3_base'},
                        'feeTier': {'type': 'integer', 'example': 500}
                    }
                }
            }
        },
        'PriceResponse': {
            'type': 'object',
            'properties': {
                'asOfMs': {'type': 'integer'},
                'chainId': {'type': 'integer'},
                'tokenIn': {'type': 'string'},
                'tokenOut': {'type': 'string'},
                'decimalsIn': {'type': 'integer'},
                'decimalsOut': {'type': 'integer'},
                'midPrice': {'type': 'string'},
                'depthPoints': {
                    'type': 'array',
                    'items': {'$ref': '#/definitions/DepthPoint'}
                },
                'sourcesUsed': {
                    'type': 'array',
                    'items': {'type': 'string'}
                },
                'latencyMs': {'type': 'integer'},
                'confidenceScore': {'type': 'number'},
                'stale': {'type': 'boolean'},
                'reasonCodes': {
                    'type': 'array',
                    'items': {'type': 'string'}
                }
            }
        },
        'HealthResponse': {
            'type': 'object',
            'properties': {
                'status': {'type': 'string', 'example': 'ok'},
                'chains': {'type': 'object'},
                'timestamp': {'type': 'integer'}
            }
        }
    }
}
Swagger(app, template=swagger_template)

# =============================================================================
# CHAIN CONFIGURATION
# Using better RPC endpoints with higher rate limits
# =============================================================================

CHAIN_CONFIG = {
    8453: {  # Base
        'name': 'base',
        'rpc': os.environ.get('BASE_RPC_URL', 'https://base.llamarpc.com'),
    },
    1: {  # Ethereum Mainnet
        'name': 'ethereum',
        'rpc': os.environ.get('ETH_RPC_URL', 'https://eth.llamarpc.com'),
    },
    42161: {  # Arbitrum
        'name': 'arbitrum',
        'rpc': os.environ.get('ARB_RPC_URL', 'https://arbitrum.llamarpc.com'),
    },
}

# Uniswap V3 Quoter V2 addresses per chain
QUOTER_V2_ADDRESSES = {
    8453: '0x3d4e44Eb1374240CE5F1B871ab261CD16335B76a',  # Base
    1: '0x61fFE014bA17989E743c5F6cB21bF9697530B21e',  # Ethereum
    42161: '0x61fFE014bA17989E743c5F6cB21bF9697530B21e',  # Arbitrum
}

# =============================================================================
# ABIs
# =============================================================================

QUOTER_ABI = [
    {  # quoteExactInputSingle (for SELL side)
        "inputs": [
            {"components": [
                {"internalType": "address", "name": "tokenIn", "type": "address"},
                {"internalType": "address", "name": "tokenOut", "type": "address"},
                {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                {"internalType": "uint24", "name": "fee", "type": "uint24"},
                {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"}
            ], "internalType": "struct IQuoterV2.QuoteExactInputSingleParams", "name": "params", "type": "tuple"}
        ],
        "name": "quoteExactInputSingle",
        "outputs": [
            {"internalType": "uint256", "name": "amountOut", "type": "uint256"},
            {"internalType": "uint160", "name": "sqrtPriceX96After", "type": "uint160"},
            {"internalType": "uint32", "name": "initializedTicksCrossed", "type": "uint32"},
            {"internalType": "uint256", "name": "gasEstimate", "type": "uint256"}
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {  # quoteExactOutputSingle (for BUY side)
        "inputs": [
            {"components": [
                {"internalType": "address", "name": "tokenIn", "type": "address"},
                {"internalType": "address", "name": "tokenOut", "type": "address"},
                {"internalType": "uint256", "name": "amount", "type": "uint256"},
                {"internalType": "uint24", "name": "fee", "type": "uint24"},
                {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"}
            ], "internalType": "struct IQuoterV2.QuoteExactOutputSingleParams", "name": "params", "type": "tuple"}
        ],
        "name": "quoteExactOutputSingle",
        "outputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "uint160", "name": "sqrtPriceX96After", "type": "uint160"},
            {"internalType": "uint32", "name": "initializedTicksCrossed", "type": "uint32"},
            {"internalType": "uint256", "name": "gasEstimate", "type": "uint256"}
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

ERC20_ABI = [{
    "constant": True,
    "inputs": [],
    "name": "decimals",
    "outputs": [{"name": "", "type": "uint8"}],
    "type": "function"
}]

# =============================================================================
# CONSTANTS
# =============================================================================

FEE_TIERS = [100, 500, 3000, 10000]
DEFAULT_AMOUNT_GRID = [100, 500, 1000, 5000, 10000]  # Human units fallback
DEFAULT_MAX_LATENCY_MS = 10000  # Increased for slower connections
CACHE_TTL_MS = 500  # Coalesce identical requests within this window
DEVIATION_THRESHOLD_BPS = Decimal('50')
LARGE_DEVIATION_THRESHOLD_BPS = Decimal('200')
RPC_TIMEOUT_SECONDS = 8  # Increased timeout
ONEINCH_TIMEOUT_SECONDS = 2
MAX_PARALLEL_WORKERS = 8  # Reduced further to avoid rate limiting

# =============================================================================
# CACHES
# =============================================================================

_decimals_cache: dict[str, int] = {}
_web3_cache: dict[int, Web3] = {}

# Request cache: {cache_key: (timestamp_ms, response_dict)}
_request_cache: dict[str, tuple[int, dict]] = {}
_request_cache_lock = Lock()


# =============================================================================
# HELPERS
# =============================================================================

def get_web3(chain_id: int) -> Web3:
    """Get or create Web3 instance for chain."""
    if chain_id not in _web3_cache:
        if chain_id not in CHAIN_CONFIG:
            raise ValueError(f"Unsupported chainId: {chain_id}")
        _web3_cache[chain_id] = Web3(Web3.HTTPProvider(
            CHAIN_CONFIG[chain_id]['rpc'],
            request_kwargs={'timeout': RPC_TIMEOUT_SECONDS}
        ))
    return _web3_cache[chain_id]


def get_quoter_address(chain_id: int) -> str:
    """Get Uniswap V3 QuoterV2 address for chain."""
    if chain_id not in QUOTER_V2_ADDRESSES:
        raise ValueError(f"No QuoterV2 address for chainId: {chain_id}")
    return QUOTER_V2_ADDRESSES[chain_id]


def get_token_decimals(chain_id: int, token_address: str) -> int:
    """Fetch token decimals from on-chain with caching."""
    checksummed = Web3.to_checksum_address(token_address)
    cache_key = f"{chain_id}:{checksummed}"

    if cache_key in _decimals_cache:
        return _decimals_cache[cache_key]

    try:
        w3 = get_web3(chain_id)
        token = w3.eth.contract(address=checksummed, abi=ERC20_ABI)
        decimals = token.functions.decimals().call()
        _decimals_cache[cache_key] = decimals
        return decimals
    except Exception as e:
        raise ValueError(f"Could not fetch decimals for {checksummed} on chain {chain_id}: {e}")


def generate_cache_key(
        chain_id: int,
        token_in: str,
        token_out: str,
        amount_grid: list[int]
) -> str:
    """Generate deterministic cache key for request deduplication."""
    key_data = {
        'chainId': chain_id,
        'tokenIn': token_in.lower(),
        'tokenOut': token_out.lower(),
        'amountGrid': sorted(amount_grid)
    }
    key_str = json.dumps(key_data, sort_keys=True)
    return hashlib.sha256(key_str.encode()).hexdigest()[:16]


def get_cached_response(cache_key: str) -> Optional[dict]:
    """Return cached response if within TTL, else None."""
    with _request_cache_lock:
        if cache_key in _request_cache:
            cached_time, cached_response = _request_cache[cache_key]
            now_ms = int(time.time() * 1000)
            if now_ms - cached_time < CACHE_TTL_MS:
                return cached_response
            else:
                del _request_cache[cache_key]
    return None


def set_cached_response(cache_key: str, response: dict) -> None:
    """Cache response with current timestamp."""
    with _request_cache_lock:
        _request_cache[cache_key] = (int(time.time() * 1000), response)


def decimal_to_str(d: Decimal | None, precision: int = 18) -> str | None:
    """Convert Decimal to string with fixed precision."""
    if d is None:
        return None
    quantized = d.quantize(Decimal(10) ** -precision, rounding=ROUND_DOWN)
    return format(quantized, 'f')


def decimal_to_float(d: Decimal | None, precision: int = 4) -> float | None:
    """Convert Decimal to float with bounded precision for API responses."""
    if d is None:
        return None
    quantized = d.quantize(Decimal(10) ** -precision, rounding=ROUND_DOWN)
    return float(quantized)


def parse_base_unit_amount(value: int | str, field_name: str) -> int:
    """Normalize user-provided amount to int (base units)."""
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.lower().startswith('0x'):
            raise ValueError(f"{field_name} must be a base-10 integer string, got hex value")
        try:
            return int(stripped, 10)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be an integer string, got '{value}'") from exc
    raise ValueError(f"{field_name} must be provided as int or base-10 string")


def parse_amount_grid(raw: list[int | str] | str, field_name: str = 'amountGrid') -> list[int]:
    """Parse comma-separated string or list of base-unit amounts into ints."""
    if isinstance(raw, str):
        tokens = [token.strip() for token in raw.split(',') if token.strip()]
    elif isinstance(raw, list):
        tokens = raw
    else:
        raise ValueError(f"{field_name} must be a list or comma-separated string of integers")

    parsed: list[int] = []
    for idx, token in enumerate(tokens):
        parsed.append(parse_base_unit_amount(token, f'{field_name}[{idx}]'))

    if not parsed:
        raise ValueError(f"{field_name} must include at least one amount")
    return parsed


def normalize_preferred_sources(raw: list[str] | str | None) -> list[str] | None:
    """Normalize preferredSources payload into a cleaned list."""
    if raw is None:
        return None
    if isinstance(raw, list):
        cleaned = [str(item).strip() for item in raw if str(item).strip()]
    elif isinstance(raw, str):
        cleaned = [token.strip() for token in raw.split(',') if token.strip()]
    else:
        raise ValueError('preferredSources must be a comma-separated string or list of strings')
    return cleaned or None


def calculate_price(
        amount_in_raw: int,
        amount_out_raw: int,
        decimals_in: int,
        decimals_out: int
) -> Decimal:
    """Calculate price in human units (amount_out per amount_in)."""
    amount_in_human = Decimal(amount_in_raw) / Decimal(10 ** decimals_in)
    amount_out_human = Decimal(amount_out_raw) / Decimal(10 ** decimals_out)
    if amount_in_human == 0:
        return Decimal('0')
    return amount_out_human / amount_in_human


def calculate_impact_bps(price: Decimal, mid_price: Decimal) -> Decimal:
    """Calculate price impact in basis points vs mid price."""
    if mid_price == 0:
        return Decimal('0')
    return ((price - mid_price) / mid_price) * Decimal('10000')


# =============================================================================
# UNISWAP QUOTER
# =============================================================================

def get_sell_quote_for_fee_tier(
        chain_id: int,
        token_in: str,
        token_out: str,
        amount_in_raw: int,
        fee_tier: int,
        retries: int = 2
) -> int | None:
    """Get SELL quote (exact input) for a specific fee tier with retries."""
    for attempt in range(retries + 1):
        try:
            w3 = get_web3(chain_id)
            quoter_address = get_quoter_address(chain_id)
            quoter = w3.eth.contract(
                address=Web3.to_checksum_address(quoter_address),
                abi=QUOTER_ABI
            )

            result = quoter.functions.quoteExactInputSingle({
                'tokenIn': Web3.to_checksum_address(token_in),
                'tokenOut': Web3.to_checksum_address(token_out),
                'amountIn': amount_in_raw,
                'fee': fee_tier,
                'sqrtPriceLimitX96': 0
            }).call()

            return result[0]  # amountOut
        except Exception as e:
            if attempt < retries:
                time.sleep(0.3 * (attempt + 1))  # Backoff between retries
                continue
            # Silently fail - this fee tier may not have a pool
            return None
    return None


def get_all_quotes_parallel(
        chain_id: int,
        token_in: str,
        token_out: str,
        amounts_raw: list[int],
        max_latency_ms: int
) -> dict[int, tuple[int | None, int | None]]:
    """
    Get best quotes for ALL amounts in parallel.
    Returns {amount_raw: (best_result, fee_used)}
    """
    results: dict[int, tuple[int | None, int | None]] = {}

    quote_fn = get_sell_quote_for_fee_tier

    tasks = [(amount, fee) for amount in amounts_raw for fee in FEE_TIERS]

    timeout_seconds = max_latency_ms / 1000.0

    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_WORKERS) as executor:
        future_to_task = {
            executor.submit(quote_fn, chain_id, token_in, token_out, amount, fee): (amount, fee)
            for amount, fee in tasks
        }

        amount_results: dict[int, list[tuple[int, int | None]]] = {amt: [] for amt in amounts_raw}

        try:
            for future in as_completed(future_to_task, timeout=timeout_seconds):
                amount, fee = future_to_task[future]
                try:
                    output = future.result(timeout=1)
                    amount_results[amount].append((fee, output))
                except Exception:
                    pass
        except TimeoutError:
            # Some futures didn't complete in time, continue with what we have
            pass

        # Find best fee tier for each amount
        for amount in amounts_raw:
            best_result, best_fee = None, None
            for fee, result in amount_results[amount]:
                if result is not None:
                    if best_result is None or result > best_result:
                        best_result = result
                        best_fee = fee
            results[amount] = (best_result, best_fee)

    return results


# =============================================================================
# 1INCH REFERENCE PRICE
# =============================================================================

def get_1inch_spot_price(chain_id: int, token_in: str, token_out: str) -> Decimal | None:
    """Fetch spot price from 1inch API as reference source."""
    api_key = os.environ.get('ONEINCH_API_KEY')
    if not api_key:
        return None

    url = f"https://api.1inch.dev/price/v1.1/{chain_id}"

    params = {
        "tokens": Web3.to_checksum_address(token_in),
        "currency": Web3.to_checksum_address(token_out)
    }

    auth_formats = [
        {"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
        {"Authorization": api_key, "Accept": "application/json"},
    ]

    for headers in auth_formats:
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=ONEINCH_TIMEOUT_SECONDS)

            if resp.status_code == 200:
                data = resp.json()
                token_in_checksum = Web3.to_checksum_address(token_in)
                if token_in_checksum in data:
                    return Decimal(str(data[token_in_checksum]))
            elif resp.status_code == 403:
                continue
            else:
                return None

        except Exception:
            return None

    return None


# =============================================================================
# MAIN PRICING LOGIC
# =============================================================================

@dataclass
class PriceRequest:
    chain_id: int
    token_in: str
    token_out: str
    amount_grid: list[int]  # In BASE UNITS (raw)
    max_latency_ms: int = DEFAULT_MAX_LATENCY_MS
    preferred_sources: list[str] | None = None


def build_depth_curve(req: PriceRequest) -> dict:
    """
    Build a depth curve by sampling the provided amount grid.
    Returns pricing snapshot per README spec.
    """
    start_time = time.time()

    # Validate chain
    if req.chain_id not in CHAIN_CONFIG:
        raise ValueError(f"Unsupported chainId: {req.chain_id}. Supported: {list(CHAIN_CONFIG.keys())}")

    # Check cache first
    cache_key = generate_cache_key(
        req.chain_id, req.token_in, req.token_out, req.amount_grid
    )
    cached = get_cached_response(cache_key)
    if cached is not None:
        return cached

    # Checksum addresses
    token_in = Web3.to_checksum_address(req.token_in)
    token_out = Web3.to_checksum_address(req.token_out)

    # Fetch decimals
    decimals_in = get_token_decimals(req.chain_id, token_in)
    decimals_out = get_token_decimals(req.chain_id, token_out)

    # Get all quotes in parallel
    quotes = get_all_quotes_parallel(
        req.chain_id, token_in, token_out,
        req.amount_grid, req.max_latency_ms
    )

    depth_points: list[dict] = []
    mid_price: Decimal | None = None
    fees_used: set[int] = set()
    sources_used: list[str] = [f'uniswap_v3_{CHAIN_CONFIG[req.chain_id]["name"]}']
    reason_codes: list[str] = []
    successful_quotes = 0

    for amount_raw in req.amount_grid:
        result_raw, fee_used = quotes[amount_raw]

        if result_raw is not None and fee_used is not None:
            successful_quotes += 1
            fees_used.add(fee_used)

            amount_in_raw = amount_raw
            amount_out_raw = result_raw

            price = calculate_price(amount_in_raw, amount_out_raw, decimals_in, decimals_out)

            if mid_price is None:
                mid_price = price

            impact_bps = calculate_impact_bps(price, mid_price)

            impact_bps_value = decimal_to_float(impact_bps, precision=4)
            venue_prefix = f"uniswap_v3_{CHAIN_CONFIG[req.chain_id]['name']}"
            provenance_venue = venue_prefix

            depth_point = {
                'amountInRaw': str(amount_in_raw),
                'amountOutRaw': str(amount_out_raw),
                'price': decimal_to_str(price),
                'impactBps': impact_bps_value if impact_bps_value is not None else 0.0,
                'provenance': {'venue': provenance_venue}
            }

            if fee_used is not None:
                depth_point['provenance']['feeTier'] = fee_used

            depth_points.append(depth_point)

    # Calculate latency
    latency_ms = int((time.time() - start_time) * 1000)

    # ==========================================================================
    # HARD REJECT: If no quotes succeeded, error instead of fabricating data
    # (per README "Definition of Done")
    # ==========================================================================
    if successful_quotes == 0:
        raise ValueError(
            f"All sources unavailable for {token_in}/{token_out} on chain {req.chain_id}. "
            f"No liquidity found in any fee tier."
        )

    # Confidence scoring
    confidence = Decimal('0.95')

    if len(fees_used) > 1:
        confidence -= Decimal('0.05')
        reason_codes.append('fragmented_liquidity_multiple_fee_tiers')

    if latency_ms > 1000:
        confidence -= Decimal('0.10')
        reason_codes.append('high_latency')

    # 1inch sanity check
    use_1inch = req.preferred_sources is None or '1inch' in req.preferred_sources
    oneinch_price = None

    if use_1inch:
        oneinch_price = get_1inch_spot_price(req.chain_id, token_in, token_out)

    if oneinch_price is not None:
        sources_used.append('1inch_spot')

        if mid_price is not None and oneinch_price > 0:
            deviation_bps = abs(calculate_impact_bps(mid_price, oneinch_price))

            if deviation_bps > LARGE_DEVIATION_THRESHOLD_BPS:
                confidence -= Decimal('0.25')
                reason_codes.append(f'large_price_deviation_vs_1inch_{decimal_to_str(deviation_bps, 2)}bps')
            elif deviation_bps > DEVIATION_THRESHOLD_BPS:
                confidence -= Decimal('0.15')
                reason_codes.append(f'price_deviation_vs_1inch_{decimal_to_str(deviation_bps, 2)}bps')
    else:
        confidence -= Decimal('0.05')
        reason_codes.append('no_reference_source')

    # Clamp confidence
    confidence = max(Decimal('0'), min(Decimal('1'), confidence))

    # Determine staleness
    stale = latency_ms > req.max_latency_ms or confidence < Decimal('0.5')

    response = {
        'asOfMs': int(time.time() * 1000),
        'chainId': req.chain_id,
        'tokenIn': token_in,
        'tokenOut': token_out,
        'decimalsIn': decimals_in,
        'decimalsOut': decimals_out,
        'midPrice': decimal_to_str(mid_price) if mid_price else None,
        'depthPoints': depth_points,
        'sourcesUsed': sources_used,
        'latencyMs': latency_ms,
        'confidenceScore': decimal_to_float(confidence, precision=4) or 0.0,
        'stale': stale,
        'reasonCodes': reason_codes
    }

    # Cache successful response
    set_cached_response(cache_key, response)

    return response


# =============================================================================
# FLASK ENDPOINTS
# =============================================================================

@app.route('/price', methods=['GET', 'POST'])
def get_price_data():
    """
    API endpoint for price/depth data.

    ---
    tags:
      - Pricing
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - name: chainId
        in: query
        type: integer
        required: true
        description: Chain ID (use JSON body for POST)
      - name: tokenIn
        in: query
        type: string
        required: true
        description: ERC-20 address provided in base units (checksum or lower-case)
      - name: tokenOut
        in: query
        type: string
        required: true
        description: ERC-20 address to quote against
      - name: amountGrid
        in: query
        type: string
        required: false
        description: Comma separated list of base-unit amounts
      - name: preferredSources
        in: query
        type: string
        required: false
        description: Comma separated list of additional data sources
      - name: body
        in: body
        required: false
        description: JSON body for POST requests
        schema:
          $ref: '#/definitions/PriceRequest'
    responses:
      200:
        description: Pricing snapshot with depth points
        schema:
          $ref: '#/definitions/PriceResponse'
      400:
        description: Invalid client input
      500:
        description: Internal error while building the curve
    """
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
    else:
        data = request.args.to_dict()

    required = ['chainId', 'tokenIn', 'tokenOut']
    missing = [f for f in required if f not in data or not data[f]]
    if missing:
        return jsonify({'error': f'Missing required fields: {missing}'}), 400

    try:
        chain_id = int(data['chainId'])
    except (ValueError, TypeError):
        return jsonify({'error': 'chainId must be an integer'}), 400

    try:
        preferred_sources = normalize_preferred_sources(data.get('preferredSources'))
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    amount_grid_raw = data.get('amountGrid')
    amount_grid: list[int]

    try:
        if amount_grid_raw:
            amount_grid = parse_amount_grid(amount_grid_raw)
        elif data.get('sellAmount'):
            amount_grid = [parse_base_unit_amount(data['sellAmount'], 'sellAmount')]
        else:
            decimals_in = get_token_decimals(chain_id, data['tokenIn'])
            amount_grid = [int(amt * (10 ** decimals_in)) for amt in DEFAULT_AMOUNT_GRID]
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    try:
        max_latency = int(data.get('maxLatencyMs', DEFAULT_MAX_LATENCY_MS))
    except (ValueError, TypeError):
        return jsonify({'error': 'maxLatencyMs must be an integer'}), 400

    try:
        req = PriceRequest(
            chain_id=chain_id,
            token_in=data['tokenIn'],
            token_out=data['tokenOut'],
            amount_grid=amount_grid,
            max_latency_ms=max_latency,
            preferred_sources=preferred_sources
        )
    except Exception as e:
        return jsonify({'error': f'Invalid request: {str(e)}'}), 400

    try:
        result = build_depth_curve(req)
        return jsonify(result)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Internal error: {str(e)}'}), 500


@app.route('/depth', methods=['POST'])
def get_depth_snapshot():
    """
    Depth snapshot endpoint consumed by the NestJS quoting API.

    ---
    tags:
      - Pricing
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - name: body
        in: body
        required: true
        schema:
          $ref: '#/definitions/PricingDepthRequest'
    responses:
      200:
        description: Pricing snapshot for requested notional
        schema:
          $ref: '#/definitions/PriceResponse'
      400:
        description: Invalid client input
      500:
        description: Internal error while building the curve
    """
    data = request.get_json(silent=True) or {}
    required = ['chainId', 'sellToken', 'buyToken', 'sellAmount']
    missing = [f for f in required if f not in data or not data[f]]
    if missing:
        return jsonify({'error': f'Missing required fields: {missing}'}), 400

    try:
        chain_id = int(data['chainId'])
    except (ValueError, TypeError):
        return jsonify({'error': 'chainId must be an integer'}), 400

    try:
        preferred_sources = normalize_preferred_sources(data.get('preferredSources'))
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    amount_grid_raw = data.get('amountGrid')
    try:
        if amount_grid_raw:
            amount_grid = parse_amount_grid(amount_grid_raw)
        else:
            amount_grid = [parse_base_unit_amount(data['sellAmount'], 'sellAmount')]
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    try:
        max_latency = int(data.get('maxLatencyMs', DEFAULT_MAX_LATENCY_MS))
    except (ValueError, TypeError):
        return jsonify({'error': 'maxLatencyMs must be an integer'}), 400

    req = PriceRequest(
        chain_id=chain_id,
        token_in=data['sellToken'],
        token_out=data['buyToken'],
        amount_grid=amount_grid,
        max_latency_ms=max_latency,
        preferred_sources=preferred_sources
    )

    try:
        result = build_depth_curve(req)
        return jsonify(result)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Internal error: {str(e)}'}), 500


@app.route('/health', methods=['GET'])
def health():
    """
    Health check endpoint.

    ---
    tags:
      - Health
    produces:
      - application/json
    responses:
      200:
        description: Chain connectivity snapshot
        schema:
          $ref: '#/definitions/HealthResponse'
    """
    chain_status = {}
    for chain_id, config in CHAIN_CONFIG.items():
        try:
            w3 = get_web3(chain_id)
            chain_status[config['name']] = w3.is_connected()
        except Exception:
            chain_status[config['name']] = False

    all_ok = all(chain_status.values())

    return jsonify({
        'status': 'ok' if all_ok else 'degraded',
        'chains': chain_status,
        'timestamp': int(time.time() * 1000)
    })


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8081))
    debug_mode = os.environ.get('FLASK_DEBUG', '').lower() in ('1', 'true', 'yes')

    print("=" * 60)
    print(f"Starting Price Engine (Swagger at /apidocs) on port {port}...")
    print("=" * 60)

    # Production deployments should run via gunicorn/uwsgi, this path is for local runs.
    app.run(host='0.0.0.0', debug=debug_mode, port=port)
