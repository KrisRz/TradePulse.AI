import { useState, useEffect } from 'preact/hooks';
import { 
  Archive, BarChart3, TrendingUp, TrendingDown, Download, Filter, Calendar,
  Target, DollarSign, Clock, Activity, FileText, Eye, Zap, Award
} from 'lucide-preact';

interface ClosedPosition {
  id: string;
  symbol: string;
  side: 'long' | 'short';
  size: number;
  entryPrice: number;
  exitPrice: number;
  realizedPnL: number;
  realizedPnLPercent: number;
  openTime: string;
  closeTime: string;
  holdDuration: string;
  exitReason: 'stop_loss' | 'take_profit' | 'manual' | 'ai_signal' | 'risk_management';
  aiConfidence: number;
  strategy: string;
  commissions: number;
  tags: string[];
  exchange: string;
  leverage: number;
}

interface AnalyticsSummary {
  totalTrades: number;
  profitableTrades: number;
  losingTrades: number;
  totalPnL: number;
  winRate: number;
  avgHoldTime: string;
  bestTrade: number;
  worstTrade: number;
  profitFactor: number;
  avgPnLPerTrade: number;
  totalCommissions: number;
  sharpeRatio: number;
}

export default function ClosedPositionsAnalytics() {
  const [closedPositions, setClosedPositions] = useState<ClosedPosition[]>([]);
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState({ from: '', to: '' });
  const [filterBy, setFilterBy] = useState('all');
  const [sortBy, setSortBy] = useState<keyof ClosedPosition>('closeTime');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [selectedPeriod, setSelectedPeriod] = useState('30d');

  // Mock data for development
  const mockClosedPositions: ClosedPosition[] = [
    {
      id: 'pos_closed_001',
      symbol: 'BTCUSDT',
      side: 'long',
      size: 0.1,
      entryPrice: 94000,
      exitPrice: 96500,
      realizedPnL: 250,
      realizedPnLPercent: 2.66,
      openTime: '2024-01-14T10:30:00Z',
      closeTime: '2024-01-15T14:45:00Z',
      holdDuration: '1d 4h 15m',
      exitReason: 'take_profit',
      aiConfidence: 85,
      strategy: 'AI_REVERSAL_V2',
      commissions: 15.5,
      tags: ['profitable', 'ai_driven'],
      exchange: 'binance',
      leverage: 20
    },
    {
      id: 'pos_closed_002',
      symbol: 'BTCUSDT',
      side: 'short',
      size: 0.05,
      entryPrice: 97000,
      exitPrice: 95000,
      realizedPnL: 100,
      realizedPnLPercent: 2.06,
      openTime: '2024-01-13T15:20:00Z',
      closeTime: '2024-01-14T08:30:00Z',
      holdDuration: '17h 10m',
      exitReason: 'ai_signal',
      aiConfidence: 78,
      strategy: 'AI_MOMENTUM_V1',
      commissions: 12.2,
      tags: ['profitable', 'short_term'],
      exchange: 'binance',
      leverage: 20
    },
    {
      id: 'pos_closed_003',
      symbol: 'BTCUSDT',
      side: 'long',
      size: 0.08,
      entryPrice: 98000,
      exitPrice: 96000,
      realizedPnL: -160,
      realizedPnLPercent: -2.04,
      openTime: '2024-01-12T09:15:00Z',
      closeTime: '2024-01-12T16:20:00Z',
      holdDuration: '7h 5m',
      exitReason: 'stop_loss',
      aiConfidence: 65,
      strategy: 'AI_TECHNICAL_V3',
      commissions: 18.8,
      tags: ['loss', 'stopped_out'],
      exchange: 'binance',
      leverage: 20
    }
  ];

  const [analytics, setAnalytics] = useState<AnalyticsSummary>({
    totalTrades: 0,
    profitableTrades: 0,
    losingTrades: 0,
    totalPnL: 0,
    winRate: 0,
    avgHoldTime: '0h 0m',
    bestTrade: 0,
    worstTrade: 0,
    profitFactor: 0,
    avgPnLPerTrade: 0,
    totalCommissions: 0,
    sharpeRatio: 0
  });

  // Calculate analytics from positions
  const calculateAnalytics = (positions: ClosedPosition[]): AnalyticsSummary => {
    if (positions.length === 0) {
      return {
        totalTrades: 0,
        profitableTrades: 0,
        losingTrades: 0,
        totalPnL: 0,
        winRate: 0,
        avgHoldTime: '0h 0m',
        bestTrade: 0,
        worstTrade: 0,
        profitFactor: 0,
        avgPnLPerTrade: 0,
        totalCommissions: 0,
        sharpeRatio: 0
      };
    }

    const profitablePositions = positions.filter(pos => pos.realizedPnL > 0);
    const losingPositions = positions.filter(pos => pos.realizedPnL < 0);
    const totalPnL = positions.reduce((sum, pos) => sum + pos.realizedPnL, 0);
    const totalCommissions = positions.reduce((sum, pos) => sum + pos.commissions, 0);
    const grossProfit = profitablePositions.reduce((sum, pos) => sum + pos.realizedPnL, 0);
    const grossLoss = Math.abs(losingPositions.reduce((sum, pos) => sum + pos.realizedPnL, 0));

    return {
      totalTrades: positions.length,
      profitableTrades: profitablePositions.length,
      losingTrades: losingPositions.length,
      totalPnL: totalPnL,
      winRate: (profitablePositions.length / positions.length) * 100,
      avgHoldTime: '12h 30m', // Mock calculation
      bestTrade: Math.max(...positions.map(pos => pos.realizedPnL)),
      worstTrade: Math.min(...positions.map(pos => pos.realizedPnL)),
      profitFactor: grossLoss > 0 ? grossProfit / grossLoss : 0,
      avgPnLPerTrade: totalPnL / positions.length,
      totalCommissions: totalCommissions,
      sharpeRatio: 1.45 // Mock calculation
    };
  };

  // Load positions data
  useEffect(() => {
    loadClosedPositions();
  }, [dateRange, filterBy, selectedPeriod]);

  // Update analytics when positions change
  useEffect(() => {
    setAnalytics(calculateAnalytics(closedPositions));
  }, [closedPositions]);

  const loadClosedPositions = async () => {
    try {
      setLoading(true);
      // TODO: Replace with real API call
      // const response = await fetch('/api/real-trading/positions/closed');
      // const data = await response.json();
      
      // For now, use mock data
      setTimeout(() => {
        setClosedPositions(mockClosedPositions);
        setLoading(false);
      }, 1000);
    } catch (error) {
      console.error('Failed to load closed positions:', error);
      setLoading(false);
    }
  };

  const filteredPositions = closedPositions.filter(pos => {
    switch (filterBy) {
      case 'profitable': return pos.realizedPnL > 0;
      case 'losing': return pos.realizedPnL < 0;
      case 'long': return pos.side === 'long';
      case 'short': return pos.side === 'short';
      case 'stop_loss': return pos.exitReason === 'stop_loss';
      case 'take_profit': return pos.exitReason === 'take_profit';
      case 'ai_signal': return pos.exitReason === 'ai_signal';
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

  const exportToCSV = () => {
    const csvData = sortedPositions.map(pos => ({
      'Trade ID': pos.id,
      Symbol: pos.symbol,
      Side: pos.side.toUpperCase(),
      Size: pos.size,
      'Entry Price': pos.entryPrice,
      'Exit Price': pos.exitPrice,
      'Realized P&L': pos.realizedPnL,
      'P&L %': pos.realizedPnLPercent,
      'Open Time': pos.openTime,
      'Close Time': pos.closeTime,
      'Hold Duration': pos.holdDuration,
      'Exit Reason': pos.exitReason,
      'AI Confidence': pos.aiConfidence,
      Strategy: pos.strategy,
      Commissions: pos.commissions,
      Exchange: pos.exchange,
      Leverage: pos.leverage
    }));

    // Convert to CSV and download (mock implementation)
    console.log('Exporting to CSV:', csvData);
    alert('CSV export functionality would be implemented here');
  };

  const getExitReasonColor = (reason: string) => {
    switch (reason) {
      case 'take_profit': return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200';
      case 'stop_loss': return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200';
      case 'ai_signal': return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-200';
      case 'manual': return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300';
      case 'risk_management': return 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-200';
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300';
    }
  };

  return (
    <div className="space-y-6">
      {/* Analytics Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Total Trades</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {analytics.totalTrades}
              </p>
              <p className="text-xs text-blue-500">Completed positions</p>
            </div>
            <Archive className="h-8 w-8 text-blue-600" />
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Win Rate</p>
              <p className="text-2xl font-bold text-green-600">
                {analytics.winRate.toFixed(1)}%
              </p>
              <p className="text-xs text-green-500">
                {analytics.profitableTrades}/{analytics.totalTrades} profitable
              </p>
            </div>
            <TrendingUp className="h-8 w-8 text-green-600" />
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Total P&L</p>
              <p className={`text-2xl font-bold ${
                analytics.totalPnL >= 0 ? 'text-green-600' : 'text-red-600'
              }`}>
                ${analytics.totalPnL.toFixed(2)}
              </p>
              <p className="text-xs text-gray-500">Net profit/loss</p>
            </div>
            <DollarSign className="h-8 w-8 text-purple-600" />
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Profit Factor</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {analytics.profitFactor.toFixed(2)}
              </p>
              <p className="text-xs text-gray-500">Gross profit/loss ratio</p>
            </div>
            <Target className="h-8 w-8 text-orange-600" />
          </div>
        </div>
      </div>

      {/* Additional Analytics Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Best Trade</p>
              <p className="text-2xl font-bold text-green-600">
                ${analytics.bestTrade.toFixed(2)}
              </p>
              <p className="text-xs text-green-500">Highest profit</p>
            </div>
            <Award className="h-8 w-8 text-green-600" />
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Worst Trade</p>
              <p className="text-2xl font-bold text-red-600">
                ${analytics.worstTrade.toFixed(2)}
              </p>
              <p className="text-xs text-red-500">Largest loss</p>
            </div>
            <TrendingDown className="h-8 w-8 text-red-600" />
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Avg Hold Time</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {analytics.avgHoldTime}
              </p>
              <p className="text-xs text-gray-500">Average duration</p>
            </div>
            <Clock className="h-8 w-8 text-blue-600" />
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Sharpe Ratio</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {analytics.sharpeRatio.toFixed(2)}
              </p>
              <p className="text-xs text-gray-500">Risk-adjusted return</p>
            </div>
            <BarChart3 className="h-8 w-8 text-purple-600" />
          </div>
        </div>
      </div>

      {/* Filters and Controls */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <Calendar className="w-4 h-4 text-gray-500" />
              <select 
                className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                value={selectedPeriod}
                onChange={(e) => setSelectedPeriod((e.target as HTMLSelectElement).value)}
              >
                <option value="7d">Last 7 Days</option>
                <option value="30d">Last 30 Days</option>
                <option value="90d">Last 90 Days</option>
                <option value="1y">Last Year</option>
                <option value="all">All Time</option>
              </select>
            </div>

            <div className="flex items-center space-x-2">
              <Filter className="w-4 h-4 text-gray-500" />
              <select 
                className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                value={filterBy}
                onChange={(e) => setFilterBy((e.target as HTMLSelectElement).value)}
              >
                <option value="all">All Trades</option>
                <option value="profitable">Profitable Only</option>
                <option value="losing">Losing Only</option>
                <option value="long">Long Positions</option>
                <option value="short">Short Positions</option>
                <option value="stop_loss">Stop Loss Exits</option>
                <option value="take_profit">Take Profit Exits</option>
                <option value="ai_signal">AI Signal Exits</option>
              </select>
            </div>

            <select 
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              value={`${sortBy}_${sortOrder}`}
              onChange={(e) => {
                const [field, order] = (e.target as HTMLSelectElement).value.split('_');
                setSortBy(field as keyof ClosedPosition);
                setSortOrder(order as 'asc' | 'desc');
              }}
            >
              <option value="closeTime_desc">Latest First</option>
              <option value="closeTime_asc">Oldest First</option>
              <option value="realizedPnL_desc">Highest P&L</option>
              <option value="realizedPnL_asc">Lowest P&L</option>
              <option value="realizedPnLPercent_desc">Best % Return</option>
              <option value="holdDuration_desc">Longest Hold</option>
            </select>
          </div>

          <div className="flex items-center space-x-2">
            <button 
              onClick={exportToCSV}
              className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700 transition-colors flex items-center"
            >
              <Download className="w-4 h-4 mr-2" />
              Export CSV
            </button>
            <button className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 transition-colors flex items-center">
              <FileText className="w-4 h-4 mr-2" />
              Generate Report
            </button>
          </div>
        </div>
      </div>

      {/* Closed Positions Table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
            <Archive className="w-5 h-5 mr-2" />
            Trade History ({sortedPositions.length})
          </h3>
        </div>

        {loading ? (
          <div className="p-12 text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600 dark:text-gray-400">Loading trade history...</p>
          </div>
        ) : sortedPositions.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Symbol</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Side</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Size</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Entry Price</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Exit Price</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Realized P&L</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Hold Duration</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Exit Reason</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">AI Confidence</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {sortedPositions.map((position) => (
                  <tr key={position.id} className="hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
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
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-300">
                      ${position.exitPrice.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className={`text-sm font-medium ${
                        position.realizedPnL >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        ${position.realizedPnL.toFixed(2)}
                      </div>
                      <div className={`text-xs ${
                        position.realizedPnLPercent >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        ({position.realizedPnLPercent >= 0 ? '+' : ''}{position.realizedPnLPercent.toFixed(2)}%)
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center text-sm text-gray-900 dark:text-gray-300">
                        <Clock className="w-4 h-4 mr-1" />
                        {position.holdDuration}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getExitReasonColor(position.exitReason)}`}>
                        {position.exitReason.replace('_', ' ').toUpperCase()}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className={`w-2 h-2 rounded-full mr-2 ${
                          position.aiConfidence >= 80 ? 'bg-green-500' :
                          position.aiConfidence >= 60 ? 'bg-yellow-500' : 'bg-red-500'
                        }`}></div>
                        <span className="text-sm text-gray-900 dark:text-gray-300">
                          {position.aiConfidence}%
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <button className="text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300 transition-colors">
                        <Eye className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-12 text-center">
            <Archive className="w-12 h-12 mx-auto text-gray-400 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">No Closed Positions</h3>
            <p className="text-gray-500 dark:text-gray-400">
              Closed positions will appear here after trades are completed
            </p>
          </div>
        )}
      </div>
    </div>
  );
} 