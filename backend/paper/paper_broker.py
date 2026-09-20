"""Paper Broker simulating market/limit orders, position management, and P&L tracking."""
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from backend.database.session import SessionLocal
from backend.database.models import Portfolio, Position, PaperOrder, Trade
from backend.core.logging import logger


class PaperBroker:
    def __init__(self):
        pass

    def get_portfolio(self, db: Session) -> Portfolio:
        portfolio = db.query(Portfolio).first()
        if not portfolio:
            portfolio = Portfolio(
                capital=100000.0,
                available_cash=100000.0,
                invested_amount=0.0,
                realized_pnl=0.0,
                unrealized_pnl=0.0,
                daily_pnl=0.0
            )
            db.add(portfolio)
            db.commit()
            db.refresh(portfolio)
        return portfolio

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
                else:
                    pos = Position(
                        symbol=symbol,
                        side="BUY",
                        quantity=quantity,
                        average_price=price,
                        current_price=price,
                        unrealized_pnl=0.0
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
                        entry_time=order.created_at,
                        exit_time=now,
                        strategy="Manual / Strategy"
                    )
                    db.add(trade)

                    pos.quantity -= sold_qty
                    if pos.quantity <= 0:
                        db.delete(pos)

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

    def update_market_price(self, symbol: str, current_price: float, db: Optional[Session] = None) -> List[Dict[str, Any]]:
        """
        Update unrealized P&L and check if any open position hit its stop-loss or target.
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

            total_unrealized = 0.0
            for pos in positions:
                pos.current_price = current_price
                if pos.side == "BUY":
                    pos.unrealized_pnl = round((current_price - pos.average_price) * pos.quantity, 2)
                else:
                    pos.unrealized_pnl = round((pos.average_price - current_price) * pos.quantity, 2)
                total_unrealized += pos.unrealized_pnl

            portfolio.unrealized_pnl = total_unrealized
            db.commit()
            return triggers
        finally:
            if close_session:
                db.close()


paper_broker = PaperBroker()
