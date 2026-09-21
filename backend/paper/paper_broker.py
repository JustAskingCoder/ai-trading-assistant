"""Paper Broker simulating market/limit orders, position management, and P&L tracking."""
from datetime import datetime
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

            # Directional protection
            if side.upper() == 'BUY':
                if stop_loss is not None and stop_loss > 0 and stop_loss >= price:
                    stop_loss = round(price * 0.985, 2)
                if target is not None and target > 0 and target <= price:
                    target = round(price * 1.03, 2)
            elif side.upper() == 'SELL':
                if stop_loss is not None and stop_loss > 0 and stop_loss <= price:
                    stop_loss = round(price * 1.015, 2)
                if target is not None and target > 0 and target >= price:
                    target = round(price * 0.97, 2)

            # Record Paper Order
            order = PaperOrder(
                symbol=symbol,
                side=side.upper(),
                order_type=order_type.upper(),
                quantity=quantity,
                price=price,
                stop_loss=stop_loss,
                target=target,
                status="FILLED",
                created_at=now,
                filled_at=now
            )
            db.add(order)

            # Update or create Position
            pos = db.query(Position).filter(Position.symbol == symbol).first()

            if side.upper() == "BUY":
                cost = quantity * price
                portfolio.available_cash -= cost
                portfolio.invested_amount += cost

                if pos:
                    new_qty = pos.quantity + quantity
                    total_val = (pos.quantity * pos.average_price) + cost
                    pos.quantity = new_qty
                    pos.average_price = round(total_val / new_qty, 2)
                    pos.current_price = price
                    pos.stop_loss = stop_loss
                    pos.target = target
                    if not pos.entry_time:
                        pos.entry_time = now
                else:
                    pos = Position(
                        symbol=symbol,
                        side="BUY",
                        quantity=quantity,
                        average_price=price,
                        current_price=price,
                        unrealized_pnl=0.0,
                        stop_loss=stop_loss,
                        target=target,
                        entry_time=now
                    )
                    db.add(pos)

            elif side.upper() == "SELL":
                # Closing or reducing position
                if pos and pos.quantity > 0:
                    sold_qty = min(quantity, pos.quantity)
                    pnl = round((price - pos.average_price) * sold_qty, 2)
                    pnl_pct = round((price - pos.average_price) / pos.average_price * 100.0, 2)

                    cost_basis = sold_qty * pos.average_price
                    portfolio.invested_amount -= cost_basis
                    portfolio.available_cash += (sold_qty * price)
                    portfolio.realized_pnl += pnl
                    portfolio.daily_pnl += pnl

                    # Record completed trade
                    trade = Trade(
                        symbol=symbol,
                        side="BUY",
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
                    if pos.quantity <= 0:
                        db.delete(pos)

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
        db: Optional[Session] = None
    ) -> List[Dict[str, Any]]:
        """
        Update unrealized P&L and check if any open position hit its stop-loss, target, or 10-minute window limit.
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

                if pos.entry_time:
                    now_utc = datetime.utcnow()
                    pos_time = pos.entry_time
                    if isinstance(pos_time, str):
                        try:
                            pos_time = datetime.fromisoformat(pos_time.replace("Z", "+00:00"))
                        except Exception:
                            pass
                    pos_dt = pos_time.replace(tzinfo=None) if getattr(pos_time, 'tzinfo', None) is not None else pos_time
                    elapsed_sec = (now_utc - pos_dt).total_seconds()
                    if elapsed_sec >= 600.0 and not reason:
                        reason = "10-Min Window Expired"
                    elif candle_time and not reason:
                        c_time = candle_time.replace(tzinfo=None) if getattr(candle_time, 'tzinfo', None) is not None else candle_time
                        try:
                            candle_elapsed_min = (c_time - pos_dt).total_seconds() / 60.0
                            if candle_elapsed_min >= 10.0:
                                reason = "10-Min Window Expired"
                        except Exception:
                            pass

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
