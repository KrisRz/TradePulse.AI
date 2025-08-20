import React, { useState, useEffect } from 'react';

interface PriceData {
  timestamp: string;
  price: number;
}

interface SimpleBitcoinChartProps {
  height?: number;
  className?: string;
  showDetails?: boolean;
}

export default function SimpleBitcoinChart({ 
  height = 200, 
  className = "",
  showDetails = true 
}: SimpleBitcoinChartProps) {
  const [currentPrice, setCurrentPrice] = useState<number>(0);
  const [priceHistory, setPriceHistory] = useState<PriceData[]>([]);
  const [priceChange, setPriceChange] = useState<number>(0);
  const [priceChangePercent, setPriceChangePercent] = useState<number>(0);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Generate mock price data for demonstration
    const generateMockData = () => {
      const basePrice = 48000;
      const data: PriceData[] = [];
      const now = new Date();
      
      for (let i = 23; i >= 0; i--) {
        const timestamp = new Date(now.getTime() - i * 60 * 60 * 1000).toISOString();
        const volatility = (Math.random() - 0.5) * 2000; // ±$1000 volatility
        const price = basePrice + volatility + (Math.random() > 0.6 ? 500 : -300);
        data.push({ timestamp, price });
      }
      
      return data;
    };

    const mockData = generateMockData();
    setPriceHistory(mockData);
    
    if (mockData.length > 0) {
      const latest = mockData[mockData.length - 1];
      const previous = mockData[mockData.length - 2];
      
      setCurrentPrice(latest.price);
      const change = latest.price - previous.price;
      setPriceChange(change);
      setPriceChangePercent((change / previous.price) * 100);
    }
    
    setIsLoading(false);

    // Real-time price updates
    const fetchPrice = async () => {
      try {
        const response = await fetch('/api/live/bitcoin-price');
        if (response.ok) {
          const data = await response.json();
          const newPrice = parseFloat(data.price);
          
          // Update current price
          setCurrentPrice(newPrice);
          
          // Add to history (keep last 24 hours)
          setPriceHistory(prev => {
            const newEntry = {
              timestamp: new Date().toISOString(),
              price: newPrice
            };
            const updated = [...prev, newEntry].slice(-24);
            
            // Calculate price change
            if (updated.length >= 2) {
              const change = newPrice - updated[updated.length - 2].price;
              setPriceChange(change);
              setPriceChangePercent((change / updated[updated.length - 2].price) * 100);
            }
            
            return updated;
          });
        }
      } catch (error) {
        console.error('Failed to fetch Bitcoin price:', error);
      }
    };

    // Update every 30 seconds
    const interval = setInterval(fetchPrice, 30000);
    
    // Initial fetch
    fetchPrice();

    return () => clearInterval(interval);
  }, []);

  const createSVGPath = () => {
    if (priceHistory.length < 2) return '';
    
    const width = 400;
    const chartHeight = height - 40;
    
    const prices = priceHistory.map(d => d.price);
    const minPrice = Math.min(...prices);
    const maxPrice = Math.max(...prices);
    const priceRange = maxPrice - minPrice;
    
    if (priceRange === 0) return '';
    
    const points = priceHistory.map((d, i) => {
      const x = (i / (priceHistory.length - 1)) * width;
      const y = chartHeight - ((d.price - minPrice) / priceRange) * chartHeight;
      return `${x},${y}`;
    });
    
    return `M ${points.join(' L ')}`;
  };

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(price);
  };

  if (isLoading) {
    return (
      <div className={`bg-white rounded-lg border border-gray-200 p-6 ${className}`}>
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="h-8 bg-gray-200 rounded w-1/2 mb-4"></div>
          <div className={`bg-gray-200 rounded`} style={{ height: height }}></div>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-lg border border-gray-200 p-6 ${className}`}>
      {showDetails && (
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Bitcoin Price</h3>
          <div className="flex items-center gap-4">
            <span className="text-2xl font-bold text-gray-900">
              {formatPrice(currentPrice)}
            </span>
            <span className={`text-sm font-medium px-2 py-1 rounded ${
              priceChange >= 0 
                ? 'text-green-700 bg-green-100' 
                : 'text-red-700 bg-red-100'
            }`}>
              {priceChange >= 0 ? '+' : ''}{formatPrice(priceChange)} ({priceChangePercent.toFixed(2)}%)
            </span>
          </div>
        </div>
      )}
      
      <div className="relative" style={{ height: height }}>
        <svg
          width="100%"
          height={height}
          viewBox={`0 0 400 ${height}`}
          className="overflow-visible"
        >
          {/* Grid lines */}
          <defs>
            <pattern id="grid" width="40" height="20" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 20" fill="none" stroke="#f3f4f6" strokeWidth="1"/>
            </pattern>
          </defs>
          <rect width="400" height={height} fill="url(#grid)" />
          
          {/* Price line */}
          <path
            d={createSVGPath()}
            fill="none"
            stroke={priceChange >= 0 ? "#10b981" : "#ef4444"}
            strokeWidth="2"
            className="drop-shadow-sm"
          />
          
          {/* Price dots */}
          {priceHistory.map((d, i) => {
            const x = (i / (priceHistory.length - 1)) * 400;
            const prices = priceHistory.map(p => p.price);
            const minPrice = Math.min(...prices);
            const maxPrice = Math.max(...prices);
            const priceRange = maxPrice - minPrice;
            const y = priceRange === 0 ? height / 2 : 
              (height - 40) - ((d.price - minPrice) / priceRange) * (height - 40);
            
            return (
              <circle
                key={i}
                cx={x}
                cy={y}
                r="3"
                fill={priceChange >= 0 ? "#10b981" : "#ef4444"}
                className="opacity-60 hover:opacity-100 transition-opacity"
              />
            );
          })}
          
          {/* Current price indicator */}
          {priceHistory.length > 0 && (
            <g>
              <circle
                cx={400}
                cy={(() => {
                  const prices = priceHistory.map(p => p.price);
                  const minPrice = Math.min(...prices);
                  const maxPrice = Math.max(...prices);
                  const priceRange = maxPrice - minPrice;
                  return priceRange === 0 ? height / 2 : 
                    (height - 40) - ((currentPrice - minPrice) / priceRange) * (height - 40);
                })()}
                r="4"
                fill={priceChange >= 0 ? "#10b981" : "#ef4444"}
                className="animate-pulse"
              />
            </g>
          )}
        </svg>
        
        {/* Time labels */}
        <div className="absolute bottom-0 left-0 right-0 flex justify-between text-xs text-gray-500 mt-2">
          <span>24h ago</span>
          <span>12h ago</span>
          <span>Now</span>
        </div>
      </div>
    </div>
  );
} 