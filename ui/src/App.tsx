import { useCallback, useEffect, useMemo, useState } from 'react'
import { AuroraPulse } from './components/AuroraPulse'
import './App.css'

const API_BASE_URL = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '') ?? 'http://localhost:3000'

const TOKEN_OPTIONS = [
  {
    key: 'base-weth',
    label: 'Base WETH',
    symbol: 'WETH',
    address: '0x4200000000000000000000000000000000000006',
    decimals: 18,
  },
  {
    key: 'base-usdc',
    label: 'Base USDC',
    symbol: 'USDC',
    address: '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913',
    decimals: 6,
  },
] as const

const ROUTE_PRESETS = [
  { label: 'Base · WETH → USDC', sellTokenKey: 'base-weth', buyTokenKey: 'base-usdc' },
  { label: 'Base · USDC → WETH', sellTokenKey: 'base-usdc', buyTokenKey: 'base-weth' },
] as const

type TokenOption = (typeof TOKEN_OPTIONS)[number]
type TokenKey = TokenOption['key']

type FormState = {
  sellTokenKey: TokenKey
  buyTokenKey: TokenKey
  sellAmount: string
  recipient: string
}

type PriceResponse = {
  chainId: number
  sellToken: string
  buyToken: string
  sellAmount: string
  buyAmount: string
  pricingSnapshot?: {
    asOfMs: number
    confidenceScore: number
    sourcesUsed: string[]
  }
}

type QuoteResponse = {
  quoteId: string
  chainId: number
  taker: string
  recipient: string
  sellToken: string
  buyToken: string
  sellAmount: string
  buyAmount: string
  feeAmount: string
  feeBps: number
  expiry: number
  nonce: string
  pricing?: {
    asOfMs: number
    confidenceScore: number
    sourcesUsed: string[]
  }
  tx: {
    to: string
    data: string
    value: string
  }
}

const formatAddress = (address?: string) => {
  if (!address) return '—'
  return `${address.slice(0, 6)}…${address.slice(-4)}`
}

const getTokenByKey = (key: TokenKey): TokenOption => {
  return TOKEN_OPTIONS.find((token) => token.key === key) ?? TOKEN_OPTIONS[0]
}

const findTokenByAddress = (address?: string) => {
  if (!address) return undefined
  return TOKEN_OPTIONS.find((token) => token.address.toLowerCase() === address.toLowerCase())
}

const decimalsForAddress = (address?: string) => findTokenByAddress(address)?.decimals ?? 18
const symbolForAddress = (address?: string) => findTokenByAddress(address)?.symbol ?? 'token'

const formatAmount = (raw: string, decimals = 18) => {
  if (!raw) return '0'
  try {
    const normalized = BigInt(raw).toString()
    const padded = normalized.padStart(decimals + 1, '0')
    const whole = padded.slice(0, -decimals) || '0'
    const fraction = padded.slice(-decimals).replace(/0+$/, '')
    return fraction ? `${whole}.${fraction}` : whole
  } catch {
    return raw
  }
}

const toHexValue = (value: string) => {
  if (!value) return '0x0'
  if (value.startsWith('0x')) return value
  try {
    const normalized = BigInt(value)
    return `0x${normalized.toString(16)}`
  } catch {
    return '0x0'
  }
}

function App() {
  const [form, setForm] = useState<FormState>({
    sellTokenKey: ROUTE_PRESETS[0].sellTokenKey,
    buyTokenKey: ROUTE_PRESETS[0].buyTokenKey,
    sellAmount: '100000000000000000',
    recipient: '',
  })
  const [account, setAccount] = useState<string>()
  const [walletChain, setWalletChain] = useState<number | null>(null)
  const [priceResult, setPriceResult] = useState<PriceResponse | null>(null)
  const [quoteResult, setQuoteResult] = useState<QuoteResponse | null>(null)
  const [loading, setLoading] = useState<'price' | 'quote' | 'tx' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [info, setInfo] = useState<string | null>(null)

  const hasEthereum = typeof window !== 'undefined' && Boolean(window.ethereum)

  useEffect(() => {
    if (!window.ethereum) return

    const handleAccountsChanged = (addresses: unknown) => {
      if (Array.isArray(addresses) && addresses.length > 0) {
        setAccount(addresses[0])
      } else {
        setAccount(undefined)
      }
    }

    const handleChainChanged = (chainHex: unknown) => {
      if (typeof chainHex === 'string') {
        setWalletChain(parseInt(chainHex, 16))
      }
    }

    window.ethereum.on?.('accountsChanged', handleAccountsChanged)
    window.ethereum.on?.('chainChanged', handleChainChanged)

    return () => {
      window.ethereum?.removeListener?.('accountsChanged', handleAccountsChanged)
      window.ethereum?.removeListener?.('chainChanged', handleChainChanged)
    }
  }, [])

  const updateField = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  const applyPreset = (presetIndex: number) => {
    const preset = ROUTE_PRESETS[presetIndex]
    setForm((prev) => ({
      ...prev,
      sellTokenKey: preset.sellTokenKey,
      buyTokenKey: preset.buyTokenKey,
    }))
  }

  const sellToken = useMemo(() => getTokenByKey(form.sellTokenKey), [form.sellTokenKey])
  const buyToken = useMemo(() => getTokenByKey(form.buyTokenKey), [form.buyTokenKey])

  const requireChain = () => {
    if (!walletChain) {
      setError('Connect MetaMask to sync the chain id first.')
      return false
    }
    return true
  }

  const connectWallet = async () => {
    if (!window.ethereum) {
      setError('MetaMask is not detected. Please install the extension.')
      return
    }
    try {
      setError(null)
      const accounts = (await window.ethereum.request<string[]>({ method: 'eth_requestAccounts' })) ?? []
      if (accounts.length > 0) {
        setAccount(accounts[0])
      }
      const chainHex = await window.ethereum.request<string>({ method: 'eth_chainId' })
      if (chainHex) {
        setWalletChain(parseInt(chainHex, 16))
      }
      setInfo('Wallet connected')
    } catch (err) {
      setError((err as Error).message || 'MetaMask rejected the request')
    }
  }

  const disconnectWallet = () => {
    setAccount(undefined)
    setWalletChain(null)
  }

  const postJson = useCallback(async <T,>(endpoint: string, payload: unknown) => {
    const response = await fetch(`${API_BASE_URL}/${endpoint.replace(/^\//, '')}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!response.ok) {
      const message = await response.text()
      throw new Error(message || `API ${endpoint} responded with ${response.status}`)
    }
    return (await response.json()) as T
  }, [])

  const requestPrice = async () => {
    if (!requireChain()) return
    setLoading('price')
    setError(null)
    setInfo(null)
    setQuoteResult(null)
    try {
      const payload = {
        chainId: walletChain!,
        sellToken: sellToken.address,
        buyToken: buyToken.address,
        sellAmount: form.sellAmount.trim(),
      }
      const data = await postJson<PriceResponse>('price', payload)
      setPriceResult(data)
      setInfo('Indicative price received')
    } catch (err) {
      setError((err as Error).message || 'Unable to fetch price')
    } finally {
      setLoading(null)
    }
  }

  const requestQuote = async () => {
    if (!account) {
      setError('Connect MetaMask before requesting a firm quote')
      return
    }
    if (!requireChain()) return
    setLoading('quote')
    setError(null)
    setInfo(null)
    try {
      const payload = {
        chainId: walletChain!,
        sellToken: sellToken.address,
        buyToken: buyToken.address,
        sellAmount: form.sellAmount.trim(),
        taker: account,
        recipient: form.recipient.trim() || account,
      }
      const data = await postJson<QuoteResponse>('quote', payload)
      setQuoteResult(data)
      setInfo('Firm quote ready — push it to the wallet when you are ready')
    } catch (err) {
      setError((err as Error).message || 'RFQ request failed')
    } finally {
      setLoading(null)
    }
  }

  const pushQuoteToWallet = async () => {
    if (!window.ethereum || !account || !quoteResult) return
    setLoading('tx')
    setError(null)
    setInfo(null)
    try {
      await window.ethereum.request({
        method: 'eth_sendTransaction',
        params: [
          {
            from: account,
            to: quoteResult.tx.to,
            data: quoteResult.tx.data,
            value: toHexValue(quoteResult.tx.value),
          },
        ],
      })
      setInfo('Transaction pushed to MetaMask')
    } catch (err) {
      setError((err as Error).message || 'MetaMask rejected the transaction')
    } finally {
      setLoading(null)
    }
  }

  const walletStatus = account
    ? `Connected: ${formatAddress(account)}${walletChain ? ` · chain ${walletChain}` : ''}`
    : 'Wallet disconnected'

  const confidence = useMemo(() => {
    if (quoteResult?.pricing?.confidenceScore != null) {
      return quoteResult.pricing.confidenceScore
    }
    if (priceResult?.pricingSnapshot?.confidenceScore != null) {
      return priceResult.pricingSnapshot.confidenceScore
    }
    return 0.5
  }, [priceResult, quoteResult])

  const freshness = useMemo(() => {
    if (quoteResult?.pricing?.asOfMs) return quoteResult.pricing.asOfMs
    if (priceResult?.pricingSnapshot?.asOfMs) return priceResult.pricingSnapshot.asOfMs
    return undefined
  }, [priceResult, quoteResult])

  return (
    <div className="app-shell">
      <header className="rfq-hero">
        <div>
          <p className="eyebrow">RFQ desk · MVP</p>
          <h1>Instant RFQ swap over your own API</h1>
          <p className="subtitle">
            Connect MetaMask, pull an indicative price, upgrade to a firm quote, and ship the transaction in one go.
          </p>
          <div className="preset-chips">
            {ROUTE_PRESETS.map((preset, idx) => (
              <button key={preset.label} onClick={() => applyPreset(idx)}>
                {preset.label}
              </button>
            ))}
          </div>
        </div>
        <div className="wallet-card">
          <small>API · {API_BASE_URL}</small>
          <p>{walletStatus}</p>
          <div className="wallet-actions">
            <button onClick={connectWallet} className="primary">
              {account ? 'Switch account' : 'Connect MetaMask'}
            </button>
            {account && (
              <button onClick={disconnectWallet} className="ghost">
                Disconnect
              </button>
            )}
          </div>
        </div>
      </header>

      {!hasEthereum && (
        <div className="banner warning">
          MetaMask is not available in this browser. Install the extension to sign RFQs.
        </div>
      )}

      {error && <div className="banner danger">{error}</div>}

      {info && <div className="banner info">{info}</div>}

      <main className="rfq-grid">
        <section className="panel form-panel">
          <h2>Request parameters</h2>

          <label>
            <span>Sell token</span>
            <select
              value={form.sellTokenKey}
              onChange={(event) => updateField('sellTokenKey', event.target.value as TokenKey)}
            >
              {TOKEN_OPTIONS.map((token) => (
                <option key={token.key} value={token.key}>
                  {token.symbol} · {token.label}
                </option>
              ))}
            </select>
          </label>

          <label>
            <span>Buy token</span>
            <select
              value={form.buyTokenKey}
              onChange={(event) => updateField('buyTokenKey', event.target.value as TokenKey)}
            >
              {TOKEN_OPTIONS.map((token) => (
                <option key={token.key} value={token.key}>
                  {token.symbol} · {token.label}
                </option>
              ))}
            </select>
          </label>

          <label>
            <span>Sell amount (raw units)</span>
            <input
              type="text"
              value={form.sellAmount}
              onChange={(event) => updateField('sellAmount', event.target.value)}
              placeholder="100000..."
            />
            <small>The display assumes each token uses its on-chain decimals.</small>
          </label>

          <label>
            <span>Recipient (optional)</span>
            <input
              type="text"
              value={form.recipient}
              onChange={(event) => updateField('recipient', event.target.value)}
              placeholder={account ?? '0x...'}
            />
          </label>

          <div className="form-actions">
            <button onClick={requestPrice} disabled={loading === 'price' || !walletChain}>
              {loading === 'price' ? 'Requesting…' : 'Get indicative price'}
            </button>
            <button onClick={requestQuote} className="primary" disabled={loading === 'quote' || !walletChain}>
              {loading === 'quote' ? 'Requesting…' : 'Request firm quote'}
            </button>
          </div>
        </section>

        <section className="panel results-panel">
          <div className="results-header">
            <div>
              <h2>Quote monitor</h2>
              <p>Latest responses from /price and /quote</p>
            </div>
            <AuroraPulse
              confidence={confidence}
              asOf={freshness}
              label={quoteResult ? 'firm quote' : 'indicative price'}
            />
          </div>

          <div className="result-card">
            <h3>/price</h3>
            {priceResult ? (
              <>
                <dl>
                  <div>
                    <dt>Sell → Buy</dt>
                    <dd>
                      {formatAmount(priceResult.sellAmount, decimalsForAddress(priceResult.sellToken))}{' '}
                      {symbolForAddress(priceResult.sellToken)} →{' '}
                      {formatAmount(priceResult.buyAmount, decimalsForAddress(priceResult.buyToken))}{' '}
                      {symbolForAddress(priceResult.buyToken)}
                    </dd>
                  </div>
                  <div>
                    <dt>Confidence</dt>
                    <dd>{priceResult.pricingSnapshot?.confidenceScore?.toFixed(2) ?? '—'}</dd>
                  </div>
                  <div>
                    <dt>Sources</dt>
                    <dd>{priceResult.pricingSnapshot?.sourcesUsed?.join(', ') || '—'}</dd>
                  </div>
                </dl>
                <pre>{JSON.stringify(priceResult, null, 2)}</pre>
              </>
            ) : (
              <p className="empty-state">Request an indicative price to see the payload here.</p>
            )}
          </div>

          <div className="result-card">
            <h3>/quote</h3>
            {quoteResult ? (
              <>
                <dl>
                  <div>
                    <dt>Quote ID</dt>
                    <dd>{quoteResult.quoteId}</dd>
                  </div>
                  <div>
                    <dt>Expiry</dt>
                    <dd>{new Date(quoteResult.expiry * 1000).toLocaleTimeString()}</dd>
                  </div>
                  <div>
                    <dt>Fee</dt>
                    <dd>
                      {quoteResult.feeBps} bps · {formatAmount(quoteResult.feeAmount, decimalsForAddress(quoteResult.sellToken))}{' '}
                      {symbolForAddress(quoteResult.sellToken)}
                    </dd>
                  </div>
                </dl>
                <pre>{JSON.stringify(quoteResult, null, 2)}</pre>
                <button onClick={pushQuoteToWallet} disabled={loading === 'tx'}>
                  {loading === 'tx' ? 'Pushing…' : 'Send tx to MetaMask'}
                </button>
              </>
            ) : (
              <p className="empty-state">Firm quotes will show up once /quote responds.</p>
            )}
          </div>
        </section>
      </main>
    </div>
  )
}

export default App
