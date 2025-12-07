import React from 'react';
import { TradingProvider } from './context/TradingContext';
import { ChatLayout } from './components/ChatLayout';
import './styles.css';

export const App: React.FC = () => (
  <TradingProvider>
    <ChatLayout />
  </TradingProvider>
);
