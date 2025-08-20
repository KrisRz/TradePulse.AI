/**
 * Basic OrderForm test to verify Jest configuration
 */

describe('OrderForm Basic Tests', () => {
  test('Jest configuration is working', () => {
    expect(true).toBe(true);
  });

  test('TypeScript compilation works', () => {
    const testData: { symbol: string; price: number } = {
      symbol: 'BTCUSDT',
      price: 50000
    };
    
    expect(testData.symbol).toBe('BTCUSDT');
    expect(testData.price).toBe(50000);
  });

  test('Jest mocking works', () => {
    const mockFn = jest.fn();
    mockFn('test');
    
    expect(mockFn).toHaveBeenCalledWith('test');
    expect(mockFn).toHaveBeenCalledTimes(1);
  });
}); 