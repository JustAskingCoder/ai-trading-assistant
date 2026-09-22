import { MarketTradingStatus } from '../types';

/**
 * Get current time in Indian Standard Time (Asia/Kolkata / UTC + 5:30).
 */
export function getISTDate(): Date {
  const now = new Date();
  const utc = now.getTime() + now.getTimezoneOffset() * 60000;
  return new Date(utc + 3600000 * 5.5);
}

/**
 * Evaluates whether Indian exchanges (NSE/BSE) are currently in an active trading session.
 * Regular trading session: Monday to Friday, 09:15 to 15:30 IST.
 */
export function getNSEMarketStatus(): MarketTradingStatus {
  const ist = getISTDate();
  const day = ist.getDay(); // 0 = Sunday, 1 = Monday, ..., 6 = Saturday
  const hours = ist.getHours();
  const minutes = ist.getMinutes();
  const seconds = ist.getSeconds();
  const timeInMinutes = hours * 60 + minutes;

  const openTime = 9 * 60 + 15;   // 09:15 IST
  const closeTime = 15 * 60 + 30; // 15:30 IST

  const isWeekday = day >= 1 && day <= 5;
  const isMarketHours = timeInMinutes >= openTime && timeInMinutes <= closeTime;
  const isOpen = isWeekday && isMarketHours;

  const pad = (n: number) => (n < 10 ? '0' + n : n);
  const timeStr = `${pad(hours)}:${pad(minutes)}:${pad(seconds)} IST`;

  let reason = 'Regular Trading Session';
  let nextOpen: string | null = null;

  if (!isWeekday) {
    reason = 'Closed for the Weekend';
    nextOpen = 'Monday at 09:15 AM IST';
  } else if (timeInMinutes < openTime) {
    reason = 'Pre-Market Session (Opens at 09:15 AM IST)';
    nextOpen = 'Today at 09:15 AM IST';
  } else if (timeInMinutes > closeTime) {
    reason = 'Regular Session Closed at 03:30 PM IST';
    nextOpen = day === 5 ? 'Monday at 09:15 AM IST' : 'Tomorrow at 09:15 AM IST';
  }

  return {
    market: 'NSE',
    is_open: isOpen,
    status: isOpen ? 'OPEN' : 'CLOSED',
    current_time_ist: timeStr,
    trading_hours: '09:15 - 15:30 IST (Mon - Fri)',
    message: isOpen ? 'Market is Open' : 'Market is Closed',
    reason,
    next_open: nextOpen,
  };
}

/**
 * Evaluates whether Forex market is open (24/5 from Monday morning to Saturday morning IST).
 */
export function getForexMarketStatus(): MarketTradingStatus {
  const ist = getISTDate();
  const day = ist.getDay();
  const hours = ist.getHours();
  const minutes = ist.getMinutes();
  const seconds = ist.getSeconds();
  const timeInMinutes = hours * 60 + minutes;

  let isOpen = true;
  if (day === 6 && timeInMinutes >= 2 * 60 + 30) {
    isOpen = false;
  } else if (day === 0) {
    isOpen = false;
  } else if (day === 1 && timeInMinutes < 2 * 60 + 30) {
    isOpen = false;
  }

  const pad = (n: number) => (n < 10 ? '0' + n : n);
  const timeStr = `${pad(hours)}:${pad(minutes)}:${pad(seconds)} IST`;

  return {
    market: 'FOREX',
    is_open: isOpen,
    status: isOpen ? 'OPEN' : 'CLOSED',
    current_time_ist: timeStr,
    trading_hours: '24/5 (Mon 02:30 - Sat 02:30 IST)',
    message: isOpen ? 'Forex Market is Open' : 'Forex Market is Closed for the Weekend',
    reason: isOpen ? '24/5 Global Trading Session' : 'Closed for Weekend',
    next_open: isOpen ? null : 'Monday 02:30 AM IST',
  };
}

/**
 * Returns market trading status for any symbol or category.
 */
export function getMarketStatusForSymbol(symbol: string): MarketTradingStatus {
  const clean = symbol.toUpperCase().replace('/', '').replace(' ', '');
  const forexSymbols = ['USDINR', 'EURUSD', 'GBPUSD', 'USDJPY', 'EURINR', 'GBPINR', 'AUDUSD'];
  if (forexSymbols.includes(clean) || clean.includes('=X') || clean.includes('USD')) {
    return getForexMarketStatus();
  }
  return getNSEMarketStatus();
}
