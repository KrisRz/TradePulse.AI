import { useState } from 'preact/hooks';
import { 
  Filter, 
  X, 
  Search, 
  TrendingUp, 
  Brain, 
  Clock,
  Save,
  Trash2,
  RotateCcw,
  Settings
} from 'lucide-preact';

interface SignalFiltersData {
  symbol: string;
  signalType: 'BUY' | 'SELL' | 'HOLD' | '';
  strategy: string;
  confidenceMin: number;
  confidenceMax: number;
  timeframe: '1h' | '4h' | '24h' | '';
  dateFrom: string;
  dateTo: string;
  minPnL: string;
  maxPnL: string;
  status: 'ACTIVE' | 'EXECUTED' | 'EXPIRED' | 'CANCELLED' | '';
  source: 'AI' | 'MANUAL' | '';
  priceMin: string;
  priceMax: string;
  volumeMin: string;
  volumeMax: string;
  searchTerm: string;
}

type SignalFilterDataValue = string | number;

interface FilterPreset {
  id: string;
  name: string;
  description: string;
  filters: SignalFiltersData;
  isDefault: boolean;
  createdAt: Date;
  usageCount: number;
}

interface SignalFiltersProps {
  initialFilters?: Partial<SignalFiltersData>;
  onFiltersChange?: (filters: SignalFiltersData) => void;
  onPresetSave?: (preset: FilterPreset) => void;
  onPresetLoad?: (preset: FilterPreset) => void;
  onReset?: () => void;
  showPresets?: boolean;
  showAdvanced?: boolean;
}

const defaultFilters: SignalFiltersData = {
  symbol: '',
  signalType: '',
  strategy: '',
  confidenceMin: 0,
  confidenceMax: 100,
  timeframe: '',
  dateFrom: '',
  dateTo: '',
  minPnL: '',
  maxPnL: '',
  status: '',
  source: '',
  priceMin: '',
  priceMax: '',
  volumeMin: '',
  volumeMax: '',
  searchTerm: ''
};

export default function SignalFilters({
  initialFilters = {},
  onFiltersChange,
  onPresetSave,
  onPresetLoad,
  onReset,
  showPresets = true,
  showAdvanced = true
}: SignalFiltersProps) {
  const [filters, setFilters] = useState<SignalFiltersData>({
    ...defaultFilters,
    ...initialFilters
  });
  
  const [presets, setPresets] = useState<FilterPreset[]>([]);
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [showPresetModal, setShowPresetModal] = useState(false);
  const [newPresetName, setNewPresetName] = useState('');
  const [newPresetDescription, setNewPresetDescription] = useState('');
  const [activeFiltersCount, setActiveFiltersCount] = useState(0);

  useEffect(() => {
    // Load saved presets from localStorage
    const savedPresets = localStorage.getItem('signalFilterPresets');
    if (savedPresets) {
      try {
        const parsedPresets = JSON.parse(savedPresets);
        setPresets(parsedPresets);
      } catch (error) {
        console.error('Failed to load filter presets:', error);
      }
    }

    // Initialize with default presets
    const defaultPresets: FilterPreset[] = [
      {
        id: 'high-confidence',
        name: 'High Confidence',
        description: 'Signals with confidence > 80%',
        filters: {
          ...defaultFilters,
          confidenceMin: 80,
          confidenceMax: 100
        },
        isDefault: true,
        createdAt: new Date(),
        usageCount: 0
      },
      {
        id: 'recent-signals',
        name: 'Recent Signals',
        description: 'Signals from the last 24 hours',
        filters: {
          ...defaultFilters,
          dateFrom: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString().split('T')[0],
          dateTo: new Date().toISOString().split('T')[0]
        },
        isDefault: true,
        createdAt: new Date(),
        usageCount: 0
      },
      {
        id: 'profitable-signals',
        name: 'Profitable Signals',
        description: 'Signals that resulted in profit',
        filters: {
          ...defaultFilters,
          minPnL: '0',
          status: 'EXECUTED'
        },
        isDefault: true,
        createdAt: new Date(),
        usageCount: 0
      },
      {
        id: 'ai-only',
        name: 'AI Only',
        description: 'AI-generated signals only',
        filters: {
          ...defaultFilters,
          source: 'AI'
        },
        isDefault: true,
        createdAt: new Date(),
        usageCount: 0
      }
    ];

    if (!savedPresets) {
      setPresets(defaultPresets);
      localStorage.setItem('signalFilterPresets', JSON.stringify(defaultPresets));
    }
  }, []);

  useEffect(() => {
    // Count active filters
    const count = Object.entries(filters).filter(([key, value]) => {
      if (key === 'confidenceMin' && value === 0) return false;
      if (key === 'confidenceMax' && value === 100) return false;
      return value !== '' && value !== null && value !== undefined;
    }).length;
    
    setActiveFiltersCount(count);
    
    // Notify parent component
    onFiltersChange?.(filters);
  }, [filters, onFiltersChange]);

  const handleFilterChange = (key: keyof SignalFiltersData, value: string | number) => {
    setFilters(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const handleReset = () => {
    setFilters(defaultFilters);
    onReset?.();
  };

  const handlePresetSave = () => {
    if (!newPresetName.trim()) return;

    const preset: FilterPreset = {
      id: Date.now().toString(),
      name: newPresetName,
      description: newPresetDescription,
      filters: { ...filters },
      isDefault: false,
      createdAt: new Date(),
      usageCount: 0
    };

    const updatedPresets = [...presets, preset];
    setPresets(updatedPresets);
    localStorage.setItem('signalFilterPresets', JSON.stringify(updatedPresets));
    
    onPresetSave?.(preset);
    setShowPresetModal(false);
    setNewPresetName('');
    setNewPresetDescription('');
  };

  const handlePresetLoad = (preset: FilterPreset) => {
    setFilters(preset.filters);
    
    // Update usage count
    const updatedPresets = presets.map(p => 
      p.id === preset.id 
        ? { ...p, usageCount: p.usageCount + 1 }
        : p
    );
    setPresets(updatedPresets);
    localStorage.setItem('signalFilterPresets', JSON.stringify(updatedPresets));
    
    onPresetLoad?.(preset);
  };

  const handlePresetDelete = (presetId: string) => {
    if (window.confirm('Are you sure you want to delete this preset?')) {
      const updatedPresets = presets.filter(p => p.id !== presetId);
      setPresets(updatedPresets);
      localStorage.setItem('signalFilterPresets', JSON.stringify(updatedPresets));
    }
  };

  const quickFilters = [
    {
      label: 'Active Signals',
      filters: { status: 'ACTIVE' as const },
      icon: TrendingUp,
      color: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
    },
    {
      label: 'High Confidence',
      filters: { confidenceMin: 80 },
      icon: Target,
      color: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
    },
    {
      label: 'AI Signals',
      filters: { source: 'AI' as const },
      icon: Brain,
      color: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200'
    },
    {
      label: 'Recent',
      filters: { dateFrom: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString().split('T')[0] },
      icon: Clock,
      color: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200'
    }
  ];

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <Filter className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Signal Filters
          </h3>
          {activeFiltersCount > 0 && (
            <span className="bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 text-xs font-medium px-2.5 py-0.5 rounded-full">
              {activeFiltersCount} active
            </span>
          )}
        </div>
        
        <div className="flex items-center space-x-2">
          {showAdvanced && (
            <button
              onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
              className="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
            >
              <Settings className="w-4 h-4 mr-1" />
              Advanced
            </button>
          )}
          
          <button
            onClick={handleReset}
            className="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
          >
            <RotateCcw className="w-4 h-4 mr-1" />
            Reset
          </button>
        </div>
      </div>

      {/* Quick Filters */}
      <div className="mb-6">
        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
          Quick Filters
        </h4>
        <div className="flex flex-wrap gap-2">
          {quickFilters.map((quickFilter, index) => {
            const IconComponent = quickFilter.icon;
            return (
              <button
                key={index}
                onClick={() => {
                  setFilters(prev => ({
                    ...prev,
                    ...quickFilter.filters
                  }));
                }}
                className={`flex items-center px-3 py-1 rounded-full text-sm font-medium transition-colors ${quickFilter.color}`}
              >
                <IconComponent className="w-4 h-4 mr-1" />
                {quickFilter.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Basic Filters */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {/* Search */}
        <div className="lg:col-span-2">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Search
          </label>
          <div className="relative">
            <input
              type="text"
              value={filters.searchTerm}
              onChange={(e) => handleFilterChange('searchTerm', e.currentTarget.value)}
              placeholder="Search signals, symbols, strategies..."
              className="w-full px-3 py-2 pl-10 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
            <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
          </div>
        </div>

        {/* Symbol */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Symbol
          </label>
          <input
            type="text"
            value={filters.symbol}
            onChange={(e) => handleFilterChange('symbol', e.currentTarget.value)}
            placeholder="BTCUSDT"
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          />
        </div>

        {/* Signal Type */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Signal Type
          </label>
          <select
            value={filters.signalType}
            onChange={(e) => handleFilterChange('signalType', e.currentTarget.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="">All Types</option>
            <option value="BUY">Buy</option>
            <option value="SELL">Sell</option>
            <option value="HOLD">Hold</option>
          </select>
        </div>

        {/* Strategy */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Strategy
          </label>
          <select
            value={filters.strategy}
            onChange={(e) => handleFilterChange('strategy', e.currentTarget.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="">All Strategies</option>
            <option value="AI_BREAKOUT">AI Breakout</option>
            <option value="AI_REVERSAL">AI Reversal</option>
            <option value="AI_MOMENTUM">AI Momentum</option>
            <option value="AI_TREND">AI Trend</option>
            <option value="MANUAL">Manual</option>
          </select>
        </div>

        {/* Confidence Range */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Confidence Range
          </label>
          <div className="flex space-x-2">
            <input
              type="number"
              min="0"
              max="100"
              value={filters.confidenceMin}
              onChange={(e) => handleFilterChange('confidenceMin', parseInt(e.currentTarget.value) || 0)}
              placeholder="Min"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
            <input
              type="number"
              min="0"
              max="100"
              value={filters.confidenceMax}
              onChange={(e) => handleFilterChange('confidenceMax', parseInt(e.currentTarget.value) || 100)}
              placeholder="Max"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>
        </div>

        {/* Status */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Status
          </label>
          <select
            value={filters.status}
            onChange={(e) => handleFilterChange('status', e.currentTarget.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="">All Status</option>
            <option value="ACTIVE">Active</option>
            <option value="EXECUTED">Executed</option>
            <option value="EXPIRED">Expired</option>
            <option value="CANCELLED">Cancelled</option>
          </select>
        </div>
      </div>

      {/* Advanced Filters */}
      {showAdvancedFilters && (
        <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">
            Advanced Filters
          </h4>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* Date Range */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Date From
              </label>
              <input
                type="date"
                value={filters.dateFrom}
                onChange={(e) => handleFilterChange('dateFrom', e.currentTarget.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Date To
              </label>
              <input
                type="date"
                value={filters.dateTo}
                onChange={(e) => handleFilterChange('dateTo', e.currentTarget.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>

            {/* Timeframe */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Timeframe
              </label>
              <select
                value={filters.timeframe}
                onChange={(e) => handleFilterChange('timeframe', e.currentTarget.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                <option value="">All Timeframes</option>
                <option value="1h">1 Hour</option>
                <option value="4h">4 Hours</option>
                <option value="24h">24 Hours</option>
              </select>
            </div>

            {/* P&L Range */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Min P&L
              </label>
              <input
                type="number"
                value={filters.minPnL}
                onChange={(e) => handleFilterChange('minPnL', e.currentTarget.value)}
                placeholder="0"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Max P&L
              </label>
              <input
                type="number"
                value={filters.maxPnL}
                onChange={(e) => handleFilterChange('maxPnL', e.currentTarget.value)}
                placeholder="1000"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>

            {/* Source */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Source
              </label>
              <select
                value={filters.source}
                onChange={(e) => handleFilterChange('source', e.currentTarget.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                <option value="">All Sources</option>
                <option value="AI">AI Generated</option>
                <option value="MANUAL">Manual</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Presets */}
      {showPresets && presets.length > 0 && (
        <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Saved Presets
            </h4>
            <button
              onClick={() => setShowPresetModal(true)}
              className="flex items-center px-3 py-1 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Save className="w-4 h-4 mr-1" />
              Save Current
            </button>
          </div>
          
          <div className="flex flex-wrap gap-2">
            {presets.map((preset) => (
              <div key={preset.id} className="flex items-center bg-gray-50 dark:bg-gray-700 rounded-lg p-2">
                <button
                  onClick={() => handlePresetLoad(preset)}
                  className="text-sm text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                >
                  {preset.name}
                </button>
                {!preset.isDefault && (
                  <button
                    onClick={() => handlePresetDelete(preset.id)}
                    className="ml-2 text-gray-400 hover:text-red-600 dark:hover:text-red-400 transition-colors"
                  >
                    <X className="w-3 h-3" />
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Save Preset Modal */}
      {showPresetModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Save Filter Preset
            </h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Preset Name
                </label>
                <input
                  type="text"
                  value={newPresetName}
                  onChange={(e) => setNewPresetName(e.currentTarget.value)}
                  placeholder="Enter preset name"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Description (Optional)
                </label>
                <textarea
                  value={newPresetDescription}
                  onChange={(e) => setNewPresetDescription(e.currentTarget.value)}
                  placeholder="Describe this filter preset"
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                />
              </div>
            </div>
            
            <div className="flex justify-end space-x-3 mt-6">
              <button
                onClick={() => setShowPresetModal(false)}
                className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handlePresetSave}
                disabled={!newPresetName.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Save Preset
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
} 