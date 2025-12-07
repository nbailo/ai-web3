import React from 'react';
import { useTrading } from '../context/TradingContext';

export const RightPanel: React.FC = () => {
  const { strategy, riskMetrics, backtest, isLoading, activeTab, setActiveTab } = useTrading();

  const formatPrice = (val: number) => {
    if (!val) return '—';
    return val >= 1 ? `$${val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : `$${val.toFixed(6)}`;
  };

  const formatPercent = (val: number) => {
    if (val === undefined || val === null) return '—';
    return `${(val * 100).toFixed(1)}%`;
  };

  return (
    <aside className="right-panel">
      <div className="tabs">
        <button className={`tab ${activeTab === 'strategy' ? 'tab-active' : ''}`} onClick={() => setActiveTab('strategy')}>Strategy</button>
        <button className={`tab ${activeTab === 'backtest' ? 'tab-active' : ''}`} onClick={() => setActiveTab('backtest')}>Backtest</button>
        <button className={`tab ${activeTab === 'risk' ? 'tab-active' : ''}`} onClick={() => setActiveTab('risk')}>Risk</button>
      </div>

      {isLoading && (
        <div className="card section">
          <div className="section-title">Processing...</div>
          <p className="muted">Generating strategy with ASI:One reasoning engine...</p>
        </div>
      )}

      {!isLoading && activeTab === 'strategy' && (
        <div className="card section">
          <div className="section-title">Current Strategy</div>
          {strategy ? (
            <>
              <div className="strategy-grid">
                <div>
                  <div className="label">Pair</div>
                  <div className="value">{strategy.pair}</div>
                </div>
                <div>
                  <div className="label">Name</div>
                  <div className="value">{strategy.name}</div>
                </div>
                <div>
                  <div className="label">Entry</div>
                  <div className="value">{formatPrice(strategy.entry_price)}</div>
                </div>
                <div>
                  <div className="label">Exit</div>
                  <div className="value">{formatPrice(strategy.exit_price)}</div>
                </div>
                <div>
                  <div className="label">Stop Loss</div>
                  <div className="value negative">{formatPrice(strategy.stop_loss)}</div>
                </div>
                <div>
                  <div className="label">Take Profit</div>
                  <div className="value positive">{formatPrice(strategy.take_profit)}</div>
                </div>
                <div>
                  <div className="label">Position Size</div>
                  <div className="value">{formatPrice(strategy.position_size)}</div>
                </div>
                <div>
                  <div className="label">Risk Level</div>
                  <div className={`value ${strategy.risk_level === 'low' ? 'positive' : strategy.risk_level === 'high' ? 'negative' : ''}`}>
                    {strategy.risk_level.charAt(0).toUpperCase() + strategy.risk_level.slice(1)}
                  </div>
                </div>
                <div>
                  <div className="label">Expected Return</div>
                  <div className="value positive">{strategy.expected_return.toFixed(1)}%</div>
                </div>
                <div>
                  <div className="label">Confidence</div>
                  <div className="value">{(strategy.confidence * 100).toFixed(0)}%</div>
                </div>
              </div>
              <button className="primary-btn full">Approve &amp; Execute</button>
            </>
          ) : (
            <p className="muted">
              No strategy generated yet. Ask the bot to create a trading strategy, e.g., "Generate a data-driven strategy for ETH".
            </p>
          )}
        </div>
      )}

      {!isLoading && activeTab === 'backtest' && (
        <div className="card section">
          <div className="section-title">Backtest Results</div>
          {backtest ? (
            <div className="strategy-grid">
              <div>
                <div className="label">Win Rate</div>
                <div className={`value ${backtest.win_rate >= 0.5 ? 'positive' : 'negative'}`}>{formatPercent(backtest.win_rate)}</div>
              </div>
              <div>
                <div className="label">Sharpe Ratio</div>
                <div className={`value ${backtest.sharpe_ratio >= 1 ? 'positive' : ''}`}>{backtest.sharpe_ratio.toFixed(2)}</div>
              </div>
              <div>
                <div className="label">Total Return</div>
                <div className={`value ${backtest.total_return >= 0 ? 'positive' : 'negative'}`}>{formatPercent(backtest.total_return)}</div>
              </div>
              <div>
                <div className="label">Max Drawdown</div>
                <div className="value negative">{formatPercent(backtest.max_drawdown)}</div>
              </div>
              <div>
                <div className="label">Total Trades</div>
                <div className="value">{backtest.total_trades}</div>
              </div>
            </div>
          ) : (
            <p className="muted">No backtest data yet. Generate a strategy to see backtest results.</p>
          )}
        </div>
      )}

      {!isLoading && activeTab === 'risk' && (
        <div className="card section">
          <div className="section-title">Risk Metrics</div>
          {riskMetrics ? (
            <div className="strategy-grid">
              <div>
                <div className="label">Risk/Reward</div>
                <div className={`value ${riskMetrics.risk_reward_ratio >= 2 ? 'positive' : ''}`}>{riskMetrics.risk_reward_ratio.toFixed(2)}</div>
              </div>
              <div>
                <div className="label">Max Drawdown</div>
                <div className="value negative">{riskMetrics.max_drawdown.toFixed(1)}%</div>
              </div>
              <div>
                <div className="label">Position Risk</div>
                <div className="value">{riskMetrics.position_risk.toFixed(1)}%</div>
              </div>
              <div>
                <div className="label">Portfolio Risk</div>
                <div className="value">{riskMetrics.portfolio_risk.toFixed(1)}%</div>
              </div>
              <div>
                <div className="label">VaR (95%)</div>
                <div className="value negative">{formatPrice(riskMetrics.var_95)}</div>
              </div>
            </div>
          ) : (
            <p className="muted">No risk metrics yet. Generate a strategy to see risk analysis.</p>
          )}
        </div>
      )}
    </aside>
  );
};
