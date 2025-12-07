import React from 'react';
import { Sidebar } from './Sidebar';
import { ChatWindow } from './ChatWindow';
import { RightPanel } from './RightPanel';

export const ChatLayout: React.FC = () => {
  return (
    <div className="app-root">
      <header className="app-header">
        <div className="app-title">Autonomous Trading Reasoner</div>
        <div className="app-status">
          <span className="status-dot online" /> ASI:One Online
          <span className="status-separator" />
          <span className="status-dot online" /> Market Data Connected
        </div>
        <div className="app-user">Risk: Moderate</div>
      </header>
      <div className="app-body">
        <Sidebar />
        <ChatWindow />
        <RightPanel />
      </div>
    </div>
  );
};
