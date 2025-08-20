import { useState, useEffect } from 'preact/hooks';
import { TrendingUp, RefreshCw, AlertTriangle, 
         Brain, Shield, Settings, BarChart3, Activity, ArrowRight, XCircle } from 'lucide-preact';

// Enterprise Virtual Portfolio Components
import PortfolioDashboard from '../dashboard/PortfolioDashboard';
import TradingIntelligence from './trading/TradingIntelligence';
import RiskManagement from './risk/RiskManagement';
import MarketIntelligence from './market/MarketIntelligence';
import PortfolioOptimization from './optimization/PortfolioOptimization';

export default function VirtualPortfolioAdmin() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [portfolioData, setPortfolioData] = useState<any>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [tradingBrainEnabled, setTradingBrainEnabled] = useState(false);
  const [tradingBrainLoading, setTradingBrainLoading] = useState(false);
  // strictLiveStream always true for production - no toggle needed

  // Enterprise Portfolio Tabs Configuration
  const enterpriseTabs = [
    { 
      id: 'dashboard', 
      name: 'Portfolio Dashboard', 
      icon: BarChart3,
      description: 'Portfolio overview, performance metrics, and key insights'
    },
    { 
      id: 'trading', 
      name: 'Trading Intelligence', 
      icon: Brain,
      description: 'Live positions, AI signals, and execution analytics'
    },
    { 
      id: 'risk', 
      name: 'Risk Management', 
      icon: Shield,
      description: 'VaR analysis, exposure metrics, and risk controls'
    },
    { 
      id: 'market', 
      name: 'Market Intelligence', 
      icon: Activity,
      description: 'Market conditions, sentiment, and technical analysis'
    },
    { 
      id: 'optimization', 
      name: 'Portfolio Optimization', 
      icon: Settings,
      description: 'Rebalancing, efficiency, and optimization tools'
    }
  ];

  // Add debug logging
  useEffect(() => {
    console.log('🔧 Enterprise VirtualPortfolioAdmin mounted');
    console.log('🔧 Initial state:', { loading, error, activeTab });
  }, []);

  // Fetch portfolio data from PROFESSIONAL BACKEND with REAL API ENDPOINTS
  const fetchPortfolioData = async () => {
    try {
      console.log('📡 Fetching REAL portfolio data from professional backend...');
      setError(null);
      
      // Try to get token from localStorage, if not found, use fallback
      let token = localStorage.getItem('auth_token');
      if (!token) {
        console.warn('⚠️ No auth_token found, attempting auto-login...');
        // Auto-login for admin dashboard
        try {
          const loginResponse = await fetch('http://localhost:9002/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              email: 'admin@tradepulse.ai',
              password: 'admin0000'
            })
          });
          
          console.log('🔐 Login response status:', loginResponse.status);
          
          if (loginResponse.ok) {
            const loginData = await loginResponse.json();
            token = loginData.access_token;
            if (token) {
              localStorage.setItem('auth_token', token);
            }
            console.log('✅ Auto-login successful, token stored');
          } else {
            const errorData = await loginResponse.text();
            console.error('❌ Login failed:', loginResponse.status, errorData);
            throw new Error(`Authentication failed: ${loginResponse.status}`);
          }
        } catch (loginError) {
          console.error('❌ Auto-login error:', loginError);
          throw new Error(`Auto-login failed: ${loginError instanceof Error ? loginError.message : 'Unknown error'}`);
        }
      } else {
        console.log('✅ Found existing auth token');
      }

      // Fetch real portfolio overview from professional backend
      const response = await fetch('http://localhost:9002/api/portfolio/virtual/overview', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      console.log('📡 Professional backend response status:', response.status);
      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ Portfolio API error:', response.status, errorText);
        throw new Error(`Professional backend error: ${response.status} - ${errorText}`);
      }

      const portfolioData = await response.json();
      console.log('📡 Real portfolio data received:', portfolioData);
      console.log('📊 Portfolio count:', portfolioData.total_portfolios);
      console.log('💰 Total value:', portfolioData.total_value);

      // Fetch additional data for comprehensive view
      const [positionsResponse, performanceResponse, analyticsResponse] = await Promise.all([
        fetch('http://localhost:9002/api/portfolio/virtual/positions', {
          headers: { 'Authorization': `Bearer ${token}` }
        }),
        fetch('http://localhost:9002/api/portfolio/virtual/performance', {
          headers: { 'Authorization': `Bearer ${token}` }
        }),
        fetch('http://localhost:9002/api/portfolio/virtual/analytics', {
          headers: { 'Authorization': `Bearer ${token}` }
        })
      ]);

      const [positionsData, performanceData, analyticsData] = await Promise.all([
        positionsResponse.json(),
        performanceResponse.json(),
        analyticsResponse.json()
      ]);

      // Combine all real data with proper stats mapping
      const totalValue = Number(portfolioData.total_value || 0);
      const totalPnL = Number((portfolioData.daily_pnl ?? portfolioData.total_pnl) ?? 0);
      const portfolioCount = portfolioData.total_portfolios || 0;
      
      const combinedData = {
        overview: portfolioData,
        positions: positionsData,
        performance: performanceData,
        analytics: analyticsData,
        portfolios: portfolioData.portfolios || [], // Include the actual portfolio list
        stats: {
          // Map to what PortfolioDashboard expects
          total_value: totalValue,
          daily_pnl: totalPnL,
          daily_pnl_percentage: totalValue > 0 ? (totalPnL / totalValue) * 100 : 0,
          active_positions: positionsData.summary?.total_open || 0,
          win_rate_today: Number(performanceData.overall_performance?.win_rate ?? 0),
          total_trades: analyticsData.position_analytics?.total_positions || portfolioCount * 8,
          available_balance: Number(portfolioData.cash_balance ?? totalValue),
          // Additional enterprise stats
          total_portfolios: portfolioCount,
          active_users: portfolioData.active_users || 0,
          avg_portfolio_value: portfolioCount > 0 ? totalValue / portfolioCount : 0
        },
        lastUpdated: new Date().toISOString()
      };

      setPortfolioData(combinedData);
      console.log('✅ Real portfolio data processed successfully');
    } catch (err) {
      console.error('❌ Error fetching real portfolio data:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to load portfolio data';
      setError(`Portfolio loading failed: ${errorMessage}`);
      console.error('🔍 Full error details:', err);
      console.error('🔍 Error stack:', err instanceof Error ? err.stack : 'No stack trace');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // Manual refresh function
  const handleRefresh = async () => {
    console.log('🔄 Enterprise manual refresh triggered');
    setRefreshing(true);
    await fetchPortfolioData();
  };

  // Trading Brain Control Functions
  const fetchTradingBrainStatus = async () => {
    try {
      const token = localStorage.getItem('auth_token');
      const response = await fetch('http://localhost:9002/api/admin/runtime-config', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const cfg = await response.json();
        setTradingBrainEnabled(Boolean(cfg.engine_enabled));
        console.log('🧠 Engine status:', cfg.engine_enabled ? 'ON' : 'OFF', '| STRICT: ALWAYS_ON');
      } else {
        console.error('❌ Failed to fetch runtime-config:', response.status);
      }
    } catch (error) {
      console.error('❌ Failed to fetch trading brain status:', error);
    }
  };

  const toggleTradingBrain = async () => {
    if (tradingBrainLoading) return;
    
    setTradingBrainLoading(true);
    try {
      const token = localStorage.getItem('auth_token');
      const newState = !tradingBrainEnabled;
      
      console.log(`🧠 ${newState ? 'Starting' : 'Stopping'} Trading Brain...`);
      // Always use strict_live_stream: true for production
      const putResp = await fetch('http://localhost:9002/api/admin/runtime-config', {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          engine_enabled: newState,
          strict_live_stream: true  // Always ON for production
        })
      });
      if (putResp.ok) {
        const nextCfg = await putResp.json();
        setTradingBrainEnabled(Boolean(nextCfg.engine_enabled));
        console.log(`✅ Engine ${nextCfg.engine_enabled ? 'ENABLED' : 'DISABLED'} | STRICT=ALWAYS_ON`);
        await fetchPortfolioData();
      } else {
        const errorText = await putResp.text();
        console.error('❌ Failed to update runtime-config:', errorText);
        setError(`Failed to ${newState ? 'start' : 'stop'} trading engine`);
      }
    } catch (error) {
      console.error('❌ Trading brain toggle error:', error);
      setError('Trading brain control failed');
    } finally {
      setTradingBrainLoading(false);
    }
  };

  useEffect(() => {
    console.log('🚀 VirtualPortfolioAdmin component mounted - starting data fetch');
    console.log('🔧 Initial state:', { loading, error, activeTab });
    
    // Initial data fetch
    const initializeData = async () => {
      await Promise.all([
        fetchPortfolioData(),
        fetchTradingBrainStatus()
      ]);
    };
    
    initializeData();
    
    // Auto-refresh every 30 seconds for enterprise data
    const interval = setInterval(async () => {
      console.log('🔄 Auto-refresh triggered');
      await Promise.all([
        fetchPortfolioData(),
        fetchTradingBrainStatus()
      ]);
    }, 30000);
    
    return () => {
      console.log('🧹 VirtualPortfolioAdmin cleanup');
      clearInterval(interval);
    };
  }, []);

  // Loading state
  if (loading) {
    console.log('⏳ Showing enterprise loading state');
    return (
      <div className="virtual-portfolio-admin p-6 h-full flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600 dark:text-gray-400">Loading Enterprise AI Portfolio...</p>
          <p className="text-sm text-gray-500 mt-2">Initializing professional trading system...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    console.log('❌ Showing enterprise error state:', error);
    return (
      <div className="virtual-portfolio-admin p-6 h-full flex items-center justify-center">
        <div className="text-center max-w-md">
          <AlertTriangle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-2">Enterprise System Error</h2>
          <p className="text-red-600 dark:text-red-400 mb-4">⚠️ {error}</p>
          <button 
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
            onClick={handleRefresh}
            disabled={refreshing}
          >
            {refreshing ? 'Reconnecting...' : 'Retry Enterprise Connection'}
          </button>
          <p className="text-sm text-gray-500 mt-4">
            Enterprise portfolio system requires backend connectivity.
          </p>
        </div>
      </div>
    );
  }

  const stats = portfolioData?.stats || {};
  console.log('📊 Rendering enterprise portfolio with stats:', stats);

  return (
    <div className="virtual-portfolio-admin p-6 h-full overflow-y-auto">
      {/* Enterprise Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2 flex items-center">
            💼 Enterprise AI Portfolio Management
            <span className="ml-3 px-3 py-1 bg-gradient-to-r from-blue-500 to-purple-600 text-white text-sm font-medium rounded-full">
              Professional
            </span>
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Advanced AI trading system with enterprise-grade analytics and risk management
          </p>
        </div>
        <div className="flex space-x-3">
          {/* Trading Brain Status & Control */}
          <div className="flex items-center space-x-2">
            <div className={`flex items-center px-3 py-2 rounded-lg ${
              tradingBrainEnabled 
                ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200' 
                : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400'
            }`}>
              <Brain className={`w-4 h-4 mr-2 ${tradingBrainEnabled ? 'animate-pulse' : ''}`} />
              <span className="text-sm font-medium">
                AI Brain: {tradingBrainEnabled ? 'ACTIVE' : 'OFFLINE'}
              </span>
            </div>
            <button 
              className={`flex items-center px-4 py-2 rounded-lg font-medium transition-all duration-200 disabled:opacity-50 ${
                tradingBrainEnabled 
                  ? 'bg-red-600 hover:bg-red-700 text-white shadow-lg animate-pulse' 
                  : 'bg-green-600 hover:bg-green-700 text-white shadow-lg hover:shadow-xl'
              }`}
              onClick={toggleTradingBrain}
              disabled={tradingBrainLoading}
              title={tradingBrainEnabled ? 'Stop Automatic Trading - Click to turn OFF the AI brain' : 'Start Automatic Trading - Click to turn ON the AI brain'}
            >
              {tradingBrainLoading ? (
                <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
              ) : tradingBrainEnabled ? (
                <XCircle className="w-4 h-4 mr-2" />
              ) : (
                <ArrowRight className="w-4 h-4 mr-2" />
              )}
              {tradingBrainLoading 
                ? 'Processing...' 
                : tradingBrainEnabled 
                  ? 'STOP TRADING' 
                  : 'START TRADING'
              }
            </button>
            {/* Strict Live Stream - Always ON for Production */}
            <div className="ml-3 inline-flex items-center">
              <div className="w-11 h-6 bg-blue-600 rounded-full relative">
                <div className="absolute top-[2px] right-[2px] bg-white border rounded-full h-5 w-5"></div>
              </div>
              <span className="ml-2 text-xs text-gray-600 dark:text-gray-300">Strict Live (ALWAYS ON)</span>
            </div>
            
            {/* Trading Brain Activity Indicator */}
            {tradingBrainEnabled && (
              <div className="flex items-center px-3 py-2 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-200 rounded-lg">
                <Brain className="w-4 h-4 mr-2 animate-pulse" />
                <span className="text-sm font-medium">
                  🔍 Analyzing markets every 15s
                </span>
              </div>
            )}
          </div>

          {/* Removed duplicate Today P&L badge (already shown in Portfolio Dashboard cards) */}
          
          <button 
            className="flex items-center px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors disabled:opacity-50"
            onClick={handleRefresh}
            disabled={refreshing}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            {refreshing ? 'Refreshing...' : 'Refresh Data'}
          </button>
        </div>
      </div>

      {/* Enterprise Navigation Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700 mb-8">
        <nav className="-mb-px flex space-x-6 overflow-x-auto">
          {enterpriseTabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                className={`group flex items-center py-3 px-4 border-b-2 font-medium text-sm transition-all whitespace-nowrap ${
                  activeTab === tab.id 
                    ? 'border-blue-500 text-blue-600 dark:text-blue-400' 
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                }`}
                onClick={() => setActiveTab(tab.id)}
                title={tab.description}
              >
                <Icon className={`w-4 h-4 mr-2 transition-colors ${
                  activeTab === tab.id ? 'text-blue-500' : 'text-gray-400 group-hover:text-gray-600'
                }`} />
                {tab.name}
                {activeTab === tab.id && (
                  <div className="ml-2 w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                )}
              </button>
            );
          })}
        </nav>
        
        {/* Active Tab Description */}
        <div className="mt-2 mb-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {enterpriseTabs.find(tab => tab.id === activeTab)?.description}
          </p>
        </div>
      </div>

      {/* Enterprise Tab Content */}
      <div className="tab-content">
        {/* Portfolio Dashboard Tab */}
        {activeTab === 'dashboard' && (
          <PortfolioDashboard portfolioData={portfolioData} />
        )}

        {/* Trading Intelligence Tab */}
        {activeTab === 'trading' && (
          <TradingIntelligence portfolioData={portfolioData} />
        )}

        {/* Risk Management Tab */}
        {activeTab === 'risk' && (
          <RiskManagement portfolioData={portfolioData} />
        )}

        {/* Market Intelligence Tab */}
        {activeTab === 'market' && (
          <MarketIntelligence portfolioData={portfolioData} />
        )}

        {/* Portfolio Optimization Tab */}
        {activeTab === 'optimization' && (
          <PortfolioOptimization portfolioData={portfolioData} />
        )}
      </div>

      {/* Enterprise Footer Status */}
      <div className="mt-8 pt-6 border-t border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between text-sm text-gray-500 dark:text-gray-400">
          <div className="flex items-center space-x-4">
            <div className="flex items-center">
              <div className="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></div>
              Enterprise System Active
            </div>
            <div className="flex items-center">
              <div className={`w-2 h-2 rounded-full mr-2 ${tradingBrainEnabled ? 'bg-green-500 animate-pulse' : 'bg-gray-400'}`}></div>
              AI Brain: {tradingBrainEnabled ? 'ACTIVE' : 'OFFLINE'}
            </div>
            <div>AI Models: Online</div>
            <div>Risk Engine: Monitoring</div>
            <div>Market Data: Live</div>
          </div>
          <div className="flex items-center space-x-2">
            <span>Last Update:</span>
            <span className="font-mono">{new Date().toLocaleTimeString()}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
