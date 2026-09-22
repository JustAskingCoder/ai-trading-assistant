/**
 * Multi-Currency & Precision Formatting Utilities
 * Handles Indian Equities (₹), Global Forex Pairs ($ / € / £ / ¥ / ₹ / CHF), Commodities & Crypto.
 */

export function getCurrencySymbol(symbol: string): string {
  const clean = symbol.toUpperCase().replace('/', '').replace(' ', '').replace('_', '');
  if (
    clean.includes('INR') ||
    clean.endsWith('.NS') ||
    [
      'RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK', 'SBIN',
      'BHARTIARTL', 'ITC', 'KOTAKBANK', 'LT', 'WIPRO', 'TATAMOTORS',
      'TATASTEEL', 'MARUTI', 'NIFTY', 'BANKNIFTY'
    ].includes(clean)
  ) {
    return '₹';
  }
  if (clean.includes('JPY')) return '¥';
  if (clean.includes('CHF')) return 'CHF ';
  if (clean.startsWith('EUR') && !clean.includes('USD') && !clean.includes('INR')) return '€';
  if (clean.startsWith('GBP') && !clean.includes('USD') && !clean.includes('INR')) return '£';
  return '$';
}

export function getPrecisionForSymbol(symbol: string, price?: number): number {
  const clean = symbol.toUpperCase().replace('/', '').replace(' ', '').replace('_', '');
  if (['BTCUSD', 'BTC-USD', 'BTC', 'GOLD', 'GC=F', 'USDJPY', 'JPY=X'].includes(clean)) {
    return 2;
  }
  if (
    [
      'USDINR', 'EURUSD', 'GBPUSD', 'EURINR', 'GBPINR', 'AUDUSD', 'USDCHF',
      'CHF=X', 'USDINR=X', 'EURUSD=X', 'GBPUSD=X', 'EURINR=X', 'GBPINR=X', 'AUDUSD=X'
    ].includes(clean)
  ) {
    return 4;
  }
  if (price !== undefined && price > 0 && price < 20) {
    return 4;
  }
  return 2;
}

export function formatPrice(price: number | undefined | null, symbol: string): string {
  if (price === undefined || price === null || isNaN(price)) return '—';
  const sym = getCurrencySymbol(symbol);
  const dec = getPrecisionForSymbol(symbol, price);
  const formatted = price.toLocaleString('en-US', {
    minimumFractionDigits: dec,
    maximumFractionDigits: dec,
  });
  return `${sym}${formatted}`;
}

export function formatPriceNoSymbol(price: number | undefined | null, symbol: string): string {
  if (price === undefined || price === null || isNaN(price)) return '—';
  const dec = getPrecisionForSymbol(symbol, price);
  return price.toFixed(dec);
}

export function isForexSymbol(symbol: string): boolean {
  const clean = symbol.toUpperCase().replace('/', '').replace(' ', '').replace('_', '');
  const forexSymbols = [
    'USDINR', 'EURUSD', 'GBPUSD', 'USDJPY', 'EURINR', 'GBPINR', 'AUDUSD', 'USDCHF', 'GOLD', 'BTCUSD',
    'USDINR=X', 'EURUSD=X', 'GBPUSD=X', 'JPY=X', 'EURINR=X', 'GBPINR=X', 'AUDUSD=X', 'CHF=X', 'GC=F', 'BTC-USD'
  ];
  if (forexSymbols.includes(clean) || clean.includes('=X')) return true;
  if (['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK', 'SBIN', 'BHARTIARTL', 'TATAMOTORS'].includes(clean)) return false;
  return clean.length === 6 && (clean.includes('USD') || clean.includes('EUR') || clean.includes('GBP'));
}

export function isCryptoSymbol(symbol: string): boolean {
  const clean = symbol.toUpperCase().replace('/', '').replace(' ', '').replace('_', '');
  return clean.includes('BTC') || clean.includes('ETH') || clean === 'CRYPTO';
}
