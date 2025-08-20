import { useState, useEffect } from 'preact/hooks';
import { 
  TrendingUp, 
  TrendingDown, 
  Clock, 
  Filter, 
  Download,
  Eye,
  Calendar,
  DollarSign,
  Percent,
  ArrowUpDown,
  Search,
  RefreshCw
} from 'lucide-preact';

interface Trade {
  id: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  type: 'MARKET' | 'LIMIT' | 'STOP';
  quantity: number;
  price: number;
  totalValue: number;
  fees: number;
  pnl: number;
  pnlPercent: number;
  status: 'COMPLETED' | 'PARTIALLY_FILLED' | 'CANCELLED';
  timestamp: Date;
  orderId: string;
  strategy?: string;
  confidence?: number;
  duration?: number; // in minutes
  exitReason?: 'TAKE_PROFIT' | 'STOP_LOSS' | 'MANUAL' | 'TIMEOUT';
}

interface TradeHistoryProps {
  userId?: string;
  limit?: number;
  showFilters?: boolean;
  showExportButton?: boolean;
  onTradeClick?: (trade: Trade) => void;
  onExport?: (trades: Trade[]) => void;
}

export default function TradeHistory({
  userId,
  limit = 50,
  showFilters = true,
  showExportButton = true,
  onTradeClick,
  onExport
}: TradeHistoryProps) {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filteredTrades, setFilteredTrades] = useState<Trade[]>([]);
  
  // Filters
  const [filters, setFilters] = useState({
    symbol: '',
    side: '' as '' | 'BUY' | 'SELL',
    status: '' as '' | 'COMPLETED' | 'PARTIALLY_FILLED' | 'CANCELLED',
    strategy: '',
    dateFrom: '',
    dateTo: '',
    minPnl: '',
    maxPnl: '',
    searchTerm: ''
  });

  // Sorting
  const [sortBy, setSortBy] = useState<keyof Trade>('timestamp');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  useEffect(() => {
    fetchTrades();
  }, [userId, limit]);

  useEffect(() => {
    applyFiltersAndSorting();
  }, [trades, filters, sortBy, sortOrder]);

  const fetchTrades = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Mock data for now - will be replaced with API call
      const mockTrades: Trade[] = [
        {
          id: '1',
          symbol: 'BTCUSDT',
          side: 'BUY',
          type: 'MARKET',
          quantity: 0.5,
          price: 64500,
          totalValue: 32250,
          fees: 32.25,
          pnl: 350,
          pnlPercent: 1.08,
          status: 'COMPLETED',
          timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000), // 2 hours ago
          orderId: 'ORD-001',
          strategy: 'AI_BREAKOUT',
          confidence: 0.85,
          duration: 45,
          exitReason: 'TAKE_PROFIT'
        },
        {
          id: '2',
          symbol: 'ETHUSDT',
          side: 'SELL',
          type: 'LIMIT',
          quantity: 2.0,
          price: 3200,
          totalValue: 6400,
          fees: 6.4,
          pnl: -120,
          pnlPercent: -1.88,
          status: 'COMPLETED',
          timestamp: new Date(Date.now() - 4 * 60 * 60 * 1000), // 4 hours ago
          orderId: 'ORD-002',
          strategy: 'AI_REVERSAL',
          confidence: 0.72,
          duration: 90,
          exitReason: 'STOP_LOSS'
        },
        {
          id: '3',
          symbol: 'BTCUSDT',
          side: 'BUY',
          type: 'MARKET',
          quantity: 0.3,
          price: 63800,
          totalValue: 19140,
          fees: 19.14,
          pnl: 75,
          pnlPercent: 0.39,
          status: 'COMPLETED',
          timestamp: new Date(Date.now() - 6 * 60 * 60 * 1000), // 6 hours ago
          orderId: 'ORD-003',
          strategy: 'MANUAL',
          duration: 120,
          exitReason: 'MANUAL'
        },
        {
          id: '4',
          symbol: 'ETHUSDT',
          side: 'BUY',
          type: 'LIMIT',
          quantity: 1.5,
          price: 3150,
          totalValue: 4725,
          fees: 4.73,
          pnl: 0,
          pnlPercent: 0,
          status: 'CANCELLED',
          timestamp: new Date(Date.now() - 8 * 60 * 60 * 1000), // 8 hours ago
          orderId: 'ORD-004',
          strategy: 'AI_MOMENTUM',
          confidence: 0.68
        },
        {
          id: '5',
          symbol: 'BTCUSDT',
          side: 'SELL',
          type: 'MARKET',
          quantity: 0.8,
          price: 65100,
          totalValue: 52080,
          fees: 52.08,
          pnl: 480,
          pnlPercent: 0.92,
          status: 'COMPLETED',
          timestamp: new Date(Date.now() - 12 * 60 * 60 * 1000), // 12 hours ago
          orderId: 'ORD-005',
          strategy: 'AI_TREND',
          confidence: 0.91,
          duration: 180,
          exitReason: 'TAKE_PROFIT'
        }
      ];

      // Generate more mock trades
      for (let i = 6; i <= limit; i++) {
        const symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT'];
        const sides = ['BUY', 'SELL'];
        const types = ['MARKET', 'LIMIT', 'STOP'];
        const strategies = ['AI_BREAKOUT', 'AI_REVERSAL', 'AI_MOMENTUM', 'AI_TREND', 'MANUAL'];
        const exitReasons = ['TAKE_PROFIT', 'STOP_LOSS', 'MANUAL', 'TIMEOUT'];
        
        const symbol = symbols[Math.floor(Math.random() * symbols.length)];
        const side = sides[Math.floor(Math.random() * sides.length)] as 'BUY' | 'SELL';
        const type = types[Math.floor(Math.random() * types.length)] as 'MARKET' | 'LIMIT' | 'STOP';
        const strategy = strategies[Math.floor(Math.random() * strategies.length)];
        const exitReason = exitReasons[Math.floor(Math.random() * exitReasons.length)] as any;
        
        const quantity = Math.random() * 2 + 0.1;
        const price = symbol.includes('BTC') ? 60000 + Math.random() * 10000 : 3000 + Math.random() * 500;
        const totalValue = quantity * price;
        const fees = totalValue * 0.001;
        const pnl = (Math.random() - 0.5) * 1000;
        const pnlPercent = (pnl / totalValue) * 100;
        
        mockTrades.push({
          id: i.toString(),
          symbol,
          side,
          type,
          quantity,
          price,
          totalValue,
          fees,
          pnl,
          pnlPercent,
          status: Math.random() > 0.1 ? 'COMPLETED' : 'CANCELLED',
          timestamp: new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000), // Random within last 7 days
          orderId: `ORD-${i.toString().padStart(3, '0')}`,
          strategy,
          confidence: Math.random() * 0.4 + 0.6,
          duration: Math.floor(Math.random() * 240) + 15,
          exitReason
        });
      }

      setTimeout(() => {
        setTrades(mockTrades);
        setLoading(false);
      }, 500);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch trades');
      setLoading(false);
    }
  };

  const applyFiltersAndSorting = () => {
    let filtered = [...trades];

    // Apply filters
    if (filters.symbol) {
      filtered = filtered.filter(trade => 
        trade.symbol.toLowerCase().includes(filters.symbol.toLowerCase())
      );
    }

    if (filters.side) {
      filtered = filtered.filter(trade => trade.side === filters.side);
    }

    if (filters.status) {
      filtered = filtered.filter(trade => trade.status === filters.status);
    }

    if (filters.strategy) {
      filtered = filtered.filter(trade => 
        trade.strategy?.toLowerCase().includes(filters.strategy.toLowerCase())
      );
    }

    if (filters.dateFrom) {
      const fromDate = new Date(filters.dateFrom);
      filtered = filtered.filter(trade => trade.timestamp >= fromDate);
    }

    if (filters.dateTo) {
      const toDate = new Date(filters.dateTo);
      filtered = filtered.filter(trade => trade.timestamp <= toDate);
    }

    if (filters.minPnl) {
      filtered = filtered.filter(trade => trade.pnl >= parseFloat(filters.minPnl));
    }

    if (filters.maxPnl) {
      filtered = filtered.filter(trade => trade.pnl <= parseFloat(filters.maxPnl));
    }

    if (filters.searchTerm) {
      const searchLower = filters.searchTerm.toLowerCase();
      filtered = filtered.filter(trade => 
        trade.symbol.toLowerCase().includes(searchLower) ||
        trade.orderId.toLowerCase().includes(searchLower) ||
        trade.strategy?.toLowerCase().includes(searchLower)
      );
    }

    // Apply sorting
    filtered.sort((a, b) => {
      const aValue = a[sortBy];
      const bValue = b[sortBy];
      
      if (aValue < bValue) return sortOrder === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });

    setFilteredTrades(filtered);
    setCurrentPage(1); // Reset to first page when filters change
  };

  const handleSort = (field: keyof Trade) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
  };

  const handleExport = () => {
    onExport?.(filteredTrades);
  };

  const formatTime = (date: Date) => {
    return date.toLocaleString();
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount);
  };

  const formatDuration = (minutes: number) => {
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h ${mins}m`;
  };

  // Pagination
  const totalPages = Math.ceil(filteredTrades.length / pageSize);
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const currentTrades = filteredTrades.slice(startIndex, endIndex);

  // Statistics
  const totalTrades = filteredTrades.length;
  const completedTrades = filteredTrades.filter(t => t.status === 'COMPLETED');
  const winningTrades = completedTrades.filter(t => t.pnl > 0);
  const totalPnl = completedTrades.reduce((sum, t) => sum + t.pnl, 0);
  const totalFees = completedTrades.reduce((sum, t) => sum + t.fees, 0);
  const winRate = completedTrades.length > 0 ? (winningTrades.length / completedTrades.length) * 100 : 0;

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <RefreshCw className="w-6 h-6 animate-spin text-blue-500 mr-2" />
        <span className="text-gray-600 dark:text-gray-400">Loading trade history...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="text-red-600 dark:text-red-400">{error}</div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
          <div className="text-sm text-gray-600 dark:text-gray-400">Total Trades</div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white">{totalTrades}</div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
          <div className="text-sm text-gray-600 dark:text-gray-400">Win Rate</div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white">{winRate.toFixed(1)}%</div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
          <div className="text-sm text-gray-600 dark:text-gray-400">Total P&L</div>
          <div className={`text-2xl font-bold ${
            totalPnl >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
          }`}>
            {formatCurrency(totalPnl)}
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
          <div className="text-sm text-gray-600 dark:text-gray-400">Total Fees</div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white">{formatCurrency(totalFees)}</div>
        </div>
      </div>

      {/* Filters */}
      {showFilters && (
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Filters</h3>
            <button
              onClick={() => setFilters({
                symbol: '',
                side: '',
                status: '',
                strategy: '',
                dateFrom: '',
                dateTo: '',
                minPnl: '',
                maxPnl: '',
                searchTerm: ''
              })}
              className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200"
            >
              Clear All
            </button>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Search
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={filters.searchTerm}
                  onChange={(e) => setFilters({...filters, searchTerm: e.currentTarget.value})}
                  placeholder="Symbol, Order ID, Strategy..."
                  className="w-full px-3 py-2 pl-10 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                />
                <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Symbol
              </label>
              <input
                type="text"
                value={filters.symbol}
                onChange={(e) => setFilters({...filters, symbol: e.currentTarget.value})}
                placeholder="BTCUSDT"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Side
              </label>
              <select
                value={filters.side}
                onChange={(e) => setFilters({...filters, side: e.currentTarget.value as any})}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                <option value="">All</option>
                <option value="BUY">Buy</option>
                <option value="SELL">Sell</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Status
              </label>
              <select
                value={filters.status}
                onChange={(e) => setFilters({...filters, status: e.currentTarget.value as any})}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                <option value="">All</option>
                <option value="COMPLETED">Completed</option>
                <option value="PARTIALLY_FILLED">Partially Filled</option>
                <option value="CANCELLED">Cancelled</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                From Date
              </label>
              <input
                type="date"
                value={filters.dateFrom}
                onChange={(e) => setFilters({...filters, dateFrom: e.currentTarget.value})}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                To Date
              </label>
              <input
                type="date"
                value={filters.dateTo}
                onChange={(e) => setFilters({...filters, dateTo: e.currentTarget.value})}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Min P&L
              </label>
              <input
                type="number"
                value={filters.minPnl}
                onChange={(e) => setFilters({...filters, minPnl: e.currentTarget.value})}
                placeholder="0"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Max P&L
              </label>
              <input
                type="number"
                value={filters.maxPnl}
                onChange={(e) => setFilters({...filters, maxPnl: e.currentTarget.value})}
                placeholder="1000"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>
          </div>
        </div>
      )}

      {/* Header with Export */}
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          Trade History ({filteredTrades.length} trades)
        </h3>
        
        <div className="flex items-center space-x-2">
          {showExportButton && (
            <button
              onClick={handleExport}
              className="flex items-center px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Download className="w-4 h-4 mr-2" />
              Export CSV
            </button>
          )}
          
          <button
            onClick={fetchTrades}
            className="p-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Trades Table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  <button
                    onClick={() => handleSort('timestamp')}
                    className="flex items-center space-x-1 hover:text-gray-700 dark:hover:text-gray-200"
                  >
                    <span>Time</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </button>
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  <button
                    onClick={() => handleSort('symbol')}
                    className="flex items-center space-x-1 hover:text-gray-700 dark:hover:text-gray-200"
                  >
                    <span>Symbol</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </button>
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Side
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  <button
                    onClick={() => handleSort('quantity')}
                    className="flex items-center space-x-1 hover:text-gray-700 dark:hover:text-gray-200"
                  >
                    <span>Quantity</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </button>
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  <button
                    onClick={() => handleSort('price')}
                    className="flex items-center space-x-1 hover:text-gray-700 dark:hover:text-gray-200"
                  >
                    <span>Price</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </button>
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  <button
                    onClick={() => handleSort('pnl')}
                    className="flex items-center space-x-1 hover:text-gray-700 dark:hover:text-gray-200"
                  >
                    <span>P&L</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </button>
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Strategy
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {currentTrades.map((trade) => (
                <tr key={trade.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                    <div className="flex items-center">
                      <Clock className="w-4 h-4 text-gray-400 mr-2" />
                      {formatTime(trade.timestamp)}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                    {trade.symbol}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <div className="flex items-center">
                      {trade.side === 'BUY' ? (
                        <TrendingUp className="w-4 h-4 text-green-500 mr-1" />
                      ) : (
                        <TrendingDown className="w-4 h-4 text-red-500 mr-1" />
                      )}
                      <span className={`font-medium ${
                        trade.side === 'BUY' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
                      }`}>
                        {trade.side}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                    {trade.quantity.toFixed(5)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                    ${trade.price.toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <div className={`font-medium ${
                      trade.pnl >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
                    }`}>
                      {formatCurrency(trade.pnl)}
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        {trade.pnlPercent >= 0 ? '+' : ''}{trade.pnlPercent.toFixed(2)}%
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                    <div className="flex items-center">
                      <span className="text-xs bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">
                        {trade.strategy}
                      </span>
                      {trade.confidence && (
                        <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
                          {Math.round(trade.confidence * 100)}%
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                      trade.status === 'COMPLETED' 
                        ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                        : trade.status === 'PARTIALLY_FILLED'
                        ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
                        : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
                    }`}>
                      {trade.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    <button
                      onClick={() => onTradeClick?.(trade)}
                      className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-4 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
          <div className="flex items-center text-sm text-gray-700 dark:text-gray-300">
            <span>
              Showing {startIndex + 1} to {Math.min(endIndex, filteredTrades.length)} of {filteredTrades.length} trades
            </span>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
              disabled={currentPage === 1}
              className="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded disabled:opacity-50"
            >
              Previous
            </button>
            <span className="text-sm text-gray-700 dark:text-gray-300">
              Page {currentPage} of {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
              disabled={currentPage === totalPages}
              className="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
} 