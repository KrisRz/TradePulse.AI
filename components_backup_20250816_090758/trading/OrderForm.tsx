import { useState, useEffect } from 'preact/hooks';
import { 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  Percent, 
  Shield, 
  AlertTriangle,
  Calculator,
  Clock,
  Target
} from 'lucide-preact';

interface OrderFormData {
  symbol: string;
  side: 'BUY' | 'SELL';
  type: 'MARKET' | 'LIMIT' | 'STOP' | 'STOP_LIMIT';
  quantity: number;
  price?: number;
  stopPrice?: number;
  timeInForce: 'GTC' | 'IOC' | 'FOK' | 'GTT';
  reduceOnly: boolean;
  postOnly: boolean;
  clientOrderId?: string;
}

interface OrderFormProps {
  symbol?: string;
  initialSide?: 'BUY' | 'SELL';
  maxBalance?: number;
  currentPrice?: number;
  onSubmit?: (order: OrderFormData) => void;
  onCancel?: () => void;
  disabled?: boolean;
}

export default function OrderForm({
  symbol = 'BTCUSDT',
  initialSide = 'BUY',
  maxBalance = 10000,
  currentPrice = 65000,
  onSubmit,
  onCancel,
  disabled = false
}: OrderFormProps) {
  const [formData, setFormData] = useState<OrderFormData>({
    symbol,
    side: initialSide,
    type: 'MARKET',
    quantity: 0,
    price: currentPrice,
    stopPrice: undefined,
    timeInForce: 'GTC',
    reduceOnly: false,
    postOnly: false,
    clientOrderId: undefined
  });

  const [errors, setErrors] = useState<Partial<Record<keyof OrderFormData, string>>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [estimatedCost, setEstimatedCost] = useState(0);
  const [estimatedFees, setEstimatedFees] = useState(0);

  // Calculate estimated cost and fees
  useEffect(() => {
    const price = formData.type === 'MARKET' ? currentPrice : (formData.price || currentPrice);
    const cost = formData.quantity * price;
    const fees = cost * 0.001; // 0.1% trading fee
    
    setEstimatedCost(cost);
    setEstimatedFees(fees);
  }, [formData.quantity, formData.price, formData.type, currentPrice]);

  const handleInputChange = (field: keyof OrderFormData, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));

    // Clear error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({
        ...prev,
        [field]: undefined
      }));
    }
  };

  const validateForm = (): boolean => {
    const newErrors: Partial<Record<keyof OrderFormData, string>> = {};

    if (!formData.quantity || formData.quantity <= 0) {
      newErrors.quantity = 'Quantity must be greater than 0';
    }

    if (formData.type === 'LIMIT' && (!formData.price || formData.price <= 0)) {
      newErrors.price = 'Price must be greater than 0';
    }

    if (formData.type === 'STOP' && (!formData.stopPrice || formData.stopPrice <= 0)) {
      newErrors.stopPrice = 'Stop price must be greater than 0';
    }

    if (formData.type === 'STOP_LIMIT') {
      if (!formData.price || formData.price <= 0) {
        newErrors.price = 'Price must be greater than 0';
      }
      if (!formData.stopPrice || formData.stopPrice <= 0) {
        newErrors.stopPrice = 'Stop price must be greater than 0';
      }
    }

    // Check if user has enough balance
    if (formData.side === 'BUY' && (estimatedCost + estimatedFees) > maxBalance) {
      newErrors.quantity = 'Insufficient balance';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: Event) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);
    
    try {
      await onSubmit?.(formData);
      
      // Reset form after successful submission
      setFormData({
        symbol,
        side: initialSide,
        type: 'MARKET',
        quantity: 0,
        price: currentPrice,
        stopPrice: undefined,
        timeInForce: 'GTC',
        reduceOnly: false,
        postOnly: false,
        clientOrderId: undefined
      });
    } catch (error) {
      console.error('Order submission failed:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleQuickAmount = (percentage: number) => {
    const maxQuantity = formData.side === 'BUY' 
      ? (maxBalance * 0.99) / currentPrice // 99% to account for fees
      : maxBalance / currentPrice;
    
    const quantity = (maxQuantity * percentage) / 100;
    handleInputChange('quantity', Math.floor(quantity * 100000) / 100000); // 5 decimal places
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Order Side */}
      <div className="grid grid-cols-2 gap-3">
        <button
          type="button"
          onClick={() => handleInputChange('side', 'BUY')}
          className={`flex items-center justify-center py-3 px-4 rounded-lg font-medium transition-all ${
            formData.side === 'BUY'
              ? 'bg-green-500 text-white shadow-lg shadow-green-500/25'
              : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
          }`}
          disabled={disabled}
        >
          <TrendingUp className="w-4 h-4 mr-2" />
          BUY
        </button>
        <button
          type="button"
          onClick={() => handleInputChange('side', 'SELL')}
          className={`flex items-center justify-center py-3 px-4 rounded-lg font-medium transition-all ${
            formData.side === 'SELL'
              ? 'bg-red-500 text-white shadow-lg shadow-red-500/25'
              : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
          }`}
          disabled={disabled}
        >
          <TrendingDown className="w-4 h-4 mr-2" />
          SELL
        </button>
      </div>

      {/* Order Type */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Order Type
        </label>
        <select
          value={formData.type}
          onChange={(e) => handleInputChange('type', e.currentTarget.value)}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          disabled={disabled}
        >
          <option value="MARKET">Market</option>
          <option value="LIMIT">Limit</option>
          <option value="STOP">Stop</option>
          <option value="STOP_LIMIT">Stop Limit</option>
        </select>
      </div>

      {/* Quantity */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Quantity (BTC)
        </label>
        <div className="relative">
          <input
            type="number"
            step="0.00001"
            value={formData.quantity}
            onChange={(e) => handleInputChange('quantity', parseFloat(e.currentTarget.value) || 0)}
            className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white ${
              errors.quantity ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
            }`}
            placeholder="0.00000"
            disabled={disabled}
          />
          <Calculator className="absolute right-3 top-2.5 w-4 h-4 text-gray-400" />
        </div>
        {errors.quantity && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.quantity}</p>
        )}
        
        {/* Quick Amount Buttons */}
        <div className="flex space-x-2 mt-2">
          {[25, 50, 75, 100].map((percentage) => (
            <button
              key={percentage}
              type="button"
              onClick={() => handleQuickAmount(percentage)}
              className="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
              disabled={disabled}
            >
              {percentage}%
            </button>
          ))}
        </div>
      </div>

      {/* Price (for LIMIT orders) */}
      {(formData.type === 'LIMIT' || formData.type === 'STOP_LIMIT') && (
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Price (USDT)
          </label>
          <div className="relative">
            <input
              type="number"
              step="0.01"
              value={formData.price}
              onChange={(e) => handleInputChange('price', parseFloat(e.currentTarget.value) || 0)}
              className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white ${
                errors.price ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
              }`}
              placeholder="0.00"
              disabled={disabled}
            />
            <DollarSign className="absolute right-3 top-2.5 w-4 h-4 text-gray-400" />
          </div>
          {errors.price && (
            <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.price}</p>
          )}
        </div>
      )}

      {/* Stop Price (for STOP orders) */}
      {(formData.type === 'STOP' || formData.type === 'STOP_LIMIT') && (
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Stop Price (USDT)
          </label>
          <div className="relative">
            <input
              type="number"
              step="0.01"
              value={formData.stopPrice}
              onChange={(e) => handleInputChange('stopPrice', parseFloat(e.currentTarget.value) || 0)}
              className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white ${
                errors.stopPrice ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
              }`}
              placeholder="0.00"
              disabled={disabled}
            />
            <Target className="absolute right-3 top-2.5 w-4 h-4 text-gray-400" />
          </div>
          {errors.stopPrice && (
            <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.stopPrice}</p>
          )}
        </div>
      )}

      {/* Time in Force */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Time in Force
        </label>
        <select
          value={formData.timeInForce}
          onChange={(e) => handleInputChange('timeInForce', e.currentTarget.value)}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          disabled={disabled}
        >
          <option value="GTC">Good Till Canceled</option>
          <option value="IOC">Immediate or Cancel</option>
          <option value="FOK">Fill or Kill</option>
          <option value="GTT">Good Till Time</option>
        </select>
      </div>

      {/* Advanced Options */}
      <div className="space-y-3">
        <div className="flex items-center">
          <input
            type="checkbox"
            id="reduceOnly"
            checked={formData.reduceOnly}
            onChange={(e) => handleInputChange('reduceOnly', e.currentTarget.checked)}
            className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500"
            disabled={disabled}
          />
          <label htmlFor="reduceOnly" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
            Reduce Only
          </label>
        </div>
        
        <div className="flex items-center">
          <input
            type="checkbox"
            id="postOnly"
            checked={formData.postOnly}
            onChange={(e) => handleInputChange('postOnly', e.currentTarget.checked)}
            className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500"
            disabled={disabled}
          />
          <label htmlFor="postOnly" className="ml-2 text-sm text-gray-700 dark:text-gray-300">
            Post Only
          </label>
        </div>
      </div>

      {/* Order Summary */}
      <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-gray-600 dark:text-gray-400">Estimated Cost:</span>
          <span className="font-medium text-gray-900 dark:text-white">
            ${estimatedCost.toFixed(2)}
          </span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-600 dark:text-gray-400">Estimated Fees:</span>
          <span className="font-medium text-gray-900 dark:text-white">
            ${estimatedFees.toFixed(2)}
          </span>
        </div>
        <div className="flex justify-between text-sm font-medium pt-2 border-t border-gray-200 dark:border-gray-700">
          <span className="text-gray-900 dark:text-white">Total:</span>
          <span className="text-gray-900 dark:text-white">
            ${(estimatedCost + estimatedFees).toFixed(2)}
          </span>
        </div>
      </div>

      {/* Submit Buttons */}
      <div className="flex space-x-3">
        <button
          type="submit"
          disabled={disabled || isSubmitting}
          className={`flex-1 py-3 px-4 rounded-lg font-medium transition-all ${
            formData.side === 'BUY'
              ? 'bg-green-500 hover:bg-green-600 text-white shadow-lg shadow-green-500/25'
              : 'bg-red-500 hover:bg-red-600 text-white shadow-lg shadow-red-500/25'
          } ${
            disabled || isSubmitting
              ? 'opacity-50 cursor-not-allowed'
              : 'transform hover:scale-105'
          }`}
        >
          {isSubmitting ? (
            <div className="flex items-center justify-center">
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
              Placing Order...
            </div>
          ) : (
            `${formData.side} ${formData.symbol}`
          )}
        </button>
        
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            disabled={disabled || isSubmitting}
            className="px-4 py-3 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Cancel
          </button>
        )}
      </div>
    </form>
  );
} 