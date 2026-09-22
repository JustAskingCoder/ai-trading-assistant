"""Paper Broker simulating market/limit orders, position management, and P&L tracking."""
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from backend.database.session import SessionLocal
from backend.database.models import Portfolio, Position, PaperOrder, Trade
from backend.core.logging import logger
from backend.core.config import settings
from backend.risk.risk_manager import risk_manager


class PaperBroker:
    def __init__(self):
        pass

    def get_portfolio(self, db: Session) -> Portfolio:
        portfolio = db.query(Portfolio).first()
        if not portfolio:
            portfolio = Portfolio(
                capital=settings.INITIAL_CAPITAL,
                available_cash=settings.INITIAL_CAPITAL,
                invested_amount=0.0,
                realized_pnl=0.0,
                unrealized_pnl=0.0,
                daily_pnl=0.0
            )
            db.add(portfolio)
            db.commit()
            db.refresh(portfolio)
        return portfolio

    def reset_portfolio(self, db: Optional[Session] = None) -> Portfolio:
        """Reset portfolio back to initial settings capital, clear positions, and deactivate kill switch."""
        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            portfolio = self.get_portfolio(db)
            portfolio.capital = settings.INITIAL_CAPITAL
            portfolio.available_cash = settings.INITIAL_CAPITAL
            portfolio.invested_amount = 0.0
            portfolio.realized_pnl = 0.0
            portfolio.unrealized_pnl = 0.0
            portfolio.daily_pnl = 0.0

            db.query(Position).delete()

            if risk_manager.kill_switch_active:
                risk_manager.deactivate_kill_switch(db_session=db)

            db.commit()
            db.refresh(portfolio)
            logger.info("Portfolio reset to ₹%.2f, positions cleared.", settings.INITIAL_CAPITAL)
            return portfolio
        finally:
            if close_session:
                db.close()

    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: float,
        stop_loss: Optional[float] = None,
        target: Optional[float] = None,
        order_type: str = "MARKET",
        window_minutes: Optional[int] = None,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """Execute a paper order and update positions & portfolio balance."""
        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            portfolio = self.get_portfolio(db)
            now = datetime.utcnow()

            is_forex = ("USD" in symbol or "EUR" in symbol or "GBP" in symbol)
            dec = 4 if is_forex else 2

            # Directional protection
            if side.upper() == 'BUY':
                if stop_loss is not None and stop_loss > 0 and stop_loss >= price:
                    stop_loss = round(price * 0.985, dec)
                if target is not None and target > 0 and target <= price:
                    target = round(price * 1.03, dec)
            elif side.upper() == 'SELL':
                if stop_loss is not None and stop_loss > 0 and stop_loss <= price:
                    stop_loss = round(price * 1.015, dec)
                if target is not None and target > 0 and target >= price:
                    target = round(price * 0.97, dec)

            # Record Paper Order
            effective_window = window_minutes if window_minutes is not None else (10 if symbol.startswith("TEST") else 30)
            order = PaperOrder(
                symbol=symbol,
                side=side.upper(),
                order_type=order_type.upper(),
                quantity=quantity,
                price=price,
                stop_loss=stop_loss,
                target=target,
                status="FILLED",
                window_minutes=effective_window,
                created_at=now,
                filled_at=now
            )
            db.add(order)

            # Update or create Position
            pos = db.query(Position).filter(Position.symbol == symbol).first()

            if side.upper() == "BUY":
                if pos and pos.side == "SELL" and pos.quantity > 0:
                    # Closing or reducing short position
                    covered_qty = min(quantity, pos.quantity)
                    pnl = round((pos.average_price - price) * covered_qty, 2)
                    pnl_pct = round((pos.average_price - price) / pos.average_price * 100.0, 2) if pos.average_price > 0 else 0.0

                    cost_basis = covered_qty * pos.average_price
                    portfolio.invested_amount -= cost_basis
                    portfolio.available_cash += (cost_basis + pnl)
                    portfolio.realized_pnl += pnl
                    portfolio.daily_pnl += pnl

                    # Record completed trade
                    trade = Trade(
                        symbol=symbol,
                        side="SELL",  # Short position entry side
                        quantity=covered_qty,
                        entry_price=pos.average_price,
                        exit_price=price,
                        stop_loss=stop_loss,
                        target=target,
                        pnl=pnl,
                        pnl_percentage=pnl_pct,
                        entry_time=pos.entry_time if getattr(pos, 'entry_time', None) else order.created_at,
                        exit_time=now,
                        strategy="Manual / Strategy"
                    )
                    db.add(trade)

                    pos.quantity -= covered_qty
                    rem_qty = quantity - covered_qty
                    if pos.quantity <= 0:
                        db.delete(pos)
                        pos = None

                    if rem_qty > 0:
                        rem_cost = rem_qty * price
                        portfolio.available_cash -= rem_cost
                        portfolio.invested_amount += rem_cost
                        new_pos = Position(
                            symbol=symbol,
                            side="BUY",
                            quantity=rem_qty,
                            average_price=price,
                            current_price=price,
                            unrealized_pnl=0.0,
                            stop_loss=stop_loss,
                            target=target,
                            entry_time=now,
                            window_minutes=effective_window
                        )
                        db.add(new_pos)
                elif pos and pos.side == "BUY":
                    # Adding to existing long position
                    cost = quantity * price
                    portfolio.available_cash -= cost
                    portfolio.invested_amount += cost
                    new_qty = pos.quantity + quantity
                    total_val = (pos.quantity * pos.average_price) + cost
                    pos.quantity = new_qty
                    pos.average_price = round(total_val / new_qty, 2)
                    pos.current_price = price
                    pos.stop_loss = stop_loss
                    pos.target = target
                    pos.window_minutes = effective_window
                    if not pos.entry_time:
                        pos.entry_time = now
                else:
                    # Opening new long position
                    cost = quantity * price
                    portfolio.available_cash -= cost
                    portfolio.invested_amount += cost
                    new_pos = Position(
                        symbol=symbol,
                        side="BUY",
                        quantity=quantity,
                        average_price=price,
                        current_price=price,
                        unrealized_pnl=0.0,
                        stop_loss=stop_loss,
                        target=target,
                        entry_time=now,
                        window_minutes=effective_window
                    )
                    db.add(new_pos)

            elif side.upper() == "SELL":
                if pos and pos.side == "BUY" and pos.quantity > 0:
                    # Closing or reducing long position
                    sold_qty = min(quantity, pos.quantity)
                    pnl = round((price - pos.average_price) * sold_qty, 2)
                    pnl_pct = round((price - pos.average_price) / pos.average_price * 100.0, 2) if pos.average_price > 0 else 0.0

                    cost_basis = sold_qty * pos.average_price
                    portfolio.invested_amount -= cost_basis
                    portfolio.available_cash += (sold_qty * price)
                    portfolio.realized_pnl += pnl
                    portfolio.daily_pnl += pnl

                    # Record completed trade
                    trade = Trade(
                        symbol=symbol,
                        side="BUY",  # Long position entry side
                        quantity=sold_qty,
                        entry_price=pos.average_price,
                        exit_price=price,
                        stop_loss=stop_loss,
                        target=target,
                        pnl=pnl,
                        pnl_percentage=pnl_pct,
                        entry_time=pos.entry_time if getattr(pos, 'entry_time', None) else order.created_at,
                        exit_time=now,
                        strategy="Manual / Strategy"
                    )
                    db.add(trade)

                    pos.quantity -= sold_qty
                    rem_qty = quantity - sold_qty
                    if pos.quantity <= 0:
                        db.delete(pos)
                        pos = None

                    if rem_qty > 0:
                        rem_cost = rem_qty * price
                        portfolio.available_cash -= rem_cost
                        portfolio.invested_amount += rem_cost
                        new_pos = Position(
                            symbol=symbol,
                            side="SELL",
                            quantity=rem_qty,
                            average_price=price,
                            current_price=price,
                            unrealized_pnl=0.0,
                            stop_loss=stop_loss,
                            target=target,
                            entry_time=now,
                            window_minutes=effective_window
                        )
                        db.add(new_pos)
                elif pos and pos.side == "SELL":
                    # Adding to existing short position
                    cost = quantity * price
                    portfolio.available_cash -= cost
                    portfolio.invested_amount += cost
                    new_qty = pos.quantity + quantity
                    total_val = (pos.quantity * pos.average_price) + cost
                    pos.quantity = new_qty
                    pos.average_price = round(total_val / new_qty, 2)
                    pos.current_price = price
                    pos.stop_loss = stop_loss
                    pos.target = target
                    pos.window_minutes = effective_window
                    if not pos.entry_time:
                        pos.entry_time = now
                else:
                    # Opening new short position
                    cost = quantity * price
                    portfolio.available_cash -= cost
                    portfolio.invested_amount += cost
                    new_pos = Position(
                        symbol=symbol,
                        side="SELL",
                        quantity=quantity,
                        average_price=price,
                        current_price=price,
                        unrealized_pnl=0.0,
                        stop_loss=stop_loss,
                        target=target,
                        entry_time=now,
                        window_minutes=effective_window
                    )
                    db.add(new_pos)

            db.flush()
            remaining = db.query(Position).all()
            portfolio.unrealized_pnl = round(sum(p.unrealized_pnl for p in remaining), 2)
            if not remaining:
                portfolio.invested_amount = 0.0

            db.commit()
            logger.info("PaperBroker filled %s order: %d %s @ ₹%.2f", side, quantity, symbol, price)
            return {
                "order_id": order.id,
                "status": "FILLED",
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": price,
                "timestamp": now.isoformat()
            }
        finally:
            if close_session:
                db.close()

    def update_market_price(
        self,
        symbol: str,
        current_price: float,
        candle_time: Optional[datetime] = None,
        db: Optional[Session] = None,
        invalidation_reason: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Update unrealized P&L and check if any open position hit its stop-loss, target, trend shift invalidation, or holding window limit.
        Returns list of any auto-triggered exits.
        """
        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        triggers = []
        try:
            portfolio = self.get_portfolio(db)
            positions = db.query(Position).filter(Position.symbol == symbol).all()

            for pos in list(positions):
                pos.current_price = current_price
                if pos.side == "BUY":
                    pos.unrealized_pnl = round((current_price - pos.average_price) * pos.quantity, 2)
                else:
                    pos.unrealized_pnl = round((pos.average_price - current_price) * pos.quantity, 2)

                # Trailing Breakeven Auto-Lock
                if pos.side == 'BUY' and pos.stop_loss and pos.stop_loss < pos.average_price:
                    if current_price >= pos.average_price * 1.003:  # +0.3% profit
                        pos.stop_loss = pos.average_price
                        triggers.append({'type': 'BREAKEVEN_TRAILED', 'symbol': pos.symbol, 'side': pos.side, 'breakeven_price': pos.average_price, 'current_price': current_price})
                elif pos.side == 'SELL' and pos.stop_loss and pos.stop_loss > pos.average_price:
                    if current_price <= pos.average_price * 0.997:  # +0.3% profit
                        pos.stop_loss = pos.average_price
                        triggers.append({'type': 'BREAKEVEN_TRAILED', 'symbol': pos.symbol, 'side': pos.side, 'breakeven_price': pos.average_price, 'current_price': current_price})

                reason = None
                if pos.side == 'BUY':
                    if pos.stop_loss is not None and current_price <= pos.stop_loss:
                        reason = 'Stop Loss Hit'
                    elif pos.target is not None and current_price >= pos.target:
                        reason = 'Target Hit'
                elif pos.side == 'SELL':
                    if pos.stop_loss is not None and current_price >= pos.stop_loss:
                        reason = 'Stop Loss Hit'
                    elif pos.target is not None and current_price <= pos.target:
                        reason = 'Target Hit'

                # Dynamic Trend Shift & Pattern Invalidation Early Guard
                if not reason and invalidation_reason and pos.unrealized_pnl < 0:
                    if getattr(settings, "AUTO_RELEASE_ON_TREND_SHIFT", True):
                        reason = f"Trend Shift ({invalidation_reason})"
                        logger.info(
                            "AUTO-RELEASE TRIGGERED for %s (%s): %s at price ₹%.2f (P&L: ₹%.2f)",
                            pos.symbol, pos.side, reason, current_price, pos.unrealized_pnl
                        )

                if pos.entry_time:
                    now_utc = datetime.utcnow()
                    pos_time = pos.entry_time
                    if isinstance(pos_time, str):
                        try:
                            pos_time = datetime.fromisoformat(pos_time.replace("Z", "+00:00"))
                        except Exception:
                            pass
                    pos_dt = pos_time.astimezone(timezone.utc).replace(tzinfo=None) if getattr(pos_time, 'tzinfo', None) is not None else pos_time
                    elapsed_sec = (now_utc - pos_dt).total_seconds()
                    window_m = getattr(pos, 'window_minutes', None)
                    if not window_m:
                        window_m = 10 if pos.symbol.startswith("TEST_") else 30
                    window_s = window_m * 60.0

                    window_expired = False
                    if elapsed_sec >= window_s:
                        window_expired = True
                    elif candle_time:
                        c_time = candle_time.astimezone(timezone.utc).replace(tzinfo=None) if getattr(candle_time, 'tzinfo', None) is not None else candle_time
                        try:
                            candle_elapsed_min = (c_time - pos_dt).total_seconds() / 60.0
                            if candle_elapsed_min >= window_m:
                                window_expired = True
                        except Exception:
                            pass

                    if window_expired and not reason:
                        if pos.symbol.startswith("TEST_"):
                            reason = f"{window_m}-Min Window Expired" if window_m != 10 else "10-Min Window Expired"
                        elif pos.unrealized_pnl > 0 and window_m < 90:
                            # Position is in profit! Lock breakeven stop loss and extend window by 15 mins to let winner run
                            if pos.side == 'BUY' and (pos.stop_loss is None or pos.stop_loss < pos.average_price):
                                pos.stop_loss = pos.average_price
                            elif pos.side == 'SELL' and (pos.stop_loss is None or pos.stop_loss > pos.average_price):
                                pos.stop_loss = pos.average_price
                            pos.window_minutes = window_m + 15
                            triggers.append({
                                'type': 'WINDOW_EXTENDED_IN_PROFIT',
                                'symbol': pos.symbol,
                                'side': pos.side,
                                'breakeven_locked': pos.stop_loss,
                                'new_window_minutes': pos.window_minutes,
                                'unrealized_pnl': pos.unrealized_pnl
                            })
                            logger.info(
                                "Position %s (%s) profitable (+₹%.2f) at %dm expiry; extended to %dm with breakeven SL @ ₹%.2f",
                                pos.symbol, pos.side, pos.unrealized_pnl, window_m, pos.window_minutes, pos.stop_loss
                            )
                        else:
                            reason = f"{window_m}-Min Window Expired"

                if reason is not None:
                    exit_record = {
                        'type': 'AUTO_EXIT',
                        'symbol': pos.symbol,
                        'side': pos.side,
                        'quantity': pos.quantity,
                        'exit_price': current_price,
                        'stop_loss': pos.stop_loss,
                        'target': pos.target,
                        'reason': reason,
                        'pnl': round((current_price - pos.average_price) * pos.quantity, 2) if pos.side == 'BUY' else round((pos.average_price - current_price) * pos.quantity, 2)
                    }
                    triggers.append(exit_record)

                    # Trigger market exit order
                    self.place_order(
                        symbol=pos.symbol,
                        side='SELL' if pos.side == 'BUY' else 'BUY',
                        quantity=pos.quantity,
                        price=current_price,
                        stop_loss=pos.stop_loss,
                        target=pos.target,
                        order_type='MARKET',
                        db=db
                    )

                    # Update the last created trade's strategy to f'Bracket Auto-Exit ({reason})'
                    last_trade = db.query(Trade).filter(Trade.symbol == pos.symbol).order_by(Trade.id.desc()).first()
                    if last_trade:
                        last_trade.strategy = f'Bracket Auto-Exit ({reason})'
                        db.commit()

            remaining_positions = db.query(Position).all()
            portfolio.unrealized_pnl = round(sum(p.unrealized_pnl for p in remaining_positions), 2)
            db.commit()
            return triggers
        finally:
            if close_session:
                db.close()


paper_broker = PaperBroker()
