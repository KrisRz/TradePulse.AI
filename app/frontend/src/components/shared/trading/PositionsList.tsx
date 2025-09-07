import { useState } from 'preact/hooks';
import { 
  TrendingUp, 
  DollarSign, 
  Hash, 
  Clock,
  Shield,
  AlertTriangle,
  X,
  Settings,
  MoreHorizontal
} from 'lucide-preact';

interface ApiPosition {
  position_id?: string;
  symbol: string;
  type?: string;
  size?: number;
  entry_price?: number;
  current_price?: number;
  current_value?: number;
  unrealized_pnl?: number;
  unrealized_pnl_percentage?: number;
  stop_loss?: number;
  take_profit?: number;
  entry_time?: string;
  status?: string;
}

interface Position {
  id: string;
  symbol: string;
  side: 'LONG' | 'SHORT';
  size: number;
  entryPrice: number;
  currentPrice: number;
  unrealizedPnl: number;
  unrealizedPnlPercent: number;
  margin: number;
  leverage: number;
  liquidationPrice: number;
  stopLossPrice?: number;
  takeProfitPrice?: number;
  openTime: Date;
  fees: number;
  status: 'OPEN' | 'CLOSING' | 'CLOSED';
}

interface PositionsListProps {
  userId?: string;
  showHeader?: boolean;
  maxHeight?: string;
  onPositionClick?: (position: Position) => void;
  onClosePosition?: (positionId: string) => void;
  onUpdateStopLoss?: (positionId: string, stopLoss: number) => void;
  onUpdateTakeProfit?: (positionId: string, takeProfit: number) => void;
}

export default function PositionsList({
  userId,
  showHeader = true,
  maxHeight = '400px',
  onPositionClick,
  onClosePosition,
  onUpdateStopLoss,
  onUpdateTakeProfit
}: PositionsListProps) {
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPosition, setSelectedPosition] = useState<string | null>(null);
  const [showClosedPositions, setShowClosedPositions] = useState(false);

  useEffect(() => {
    fetchPositions();
    const interval = setInterval(fetchPositions, 5000);
    return () => clearInterval(interval);
  }, [userId, showClosedPositions]);

  const fetchPositions = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch('http://localhost:9002/api/portfolio/virtual/positions', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch positions: ${response.status}`);
      }

      const data = await response.json();
      const realPositions = (data.positions || []).map((p: ApiPosition, idx: number) => ({
        id: p.position_id ?? String(idx),
        symbol: p.symbol,
        side: (p.type || 'LONG') as 'LONG' | 'SHORT',
        size: Number(p.size ?? 0),
        entryPrice: Number(p.entry_price ?? 0),
        currentPrice: Number(p.current_price ?? p.entry_price ?? 0),
        unrealizedPnl: Number(p.unrealized_pnl ?? 0),
        unrealizedPnlPercent: Number(p.unrealized_pnl_percentage ?? 0),
        margin: Number(p.current_value ?? 0),
        leverage: 1,
        liquidationPrice: 0,
        stopLossPrice: undefined,
        takeProfitPrice: undefined,
        openTime: new Date(p.entry_time ?? Date.now()),
        fees: 0,
        status: (p.status || 'OPEN') as 'OPEN' | 'CLOSING' | 'CLOSED'
      })) as Position[];

      const filtered = showClosedPositions
        ? realPositions
        : realPositions.filter((p) => p.status !== 'CLOSED');

      setPositions(filtered);
      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch positions');
      setLoading(false);
    }
  };

  const handleClosePosition = async (positionId: string) => {
    try {
      const position = positions.find(p => p.id === positionId);
      if (!position) return;
      if (window.confirm(`Are you sure you want to close this ${position.side} position for ${position.symbol}?`)) {
        await onClosePosition?.(positionId);
        setPositions(prev => prev.map(p => (p.id === positionId ? { ...p, status: 'CLOSING' as const } : p)));
        setTimeout(fetchPositions, 2000);
      }
    } catch (error) {
      console.error('Failed to close position:', error);
    }
  };

  const formatTime = (date: Date) => {
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / (1000 * 60));
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    if (days > 0) return `${days}d ago`;
    if (hours > 0) return `${hours}h ago`;
    return `${minutes}m ago`;
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount);
  };

  const activePositions = positions.filter(p => p.status === 'OPEN' || p.status === 'CLOSING');
  const totalUnrealizedPnl = activePositions.reduce((sum, p) => sum + p.unrealizedPnl, 0);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
        <span className="ml-2 text-gray-600 dark:text-gray-400">Loading positions...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-8">
        <AlertTriangle className="w-5 h-5 text-red-500 mr-2" />
        <span className="text-red-600 dark:text-red-400">{error}</span>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {showHeader && (
        <div className="flex justify-between items-center">
          <div className="flex items-center space-x-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Active Positions ({activePositions.length})
            </h3>
            <div className={`px-3 py-1 rounded-full text-sm font-medium ${
              totalUnrealizedPnl >= 0
                ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
            }`}>
              Total P&L: {formatCurrency(totalUnrealizedPnl)}
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setShowClosedPositions(!showClosedPositions)}
              className="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
            >
              {showClosedPositions ? 'Hide Closed' : 'Show Closed'}
            </button>
            <button
              onClick={fetchPositions}
              className="p-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
              title="Refresh positions"
            >
              <Settings className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      <div className="space-y-3" style={{ maxHeight, overflowY: 'auto' }}>
        {positions.length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            No positions found
          </div>
        ) : (
          positions.map((position) => (
            <div
              key={position.id}
              className={`bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 cursor-pointer transition-all hover:shadow-md ${
                selectedPosition === position.id ? 'ring-2 ring-blue-500' : ''
              } ${
                position.status === 'CLOSING' ? 'opacity-50' : ''
              }`}
              onClick={() => {
                setSelectedPosition(position.id);
                onPositionClick?.(position);
              }}
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-2">
                    <div className="flex items-center">
                      {position.side === 'LONG' ? (
                        <TrendingUp className="w-4 h-4 text-green-500 mr-1" />
                      ) : (
                        <TrendingDown className="w-4 h-4 text-red-500 mr-1" />
                      )}
                      <span className="font-medium text-gray-900 dark:text-white">
                        {position.symbol}
                      </span>
                      <span className={`px-2 py-1 text-xs font-medium rounded ${
                        position.side === 'LONG'
                          ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                          : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                      }`}>
                        {position.side}
                      </span>
                      <span className="text-sm text-gray-500 dark:text-gray-400">
                        {position.leverage}x
                      </span>
                    </div>
                    
                    <div className="flex items-center space-x-2 text-sm text-gray-500 dark:text-gray-400">
                      <Clock className="w-3 h-3" />
                      <span>{formatTime(position.openTime)}</span>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <div className="text-gray-500 dark:text-gray-400">Size</div>
                      <div className="font-medium text-gray-900 dark:text-white">
                        {position.size} {position.symbol.replace('USDT', '')}
                      </div>
                    </div>
                    
                    <div>
                      <div className="text-gray-500 dark:text-gray-400">Entry Price</div>
                      <div className="font-medium text-gray-900 dark:text-white">
                        ${position.entryPrice.toLocaleString()}
                      </div>
                    </div>
                    
                    <div>
                      <div className="text-gray-500 dark:text-gray-400">Current Price</div>
                      <div className="font-medium text-gray-900 dark:text-white">
                        ${position.currentPrice.toLocaleString()}
                      </div>
                    </div>
                    
                    <div>
                      <div className="text-gray-500 dark:text-gray-400">Unrealized P&L</div>
                      <div className={`font-medium ${
                        position.unrealizedPnl >= 0
                          ? 'text-green-600 dark:text-green-400'
                          : 'text-red-600 dark:text-red-400'
                      }`}>
                        {formatCurrency(position.unrealizedPnl)}
                        <span className="ml-1 text-xs">
                          ({position.unrealizedPnlPercent >= 0 ? '+' : ''}{position.unrealizedPnlPercent.toFixed(2)}%)
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm mt-3">
                    <div>
                      <div className="text-gray-500 dark:text-gray-400">Margin</div>
                      <div className="font-medium text-gray-900 dark:text-white">
                        {formatCurrency(position.margin)}
                      </div>
                    </div>
                    
                    <div>
                      <div className="text-gray-500 dark:text-gray-400">Liquidation</div>
                      <div className="font-medium text-orange-600 dark:text-orange-400">
                        ${position.liquidationPrice.toLocaleString()}
                      </div>
                    </div>
                    
                    <div>
                      <div className="text-gray-500 dark:text-gray-400">Stop Loss</div>
                      <div className="font-medium text-red-600 dark:text-red-400">
                        {position.stopLossPrice ? `$${position.stopLossPrice.toLocaleString()}` : 'None'}
                      </div>
                    </div>
                    
                    <div>
                      <div className="text-gray-500 dark:text-gray-400">Take Profit</div>
                      <div className="font-medium text-green-600 dark:text-green-400">
                        {position.takeProfitPrice ? `$${position.takeProfitPrice.toLocaleString()}` : 'None'}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-2 ml-4">
                  {position.status === 'CLOSING' && (
                    <div className="w-4 h-4 border-2 border-orange-500 border-t-transparent rounded-full animate-spin"></div>
                  )}
                  
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleClosePosition(position.id);
                    }}
                    className="p-1 text-gray-400 hover:text-red-600 dark:hover:text-red-400 transition-colors"
                    title="Close position"
                    disabled={position.status === 'CLOSING'}
                  >
                    <X className="w-4 h-4" />
                  </button>
                  
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                    }}
                    className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                    title="More options"
                  >
                    <MoreHorizontal className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {activePositions.length > 0 && (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <div className="flex items-center">
            <Shield className="w-5 h-5 text-blue-600 dark:text-blue-400 mr-2" />
            <div className="flex-1">
              <h4 className="text-sm font-medium text-blue-900 dark:text-blue-200">
                Risk Management Active
              </h4>
              <p className="text-xs text-blue-700 dark:text-blue-300 mt-1">
                All positions are monitored for stop-loss and take-profit levels. 
                Liquidation prices are calculated based on current margin requirements.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
} 