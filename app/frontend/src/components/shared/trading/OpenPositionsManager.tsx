import { useState, useEffect } from 'preact/hooks';
import { 
  Eye, TrendingUp, TrendingDown, X, Edit, Plus, Minus, 
  Target, Wallet, RefreshCw, CheckSquare, Filter, Download, Clock
} from 'lucide-preact';

interface RealPosition {
  id: string;
  symbol: string;
  side: 'long' | 'short';
  size: number;
  entryPrice: number;
  currentPrice: number;
  unrealizedPnL: number;
  unrealizedPnLPercent: number;
  stopLoss?: number;
  takeProfit?: number;
  marginUsed: number;
  openTime: string;
  duration: string;
  aiConfidence: number;
  strategy: string;
  riskLevel: 'low' | 'medium' | 'high';
  exchange: string;
  leverage: number;
}

interface PositionSummary {
  totalPositions: number;
  totalUnrealizedPnL: number;
  totalMarginUsed: number;
  avgAiConfidence: number;
  longPositions: number;
  shortPositions: number;
  profitablePositions: number;
}

export default function OpenPositionsManager() {
  const [positions, setPositions] = useState<RealPosition[]>([]);
  const [selectedPositions, setSelectedPositions] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState<keyof RealPosition>('openTime');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [filterBy, setFilterBy] = useState<string>('all');
  const [showBatchActions, setShowBatchActions] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(new Date());

  // Mock data for development - replace with real API calls
  // const mockPositions: RealPosition[] = [
  //   {
  //     id: 'pos_001',
  //     symbol: 'BTCUSDT',
  //     side: 'long',
  //     size: 0.1,
  //     entryPrice: 95000,
  //     currentPrice: 96500,
  //     unrealizedPnL: 150,
  //     unrealizedPnLPercent: 1.58,
  //     stopLoss: 92000,
  //     takeProfit: 98000,
  //     marginUsed: 4750,
  //     openTime: '2024-01-15T10:30:00Z',
  //     duration: '2h 15m',
  //     aiConfidence: 85,
  //     strategy: 'AI_REVERSAL_V2',
  //     riskLevel: 'medium',
  //     exchange: 'binance',
  //     leverage: 20
  //   },
  //   {
  //     id: 'pos_002',
  //     symbol: 'BTCUSDT',
  //     side: 'short',
  //     size: 0.05,
  //     entryPrice: 96000,
  //     currentPrice: 96500,
  //     unrealizedPnL: -25,
  //     unrealizedPnLPercent: -0.52,
  //     stopLoss: 97500,
  //     takeProfit: 94000,
  //     marginUsed: 2400,
  //     openTime: '2024-01-15T09:45:00Z',
  //     duration: '3h 0m',
  //     aiConfidence: 72,
  //     strategy: 'AI_MOMENTUM_V1',
  //     riskLevel: 'high',
  //     exchange: 'binance',
  //     leverage: 20
  //   }
  // ];

  // Calculate summary statistics
  const calculateSummary = (positions: RealPosition[]): PositionSummary => {
    return {
      totalPositions: positions.length,
      totalUnrealizedPnL: positions.reduce((sum, pos) => sum + pos.unrealizedPnL, 0),
      totalMarginUsed: positions.reduce((sum, pos) => sum + pos.marginUsed, 0),
      avgAiConfidence: positions.length > 0 
        ? Math.round(positions.reduce((sum, pos) => sum + pos.aiConfidence, 0) / positions.length)
        : 0,
      longPositions: positions.filter(pos => pos.side === 'long').length,
      shortPositions: positions.filter(pos => pos.side === 'short').length,
      profitablePositions: positions.filter(pos => pos.unrealizedPnL > 0).length
    };
  };

  const [summary, setSummary] = useState<PositionSummary>(calculateSummary([]));

  // Load positions data
  useEffect(() => {
    loadPositions();
    
    // Set up real-time updates
    const interval = setInterval(() => {
      loadPositions(); // Refresh positions every 2 seconds for real-time updates
      setLastUpdate(new Date());
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  const loadPositions = async () => {
    try {
      setLoading(true);
      
      // Load real open positions from backend
      const response = await fetch('http://localhost:9001/api/real-trading/positions/open', {
        headers: {
          'Authorization': 'Bearer enterprise_admin_token',
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) {
        throw new Error(`Failed to load positions: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.status === 'success' && data.data) {
        // Set real positions data
        const realPositions = data.data.positions || [];
        setPositions(realPositions);
        
        // Update summary with real data
        setSummary(data.data.summary || calculateSummary([]));
        
        console.log(`🔴 Loaded ${realPositions.length} real open positions`);
        console.log('📊 Current BTC price:', data.data.current_btc_price);
      }
      
    } catch (error) {
      console.error('❌ Failed to load real positions:', error);
      // Fallback to empty data
      setPositions([]);
      setSummary(calculateSummary([]));
    } finally {
      setLoading(false);
    }
  };

  // Update summary when positions change
  useEffect(() => {
    setSummary(calculateSummary(positions));
  }, [positions]);

  const handleSelectPosition = (positionId: string, checked: boolean) => {
    if (checked) {
      setSelectedPositions(prev => [...prev, positionId]);
    } else {
      setSelectedPositions(prev => prev.filter(id => id !== positionId));
    }
  };

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedPositions(positions.map(pos => pos.id));
    } else {
      setSelectedPositions([]);
    }
  };

  const handleClosePosition = async (positionId: string) => {
    try {
      // TODO: API call to close position
      console.log('Closing position:', positionId);
      
      // Remove from local state for demo
      setPositions(prev => prev.filter(pos => pos.id !== positionId));
      setSelectedPositions(prev => prev.filter(id => id !== positionId));
    } catch (error) {
      console.error('Failed to close position:', error);
    }
  };

  const handleBatchClose = async () => {
    try {
      // TODO: API call to close multiple positions
      console.log('Closing positions:', selectedPositions);
      
      // Remove from local state for demo
      setPositions(prev => prev.filter(pos => !selectedPositions.includes(pos.id)));
      setSelectedPositions([]);
      setShowBatchActions(false);
    } catch (error) {
      console.error('Failed to close positions:', error);
    }
  };

  const filteredPositions = positions.filter(pos => {
    switch (filterBy) {
      case 'profitable': return pos.unrealizedPnL > 0;
      case 'losing': return pos.unrealizedPnL < 0;
      case 'long': return pos.side === 'long';
      case 'short': return pos.side === 'short';
      case 'high_risk': return pos.riskLevel === 'high';
      default: return true;
    }
  });

  const sortedPositions = [...filteredPositions].sort((a, b) => {
    const aVal = a[sortBy];
    const bVal = b[sortBy];
    
    if (typeof aVal === 'string' && typeof bVal === 'string') {
      return sortOrder === 'asc' 
        ? aVal.localeCompare(bVal)
        : bVal.localeCompare(aVal);
    }
    
    if (typeof aVal === 'number' && typeof bVal === 'number') {
      return sortOrder === 'asc' ? aVal - bVal : bVal - aVal;
    }
    
    return 0;
  });

  const getRiskColor = (riskLevel: string) => {
    switch (riskLevel) {
      case 'low': return 'text-green-600 bg-green-100 dark:bg-green-900/30 dark:text-green-200';
      case 'medium': return 'text-yellow-600 bg-yellow-100 dark:bg-yellow-900/30 dark:text-yellow-200';
      case 'high': return 'text-red-600 bg-red-100 dark:bg-red-900/30 dark:text-red-200';
      default: return 'text-gray-600 bg-gray-100 dark:bg-gray-700 dark:text-gray-300';
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 80) return 'bg-green-500';
    if (confidence >= 60) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  return (
    <div className="space-y-6">
      {/* Live Data Status Header */}
      <div className="bg-gradient-to-r from-green-50 to-blue-50 dark:from-green-900/20 dark:to-blue-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            <div>
              <p className="text-sm font-medium text-green-800 dark:text-green-200">
                🔴 LIVE POSITIONS MODE - Real Exchange Data
              </p>
              <p className="text-xs text-green-600 dark:text-green-300">
                Real-time position monitoring with live P&L updates every 2 seconds
              </p>
            </div>
          </div>
          <button 
            onClick={loadPositions}
            className="flex items-center px-3 py-1 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700 transition-colors"
          >
            <RefreshCw className="w-4 h-4 mr-1" />
            Refresh Live Data
          </button>
        </div>
      </div>

      {/* Real-time Status Bar */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="flex items-center">
              <div className="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></div>
              <span className="text-sm font-medium text-blue-800 dark:text-blue-200">
                Live Position Monitoring Active
              </span>
            </div>
            <div className="text-xs text-blue-600 dark:text-blue-300">
              Last Update: {lastUpdate.toLocaleTimeString()}
            </div>
          </div>
          <button 
            onClick={loadPositions}
            className="flex items-center px-3 py-1 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 transition-colors"
          >
            <RefreshCw className="w-4 h-4 mr-1" />
            Refresh
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Open Positions</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {summary.totalPositions}
              </p>
              <p className="text-xs text-blue-500">
                {summary.longPositions}L / {summary.shortPositions}S
              </p>
            </div>
            <Eye className="h-8 w-8 text-blue-600" />
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Total Unrealized P&L</p>
              <p className={`text-2xl font-bold ${
                summary.totalUnrealizedPnL >= 0 ? 'text-green-600' : 'text-red-600'
              }`}>
                ${summary.totalUnrealizedPnL.toFixed(2)}
              </p>
              <p className="text-xs text-green-500">
                {summary.profitablePositions}/{summary.totalPositions} profitable
              </p>
            </div>
            {summary.totalUnrealizedPnL >= 0 ? (
              <TrendingUp className="h-8 w-8 text-green-600" />
            ) : (
              <TrendingDown className="h-8 w-8 text-red-600" />
            )}
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Margin Used</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                ${summary.totalMarginUsed.toLocaleString()}
              </p>
              <p className="text-xs text-orange-500">Total exposure</p>
            </div>
            <Wallet className="h-8 w-8 text-orange-600" />
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Avg AI Confidence</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {summary.avgAiConfidence}%
              </p>
              <p className="text-xs text-blue-500">AI strength</p>
            </div>
            <Target className="h-8 w-8 text-blue-600" />
          </div>
        </div>
      </div>

      {/* Controls Bar */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <Filter className="w-4 h-4 text-gray-500" />
              <select 
                className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                value={filterBy}
                onChange={(e) => setFilterBy((e.target as HTMLSelectElement).value)}
              >
                <option value="all">All Positions</option>
                <option value="profitable">Profitable Only</option>
                <option value="losing">Losing Only</option>
                <option value="long">Long Positions</option>
                <option value="short">Short Positions</option>
                <option value="high_risk">High Risk</option>
              </select>
            </div>

            <select 
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              value={`${sortBy}_${sortOrder}`}
              onChange={(e) => {
                const [field, order] = (e.target as HTMLSelectElement).value.split('_');
                setSortBy(field as keyof RealPosition);
                setSortOrder(order as 'asc' | 'desc');
              }}
            >
              <option value="openTime_desc">Newest First</option>
              <option value="openTime_asc">Oldest First</option>
              <option value="unrealizedPnL_desc">Highest P&L</option>
              <option value="unrealizedPnL_asc">Lowest P&L</option>
              <option value="size_desc">Largest Size</option>
              <option value="aiConfidence_desc">Highest Confidence</option>
            </select>
          </div>

          <div className="flex items-center space-x-2">
            {selectedPositions.length > 0 && (
              <>
                <button 
                  onClick={() => setShowBatchActions(!showBatchActions)}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 transition-colors flex items-center"
                >
                  <CheckSquare className="w-4 h-4 mr-2" />
                  Batch Actions ({selectedPositions.length})
                </button>
                
                {showBatchActions && (
                  <div className="flex items-center space-x-2">
                    <button 
                      onClick={handleBatchClose}
                      className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm hover:bg-red-700 transition-colors flex items-center"
                    >
                      <X className="w-4 h-4 mr-2" />
                      Close Selected
                    </button>
                    <button 
                      onClick={() => setSelectedPositions([])}
                      className="px-4 py-2 bg-gray-600 text-white rounded-lg text-sm hover:bg-gray-700 transition-colors"
                    >
                      Clear Selection
                    </button>
                  </div>
                )}
              </>
            )}
            
            <button className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700 transition-colors flex items-center">
              <Download className="w-4 h-4 mr-2" />
              Export
            </button>
          </div>
        </div>
      </div>

      {/* Positions Table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
            <Eye className="w-5 h-5 mr-2" />
            Live Positions ({sortedPositions.length})
          </h3>
        </div>

        {loading ? (
          <div className="p-12 text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600 dark:text-gray-400">Loading positions...</p>
          </div>
        ) : sortedPositions.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left">
                    <input 
                      type="checkbox" 
                      className="rounded border-gray-300 dark:border-gray-600"
                      checked={selectedPositions.length === sortedPositions.length && sortedPositions.length > 0}
                      onChange={(e) => handleSelectAll((e.target as HTMLInputElement).checked)}
                    />
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Symbol</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Side</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Size</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Entry Price</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Current Price</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Unrealized P&L</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Stop/Take</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Duration</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">AI Confidence</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Risk</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {sortedPositions.map((position) => (
                  <tr key={position.id} className="hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <input 
                        type="checkbox" 
                        className="rounded border-gray-300 dark:border-gray-600"
                        checked={selectedPositions.includes(position.id)}
                        onChange={(e) => handleSelectPosition(position.id, (e.target as HTMLInputElement).checked)}
                      />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900 dark:text-white">
                        {position.symbol}
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        {position.strategy}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                        position.side === 'long' 
                          ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                          : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                      }`}>
                        {position.side.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-300">
                      <div>{position.size.toFixed(4)}</div>
                      <div className="text-xs text-gray-500">{position.leverage}x</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-300">
                      ${position.entryPrice.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900 dark:text-gray-300">
                        ${position.currentPrice.toLocaleString()}
                      </div>
                      <div className={`text-xs ${
                        position.currentPrice > position.entryPrice ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {position.currentPrice > position.entryPrice ? '↗' : '↘'} 
                        {Math.abs(((position.currentPrice - position.entryPrice) / position.entryPrice) * 100).toFixed(2)}%
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className={`text-sm font-medium ${
                        position.unrealizedPnL >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        ${position.unrealizedPnL.toFixed(2)}
                      </div>
                      <div className={`text-xs ${
                        position.unrealizedPnLPercent >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        ({position.unrealizedPnLPercent.toFixed(2)}%)
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-xs text-gray-900 dark:text-gray-300">
                      <div>SL: {position.stopLoss ? `$${position.stopLoss.toLocaleString()}` : '-'}</div>
                      <div>TP: {position.takeProfit ? `$${position.takeProfit.toLocaleString()}` : '-'}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center text-sm text-gray-900 dark:text-gray-300">
                        <Clock className="w-4 h-4 mr-1" />
                        {position.duration}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className={`w-2 h-2 rounded-full mr-2 ${getConfidenceColor(position.aiConfidence)}`}></div>
                        <span className="text-sm text-gray-900 dark:text-gray-300">
                          {position.aiConfidence}%
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getRiskColor(position.riskLevel)}`}>
                        {position.riskLevel.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <div className="flex items-center space-x-1">
                        <button 
                          className="text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300 p-1 rounded transition-colors"
                          title="Edit Position"
                        >
                          <Edit className="w-4 h-4" />
                        </button>
                        <button 
                          className="text-green-600 hover:text-green-900 dark:text-green-400 dark:hover:text-green-300 p-1 rounded transition-colors"
                          title="Add to Position"
                        >
                          <Plus className="w-4 h-4" />
                        </button>
                        <button 
                          className="text-orange-600 hover:text-orange-900 dark:text-orange-400 dark:hover:text-orange-300 p-1 rounded transition-colors"
                          title="Reduce Position"
                        >
                          <Minus className="w-4 h-4" />
                        </button>
                        <button 
                          onClick={() => handleClosePosition(position.id)}
                          className="text-red-600 hover:text-red-900 dark:text-red-400 dark:hover:text-red-300 p-1 rounded transition-colors"
                          title="Close Position"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-12 text-center">
            <Eye className="w-12 h-12 mx-auto text-gray-400 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">No Open Positions</h3>
            <p className="text-gray-500 dark:text-gray-400 mb-4">
              Open positions will appear here when trades are active
            </p>
            <button className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 transition-colors">
              Open New Position
            </button>
          </div>
        )}
      </div>
    </div>
  );
} 