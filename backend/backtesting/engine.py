"""Backtesting engine strictly avoiding look-ahead bias."""
import pandas as pd
import numpy as np
from typing import Dict, Any, List
from backend.indicators.engine import calculate_indicators
from backend.strategies.base_strategy import BaseStrategy, BreakoutStrategy, MomentumStrategy, TrendFollowingStrategy


def run_backtest(
    df: pd.DataFrame,
    strategy: BaseStrategy,
    initial_capital: float = 100000.0,
    risk_percentage: float = 0.005,
    min_risk_reward: float = 1.5
) -> Dict[str, Any]:
    # Calculate indicators over the entire series
    data = calculate_indicators(df)

    capital = initial_capital
    cash = initial_capital
    position = None  # None or dict: {side, entry_price, quantity, stop_loss, target, entry_time}
    trades = []
    equity_curve = []

    # Iterate candle by candle starting after indicator warm-up period (30 candles)
    for i in range(30, len(data)):
        curr_candle = data.iloc[i]
        c_open = curr_candle["open"]
        c_high = curr_candle["high"]
        c_low = curr_candle["low"]
        c_close = curr_candle["close"]
        ts = str(curr_candle.get("timestamp", f"Candle_{i}"))

        # 1. Manage open position exits on the current candle
        if position is not None:
            pos_side = position["side"]
            pos_entry = position["entry_price"]
            pos_sl = position["stop_loss"]
            pos_target = position["target"]
            pos_qty = position["quantity"]

            exit_price = None
            exit_reason = None

            if pos_side == "BUY":
                # Check stop-loss hit
                if c_low <= pos_sl:
                    exit_price = pos_sl
                    exit_reason = "STOP_LOSS"
                # Check target hit
                elif c_high >= pos_target:
                    exit_price = pos_target
                    exit_reason = "TARGET"

            if exit_price is not None:
                pnl = (exit_price - pos_entry) * pos_qty
                pnl_pct = (exit_price - pos_entry) / pos_entry * 100.0
                cash += (pos_qty * exit_price)
                capital = cash

                trades.append({
                    "symbol": position["symbol"],
                    "side": pos_side,
                    "quantity": pos_qty,
                    "entry_price": pos_entry,
                    "exit_price": round(exit_price, 2),
                    "stop_loss": pos_sl,
                    "target": pos_target,
                    "pnl": round(pnl, 2),
                    "pnl_percentage": round(pnl_pct, 2),
                    "entry_time": position["entry_time"],
                    "exit_time": ts,
                    "exit_reason": exit_reason
                })
                position = None

        # 2. Evaluate strategy only if not in position (one position at a time for backtest clarity)
        if position is None:
            # We pass data[:i+1] to strictly avoid look-ahead bias
            signal = strategy.evaluate(data.iloc[:i + 1], -1)
            if signal and signal.get("signal") == "BUY":
                entry_p = c_close
                sl = signal["stop_loss"]
                tgt = signal["target"]
                risk_per_share = abs(entry_p - sl)

                if risk_per_share > 0:
                    risk_budget = capital * risk_percentage
                    qty = int(risk_budget / risk_per_share)
                    cost = qty * entry_p

                    if cost <= cash and qty > 0:
                        cash -= cost
                        position = {
                            "symbol": signal.get("symbol", "ASSET"),
                            "side": "BUY",
                            "entry_price": entry_p,
                            "quantity": qty,
                            "stop_loss": sl,
                            "target": tgt,
                            "entry_time": ts
                        }

        # 3. Calculate portfolio equity at candle close
        unrealized = 0.0
        if position is not None:
            unrealized = (c_close - position["entry_price"]) * position["quantity"]

        current_equity = cash + (position["quantity"] * c_close if position else 0.0)
        equity_curve.append({
            "timestamp": ts,
            "equity": round(current_equity, 2),
            "close": c_close
        })

    # Close any remaining position at last candle close
    if position is not None:
        last_close = data.iloc[-1]["close"]
        pnl = (last_close - position["entry_price"]) * position["quantity"]
        pnl_pct = (last_close - position["entry_price"]) / position["entry_price"] * 100.0
        cash += (position["quantity"] * last_close)
        capital = cash

        trades.append({
            "symbol": position["symbol"],
            "side": position["side"],
            "quantity": position["quantity"],
            "entry_price": position["entry_price"],
            "exit_price": round(last_close, 2),
            "stop_loss": position["stop_loss"],
            "target": position["target"],
            "pnl": round(pnl, 2),
            "pnl_percentage": round(pnl_pct, 2),
            "entry_time": position["entry_time"],
            "exit_time": str(data.iloc[-1].get("timestamp", "")),
            "exit_reason": "END_OF_DATA"
        })

    # Performance Metrics
    total_trades = len(trades)
    winning_trades = [t for t in trades if t["pnl"] > 0]
    losing_trades = [t for t in trades if t["pnl"] <= 0]
    win_rate = round(len(winning_trades) / total_trades * 100.0, 2) if total_trades > 0 else 0.0

    total_gain = sum(t["pnl"] for t in winning_trades)
    total_loss = abs(sum(t["pnl"] for t in losing_trades))
    profit_factor = round(total_gain / (total_loss + 1e-10), 2) if total_loss > 0 else (99.0 if total_gain > 0 else 0.0)

    net_pnl = round(sum(t["pnl"] for t in trades), 2)
    net_pnl_pct = round((net_pnl / initial_capital) * 100.0, 2)
    avg_win = round(total_gain / len(winning_trades), 2) if winning_trades else 0.0
    avg_loss = round(total_loss / len(losing_trades), 2) if losing_trades else 0.0

    # Drawdown calculation
    eq_series = pd.Series([e["equity"] for e in equity_curve])
    peak = eq_series.cummax()
    drawdown = (eq_series - peak) / peak * 100.0
    max_drawdown = round(abs(drawdown.min()), 2) if not drawdown.empty else 0.0

    return {
        "strategy": strategy.name,
        "initial_capital": initial_capital,
        "final_capital": round(capital, 2),
        "net_pnl": net_pnl,
        "net_pnl_percentage": net_pnl_pct,
        "total_trades": total_trades,
        "winning_trades": len(winning_trades),
        "losing_trades": len(losing_trades),
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "max_drawdown": max_drawdown,
        "trades": trades,
        "equity_curve": equity_curve
    }
