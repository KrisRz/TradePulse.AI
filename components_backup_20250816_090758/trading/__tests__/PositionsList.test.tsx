import { render, screen, fireEvent, waitFor } from '@testing-library/preact';
import PositionsList from '../PositionsList';

// Mock the lucide-preact icons
jest.mock('lucide-preact', () => ({
  TrendingUp: () => <div data-testid="trending-up-icon" />,
  TrendingDown: () => <div data-testid="trending-down-icon" />,
  DollarSign: () => <div data-testid="dollar-sign-icon" />,
  Percent: () => <div data-testid="percent-icon" />,
  Clock: () => <div data-testid="clock-icon" />,
  Target: () => <div data-testid="target-icon" />,
  Shield: () => <div data-testid="shield-icon" />,
  AlertTriangle: () => <div data-testid="alert-triangle-icon" />,
  X: () => <div data-testid="x-icon" />,
  Eye: () => <div data-testid="eye-icon" />,
  Settings: () => <div data-testid="settings-icon" />,
  MoreHorizontal: () => <div data-testid="more-horizontal-icon" />,
}));

// Mock fetch globally for API calls
global.fetch = jest.fn();

// Mock position data
const mockPositions = [
  {
    id: 'pos1',
    symbol: 'BTCUSDT',
    side: 'LONG' as const,
    size: 0.5,
    entryPrice: 50000,
    currentPrice: 52000,
    unrealizedPnl: 1000,
    unrealizedPnlPercent: 4.0,
    margin: 5000,
    leverage: 10,
    liquidationPrice: 45000,
    stopLossPrice: 48000,
    takeProfitPrice: 55000,
    openTime: new Date('2024-01-15T10:30:00'),
    fees: 25,
    status: 'OPEN' as const,
  },
  {
    id: 'pos2',
    symbol: 'ETHUSDT',
    side: 'SHORT' as const,
    size: 2.0,
    entryPrice: 3000,
    currentPrice: 2950,
    unrealizedPnl: 100,
    unrealizedPnlPercent: 1.67,
    margin: 1500,
    leverage: 4,
    liquidationPrice: 3200,
    openTime: new Date('2024-01-15T14:15:00'),
    fees: 12,
    status: 'OPEN' as const,
  },
  {
    id: 'pos3',
    symbol: 'ADAUSDT',
    side: 'LONG' as const,
    size: 1000,
    entryPrice: 0.5,
    currentPrice: 0.48,
    unrealizedPnl: -20,
    unrealizedPnlPercent: -4.0,
    margin: 125,
    leverage: 4,
    liquidationPrice: 0.45,
    openTime: new Date('2024-01-15T16:45:00'),
    fees: 2.5,
    status: 'OPEN' as const,
  },
];

// Define component props interface
interface TestPositionsListProps {
  userId?: string;
  showHeader?: boolean;
  maxHeight?: string;
  onPositionClick?: (position: any) => void;
  onClosePosition?: (positionId: string) => void;
  onUpdateStopLoss?: (positionId: string, stopLoss: number) => void;
  onUpdateTakeProfit?: (positionId: string, takeProfit: number) => void;
}

const defaultProps: TestPositionsListProps = {
  userId: 'test-user',
  showHeader: true,
  maxHeight: '400px',
  onPositionClick: jest.fn(),
  onClosePosition: jest.fn(),
  onUpdateStopLoss: jest.fn(),
  onUpdateTakeProfit: jest.fn(),
};

describe('PositionsList', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Mock successful API response
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, data: mockPositions }),
    });
  });

  // === RENDERING TESTS ===
  describe('Rendering', () => {
    it('renders with header by default', async () => {
      render(<PositionsList {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('Open Positions')).toBeInTheDocument();
        expect(screen.getByText('Symbol')).toBeInTheDocument();
        expect(screen.getByText('Side')).toBeInTheDocument();
        expect(screen.getByText('Size')).toBeInTheDocument();
        expect(screen.getByText('Entry Price')).toBeInTheDocument();
        expect(screen.getByText('Current Price')).toBeInTheDocument();
        expect(screen.getByText('PnL')).toBeInTheDocument();
      });
    });

    it('renders without header when showHeader is false', async () => {
      render(<PositionsList {...defaultProps} showHeader={false} />);
      
      await waitFor(() => {
        expect(screen.queryByText('Open Positions')).not.toBeInTheDocument();
        expect(screen.queryByText('Symbol')).not.toBeInTheDocument();
      });
    });

    it('applies custom maxHeight style', () => {
      render(<PositionsList {...defaultProps} maxHeight="300px" />);
      
      const container = screen.getByTestId('positions-list-container');
      expect(container).toHaveStyle('max-height: 300px');
    });

    it('shows loading state initially', () => {
      render(<PositionsList {...defaultProps} />);
      expect(screen.getByText('Loading positions...')).toBeInTheDocument();
    });
  });

  // === POSITION DISPLAY TESTS ===
  describe('Position Display', () => {
    it('displays all positions after loading', async () => {
      render(<PositionsList {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('BTCUSDT')).toBeInTheDocument();
        expect(screen.getByText('ETHUSDT')).toBeInTheDocument();
        expect(screen.getByText('ADAUSDT')).toBeInTheDocument();
      });
    });

    it('displays LONG positions with correct styling', async () => {
      render(<PositionsList {...defaultProps} />);
      
      await waitFor(() => {
        const longBadges = screen.getAllByText('LONG');
        expect(longBadges.length).toBe(2); // BTCUSDT and ADAUSDT
        longBadges.forEach(badge => {
          expect(badge).toHaveClass('bg-green-100', 'text-green-800');
        });
      });
    });

    it('displays SHORT positions with correct styling', async () => {
      render(<PositionsList {...defaultProps} />);
      
      await waitFor(() => {
        const shortBadge = screen.getByText('SHORT');
        expect(shortBadge).toHaveClass('bg-red-100', 'text-red-800');
      });
    });

    it('formats prices correctly', async () => {
      render(<PositionsList {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('$50,000.00')).toBeInTheDocument(); // BTC entry price
        expect(screen.getByText('$52,000.00')).toBeInTheDocument(); // BTC current price
        expect(screen.getByText('$3,000.00')).toBeInTheDocument();  // ETH entry price
      });
    });

    it('displays PnL with correct colors', async () => {
      render(<PositionsList {...defaultProps} />);
      
      await waitFor(() => {
        // Positive PnL (green)
        const positivePnl = screen.getByText('+$1,000.00');
        expect(positivePnl).toHaveClass('text-green-600');
        
        // Negative PnL (red)
        const negativePnl = screen.getByText('-$20.00');
        expect(negativePnl).toHaveClass('text-red-600');
      });
    });

    it('displays PnL percentages correctly', async () => {
      render(<PositionsList {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('(+4.00%)')).toBeInTheDocument();
        expect(screen.getByText('(+1.67%)')).toBeInTheDocument();
        expect(screen.getByText('(-4.00%)')).toBeInTheDocument();
      });
    });

    it('displays leverage and margin info', async () => {
      render(<PositionsList {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('10x')).toBeInTheDocument(); // BTC leverage
        expect(screen.getByText('4x')).toBeInTheDocument();  // ETH leverage
        expect(screen.getByText('$5,000.00')).toBeInTheDocument(); // BTC margin
      });
    });

    it('shows liquidation prices', async () => {
      render(<PositionsList {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('$45,000.00')).toBeInTheDocument(); // BTC liquidation
        expect(screen.getByText('$3,200.00')).toBeInTheDocument();  // ETH liquidation
      });
    });

    it('displays stop loss and take profit when set', async () => {
      render(<PositionsList {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('$48,000.00')).toBeInTheDocument(); // BTC stop loss
        expect(screen.getByText('$55,000.00')).toBeInTheDocument(); // BTC take profit
      });
    });

    it('shows open time formatted correctly', async () => {
      render(<PositionsList {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('15 Jan, 10:30')).toBeInTheDocument();
        expect(screen.getByText('15 Jan, 14:15')).toBeInTheDocument();
        expect(screen.getByText('15 Jan, 16:45')).toBeInTheDocument();
      });
    });
  });

  // === INTERACTION TESTS ===
  describe('Interactions', () => {
    it('calls onPositionClick when position row is clicked', async () => {
      const mockOnPositionClick = jest.fn();
      render(<PositionsList {...defaultProps} onPositionClick={mockOnPositionClick} />);
      
      await waitFor(() => {
        const btcRow = screen.getByText('BTCUSDT').closest('tr');
        if (btcRow) {
          fireEvent.click(btcRow);
          
          expect(mockOnPositionClick).toHaveBeenCalledWith(
            expect.objectContaining({
              id: 'pos1',
              symbol: 'BTCUSDT',
              side: 'LONG',
            })
          );
        }
      });
    });

    it('calls onClosePosition when close button is clicked', async () => {
      const mockOnClosePosition = jest.fn();
      render(<PositionsList {...defaultProps} onClosePosition={mockOnClosePosition} />);
      
      await waitFor(() => {
        const closeButtons = screen.getAllByTestId('x-icon');
        expect(closeButtons[0]).toBeTruthy();
        fireEvent.click(closeButtons[0]!);
        
        expect(mockOnClosePosition).toHaveBeenCalledWith('pos1');
      });
    });

    it('opens stop loss modal when stop loss button is clicked', async () => {
      render(<PositionsList {...defaultProps} />);
      
      await waitFor(() => {
        const stopLossButtons = screen.getAllByText('SL');
        expect(stopLossButtons[0]).toBeTruthy();
        fireEvent.click(stopLossButtons[0]!);
        
        expect(screen.getByText('Update Stop Loss')).toBeInTheDocument();
      });
    });

    it('opens take profit modal when take profit button is clicked', async () => {
      render(<PositionsList {...defaultProps} />);
      
      await waitFor(() => {
        const takeProfitButtons = screen.getAllByText('TP');
        expect(takeProfitButtons[0]).toBeTruthy();
        fireEvent.click(takeProfitButtons[0]!);
        
        expect(screen.getByText('Update Take Profit')).toBeInTheDocument();
      });
    });
  });

  // === MODAL TESTS ===
  describe('Modals', () => {
    it('updates stop loss when confirmed', async () => {
      const mockOnUpdateStopLoss = jest.fn();
      render(<PositionsList {...defaultProps} onUpdateStopLoss={mockOnUpdateStopLoss} />);
      
      await waitFor(() => {
        // Open stop loss modal
        const stopLossButtons = screen.getAllByText('SL');
        expect(stopLossButtons[0]).toBeTruthy();
        fireEvent.click(stopLossButtons[0]!);
        
        // Enter new stop loss price
        const input = screen.getByDisplayValue('48000');
        fireEvent.change(input, { target: { value: '49000' } });
        
        // Confirm update
        const updateButton = screen.getByText('Update');
        fireEvent.click(updateButton);
        
        expect(mockOnUpdateStopLoss).toHaveBeenCalledWith('pos1', 49000);
      });
    });

    it('updates take profit when confirmed', async () => {
      const mockOnUpdateTakeProfit = jest.fn();
      render(<PositionsList {...defaultProps} onUpdateTakeProfit={mockOnUpdateTakeProfit} />);
      
      await waitFor(() => {
        // Open take profit modal
        const takeProfitButtons = screen.getAllByText('TP');
        expect(takeProfitButtons[0]).toBeTruthy();
        fireEvent.click(takeProfitButtons[0]!);
        
        // Enter new take profit price
        const input = screen.getByDisplayValue('55000');
        fireEvent.change(input, { target: { value: '56000' } });
        
        // Confirm update
        const updateButton = screen.getByText('Update');
        fireEvent.click(updateButton);
        
        expect(mockOnUpdateTakeProfit).toHaveBeenCalledWith('pos1', 56000);
      });
    });

    it('closes modal when cancel is clicked', async () => {
      render(<PositionsList {...defaultProps} />);
      
      await waitFor(() => {
        // Open stop loss modal
        const stopLossButtons = screen.getAllByText('SL');
        expect(stopLossButtons[0]).toBeTruthy();
        fireEvent.click(stopLossButtons[0]!);
        
        expect(screen.getByText('Update Stop Loss')).toBeInTheDocument();
        
        // Cancel
        const cancelButton = screen.getByText('Cancel');
        fireEvent.click(cancelButton);
        
        expect(screen.queryByText('Update Stop Loss')).not.toBeInTheDocument();
      });
    });
  });

  // === ERROR HANDLING TESTS ===
  describe('Error Handling', () => {
    it('displays error message when API call fails', async () => {
      (global.fetch as jest.Mock).mockRejectedValue(new Error('API Error'));
      
      render(<PositionsList {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('Error loading positions. Please try again.')).toBeInTheDocument();
      });
    });

    it('displays error message when API returns error response', async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => ({ success: false, message: 'Server error' }),
      });
      
      render(<PositionsList {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('Error loading positions. Please try again.')).toBeInTheDocument();
      });
    });

    it('retries API call when retry button is clicked', async () => {
      (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('API Error'))
                                   .mockResolvedValue({
                                     ok: true,
                                     json: async () => ({ success: true, data: mockPositions }),
                                   });
      
      render(<PositionsList {...defaultProps} />);
      
      await waitFor(() => {
        const retryButton = screen.getByText('Retry');
        fireEvent.click(retryButton);
      });
      
      await waitFor(() => {
        expect(screen.getByText('BTCUSDT')).toBeInTheDocument();
      });
    });
  });

  // === EMPTY STATE TESTS ===
  describe('Empty State', () => {
    it('displays empty state when no positions', async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => ({ success: true, data: [] }),
      });
      
      render(<PositionsList {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText('No open positions')).toBeInTheDocument();
        expect(screen.getByText('Your trading positions will appear here')).toBeInTheDocument();
      });
    });
  });

  // === RESPONSIVE DESIGN TESTS ===
  describe('Responsive Design', () => {
    it('has proper table structure for accessibility', async () => {
      render(<PositionsList {...defaultProps} />);
      
      await waitFor(() => {
        const table = screen.getByRole('table');
        expect(table).toBeInTheDocument();
        
        const headers = screen.getAllByRole('columnheader');
        expect(headers.length).toBeGreaterThan(0);
      });
    });

    it('applies overflow styles for scrolling', () => {
      render(<PositionsList {...defaultProps} />);
      
      const container = screen.getByTestId('positions-list-container');
      expect(container).toHaveClass('overflow-y-auto');
    });
  });

  // === REAL-TIME UPDATES TESTS ===
  describe('Real-time Updates', () => {
    it('refreshes positions on component mount', () => {
      render(<PositionsList {...defaultProps} />);
      
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/portfolio/positions'),
        expect.objectContaining({
          method: 'GET',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
        })
      );
    });

    it('updates positions when userId changes', async () => {
      const { rerender } = render(<PositionsList {...defaultProps} userId="user1" />);
      
      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining('userId=user1'),
          expect.any(Object)
        );
      });
      
      jest.clearAllMocks();
      
      rerender(<PositionsList {...defaultProps} userId="user2" />);
      
      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining('userId=user2'),
          expect.any(Object)
        );
      });
    });
  });

  // === ACCESSIBILITY TESTS ===
  describe('Accessibility', () => {
    it('has proper ARIA labels', async () => {
      render(<PositionsList {...defaultProps} />);
      
      await waitFor(() => {
        const table = screen.getByRole('table');
        expect(table).toHaveAttribute('aria-label', 'Trading positions');
      });
    });

    it('has proper button labels for actions', async () => {
      render(<PositionsList {...defaultProps} />);
      
      await waitFor(() => {
        const closeButtons = screen.getAllByLabelText('Close position');
        expect(closeButtons.length).toBeGreaterThan(0);
        
        const stopLossButtons = screen.getAllByLabelText('Update stop loss');
        expect(stopLossButtons.length).toBeGreaterThan(0);
        
        const takeProfitButtons = screen.getAllByLabelText('Update take profit');
        expect(takeProfitButtons.length).toBeGreaterThan(0);
      });
    });

         it('supports keyboard navigation', async () => {
       render(<PositionsList {...defaultProps} />);
       
       await waitFor(() => {
         const firstRow = screen.getByText('BTCUSDT').closest('tr');
         if (firstRow) {
           expect(firstRow).toHaveAttribute('tabindex', '0');
         }
       });
     });
  });
}); 