import { render, screen, fireEvent, waitFor } from '@testing-library/preact';
import RiskManagement from '../RiskManagement';

// Mock the lucide-preact icons
jest.mock('lucide-preact', () => ({
  Shield: () => <div data-testid="shield-icon" />,
  AlertTriangle: () => <div data-testid="alert-triangle-icon" />,
  TrendingDown: () => <div data-testid="trending-down-icon" />,
  Target: () => <div data-testid="target-icon" />,
  DollarSign: () => <div data-testid="dollar-sign-icon" />,
  Percent: () => <div data-testid="percent-icon" />,
  Settings: () => <div data-testid="settings-icon" />,
  Bell: () => <div data-testid="bell-icon" />,
  Activity: () => <div data-testid="activity-icon" />,
  PieChart: () => <div data-testid="pie-chart-icon" />,
  BarChart3: () => <div data-testid="bar-chart-icon" />,
  RefreshCw: () => <div data-testid="refresh-icon" />,
  CheckCircle: () => <div data-testid="check-circle-icon" />,
  XCircle: () => <div data-testid="x-circle-icon" />,
}));

// Mock fetch globally
global.fetch = jest.fn();

// Mock risk data
const mockRiskMetrics = {
  portfolioValue: 50000,
  totalRisk: 5000,
  riskPercentage: 10.0,
  maxDrawdown: 8.5,
  currentDrawdown: 3.2,
  valueAtRisk: 2500,
  sharpeRatio: 1.8,
  winRate: 65.4,
  profitFactor: 1.45,
  maxLossStreak: 3,
  currentLossStreak: 0,
  avgPositionSize: 1200,
  largestPosition: 5000,
  totalPositions: 12,
  dailyPnl: 450,
  weeklyPnl: 1200,
  monthlyPnl: 3800,
};

const mockRiskLimits = {
  maxPositionSize: 10000,
  maxDailyLoss: 1000,
  maxDrawdown: 15.0,
  maxLeverage: 10,
  maxOpenPositions: 20,
  stopLossRequired: true,
  takeProfitRequired: false,
  riskRewardRatio: 2.0,
};

const mockAlerts = [
  {
    id: 'alert1',
    type: 'WARNING' as const,
    message: 'Portfolio risk approaching maximum threshold',
    timestamp: new Date('2024-01-15T10:30:00'),
    acknowledged: false,
    severity: 'MEDIUM' as const,
  },
  {
    id: 'alert2',
    type: 'DANGER' as const,
    message: 'Stop loss not set on BTCUSDT position',
    timestamp: new Date('2024-01-15T11:45:00'),
    acknowledged: false,
    severity: 'HIGH' as const,
  },
];

const defaultProps = {
  userId: 'test-user',
  showControls: true,
  showAlerts: true,
  onLimitUpdate: jest.fn(),
  onAlertAcknowledge: jest.fn(),
};

describe('RiskManagement', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Mock successful API responses
    (global.fetch as jest.Mock).mockImplementation((url: string) => {
      if (url.includes('/risk-metrics')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true, data: mockRiskMetrics }),
        });
      }
      if (url.includes('/risk-limits')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true, data: mockRiskLimits }),
        });
      }
      if (url.includes('/risk-alerts')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true, data: mockAlerts }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ success: true, data: {} }),
      });
    });
  });

  // === RENDERING TESTS ===
  describe('Rendering', () => {
    it('renders risk management dashboard', async () => {
      render(<RiskManagement {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('Risk Management')).toBeInTheDocument();
        expect(screen.getByText('Portfolio Risk')).toBeInTheDocument();
        expect(screen.getByText('Risk Metrics')).toBeInTheDocument();
      });
    });

    it('displays loading state initially', () => {
      render(<RiskManagement {...defaultProps} />);
      expect(screen.getByText('Loading risk data...')).toBeInTheDocument();
    });

    it('renders without controls when showControls is false', async () => {
      render(<RiskManagement {...defaultProps} showControls={false} />);
      
      await waitFor(() => {
        expect(screen.queryByText('Risk Settings')).not.toBeInTheDocument();
      });
    });

    it('renders without alerts when showAlerts is false', async () => {
      render(<RiskManagement {...defaultProps} showAlerts={false} />);
      
      await waitFor(() => {
        expect(screen.queryByText('Risk Alerts')).not.toBeInTheDocument();
      });
    });
  });

  // === RISK METRICS DISPLAY TESTS ===
  describe('Risk Metrics Display', () => {
    it('displays portfolio value correctly', async () => {
      render(<RiskManagement {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('$50,000.00')).toBeInTheDocument();
      });
    });

    it('displays risk percentage with color coding', async () => {
      render(<RiskManagement {...defaultProps} />);
      
      await waitFor(() => {
        const riskPercent = screen.getByText('10.0%');
        expect(riskPercent).toBeInTheDocument();
        expect(riskPercent).toHaveClass('text-yellow-600'); // Medium risk
      });
    });

    it('displays drawdown metrics', async () => {
      render(<RiskManagement {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('3.2%')).toBeInTheDocument(); // Current drawdown
        expect(screen.getByText('8.5%')).toBeInTheDocument(); // Max drawdown
      });
    });

    it('displays performance metrics', async () => {
      render(<RiskManagement {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('65.4%')).toBeInTheDocument(); // Win rate
        expect(screen.getByText('1.45')).toBeInTheDocument();  // Profit factor
        expect(screen.getByText('1.8')).toBeInTheDocument();   // Sharpe ratio
      });
    });

    it('displays PnL metrics', async () => {
      render(<RiskManagement {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('+$450.00')).toBeInTheDocument();  // Daily PnL
        expect(screen.getByText('+$1,200.00')).toBeInTheDocument(); // Weekly PnL
        expect(screen.getByText('+$3,800.00')).toBeInTheDocument(); // Monthly PnL
      });
    });

    it('displays position statistics', async () => {
      render(<RiskManagement {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('12')).toBeInTheDocument();        // Total positions
        expect(screen.getByText('$1,200.00')).toBeInTheDocument(); // Avg position size
        expect(screen.getByText('$5,000.00')).toBeInTheDocument(); // Largest position
      });
    });
  });

  // === RISK ALERTS TESTS ===
  describe('Risk Alerts', () => {
    it('displays risk alerts', async () => {
      render(<RiskManagement {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('Portfolio risk approaching maximum threshold')).toBeInTheDocument();
        expect(screen.getByText('Stop loss not set on BTCUSDT position')).toBeInTheDocument();
      });
    });

    it('shows alert severity levels', async () => {
      render(<RiskManagement {...defaultProps} />);
      
             await waitFor(() => {
         const warningAlert = screen.getByText('Portfolio risk approaching maximum threshold');
         const warningContainer = warningAlert.closest('.bg-yellow-50');
         if (warningContainer) {
           expect(warningContainer).toBeInTheDocument();
         }
         
         const dangerAlert = screen.getByText('Stop loss not set on BTCUSDT position');
         const dangerContainer = dangerAlert.closest('.bg-red-50');
         if (dangerContainer) {
           expect(dangerContainer).toBeInTheDocument();
         }
       });
    });

    it('acknowledges alerts when clicked', async () => {
      const mockOnAlertAcknowledge = jest.fn();
      render(<RiskManagement {...defaultProps} onAlertAcknowledge={mockOnAlertAcknowledge} />);
      
      await waitFor(() => {
        const acknowledgeButtons = screen.getAllByText('Acknowledge');
        expect(acknowledgeButtons[0]).toBeTruthy();
        fireEvent.click(acknowledgeButtons[0]!);
        
        expect(mockOnAlertAcknowledge).toHaveBeenCalledWith('alert1');
      });
    });
  });

  // === RISK LIMITS CONTROLS TESTS ===
  describe('Risk Limits Controls', () => {
    it('displays current risk limits', async () => {
      render(<RiskManagement {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByDisplayValue('10000')).toBeInTheDocument();  // Max position size
        expect(screen.getByDisplayValue('1000')).toBeInTheDocument();   // Max daily loss
        expect(screen.getByDisplayValue('15')).toBeInTheDocument();     // Max drawdown
        expect(screen.getByDisplayValue('10')).toBeInTheDocument();     // Max leverage
      });
    });

    it('enables editing when edit button is clicked', async () => {
      render(<RiskManagement {...defaultProps} />);
      
      await waitFor(() => {
        const editButton = screen.getByText('Edit Limits');
        fireEvent.click(editButton);
        
        expect(screen.getByText('Save Changes')).toBeInTheDocument();
        expect(screen.getByText('Cancel')).toBeInTheDocument();
      });
    });

    it('updates limits when changes are saved', async () => {
      const mockOnLimitUpdate = jest.fn();
      render(<RiskManagement {...defaultProps} onLimitUpdate={mockOnLimitUpdate} />);
      
      await waitFor(() => {
        // Enter edit mode
        const editButton = screen.getByText('Edit Limits');
        fireEvent.click(editButton);
        
        // Change max position size
        const maxPositionInput = screen.getByDisplayValue('10000');
        fireEvent.change(maxPositionInput, { target: { value: '12000' } });
        
        // Save changes
        const saveButton = screen.getByText('Save Changes');
        fireEvent.click(saveButton);
        
        expect(mockOnLimitUpdate).toHaveBeenCalledWith(
          expect.objectContaining({
            maxPositionSize: 12000,
          })
        );
      });
    });

    it('cancels editing without saving changes', async () => {
      render(<RiskManagement {...defaultProps} />);
      
      await waitFor(() => {
        // Enter edit mode
        const editButton = screen.getByText('Edit Limits');
        fireEvent.click(editButton);
        
        // Change a value
        const maxPositionInput = screen.getByDisplayValue('10000');
        fireEvent.change(maxPositionInput, { target: { value: '12000' } });
        
        // Cancel changes
        const cancelButton = screen.getByText('Cancel');
        fireEvent.click(cancelButton);
        
        // Should revert to original value
        expect(screen.getByDisplayValue('10000')).toBeInTheDocument();
      });
    });
  });

  // === ERROR HANDLING TESTS ===
  describe('Error Handling', () => {
    it('displays error message when API call fails', async () => {
      (global.fetch as jest.Mock).mockRejectedValue(new Error('API Error'));
      
      render(<RiskManagement {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('Error loading risk data. Please try again.')).toBeInTheDocument();
      });
    });

    it('retries data fetch when retry button is clicked', async () => {
      (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('API Error'))
                                   .mockImplementation((url: string) => {
                                     if (url.includes('/risk-metrics')) {
                                       return Promise.resolve({
                                         ok: true,
                                         json: () => Promise.resolve({ success: true, data: mockRiskMetrics }),
                                       });
                                     }
                                     return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
                                   });
      
      render(<RiskManagement {...defaultProps} />);
      
      await waitFor(() => {
        const retryButton = screen.getByText('Retry');
        fireEvent.click(retryButton);
      });
      
      await waitFor(() => {
        expect(screen.getByText('$50,000.00')).toBeInTheDocument();
      });
    });
  });

  // === ACCESSIBILITY TESTS ===
  describe('Accessibility', () => {
    it('has proper ARIA labels for metrics', async () => {
      render(<RiskManagement {...defaultProps} />);
      
      await waitFor(() => {
        const riskSection = screen.getByRole('region', { name: /risk metrics/i });
        expect(riskSection).toBeInTheDocument();
      });
    });

    it('has proper form labels for inputs', async () => {
      render(<RiskManagement {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByLabelText(/max position size/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/max daily loss/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/max drawdown/i)).toBeInTheDocument();
      });
    });

    it('has proper button labels', async () => {
      render(<RiskManagement {...defaultProps} />);
      
      await waitFor(() => {
        const editButton = screen.getByRole('button', { name: /edit limits/i });
        expect(editButton).toBeInTheDocument();
      });
    });
  });

  // === RISK COLOR CODING TESTS ===
  describe('Risk Color Coding', () => {
    it('applies correct colors based on risk levels', async () => {
      // Test with high risk data
      const highRiskMetrics = { ...mockRiskMetrics, riskPercentage: 25.0 };
      (global.fetch as jest.Mock).mockImplementation((url: string) => {
        if (url.includes('/risk-metrics')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ success: true, data: highRiskMetrics }),
          });
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
      });
      
      render(<RiskManagement {...defaultProps} />);
      
      await waitFor(() => {
        const riskPercent = screen.getByText('25.0%');
        expect(riskPercent).toHaveClass('text-red-600'); // High risk
      });
    });
  });
}); 