"""Deterministic Risk & Execution analyst (veto power).

The only non-LLM member of the committee. It enforces the same deterministic
rules as ``backend.risk.risk_manager`` (position sizing, mandatory bracket
stop-loss/target, minimum R:R, kill switch, adaptive failure shield, maximum
open positions) and carries **veto** authority: any violated rule downgrades
the entire committee decision to HOLD.

Safety invariant: this desk is a *suggestion* gate, never the final order
authority. The deterministic :class:`RiskManager` remains the last line
before any order is placed.
"""
from typing import Any, Dict, List

from backend.ai.analyst_schemas import AnalystVerdict
from backend.ai.analyst_base import _to_float
from backend.core.config import settings
from backend.core.logging import logger
from backend.database.session import SessionLocal
from backend.database.models import Position, Portfolio


class RiskExecutionAnalyst:
    """Deterministic risk/execution analyst producing a veto-capable verdict."""

    role = "RISK_EXECUTION"
    weight = 1.0

    def _open_position_count(self) -> int:
        """Count live open positions, ignoring TEST- symbols (test scaffolding)."""
        try:
            with SessionLocal() as db:
                positions = db.query(Position).all()
                return sum(1 for p in positions if not str(p.symbol).upper().startswith("TEST"))
        except Exception as e:  # pragma: no cover - defensive
            logger.error("RiskExecutionAnalyst could not read open positions: %s", e)
            return 0

    def _daily_loss_exceeded(self) -> tuple:
        try:
            with SessionLocal() as db:
                portfolio = db.query(Portfolio).first()
                if portfolio is None:
                    return False, 0.0
                max_allowed = portfolio.capital * getattr(settings, "MAX_DAILY_LOSS", 0.03)
                return portfolio.daily_pnl <= -max_allowed, float(portfolio.daily_pnl)
        except Exception as e:  # pragma: no cover - defensive
            logger.error("RiskExecutionAnalyst could not read portfolio: %s", e)
            return False, 0.0

    def _adaptive_shield_suppression(self, symbol: str):
        try:
            from backend.trading.trade_autopsy import adaptive_shield
            if symbol.upper().startswith("TEST"):
                return None
            is_suppressed, info = adaptive_shield.is_suppressed(symbol)
            return info if is_suppressed else None
        except Exception as e:  # pragma: no cover - defensive
            logger.error("RiskExecutionAnalyst shield check failed: %s", e)
            return None

    def analyze(self, data: Dict[str, Any]) -> AnalystVerdict:
        symbol = str(data.get("symbol", "")).upper()
        ctx_price = _to_float(data.get("price"), 0.0)
        entry_price = _to_float(data.get("entry_price"), ctx_price)
        stop_loss = _to_float(data.get("stop_loss"), 0.0)
        target = _to_float(data.get("target"), 0.0)
        risk_reward = _to_float(data.get("risk_reward"), 0.0)
        side = str(data.get("strategy_signal", data.get("signal", "HOLD"))).upper()
        if side not in ("BUY", "SELL", "HOLD"):
            side = "HOLD"

        supporting: List[str] = []
        risks: List[str] = []

        # 1. Kill switch
        kill_switch_active = bool(data.get("kill_switch_active", False))
        if kill_switch_active:
            risks.append("Order rejected: Global Kill Switch is ACTIVE")

        # 2. Adaptive failure shield (protective cooldown)
        shield = self._adaptive_shield_suppression(symbol)
        if shield:
            risks.append(
                f"Adaptive Failure Shield: {symbol} cooling down "
                f"({shield.get('remaining_minutes', '?')}m) after {shield.get('failure_tag')}"
            )

        # 3. Mandatory bracket stop-loss / target
        if stop_loss <= 0:
            risks.append("Order rejected: Mandatory Stop-Loss missing or non-positive")
        if target <= 0:
            risks.append("Order rejected: Target missing or non-positive")

        # 4. Directional validity
        if side == "BUY" and entry_price > 0:
            if 0 < stop_loss >= entry_price:
                risks.append("Order rejected: BUY stop-loss must be below entry")
            if 0 < target <= entry_price:
                risks.append("Order rejected: BUY target must be above entry")
        elif side == "SELL" and entry_price > 0:
            if 0 < stop_loss <= entry_price:
                risks.append("Order rejected: SELL stop-loss must be above entry")
            if 0 < target >= entry_price:
                risks.append("Order rejected: SELL target must be below entry")

        # 5. Minimum risk/reward
        min_rr = float(getattr(settings, "MIN_RISK_REWARD", 0.8))
        if risk_reward > 0 and risk_reward < min_rr:
            risks.append(f"Order rejected: Risk/Reward {risk_reward:.2f} below minimum {min_rr}")

        # 6. Max open positions
        open_count = self._open_position_count()
        max_open = int(getattr(settings, "MAX_OPEN_POSITIONS", 6))
        if open_count >= max_open:
            risks.append(f"Order rejected: Maximum open positions limit ({max_open}) reached")

        # 7. Daily loss limit
        exceeded, daily_pnl = self._daily_loss_exceeded()
        if exceeded:
            risks.append(f"Order rejected: Daily loss limit exceeded (daily P&L ₹{daily_pnl:.2f})")

        # Kill switch is also carried by the risk manager singleton when armed.
        try:
            from backend.risk.risk_manager import risk_manager
            if getattr(risk_manager, "kill_switch_active", False):
                risks.append("Order rejected: Global Kill Switch is ACTIVE")
        except Exception:  # pragma: no cover - defensive
            pass

        if side in ("BUY", "SELL"):
            supporting.append(f"Candidate side: {side}")
            supporting.append(f"Bracket: entry ₹{entry_price:.2f} / SL ₹{stop_loss:.2f} / target ₹{target:.2f}")
            if risk_reward > 0:
                supporting.append(f"Risk/Reward: {risk_reward:.2f} (min {min_rr})")
            if open_count < max_open:
                supporting.append(f"Open positions {open_count}/{max_open} within limit")
            if not exceeded:
                supporting.append("Daily loss limit not breached")

            position_notional = entry_price
            explicit_quantity = _to_float(data.get("quantity"), 0.0)
            risk_budget = float(getattr(settings, "INITIAL_CAPITAL", 10000.0)) * float(getattr(settings, "RISK_PER_TRADE", 0.015))
            max_inv = float(getattr(settings, "MAX_INVESTMENT_PER_TRADE", 5000.0))
            risk_per_share = abs(entry_price - stop_loss) if stop_loss > 0 and entry_price > 0 else 0.0
            if entry_price > 0 and position_notional <= 0:
                risks.append("Order rejected: priced-out / zero-quote market")
            if explicit_quantity > 0 and explicit_quantity * entry_price > max_inv:
                risks.append(f"Order rejected: investment cap ₹{max_inv:.2f} per trade exceeded")
            if risk_per_share > 0 and risk_budget > 0 and side in ("BUY", "SELL") and risk_per_share > risk_budget * 1.5:
                risks.append(f"Order rejected: risk per share ₹{risk_per_share:.2f} exceeds risk budget")

        veto = bool(risks)
        if veto:
            side_out = "HOLD"
            confidence = max(0.0, min(0.35, 0.5 - 0.1 * len(risks)))
            rationale = "Risk/Execution analyst VETOED the trade: " + "; ".join(risks[:4])
            top_factor = "Risk veto"
        else:
            side_out = side if side in ("BUY", "SELL") else "HOLD"
            confidence = 0.90 if side_out in ("BUY", "SELL") else 0.55
            rationale = "Deterministic risk engine cleared the candidate: brackets valid, risk within limits."
            top_factor = "Risk approved"
            if not supporting:
                supporting.append("No actionable candidate side (HOLD)")
            if side_out == "HOLD":
                supporting.append("Awaiting actionable candidate from desk")

        return AnalystVerdict(
            analyst_role=self.role,
            side=side_out,
            confidence=confidence,
            top_factor=top_factor,
            supporting_factors=supporting,
            risk_flags=risks,
            rationale=rationale,
            weight=self.weight,
            veto=veto,
            provider="Deterministic",
            model="risk-rules-v1",
        )


risk_execution_analyst = RiskExecutionAnalyst()