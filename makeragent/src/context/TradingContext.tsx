import React, { createContext, useContext, useState, ReactNode } from 'react';

export interface StrategyData {
  pair: string;
  name: string;
  entry_price: number;
  exit_price: number;
  stop_loss: number;
  take_profit: number;
  position_size: number;
  expected_return: number;
  risk_level: string;
  confidence: number;
}

export interface RiskMetrics {
  risk_reward_ratio: number;
  max_drawdown: number;
  position_risk: number;
  portfolio_risk: number;
  var_95: number;
}

export interface BacktestData {
  win_rate: number;
  sharpe_ratio: number;
  total_return: number;
  max_drawdown: number;
  total_trades: number;
}

interface TradingContextType {
  strategy: StrategyData | null;
  riskMetrics: RiskMetrics | null;
  backtest: BacktestData | null;
  isLoading: boolean;
  activeTab: 'strategy' | 'positions' | 'backtest' | 'risk';
  setStrategy: (s: StrategyData | null) => void;
  setRiskMetrics: (r: RiskMetrics | null) => void;
  setBacktest: (b: BacktestData | null) => void;
  setIsLoading: (l: boolean) => void;
  setActiveTab: (t: 'strategy' | 'positions' | 'backtest' | 'risk') => void;
}

const TradingContext = createContext<TradingContextType | undefined>(undefined);

export const TradingProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [strategy, setStrategy] = useState<StrategyData | null>(null);
  const [riskMetrics, setRiskMetrics] = useState<RiskMetrics | null>(null);
  const [backtest, setBacktest] = useState<BacktestData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'strategy' | 'positions' | 'backtest' | 'risk'>('strategy');

  return (
    <TradingContext.Provider
      value={{
        strategy,
        riskMetrics,
        backtest,
        isLoading,
        activeTab,
        setStrategy,
        setRiskMetrics,
        setBacktest,
        setIsLoading,
        setActiveTab,
      }}
    >
      {children}
    </TradingContext.Provider>
  );
};

export const useTrading = () => {
  const ctx = useContext(TradingContext);
  if (!ctx) throw new Error('useTrading must be used within TradingProvider');
  return ctx;
};
