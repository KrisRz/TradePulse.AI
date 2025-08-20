import { useState, useEffect } from 'preact/hooks';
import { 
  DollarSign, TrendingUp, TrendingDown, AlertTriangle, Clock, Target, Zap, BarChart3, 
  Eye, Wallet, Signal, Lock, Shield, Settings, Activity, CreditCard, Globe,
  CheckCircle, Play, Pause, RefreshCw, PieChart, LineChart, Archive, FileText,
  Users, Bell, Database
} from 'lucide-preact';
import SignalLogsAdmin from '../../signals/SignalLogsAdmin';
import { OpenPositionsManager, WalletManagement } from '../../../shared/trading';
import { ClosedPositionsAnalytics } from '../../../shared/analytics';
import { LiveBitcoinChart } from '../../../shared/charts';

export default function RealTradingAdmin() {
  const [activeTab, setActiveTab] = useState('overview');
  const [tradingEnabled, setTradingEnabled] = useState(false);
  const [loading, setLoading] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(new Date());
  const [bitcoinPrice, setBitcoinPrice] = useState(96500);

  // Enhanced tab structure from the plan
  const tabs = [
    { id: 'overview', label: 'Portfolio Overview', icon: PieChart },
    { id: 'open-positions', label: 'Open Positions', icon: Eye },
    { id: 'closed-positions', label: 'Closed Positions', icon: Archive },
    { id: 'orders', label: 'Order Management', icon: FileText },
    { id: 'wallet', label: 'Wallet', icon: Wallet },
    { id: 'chart', label: 'Live Chart', icon: LineChart },
    { id: 'risk', label: 'Risk Management', icon: Shield },
    { id: 'controls', label: 'Trading Controls', icon: Settings },
    { id: 'broker', label: 'Broker Integration', icon: Globe },
    { id: 'compliance', label: 'Compliance', icon: CheckCircle },
    { id: 'signals', label: 'AI Signals', icon: Signal }
  ];

  // Update price every few seconds (mock)
  useEffect(() => {
    const interval = setInterval(() => {
      setBitcoinPrice(prev => {
        const change = (Math.random() - 0.5) * 100;
        return Math.max(prev + change, 50000);
      });
      setLastUpdate(new Date());
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-6">
      {/* Enhanced Header with Live Bitcoin Price */}
      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center">
            <DollarSign className="h-8 w-8 mr-3 text-emerald-600" />
            Real Money Trading
          </h2>
          <div className="flex items-center space-x-4 mt-2">
            <span className="text-sm text-gray-600 dark:text-gray-400">Live BTC:</span>
            <span className="text-lg font-bold text-orange-600">
              ${bitcoinPrice.toLocaleString()}
            </span>
            <span className="text-xs text-gray-500">
              Updated: {lastUpdate.toLocaleTimeString()}
            </span>
          </div>
        </div>
        
        <div className="flex items-center space-x-3">
          <div className={`flex items-center px-3 py-1 rounded-full text-sm font-medium ${
            tradingEnabled 
              ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200' 
              : 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200'
          }`}>
            {tradingEnabled ? <Play className="w-4 h-4 mr-1" /> : <Pause className="w-4 h-4 mr-1" />}
            {tradingEnabled ? 'Trading Active' : 'Trading Paused'}
          </div>
          <div className="flex items-center px-3 py-1 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-200 rounded-full text-sm">
            <Lock className="w-4 h-4 mr-1" />
            Development Mode
          </div>
        </div>
      </div>

      {/* Development Notice */}
      <div className="bg-gradient-to-r from-yellow-50 to-orange-50 dark:from-yellow-900/20 dark:to-orange-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
        <div className="flex items-start">
          <AlertTriangle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 mr-3 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
              🚧 Enterprise Real Money Trading - In Development
            </p>
            <p className="text-xs text-yellow-600 dark:text-yellow-300 mt-1">
              This is a comprehensive preview of our institutional-grade trading platform. Features include advanced risk management, 
              multi-exchange connectivity, AI-driven execution, and full regulatory compliance.
            </p>
          </div>
        </div>
      </div>

      {/* System Status Bar */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center space-x-6 text-sm">
            <div className="flex items-center">
              <div className="w-2 h-2 bg-red-500 rounded-full mr-2"></div>
              <span className="text-gray-600 dark:text-gray-400">Exchange: Disconnected</span>
            </div>
            <div className="flex items-center">
              <div className="w-2 h-2 bg-red-500 rounded-full mr-2"></div>
              <span className="text-gray-600 dark:text-gray-400">API: Not Connected</span>
            </div>
            <div className="flex items-center">
              <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
              <span className="text-gray-600 dark:text-gray-400">AI Engine: Active</span>
            </div>
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">
            Last Update: {lastUpdate.toLocaleTimeString()}
          </div>
        </div>
      </div>

      {/* Enhanced Tab Navigation */}
      <div className="border-b border-gray-200 dark:border-gray-700 overflow-x-auto">
        <nav className="-mb-px flex space-x-8 min-w-max">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                className={`py-3 px-1 border-b-2 font-medium text-sm transition-colors whitespace-nowrap ${
                  activeTab === tab.id 
                    ? 'border-emerald-500 text-emerald-600 dark:text-emerald-400' 
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                }`}
                onClick={() => setActiveTab(tab.id)}
              >
                <div className="flex items-center">
                  <Icon className="w-4 h-4 mr-2" />
                  {tab.label}
                </div>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Portfolio Overview Tab */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Account Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Account Balance</p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">$0.00</p>
                  <p className="text-xs text-red-500 mt-1">● Not Connected</p>
                </div>
                <div className="p-3 bg-green-100 dark:bg-green-900/30 rounded-lg">
                  <Wallet className="h-6 w-6 text-green-600" />
                </div>
              </div>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Buying Power</p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">$0.00</p>
                  <p className="text-xs text-gray-500 mt-1">Available for trading</p>
                </div>
                <div className="p-3 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                  <CreditCard className="h-6 w-6 text-blue-600" />
                </div>
              </div>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Day P&L</p>
                  <p className="text-2xl font-bold text-gray-400">$0.00</p>
                  <p className="text-xs text-gray-500 mt-1">+0.00%</p>
                </div>
                <div className="p-3 bg-gray-100 dark:bg-gray-700 rounded-lg">
                  <TrendingUp className="h-6 w-6 text-gray-400" />
                </div>
              </div>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Total P&L</p>
                  <p className="text-2xl font-bold text-gray-400">$0.00</p>
                  <p className="text-xs text-gray-500 mt-1">All time</p>
                </div>
                <div className="p-3 bg-gray-100 dark:bg-gray-700 rounded-lg">
                  <BarChart3 className="h-6 w-6 text-gray-400" />
                </div>
              </div>
            </div>
          </div>

          {/* Portfolio Allocation & Performance */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Portfolio Allocation</h3>
              <div className="space-y-4">
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                  <PieChart className="w-12 h-12 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No positions to display</p>
                  <p className="text-xs">Connect to broker to view allocation</p>
                </div>
              </div>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Performance Metrics</h3>
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Sharpe Ratio</span>
                  <span className="text-sm font-medium text-gray-900 dark:text-white">--</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Max Drawdown</span>
                  <span className="text-sm font-medium text-gray-900 dark:text-white">--</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Win Rate</span>
                  <span className="text-sm font-medium text-gray-900 dark:text-white">--</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Avg Trade</span>
                  <span className="text-sm font-medium text-gray-900 dark:text-white">--</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Open Positions Tab - NEW INTEGRATED COMPONENT */}
      {activeTab === 'open-positions' && (
        <OpenPositionsManager />
      )}

      {/* Closed Positions Tab - NEW INTEGRATED COMPONENT */}
      {activeTab === 'closed-positions' && (
        <ClosedPositionsAnalytics />
      )}

      {/* Order Management Tab */}
      {activeTab === 'orders' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Order Entry */}
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Place Order</h3>
              <div className="space-y-4 opacity-50 pointer-events-none">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Symbol</label>
                  <input type="text" className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700" placeholder="BTCUSDT" />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Side</label>
                    <select className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700">
                      <option>Buy</option>
                      <option>Sell</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Order Type</label>
                    <select className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700">
                      <option>Market</option>
                      <option>Limit</option>
                      <option>Stop</option>
                    </select>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Quantity</label>
                  <input type="number" className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700" placeholder="0.00" />
                </div>
                <button className="w-full bg-green-600 hover:bg-green-700 text-white font-medium py-2 px-4 rounded-md transition-colors">
                  Place Order
                </button>
              </div>
            </div>

            {/* Order History */}
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Order History</h3>
              <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                <FileText className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No orders placed</p>
                <p className="text-xs">Order history will appear here</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Wallet Tab - NOW INTEGRATED */}
      {activeTab === 'wallet' && (
        <WalletManagement />
      )}

      {/* Live Chart Tab - NOW INTEGRATED */}
      {activeTab === 'chart' && (
        <LiveBitcoinChart />
      )}

      {/* Risk Management Tab */}
      {activeTab === 'risk' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
                <Shield className="w-5 h-5 mr-2" />
                Risk Limits
              </h3>
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Max Position Size</span>
                  <span className="text-sm font-medium text-gray-900 dark:text-white">Not Set</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Daily Loss Limit</span>
                  <span className="text-sm font-medium text-gray-900 dark:text-white">Not Set</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Max Drawdown</span>
                  <span className="text-sm font-medium text-gray-900 dark:text-white">Not Set</span>
                </div>
              </div>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Emergency Controls</h3>
              <div className="space-y-3">
                <button className="w-full bg-red-600 hover:bg-red-700 text-white font-medium py-2 px-4 rounded-md transition-colors opacity-50 cursor-not-allowed">
                  <AlertTriangle className="w-4 h-4 mr-2 inline" />
                  Emergency Stop All
                </button>
                <button className="w-full bg-orange-600 hover:bg-orange-700 text-white font-medium py-2 px-4 rounded-md transition-colors opacity-50 cursor-not-allowed">
                  <Eye className="w-4 h-4 mr-2 inline" />
                  Close All Positions
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Trading Controls Tab */}
      {activeTab === 'controls' && (
        <div className="space-y-6">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
              <Settings className="w-5 h-5 mr-2" />
              AI Trading Controls
            </h3>
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <label className="text-sm font-medium text-gray-900 dark:text-white">Auto Trading</label>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Enable AI-driven automatic trading</p>
                </div>
                <button 
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    tradingEnabled ? 'bg-green-600' : 'bg-gray-200 dark:bg-gray-700'
                  } opacity-50 cursor-not-allowed`}
                >
                  <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    tradingEnabled ? 'translate-x-6' : 'translate-x-1'
                  }`} />
                </button>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-900 dark:text-white mb-2">
                  Minimum AI Confidence Threshold
                </label>
                <input 
                  type="range" 
                  min="50" 
                  max="95" 
                  value="70" 
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700 opacity-50"
                  disabled
                />
                <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
                  <span>50%</span>
                  <span>70%</span>
                  <span>95%</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Broker Integration Tab */}
      {activeTab === 'broker' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Exchange Connections</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Binance</span>
                  <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200">
                    <AlertTriangle className="w-3 h-3 mr-1" />
                    Disconnected
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Coinbase Pro</span>
                  <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200">
                    <AlertTriangle className="w-3 h-3 mr-1" />
                    Disconnected
                  </span>
                </div>
              </div>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">API Status</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Rate Limits</span>
                  <span className="text-sm font-medium text-gray-900 dark:text-white">--/--</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Latency</span>
                  <span className="text-sm font-medium text-gray-900 dark:text-white">-- ms</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Compliance Tab */}
      {activeTab === 'compliance' && (
        <div className="space-y-6">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
              <CheckCircle className="w-5 h-5 mr-2" />
              Regulatory Compliance
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">KYC Status</span>
                  <span className="text-sm font-medium text-gray-900 dark:text-white">Not Required (Dev)</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Audit Trail</span>
                  <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200">
                    <CheckCircle className="w-3 h-3 mr-1" />
                    Active
                  </span>
                </div>
              </div>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Position Reporting</span>
                  <span className="text-sm font-medium text-gray-900 dark:text-white">Automated</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Data Retention</span>
                  <span className="text-sm font-medium text-gray-900 dark:text-white">7 Years</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* AI Signals Tab */}
      {activeTab === 'signals' && (
        <div className="space-y-6">
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <div className="flex items-center">
              <Signal className="w-5 h-5 text-blue-600 dark:text-blue-400 mr-3" />
              <div>
                <p className="text-sm font-medium text-blue-800 dark:text-blue-200">
                  AI Trading Signals - Real Money Mode
                </p>
                <p className="text-xs text-blue-600 dark:text-blue-300 mt-1">
                  Real-time AI signals for institutional trading (Development Preview)
                </p>
              </div>
            </div>
          </div>
          
          <SignalLogsAdmin />
        </div>
      )}
    </div>
  );
} 