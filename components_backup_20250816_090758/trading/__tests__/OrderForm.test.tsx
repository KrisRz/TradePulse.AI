import { render, screen, fireEvent, waitFor } from '@testing-library/preact';
import OrderForm from '../OrderForm';

// Mock the lucide-preact icons
jest.mock('lucide-preact', () => ({
  TrendingUp: () => <div data-testid="trending-up-icon" />,
  TrendingDown: () => <div data-testid="trending-down-icon" />,
  DollarSign: () => <div data-testid="dollar-sign-icon" />,
  Percent: () => <div data-testid="percent-icon" />,
  Calculator: () => <div data-testid="calculator-icon" />,
  AlertTriangle: () => <div data-testid="alert-triangle-icon" />,
}));

// Define props interface to match actual component
interface TestOrderFormProps {
  symbol?: string;
  initialSide?: 'BUY' | 'SELL';
  maxBalance?: number;
  currentPrice?: number;
  onSubmit?: (order: any) => void;
  onCancel?: () => void;
  disabled?: boolean;
}

// Mock default props
const defaultProps: TestOrderFormProps = {
  symbol: 'BTCUSDT',
  maxBalance: 10000,
  currentPrice: 45000,
  onSubmit: jest.fn(),
  disabled: false,
};

describe('OrderForm', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // === RENDERING TESTS ===
  describe('Rendering', () => {
    it('renders with all essential elements', () => {
      render(<OrderForm {...defaultProps} />);
      
      // Check main structure
      expect(screen.getByText('Place Order')).toBeInTheDocument();
      expect(screen.getByText('BTCUSDT')).toBeInTheDocument();
      expect(screen.getByText('$45,000.00')).toBeInTheDocument();
      expect(screen.getByText('Balance: $10,000.00')).toBeInTheDocument();
      
      // Check order side buttons
      expect(screen.getByRole('button', { name: /buy/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /sell/i })).toBeInTheDocument();
      
      // Check order type selector
      expect(screen.getByText('Market')).toBeInTheDocument();
      expect(screen.getByText('Limit')).toBeInTheDocument();
      
      // Check form inputs
      expect(screen.getByLabelText(/quantity/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/price/i)).toBeInTheDocument();
    });

    it('displays correct price formatting', () => {
      render(<OrderForm {...defaultProps} currentPrice={123456.789} />);
      expect(screen.getByText('$123,456.79')).toBeInTheDocument();
    });

    it('displays correct balance formatting', () => {
      render(<OrderForm {...defaultProps} maxBalance={1234567.89} />);
      expect(screen.getByText('Balance: $1,234,567.89')).toBeInTheDocument();
    });
  });

  // === ORDER SIDE SELECTION TESTS ===
  describe('Order Side Selection', () => {
    it('defaults to BUY side', () => {
      render(<OrderForm {...defaultProps} />);
      const buyButton = screen.getByRole('button', { name: /buy/i });
      expect(buyButton).toHaveClass('bg-green-600');
    });

    it('switches to SELL side when clicked', () => {
      render(<OrderForm {...defaultProps} />);
      const sellButton = screen.getByRole('button', { name: /sell/i });
      
      fireEvent.click(sellButton);
      
      expect(sellButton).toHaveClass('bg-red-600');
    });

    it('updates submit button text based on selected side', () => {
      render(<OrderForm {...defaultProps} />);
      
      // Default BUY
      expect(screen.getByRole('button', { name: /place buy order/i })).toBeInTheDocument();
      
      // Switch to SELL
      const sellButton = screen.getByRole('button', { name: /sell/i });
      fireEvent.click(sellButton);
      
      expect(screen.getByRole('button', { name: /place sell order/i })).toBeInTheDocument();
    });
  });

  // === ORDER TYPE SELECTION TESTS ===
  describe('Order Type Selection', () => {
    it('defaults to Market order', () => {
      render(<OrderForm {...defaultProps} />);
      expect(screen.getByText('Market')).toHaveClass('bg-blue-600');
    });

    it('switches to Limit order when clicked', () => {
      render(<OrderForm {...defaultProps} />);
      const limitButton = screen.getByText('Limit');
      
      fireEvent.click(limitButton);
      
      expect(limitButton).toHaveClass('bg-blue-600');
    });

    it('disables price input for Market orders', () => {
      render(<OrderForm {...defaultProps} />);
      const priceInput = screen.getByLabelText(/price/i);
      expect(priceInput).toBeDisabled();
    });

    it('enables price input for Limit orders', () => {
      render(<OrderForm {...defaultProps} />);
      const limitButton = screen.getByText('Limit');
      fireEvent.click(limitButton);
      
      const priceInput = screen.getByLabelText(/price/i);
      expect(priceInput).not.toBeDisabled();
    });
  });

  // === FORM VALIDATION TESTS ===
  describe('Form Validation', () => {
    it('shows error for empty quantity', async () => {
      render(<OrderForm {...defaultProps} />);
      const submitButton = screen.getByRole('button', { name: /place buy order/i });
      
      fireEvent.click(submitButton);
      
      await waitFor(() => {
        expect(screen.getByText(/quantity is required/i)).toBeInTheDocument();
      });
    });

    it('shows error for invalid quantity format', async () => {
      render(<OrderForm {...defaultProps} />);
      const quantityInput = screen.getByLabelText(/quantity/i);
      const submitButton = screen.getByRole('button', { name: /place buy order/i });
      
      fireEvent.change(quantityInput, { target: { value: 'invalid' } });
      fireEvent.click(submitButton);
      
      await waitFor(() => {
        expect(screen.getByText(/invalid quantity/i)).toBeInTheDocument();
      });
    });

    it('shows error for negative quantity', async () => {
      render(<OrderForm {...defaultProps} />);
      const quantityInput = screen.getByLabelText(/quantity/i);
      const submitButton = screen.getByRole('button', { name: /place buy order/i });
      
      fireEvent.change(quantityInput, { target: { value: '-1' } });
      fireEvent.click(submitButton);
      
      await waitFor(() => {
        expect(screen.getByText(/quantity must be positive/i)).toBeInTheDocument();
      });
    });

    it('shows error for insufficient balance', async () => {
      render(<OrderForm {...defaultProps} maxBalance={100} />);
      const quantityInput = screen.getByLabelText(/quantity/i);
      const submitButton = screen.getByRole('button', { name: /place buy order/i });
      
      fireEvent.change(quantityInput, { target: { value: '1' } });
      fireEvent.click(submitButton);
      
      await waitFor(() => {
        expect(screen.getByText(/insufficient balance/i)).toBeInTheDocument();
      });
    });

    it('validates limit price when required', async () => {
      render(<OrderForm {...defaultProps} />);
      
      // Switch to limit order
      const limitButton = screen.getByText('Limit');
      fireEvent.click(limitButton);
      
      const quantityInput = screen.getByLabelText(/quantity/i);
      const submitButton = screen.getByRole('button', { name: /place buy order/i });
      
      fireEvent.change(quantityInput, { target: { value: '0.1' } });
      fireEvent.click(submitButton);
      
      await waitFor(() => {
        expect(screen.getByText(/price is required for limit orders/i)).toBeInTheDocument();
      });
    });
  });

  // === QUICK AMOUNT BUTTONS TESTS ===
  describe('Quick Amount Buttons', () => {
    it('renders percentage buttons', () => {
      render(<OrderForm {...defaultProps} />);
      
      expect(screen.getByText('25%')).toBeInTheDocument();
      expect(screen.getByText('50%')).toBeInTheDocument();
      expect(screen.getByText('75%')).toBeInTheDocument();
      expect(screen.getByText('Max')).toBeInTheDocument();
    });

    it('calculates correct quantity for 25%', () => {
      render(<OrderForm {...defaultProps} maxBalance={10000} currentPrice={50000} />);
      const quantityInput = screen.getByLabelText(/quantity/i);
      const button25 = screen.getByText('25%');
      
      fireEvent.click(button25);
      
      // 25% of $10,000 = $2,500 / $50,000 = 0.05 BTC
      expect(quantityInput).toHaveValue('0.05');
    });

    it('calculates correct quantity for Max', () => {
      render(<OrderForm {...defaultProps} maxBalance={10000} currentPrice={40000} />);
      const quantityInput = screen.getByLabelText(/quantity/i);
      const maxButton = screen.getByText('Max');
      
      fireEvent.click(maxButton);
      
      // Max of $10,000 / $40,000 = 0.25 BTC
      expect(quantityInput).toHaveValue('0.25');
    });
  });

  // === FORM SUBMISSION TESTS ===
  describe('Form Submission', () => {
    it('submits valid market buy order', async () => {
      const mockSubmit = jest.fn();
      render(<OrderForm {...defaultProps} onSubmit={mockSubmit} />);
      
      const quantityInput = screen.getByLabelText(/quantity/i);
      const submitButton = screen.getByRole('button', { name: /place buy order/i });
      
      fireEvent.change(quantityInput, { target: { value: '0.1' } });
      fireEvent.click(submitButton);
      
      await waitFor(() => {
        expect(mockSubmit).toHaveBeenCalledWith({
          symbol: 'BTCUSDT',
          side: 'BUY',
          type: 'MARKET',
          quantity: 0.1,
          price: undefined,
        });
      });
    });

    it('submits valid limit sell order', async () => {
      const mockSubmit = jest.fn();
      render(<OrderForm {...defaultProps} onSubmit={mockSubmit} />);
      
      // Switch to SELL and LIMIT
      const sellButton = screen.getByRole('button', { name: /sell/i });
      const limitButton = screen.getByText('Limit');
      fireEvent.click(sellButton);
      fireEvent.click(limitButton);
      
      const quantityInput = screen.getByLabelText(/quantity/i);
      const priceInput = screen.getByLabelText(/price/i);
      const submitButton = screen.getByRole('button', { name: /place sell order/i });
      
      fireEvent.change(quantityInput, { target: { value: '0.5' } });
      fireEvent.change(priceInput, { target: { value: '46000' } });
      fireEvent.click(submitButton);
      
      await waitFor(() => {
        expect(mockSubmit).toHaveBeenCalledWith({
          symbol: 'BTCUSDT',
          side: 'SELL',
          type: 'LIMIT',
          quantity: 0.5,
          price: 46000,
        });
      });
    });

    it('prevents submission when loading', () => {
      const mockSubmit = jest.fn();
      render(<OrderForm {...defaultProps} onSubmit={mockSubmit} disabled={true} />);
      
      const submitButton = screen.getByRole('button', { name: /placing order/i });
      expect(submitButton).toBeDisabled();
      
      fireEvent.click(submitButton);
      expect(mockSubmit).not.toHaveBeenCalled();
    });
  });

  // === COST CALCULATION TESTS ===
  describe('Cost Calculation', () => {
    it('calculates total cost for market order', () => {
      render(<OrderForm {...defaultProps} currentPrice={50000} />);
      const quantityInput = screen.getByLabelText(/quantity/i);
      
      fireEvent.change(quantityInput, { target: { value: '0.2' } });
      
      // 0.2 BTC * $50,000 = $10,000
      expect(screen.getByText(/total: \$10,000\.00/i)).toBeInTheDocument();
    });

    it('calculates total cost for limit order', () => {
      render(<OrderForm {...defaultProps} />);
      
      // Switch to limit order
      const limitButton = screen.getByText('Limit');
      fireEvent.click(limitButton);
      
      const quantityInput = screen.getByLabelText(/quantity/i);
      const priceInput = screen.getByLabelText(/price/i);
      
      fireEvent.change(quantityInput, { target: { value: '0.1' } });
      fireEvent.change(priceInput, { target: { value: '48000' } });
      
      // 0.1 BTC * $48,000 = $4,800
      expect(screen.getByText(/total: \$4,800\.00/i)).toBeInTheDocument();
    });
  });

  // === DISABLED STATE TESTS ===
  describe('Disabled State', () => {
    it('disables all inputs when disabled prop is true', () => {
      render(<OrderForm {...defaultProps} disabled={true} />);
      
      expect(screen.getByLabelText(/quantity/i)).toBeDisabled();
      expect(screen.getByLabelText(/price/i)).toBeDisabled();
      expect(screen.getByRole('button', { name: /place buy order/i })).toBeDisabled();
    });
  });

  // === ACCESSIBILITY TESTS ===
  describe('Accessibility', () => {
    it('has proper form labels', () => {
      render(<OrderForm {...defaultProps} />);
      
      expect(screen.getByLabelText(/quantity/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/price/i)).toBeInTheDocument();
    });

    it('has proper ARIA attributes', () => {
      render(<OrderForm {...defaultProps} />);
      
      const form = screen.getByRole('form');
      expect(form).toHaveAttribute('aria-label', 'Trading order form');
    });

    it('announces errors to screen readers', async () => {
      render(<OrderForm {...defaultProps} />);
      const submitButton = screen.getByRole('button', { name: /place buy order/i });
      
      fireEvent.click(submitButton);
      
      await waitFor(() => {
        const errorMessage = screen.getByText(/quantity is required/i);
        expect(errorMessage).toHaveAttribute('role', 'alert');
      });
    });
  });
}); 