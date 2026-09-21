"""Deterministic Risk Management Engine for AI Trading Assistant."""
from typing import Dict, Any, Tuple, Optional
from backend.core.config import settings
from backend.core.logging import logger
from backend.database.session import SessionLocal
from backend.database.models import Portfolio, Position, RiskEvent


class RiskManager:
    def __init__(self, db_session=None):
        self.kill_switch_active = False
        self._db = db_session

    def activate_kill_switch(self, reason: str = "Manual activation") -> None:
        self.kill_switch_active = True
        logger.warning("KILL SWITCH ACTIVATED: %s", reason)
        self._log_risk_event("KILL_SWITCH_ON", f"Kill switch activated: {reason}", "CRITICAL")

    def deactivate_kill_switch(self, db_session=None) -> None:
        self.kill_switch_active = False
        logger.info("Kill switch deactivated.")
        self._log_risk_event("KILL_SWITCH_OFF", "Kill switch deactivated by operator", "INFO", db_session=db_session)

    def _log_risk_event(self, event_type: str, description: str, severity: str = "WARNING", db_session=None):
        should_close = False
        if db_session:
            db = db_session
        elif self._db:
            db = self._db
        else:
            db = SessionLocal()
            should_close = True
        try:
            event = RiskEvent(
                event_type=event_type,
                description=description,
                severity=severity
            )
            db.add(event)
            db.commit()
        except Exception as e:
            logger.error("Failed to log risk event: %s", e)
        finally:
            if should_close:
                db.close()

    def evaluate_order(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        stop_loss: float,
        target: float,
        portfolio: Portfolio,
        open_positions_count: int,
        requested_quantity: Optional[int] = None
    ) -> Tuple[bool, int, str]:
        """
        Evaluate if a proposed order meets deterministic risk rules and calculate quantity.
        Returns: (approved: bool, quantity: int, reason: str)
        """
        # 1. Check Kill Switch
        if self.kill_switch_active:
            reason = "Order rejected: Global Kill Switch is ACTIVE."
            self._log_risk_event("REJECT_KILL_SWITCH", reason, "CRITICAL")
            return False, 0, reason

        # 2. Check Stop Loss Mandatory
        if stop_loss is None or stop_loss <= 0:
            reason = "Order rejected: Mandatory Stop-Loss missing or non-positive."
            self._log_risk_event("REJECT_NO_STOP_LOSS", reason, "HIGH")
            return False, 0, reason

        # 3. Check Directional Validity
        if side.upper() == "BUY":
            if stop_loss >= entry_price:
                reason = f"Order rejected: BUY Stop-loss ({stop_loss}) must be below Entry price ({entry_price})."
                return False, 0, reason
            if target <= entry_price:
                reason = f"Order rejected: BUY Target ({target}) must be above Entry price ({entry_price})."
                return False, 0, reason
        elif side.upper() == "SELL":
            if stop_loss <= entry_price:
                reason = f"Order rejected: SELL Stop-loss ({stop_loss}) must be above Entry price ({entry_price})."
                return False, 0, reason
            if target >= entry_price:
                reason = f"Order rejected: SELL Target ({target}) must be below Entry price ({entry_price})."
                return False, 0, reason

        # 4. Check Risk/Reward Ratio
        risk_per_share = abs(entry_price - stop_loss)
        reward_per_share = abs(target - entry_price)
        rr_ratio = reward_per_share / (risk_per_share + 1e-10)

        if rr_ratio < settings.MIN_RISK_REWARD:
            reason = f"Order rejected: Risk/Reward ratio {rr_ratio:.2f} is below minimum required {settings.MIN_RISK_REWARD}."
            self._log_risk_event("REJECT_LOW_RR", reason, "WARNING")
            return False, 0, reason

        # 5. Check Max Open Positions
        if open_positions_count >= settings.MAX_OPEN_POSITIONS:
            reason = f"Order rejected: Maximum open positions limit ({settings.MAX_OPEN_POSITIONS}) reached."
            self._log_risk_event("REJECT_MAX_POSITIONS", reason, "WARNING")
            return False, 0, reason

        # 6. Check Daily Loss Limit
        max_allowed_daily_loss = portfolio.capital * settings.MAX_DAILY_LOSS
        if portfolio.daily_pnl <= -max_allowed_daily_loss:
            reason = f"Order rejected: Daily loss limit exceeded (-₹{-portfolio.daily_pnl:.2f} >= max -₹{max_allowed_daily_loss:.2f})."
            self.activate_kill_switch("Daily loss limit exceeded")
            return False, 0, reason

        # 7. Position Sizing & Investment Cap
        max_trade_cap = getattr(settings, 'MAX_INVESTMENT_PER_TRADE', 5000.0)
        max_qty_by_cap = int(max_trade_cap / entry_price)
        if max_qty_by_cap <= 0:
            reason = f"Order rejected: Share price (₹{entry_price:.2f}) exceeds maximum ₹{max_trade_cap:.2f} investment limit per trade."
            self._log_risk_event("REJECT_TRADE_CAP", reason, "WARNING")
            return False, 0, reason

        risk_budget = portfolio.capital * settings.RISK_PER_TRADE
        if requested_quantity is not None and requested_quantity > 0:
            ideal_quantity = min(requested_quantity, max_qty_by_cap)
        else:
            ideal_quantity = int(risk_budget / (risk_per_share + 1e-10))
            if ideal_quantity <= 0:
                ideal_quantity = 1 if (1 * entry_price <= max_trade_cap and 1 * risk_per_share <= risk_budget * 1.5) else 0
                if ideal_quantity <= 0:
                    reason = f"Order rejected: Risk per share (₹{risk_per_share:.2f}) exceeds risk budget (₹{risk_budget:.2f})."
                    self._log_risk_event("REJECT_RISK_BUDGET", reason, "WARNING")
                    return False, 0, reason
        ideal_quantity = min(ideal_quantity, max_qty_by_cap)

        # 8. Check Available Cash / Exposure
        if ideal_quantity * entry_price > portfolio.available_cash:
            ideal_quantity = int(portfolio.available_cash / entry_price)
            if ideal_quantity <= 0:
                reason = f"Order rejected: Insufficient cash (Available: ₹{portfolio.available_cash:.2f}, Required: ₹{entry_price:.2f})."
                self._log_risk_event("REJECT_INSUFFICIENT_CASH", reason, "WARNING")
                return False, 0, reason

        logger.info(
            "Order APPROVED by RiskManager: %s %d %s @ ₹%.2f (Risk: ₹%.2f, R:R: %.2f)",
            side, ideal_quantity, symbol, entry_price, ideal_quantity * risk_per_share, rr_ratio
        )
        return True, ideal_quantity, "Order approved by deterministic risk engine."


risk_manager = RiskManager()
