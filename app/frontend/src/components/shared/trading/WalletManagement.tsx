import { useState } from 'preact/hooks';
import { Wallet, DollarSign, Download, ArrowUp, RefreshCw, ArrowUpRight, ArrowDownLeft, Clock, Shield, AlertTriangle, CheckCircle, EyeOff, Copy, ExternalLink, Filter, Search } from 'lucide-preact';

interface WalletBalance {
  currency: string;
  symbol: string;
  balance: number;
  usdValue: number;
  change24h: number;
  locked: number;
  available: number;
  icon: string;
}

interface Transaction {
  id: string;
  type: 'deposit' | 'withdrawal' | 'trade' | 'fee';
  currency: string;
  amount: number;
  usdValue: number;
  status: 'pending' | 'completed' | 'failed' | 'cancelled';
  timestamp: string;
  txHash?: string;
  address?: string;
  network?: string;
  fee: number;
}

interface WithdrawalLimits {
  dailyLimit: number;
  monthlyLimit: number;
  minimumAmount: number;
  processingFee: number;
  currency: string;
}

export default function WalletManagement() {
  const [balances, setBalances] = useState<WalletBalance[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [withdrawalLimits, setWithdrawalLimits] = useState<WithdrawalLimits | null>(null);
  const [selectedCurrency, setSelectedCurrency] = useState('USD');
  const [activeTab, setActiveTab] = useState('overview');
  const [showValues, setShowValues] = useState(true);
  const [depositAmount, setDepositAmount] = useState('');
  const [withdrawAmount, setWithdrawAmount] = useState('');
  const [withdrawAddress, setWithdrawAddress] = useState('');
  const [loading, setLoading] = useState(true);
  const [limitsLoading, setLimitsLoading] = useState(false);
  const [filter, setFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');

  // Fetch real withdrawal limits from backend - NO MOCKS!
  const fetchWithdrawalLimits = async () => {
    try {
      setLimitsLoading(true);
      const token = localStorage.getItem('auth_token');

      if (!token) {
        console.error('❌ No auth token for withdrawal limits');
        return;
      }

      const response = await fetch('/api/trading/withdrawal-limits', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const limits: WithdrawalLimits = await response.json();
        console.log('✅ Real withdrawal limits loaded:', limits);
        setWithdrawalLimits(limits);
      } else {
        console.error('❌ Failed to fetch withdrawal limits:', response.status);
        // NO FALLBACKS - keep null to show error state
      }
    } catch (error) {
      console.error('❌ Error fetching withdrawal limits:', error);
      // NO FALLBACKS - keep null to show error state
    } finally {
      setLimitsLoading(false);
    }
  };

  // Mock wallet data (will be replaced with real API calls)
  const mockBalances: WalletBalance[] = [
    {
      currency: 'USD',
      symbol: '$',
      balance: 0,
      usdValue: 0,
      change24h: 0,
      locked: 0,
      available: 0,
      icon: '💵'
    },
    {
      currency: 'BTC',
      symbol: '₿',
      balance: 0,
      usdValue: 0,
      change24h: 0,
      locked: 0,
      available: 0,
      icon: '₿'
    },
    {
      currency: 'ETH',
      symbol: 'Ξ',
      balance: 0,
      usdValue: 0,
      change24h: 0,
      locked: 0,
      available: 0,
      icon: 'Ξ'
    },
    {
      currency: 'USDT',
      symbol: '₮',
      balance: 0,
      usdValue: 0,
      change24h: 0,
      locked: 0,
      available: 0,
      icon: '₮'
    }
  ];

  const mockTransactions: Transaction[] = [
    {
      id: 'tx_001',
      type: 'deposit',
      currency: 'USD',
      amount: 0,
      usdValue: 0,
      status: 'completed',
      timestamp: '2024-01-15T10:30:00Z',
      fee: 0
    }
  ];

  const tabs = [
    { id: 'overview', label: 'Overview', icon: Wallet },
    { id: 'deposit', label: 'Deposit', icon: ArrowDownLeft },
    { id: 'withdraw', label: 'Withdraw', icon: ArrowUpRight },
    { id: 'history', label: 'History', icon: Clock }
  ];

  useEffect(() => {
    loadWalletData();
  }, []);

  const loadWalletData = async () => {
    try {
      setLoading(true);

      // Load real wallet balances from backend
      const balanceResponse = await fetch('/api/real-trading/wallet/balances', {
        headers: {
          'Authorization': 'Bearer enterprise_admin_token',
          'Content-Type': 'application/json'
        }
      });

      if (balanceResponse.ok) {
        const balanceData = await balanceResponse.json();
        if (balanceData.status === 'success' && balanceData.data.balances) {
          setBalances(balanceData.data.balances);
          console.log('✅ Loaded real wallet balances');
        }
      } else {
        console.error('Failed to load wallet balances:', balanceResponse.status);
      }

      // Load real withdrawal limits - NO FALLBACKS!
      await fetchWithdrawalLimits();
      
      // Load real transaction history from backend
      const transactionResponse = await fetch('/api/real-trading/wallet/transactions', {
        headers: {
          'Authorization': 'Bearer enterprise_admin_token',
          'Content-Type': 'application/json'
        }
      });
      
      if (transactionResponse.ok) {
        const transactionData = await transactionResponse.json();
        if (transactionData.status === 'success' && transactionData.data.transactions) {
          setTransactions(transactionData.data.transactions);
          console.log('✅ Loaded real transaction history');
        }
      } else {
        console.error('Failed to load transactions:', transactionResponse.status);
      }
      
    } catch (error) {
      console.error('Failed to load wallet data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getTotalUSDValue = () => {
    return balances.reduce((total, balance) => total + balance.usdValue, 0);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-600 bg-green-100 dark:bg-green-900/30 dark:text-green-200';
      case 'pending': return 'text-yellow-600 bg-yellow-100 dark:bg-yellow-900/30 dark:text-yellow-200';
      case 'failed': return 'text-red-600 bg-red-100 dark:bg-red-900/30 dark:text-red-200';
      case 'cancelled': return 'text-gray-600 bg-gray-100 dark:bg-gray-700 dark:text-gray-300';
      default: return 'text-gray-600 bg-gray-100 dark:bg-gray-700 dark:text-gray-300';
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'deposit': return <ArrowDownLeft className="w-4 h-4 text-green-600" />;
      case 'withdrawal': return <ArrowUpRight className="w-4 h-4 text-red-600" />;
      case 'trade': return <RefreshCw className="w-4 h-4 text-blue-600" />;
      case 'fee': return <DollarSign className="w-4 h-4 text-orange-600" />;
      default: return <Clock className="w-4 h-4 text-gray-600" />;
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    // You could add a toast notification here
  };

  const filteredTransactions = transactions.filter(tx => {
    const matchesFilter = filter === 'all' || tx.type === filter;
    const matchesSearch = searchTerm === '' || 
      tx.currency.toLowerCase().includes(searchTerm.toLowerCase()) ||
      tx.id.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  return (
    <div className="space-y-6">
      {/* Wallet Header */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center">
              <Wallet className="h-8 w-8 mr-3 text-blue-600" />
              Wallet Management
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Manage your trading funds across multiple currencies
            </p>
          </div>
          
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setShowValues(!showValues)}
              className="flex items-center px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-lg text-sm hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
            >
              {showValues ? <Eye className="w-4 h-4 mr-1" /> : <EyeOff className="w-4 h-4 mr-1" />}
              {showValues ? 'Hide' : 'Show'} Values
            </button>
            <button
              onClick={loadWalletData}
              className="flex items-center px-3 py-1 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 transition-colors"
            >
              <RefreshCw className="w-4 h-4 mr-1" />
              Refresh
            </button>
          </div>
        </div>

        {/* Total Portfolio Value */}
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-blue-600 dark:text-blue-400 font-medium">Total Portfolio Value</p>
              <p className="text-3xl font-bold text-blue-800 dark:text-blue-200">
                {showValues ? `$${getTotalUSDValue().toLocaleString()}` : '••••••'}
              </p>
            </div>
            <div className="text-right">
              <p className="text-sm text-blue-600 dark:text-blue-400">24h Change</p>
              <p className="text-lg font-bold text-blue-800 dark:text-blue-200">
                {showValues ? '+$0.00 (0.00%)' : '••••••'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Development Notice */}
      <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
        <div className="flex items-center">
          <AlertTriangle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 mr-3" />
          <div>
            <p className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
              Wallet Management - Development Mode
            </p>
            <p className="text-xs text-yellow-600 dark:text-yellow-300 mt-1">
              Real money wallet features are currently disabled. This interface shows the planned functionality for managing trading funds.
            </p>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                className={`py-3 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === tab.id 
                    ? 'border-blue-500 text-blue-600 dark:text-blue-400' 
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

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Currency Balances */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Currency Balances</h3>
            </div>
            
            {loading ? (
              <div className="p-8 text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
                <p className="text-gray-600 dark:text-gray-400">Loading balances...</p>
              </div>
            ) : (
              <div className="p-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {balances.map((balance) => (
                    <div key={balance.currency} className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center">
                          <span className="text-2xl mr-3">{balance.icon}</span>
                          <div>
                            <h4 className="text-lg font-semibold text-gray-900 dark:text-white">
                              {balance.currency}
                            </h4>
                            <p className="text-sm text-gray-600 dark:text-gray-400">
                              Available: {showValues ? `${balance.available.toFixed(8)}` : '••••••'}
                            </p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-lg font-bold text-gray-900 dark:text-white">
                            {showValues ? `${balance.balance.toFixed(8)} ${balance.symbol}` : '••••••'}
                          </p>
                          <p className="text-sm text-gray-600 dark:text-gray-400">
                            {showValues ? `≈ $${balance.usdValue.toLocaleString()}` : '••••••'}
                          </p>
                        </div>
                      </div>
                      
                      {balance.locked > 0 && (
                        <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-600">
                          <div className="flex justify-between text-sm">
                            <span className="text-gray-600 dark:text-gray-400">Locked:</span>
                            <span className="text-gray-900 dark:text-white">
                              {showValues ? `${balance.locked.toFixed(8)} ${balance.symbol}` : '••••••'}
                            </span>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Deposit Tab */}
      {activeTab === 'deposit' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Deposit Form */}
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
                <ArrowDownLeft className="w-5 h-5 mr-2 text-green-600" />
                Deposit Funds
              </h3>
              
              <div className="space-y-4 opacity-50 pointer-events-none">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Select Currency
                  </label>
                  <select 
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    value={selectedCurrency}
                    onChange={(e) => setSelectedCurrency((e.target as HTMLSelectElement).value)}
                  >
                    <option value="USD">USD (Bank Transfer)</option>
                    <option value="BTC">DollarSign (BTC)</option>
                    <option value="ETH">Ethereum (ETH)</option>
                    <option value="USDT">Tether (USDT)</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Amount
                  </label>
                  <input 
                    type="number"
                    placeholder="0.00"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    value={depositAmount}
                    onChange={(e) => setDepositAmount((e.target as HTMLInputElement).value)}
                  />
                </div>
                
                <button className="w-full bg-green-600 hover:bg-green-700 text-white font-medium py-2 px-4 rounded-lg transition-colors">
                  Generate Deposit Address
                </button>
              </div>
            </div>

            {/* Deposit Instructions */}
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Deposit Instructions</h3>
              
              <div className="space-y-4">
                <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                  <div className="flex items-start">
                    <Shield className="w-5 h-5 text-blue-600 dark:text-blue-400 mr-3 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-blue-800 dark:text-blue-200">
                        Security Notice
                      </p>
                      <p className="text-xs text-blue-600 dark:text-blue-300 mt-1">
                        Always verify deposit addresses. We will never ask for your private keys.
                      </p>
                    </div>
                  </div>
                </div>
                
                <div className="space-y-3 text-sm text-gray-600 dark:text-gray-400">
                  <div className="flex items-center">
                    <div className="w-2 h-2 bg-green-500 rounded-full mr-3"></div>
                    <span>Minimum deposit: $10 USD</span>
                  </div>
                  <div className="flex items-center">
                    <div className="w-2 h-2 bg-green-500 rounded-full mr-3"></div>
                    <span>Processing time: 1-3 business days</span>
                  </div>
                  <div className="flex items-center">
                    <div className="w-2 h-2 bg-green-500 rounded-full mr-3"></div>
                    <span>No deposit fees for amounts over $100</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Withdraw Tab */}
      {activeTab === 'withdraw' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Withdrawal Form */}
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
                <ArrowUpRight className="w-5 h-5 mr-2 text-red-600" />
                Withdraw Funds
              </h3>
              
              <div className="space-y-4 opacity-50 pointer-events-none">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Select Currency
                  </label>
                  <select className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white">
                    <option value="USD">USD (Bank Transfer)</option>
                    <option value="BTC">DollarSign (BTC)</option>
                    <option value="ETH">Ethereum (ETH)</option>
                    <option value="USDT">Tether (USDT)</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Destination Address
                  </label>
                  <input 
                    type="text"
                    placeholder="Enter wallet address or bank details"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    value={withdrawAddress}
                    onChange={(e) => setWithdrawAddress((e.target as HTMLInputElement).value)}
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Amount
                  </label>
                  <input 
                    type="number"
                    placeholder="0.00"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    value={withdrawAmount}
                    onChange={(e) => setWithdrawAmount((e.target as HTMLInputElement).value)}
                  />
                </div>
                
                <button className="w-full bg-red-600 hover:bg-red-700 text-white font-medium py-2 px-4 rounded-lg transition-colors">
                  Request Withdrawal
                </button>
              </div>
            </div>

            {/* Withdrawal Limits */}
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Withdrawal Limits</h3>
              
              <div className="space-y-4">
                <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-4">
                  <div className="flex items-start">
                    <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400 mr-3 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-red-800 dark:text-red-200">
                        Important Notice
                      </p>
                      <p className="text-xs text-red-600 dark:text-red-300 mt-1">
                        All withdrawals require 2FA verification and may take 24-48 hours to process.
                      </p>
                    </div>
                  </div>
                </div>
                
                <div className="space-y-3">
                  {withdrawalLimits ? (
                    <>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600 dark:text-gray-400">Daily Limit:</span>
                        <span className="text-gray-900 dark:text-white font-medium">
                          {withdrawalLimits.currency}{withdrawalLimits.dailyLimit.toLocaleString()}
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600 dark:text-gray-400">Monthly Limit:</span>
                        <span className="text-gray-900 dark:text-white font-medium">
                          {withdrawalLimits.currency}{withdrawalLimits.monthlyLimit.toLocaleString()}
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600 dark:text-gray-400">Minimum Amount:</span>
                        <span className="text-gray-900 dark:text-white font-medium">
                          {withdrawalLimits.currency}{withdrawalLimits.minimumAmount.toLocaleString()}
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600 dark:text-gray-400">Processing Fee:</span>
                        <span className="text-gray-900 dark:text-white font-medium">
                          {withdrawalLimits.currency}{withdrawalLimits.processingFee} + network fees
                        </span>
                      </div>
                    </>
                  ) : (
                    <div className="flex items-center justify-center py-4">
                      {limitsLoading ? (
                        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                      ) : (
                        <div className="text-red-600 dark:text-red-400 text-sm">
                          ❌ Unable to load withdrawal limits - no real data available
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* History Tab */}
      {activeTab === 'history' && (
        <div className="space-y-6">
          {/* Transaction Filters */}
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-2">
                  <Filter className="w-4 h-4 text-gray-500" />
                  <select 
                    className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    value={filter}
                    onChange={(e) => setFilter((e.target as HTMLSelectElement).value)}
                  >
                    <option value="all">All Transactions</option>
                    <option value="deposit">Deposits</option>
                    <option value="withdrawal">Withdrawals</option>
                    <option value="trade">Trades</option>
                    <option value="fee">Fees</option>
                  </select>
                </div>

                <div className="flex items-center space-x-2">
                  <Search className="w-4 h-4 text-gray-500" />
                  <input 
                    type="text"
                    placeholder="Search transactions..."
                    className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm((e.target as HTMLInputElement).value)}
                  />
                </div>
              </div>

              <button className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700 transition-colors flex items-center">
                <Download className="w-4 h-4 mr-2" />
                Export CSV
              </button>
            </div>
          </div>

          {/* Transaction History */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
                <Clock className="w-5 h-5 mr-2" />
                Transaction History ({filteredTransactions.length})
              </h3>
            </div>

            {filteredTransactions.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 dark:bg-gray-700">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Type</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Currency</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Amount</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">USD Value</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Status</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Date</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                    {filteredTransactions.map((transaction) => (
                      <tr key={transaction.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            {getTypeIcon(transaction.type)}
                            <span className="ml-2 text-sm font-medium text-gray-900 dark:text-white capitalize">
                              {transaction.type}
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-300">
                          {transaction.currency}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-300">
                          {showValues ? transaction.amount.toFixed(8) : '••••••'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-300">
                          {showValues ? `$${transaction.usdValue.toLocaleString()}` : '••••••'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(transaction.status)}`}>
                            {transaction.status.toUpperCase()}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-300">
                          {new Date(transaction.timestamp).toLocaleDateString()}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                          <div className="flex items-center space-x-2">
                            {transaction.txHash && (
                              <button
                                onClick={() => copyToClipboard(transaction.txHash!)}
                                className="text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300"
                              >
                                <Copy className="w-4 h-4" />
                              </button>
                            )}
                            <button className="text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-300">
                              <ExternalLink className="w-4 h-4" />
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
                <Clock className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">No Transactions Found</h3>
                <p className="text-gray-500 dark:text-gray-400">
                  {filter === 'all' ? 
                    'Transaction history will appear here after deposits, withdrawals, or trades' :
                    `No ${filter} transactions found`
                  }
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
} 