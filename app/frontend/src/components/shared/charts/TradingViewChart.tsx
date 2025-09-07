import { useState } from 'preact/hooks';
import BinanceCandle from './BinanceCandle';
import Toolbar from './Toolbar';

interface TradingViewChartProps {
  symbol?: string;
  defaultInterval?: string;
  height?: number;
  showToolbar?: boolean;
}

export default function TradingViewChart({ 
  symbol = 'BTCUSDT', 
  defaultInterval = '1m', 
  height = 560, 
  showToolbar = true 
}: TradingViewChartProps) {
  const [interval, setInterval] = useState(defaultInterval);
  
  return (
    <div style="padding:16px; background:#0b1220; border-radius:12px;">
      <div className="flex items-center justify-between mb-4">
        <h3 style="color:#e2e8f0; font:600 18px system-ui; margin:0;">
          {symbol} — Binance (live)
        </h3>
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
          <span className="text-xs text-green-400 font-medium">LIVE</span>
        </div>
      </div>
      
      {showToolbar && <Toolbar onChange={setInterval} />}
      
      <BinanceCandle symbol={symbol} interval={interval} height={height} />
    </div>
  );
}
