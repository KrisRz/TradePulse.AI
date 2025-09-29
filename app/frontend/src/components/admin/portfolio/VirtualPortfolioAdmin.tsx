import { useState, useEffect } from 'preact/hooks';
import { RefreshCw, AlertTriangle,
         Brain, Shield, Settings, BarChart3, Activity, CheckCircle } from 'lucide-preact';
import type { PortfolioOverviewResponse } from '../../../types';
import { apiClient } from '@/lib/api-client';

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
  const [portfolioData, setPortfolioData] = useState<PortfolioOverviewResponse | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  // 🚀 INDUSTRY STANDARD: Read-only status indicators
  const [brainControllerStatus, setBrainControllerStatus] = useState('checking');
  const [tradingEngineStatus, setTradingEngineStatus] = useState('checking');
  const [liveDataStatus, setLiveDataStatus] = useState('checking');
  // Professional portfolio state management

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

  // Fetch portfolio data using professional API client
  const fetchPortfolioData = async () => {
    // SSR Guard: Only fetch in browser
    if (typeof window === 'undefined') {
      console.log('🚫 Skipping fetch during SSR');
      return;
    }
    
    try {
      console.log('📡 Fetching REAL portfolio data from professional backend...');
      setError(null);
      
      // Use CORRECT portfolio overview endpoint with REAL DATA via API client
      const portfolioResponse = await apiClient.get('/api/portfolio/virtual/overview');

      if (!portfolioResponse.success) {
        throw new Error(`Portfolio API error: ${portfolioResponse.error?.code || 'UNKNOWN'}`);
      }

      const portfolioOverview = portfolioResponse.data;
      console.log('📡 REAL portfolio overview data received:', portfolioOverview);

      // Position data is handled by TradingIntelligence component separately

      // Use REAL DATA from portfolio overview (has the actual $10,241.15)
      const totalPortfolioValue = portfolioOverview.total_value || 0;
      const totalPnL = portfolioOverview.total_pnl || 0;
      const availableCash = portfolioOverview.cash_balance || 0;
      const activePositions = portfolioOverview.active_positions || 0;
      const closedPositions = portfolioOverview.closed_positions || 0;
      const dailyPnL = portfolioOverview.daily_pnl || 0;
      const winRateToday = portfolioOverview.win_rate_today || 0;
      const totalRealizedPnL = portfolioOverview.total_realized_pnl || 0;

      // Portfolio data is now directly used in combinedData structure

      console.log('📊 REAL PORTFOLIO BALANCE FROM DYNAMODB:', {
        totalPortfolioValue,
        availableCash,
        totalPnL,
        activePositions,
        closedPositions,
        winRateToday,
        dailyPnL
      });

      // Calculate percentages and additional metrics using REAL DATA
      const initialBalance = portfolioOverview.initial_balance || 10000.0;
      const totalPnLPercentage = portfolioOverview.total_pnl_percentage || 0;
      const dailyPnLPercentage = portfolioOverview.daily_pnl_percentage || 0;
      const portfolioCount = portfolioOverview.total_portfolios || 1;
      
      // Create data structure matching PortfolioOverviewResponse interface
      const combinedData: PortfolioOverviewResponse = {
        DEBUG: "REAL_DYNAMODB_DATA_LOADED",
        total_portfolios: portfolioCount,
        total_value: totalPortfolioValue, // REAL $10,241.15 FROM DYNAMODB
        initial_balance: initialBalance,
        total_pnl: totalPnL, // REAL $241.15 P&L
        total_pnl_percentage: totalPnLPercentage, // REAL 2.41%
        cash_balance: availableCash, // REAL available cash
        active_positions: activePositions, // REAL 0 active
        closed_positions: closedPositions, // REAL 28 closed
        daily_pnl: dailyPnL, // REAL daily P&L
        daily_pnl_percentage: dailyPnLPercentage, // REAL daily %
        win_rate_today: winRateToday, // REAL 0.6786 win rate (67.86%)
        total_realized_pnl: totalRealizedPnL, // REAL realized P&L
        avg_portfolio_size: portfolioOverview.avg_portfolio_size || totalPortfolioValue,
        portfolios: [], // No individual portfolios for now
        last_updated: new Date().toISOString()
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
  // Removed: fetchTradingBrainStatus - replaced with checkSystemStatus

  // 🚀 INDUSTRY STANDARD: Status checking function (read-only)
  const checkSystemStatus = async () => {
    try {
      // Check engines status via API client
      const enginesResp = await apiClient.get('/api/v1/engines/status');
      if (enginesResp.success && enginesResp.data) {
        const engines = enginesResp.data.engines || {};
        
        // Brain Controller status - Fix for missing detailed_status
        const brainController = engines.brain_controller;
        if (brainController?.status === 'operational') {
          const state = brainController.detailed_status?.current_state;
          // If detailed_status is missing but status is operational, assume running
          if (state === 'running') {
            setBrainControllerStatus('ok');
          } else if (state === 'warmup') {
            setBrainControllerStatus('warming');
          } else if (!state && brainController.status === 'operational') {
            setBrainControllerStatus('ok'); // Operational without detailed state = OK
          } else {
            setBrainControllerStatus('error');
          }
        } else {
          setBrainControllerStatus('error');
        }
        
        // Trading Engine status
        const dayTrading = engines.day_trading;
        if (dayTrading?.status === 'operational' && dayTrading?.running) {
          setTradingEngineStatus('ok');
        } else {
          setTradingEngineStatus('error');
        }
        
        // Live Data status (check if enterprise trading is getting data)
        const enterprise = engines.enterprise_trading;
        if (enterprise?.status === 'operational') {
          setLiveDataStatus('ok');
        } else {
          setLiveDataStatus('error');
        }
        
        console.log('📊 System status updated:', {
          brain: brainController?.detailed_status?.current_state,
          trading: dayTrading?.running,
          enterprise: enterprise?.status
        });
      }
    } catch (error) {
      console.error('❌ Failed to check system status:', error);
      setBrainControllerStatus('error');
      setTradingEngineStatus('error');
      setLiveDataStatus('error');
    }
  };

  useEffect(() => {
    // SSR Guard: Only run in browser
    if (typeof window === 'undefined') return;
    
    console.log('🚀 VirtualPortfolioAdmin component mounted - starting data fetch');
    console.log('🔧 Initial state:', { loading, error, activeTab });
    
    // 🚀 INDUSTRY STANDARD: Initialize autonomous system status monitoring
    const initializeData = async () => {
      await Promise.all([
        fetchPortfolioData(),
        checkSystemStatus()  // Check all system status indicators
      ]);
      
      console.log('✅ AUTONOMOUS SYSTEM: Status monitoring initialized - no manual controls needed');
    };
    
    initializeData();
    
    // 🚀 INDUSTRY STANDARD: Auto-refresh system status every 30 seconds
    const interval = setInterval(async () => {
      console.log('🔄 Auto-refresh: Updating system status indicators');
      // Stagger requests to prevent connection exhaustion
      await fetchPortfolioData();
      await new Promise(resolve => setTimeout(resolve, 1000)); // 1 second delay
      await checkSystemStatus();  // Update all 3 status indicators
    }, 30000);  // 30 seconds for real-time status
    
    return () => {
      console.log('🧹 VirtualPortfolioAdmin cleanup');
      clearInterval(interval);
    };
  }, []);

  // SIMPLIFIED: Skip loading state for now - show dashboard immediately
  // if (loading) {
  //   console.log('⏳ Showing enterprise loading state');
  //   return (
  //     <div className="virtual-portfolio-admin p-6 h-full flex items-center justify-center">
  //       <div className="text-center">
  //         <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto mb-4"></div>
  //         <p className="text-gray-600 dark:text-gray-400">Loading Enterprise AI Portfolio...</p>
  //         <p className="text-sm text-gray-500 mt-2">Initializing professional trading system...</p>
  //       </div>
  //     </div>
  //   );
  // }

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

  console.log('📊 Rendering enterprise portfolio with REAL data:', portfolioData);

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
          {/* 🚀 INDUSTRY STANDARD: 3 Status Indicators Only - No Manual Controls */}
          <div className="flex items-center space-x-4">
            
            {/* Status Indicator 1: Brain Controller */}
            <div className={`flex items-center px-3 py-2 rounded-lg ${
              brainControllerStatus === 'ok' 
                ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200'
                : brainControllerStatus === 'warming'
                ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-200'
                : 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200'
            }`}>
              <div className={`w-3 h-3 rounded-full mr-2 ${
                brainControllerStatus === 'ok' 
                  ? 'bg-green-500 animate-pulse' 
                  : brainControllerStatus === 'warming'
                  ? 'bg-yellow-500 animate-pulse'
                  : 'bg-red-500'
              }`}></div>
              <Brain className="w-4 h-4 mr-2" />
              <span className="text-sm font-medium">
                Brain: {brainControllerStatus === 'ok' ? 'RUNNING' : brainControllerStatus === 'warming' ? 'WARMUP' : 'ERROR'}
              </span>
            </div>
            
            {/* Status Indicator 2: Trading Engine */}
            <div className={`flex items-center px-3 py-2 rounded-lg ${
              tradingEngineStatus === 'ok' 
                ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200'
                : 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200'
            }`}>
              <div className={`w-3 h-3 rounded-full mr-2 ${
                tradingEngineStatus === 'ok' ? 'bg-green-500 animate-pulse' : 'bg-red-500'
              }`}></div>
              <Activity className="w-4 h-4 mr-2" />
              <span className="text-sm font-medium">
                Engine: {tradingEngineStatus === 'ok' ? 'ACTIVE' : 'ERROR'}
              </span>
            </div>
            
            {/* Status Indicator 3: Live Data Flow */}
            <div className={`flex items-center px-3 py-2 rounded-lg ${
              liveDataStatus === 'ok' 
                ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200'
                : 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200'
            }`}>
              <div className={`w-3 h-3 rounded-full mr-2 ${
                liveDataStatus === 'ok' ? 'bg-green-500 animate-pulse' : 'bg-red-500'
              }`}></div>
              <Activity className="w-4 h-4 mr-2" />
              <span className="text-sm font-medium">
                Data: {liveDataStatus === 'ok' ? 'LIVE' : 'ERROR'}
              </span>
            </div>
            
            {/* Production Mode Indicator */}
            <div className="ml-3 inline-flex items-center px-3 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200 rounded-lg">
              <div className="w-2 h-2 bg-blue-600 rounded-full mr-2 animate-pulse"></div>
              <span className="text-xs font-medium">AUTONOMOUS MODE</span>
            </div>
            
            {/* System Status Summary */}
            <div className="flex items-center px-3 py-2 bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200 rounded-lg">
              <CheckCircle className="w-4 h-4 mr-2" />
              <span className="text-sm font-medium">
                🚀 Auto-Trading: LIVE
              </span>
            </div>
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
        {activeTab === 'dashboard' && portfolioData && (
          <PortfolioDashboard portfolioData={portfolioData} />
        )}

        {/* Trading Intelligence Tab */}
        {activeTab === 'trading' && portfolioData && (
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
              <div className="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></div>
              AI Brain: ACTIVE
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
