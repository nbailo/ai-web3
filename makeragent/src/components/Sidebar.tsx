import React from 'react';

export const Sidebar: React.FC = () => {
  return (
    <aside className="sidebar">
      <div className="card">
        <div className="bot-avatar">AR</div>
        <div className="bot-meta">
          <div className="bot-name">Trading Co-Pilot</div>
          <div className="bot-tagline">Trades with you, not for you.</div>
        </div>
      </div>

      <div className="card section">
        <div className="section-title">Mode</div>
        <div className="pill-group">
          <button className="pill pill-active">Chat</button>
          <button className="pill">Trade</button>
          <button className="pill">Backtest</button>
        </div>
      </div>

      <div className="card section">
        <div className="section-title">Risk Profile</div>
        <div className="pill-group">
          <button className="pill">Conservative</button>
          <button className="pill pill-active">Moderate</button>
          <button className="pill">Aggressive</button>
        </div>
      </div>

      <div className="card section">
        <div className="section-title">Quick Actions</div>
        <div className="quick-actions">
          <button className="quick-btn">Show my positions</button>
          <button className="quick-btn">Today&apos;s PnL</button>
          <button className="quick-btn">Explain last trade</button>
        </div>
      </div>
    </aside>
  );
};
