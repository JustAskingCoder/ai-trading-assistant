"""Generate realistic sample OHLCV CSV data for testing."""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path


def generate_sample_ohlcv(
    symbol: str = "RELIANCE",
    start_price: float = 3000.0,
    num_candles: int = 500,
    interval_minutes: int = 5,
    output_path: str = "data/RELIANCE_5m.csv"
) -> str:
    np.random.seed(42)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    start_time = datetime(2026, 1, 1, 9, 15)
    timestamps = []
    current_time = start_time

    # Generate market timestamps (skipping non-market hours 9:15 to 15:30)
    for _ in range(num_candles):
        timestamps.append(current_time)
        current_time += timedelta(minutes=interval_minutes)
        if current_time.hour > 15 or (current_time.hour == 15 and current_time.minute > 30):
            current_time = (current_time + timedelta(days=1)).replace(hour=9, minute=15)
            # Skip weekends
            while current_time.weekday() >= 5:
                current_time += timedelta(days=1)

    prices = [start_price]
    trend_factor = 0.0003
    for i in range(1, num_candles):
        # Add slight cyclical trend and random walk
        shock = np.random.normal(loc=trend_factor * np.sin(i / 30.0), scale=0.002)
        next_price = prices[-1] * (1 + shock)
        prices.append(round(next_price, 2))

    data = []
    for i in range(num_candles):
        close_p = prices[i]
        volatility = close_p * np.random.uniform(0.001, 0.004)
        open_p = prices[i - 1] if i > 0 else close_p * (1 - np.random.uniform(-0.001, 0.001))
        high_p = max(open_p, close_p) + abs(np.random.normal(0, volatility * 0.7))
        low_p = min(open_p, close_p) - abs(np.random.normal(0, volatility * 0.7))
        volume = int(np.random.lognormal(mean=11.5, sigma=0.5))

        # Occasionally inject a volume breakout
        if i % 45 == 0 and i > 0:
            volume *= 3
            if close_p > open_p:
                high_p += volatility

        data.append({
            "timestamp": timestamps[i].strftime("%Y-%m-%d %H:%M:%S"),
            "symbol": symbol,
            "open": round(open_p, 2),
            "high": round(high_p, 2),
            "low": round(low_p, 2),
            "close": round(close_p, 2),
            "volume": volume
        })

    df = pd.DataFrame(data)
    df.to_csv(output_path, index=False)
    return output_path


if __name__ == "__main__":
    path = generate_sample_ohlcv()
    print(f"Generated sample OHLCV data at {path}")
