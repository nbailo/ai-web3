import React, { useState, useRef, useEffect } from 'react';
import { useTrading } from '../context/TradingContext';

interface Message {
  id: number;
  role: 'user' | 'bot';
  content: string;
  meta?: string;
}

export const ChatWindow: React.FC = () => {
  const { setStrategy, setRiskMetrics, setBacktest, setIsLoading } = useTrading();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      role: 'bot',
      content:
        'Hi, I am your autonomous trading co-pilot. Tell me what you want to trade, for example: "Buy 100 USDC/ETH with moderate risk".',
      meta: 'System • Ready',
    },
  ]);
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (overrideText?: string) => {
    const text = (overrideText ?? input).trim();
    if (!text) return;

    const userMsg: Message = {
      id: Date.now(),
      role: 'user',
      content: text,
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');

    try {
      setIsSending(true);
      setIsLoading(true);
      const resp = await fetch('http://localhost:8001/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: 'web_user_1', message: text }),
      });

      const data = await resp.json();
      console.log('[API Response]', JSON.stringify(data, null, 2));

      // Extract strategy data if present
      if (data.strategy) {
        console.log('[Strategy Found]', data.strategy);
        setStrategy({
          pair: data.strategy.pair || 'ETH/USD',
          name: data.strategy.name || 'Strategy',
          entry_price: data.strategy.entry_price || 0,
          exit_price: data.strategy.exit_price || 0,
          stop_loss: data.strategy.stop_loss || 0,
          take_profit: data.strategy.take_profit || 0,
          position_size: data.strategy.position_size || 0,
          expected_return: data.strategy.expected_return || 0,
          risk_level: data.strategy.risk_level || 'medium',
          confidence: data.strategy.confidence || 0,
        });
      }

      // Extract risk metrics if present
      if (data.risk_metrics) {
        setRiskMetrics({
          risk_reward_ratio: data.risk_metrics.risk_reward_ratio || 0,
          max_drawdown: data.risk_metrics.max_drawdown || 0,
          position_risk: data.risk_metrics.position_risk || 0,
          portfolio_risk: data.risk_metrics.portfolio_risk || 0,
          var_95: data.risk_metrics.var_95 || 0,
        });
      }

      // Extract backtest data if present
      if (data.backtest) {
        setBacktest({
          win_rate: data.backtest.win_rate || 0,
          sharpe_ratio: data.backtest.sharpe_ratio || 0,
          total_return: data.backtest.total_return || 0,
          max_drawdown: data.backtest.max_drawdown || 0,
          total_trades: data.backtest.total_trades || 0,
        });
      }

      // The backend returns a structure like { type, message, ... }
      const botText = typeof data.message === 'string' ? data.message : JSON.stringify(data, null, 2);
      const botMsg: Message = {
        id: Date.now() + 1,
        role: 'bot',
        content: botText,
        meta: data.type === 'execution' ? 'Execution • Strategy Generated' : 'Chat • Response',
      };

      setMessages((prev) => [...prev, botMsg]);
    } catch (err: any) {
      const botMsg: Message = {
        id: Date.now() + 1,
        role: 'bot',
        content: `Request failed: ${err.message || 'Unknown error'}. Ensure Flask API is running on http://localhost:8001.`,
        meta: 'Error',
      };
      setMessages((prev) => [...prev, botMsg]);
    } finally {
      setIsSending(false);
      setIsLoading(false);
    }
  };

  const handleQuickAction = (action: string) => {
    const prompts: Record<string, string> = {
      Buy: 'Buy 100 USDC worth of ETH with moderate risk',
      Sell: 'Sell my ETH position',
      Quote: 'Get a quote for BTC/USD',
      Backtest: 'Backtest a momentum strategy on ETH/USD for the last 30 days',
      Strategy: 'Generate a data-driven trading strategy for ETH',
    };
    const prompt = prompts[action] || action;
    setInput(prompt);
  };

  return (
    <section className="chat-window">
      <div className="chat-messages">
        {messages.map((m) => (
          <div key={m.id} className={`chat-row ${m.role === 'user' ? 'row-user' : 'row-bot'}`}>
            <div className={`chat-bubble ${m.role}`}>
              {m.meta && <div className="chat-meta">{m.meta}</div>}
              <div className="chat-text">{m.content}</div>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      <div className="chat-input-bar">
        <div className="chat-quick">
          <button className="pill small" onClick={() => handleQuickAction('Buy')}>Buy</button>
          <button className="pill small" onClick={() => handleQuickAction('Sell')}>Sell</button>
          <button className="pill small" onClick={() => handleQuickAction('Quote')}>Quote</button>
          <button className="pill small" onClick={() => handleQuickAction('Backtest')}>Backtest</button>
          <button className="pill small" onClick={() => handleQuickAction('Strategy')}>Strategy</button>
        </div>
        <div className="chat-input-row">
          <textarea
            className="chat-input"
            placeholder='Ask anything or type a command, e.g. "Buy 100 USDC/ETH"'
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            rows={2}
          />
          <button className="send-btn" onClick={() => handleSend()} disabled={isSending}>
            {isSending ? 'Sending...' : 'Send'}
          </button>
        </div>
      </div>
    </section>
  );
};
