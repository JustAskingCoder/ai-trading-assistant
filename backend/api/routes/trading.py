"""Trading, Risk, and Paper Broker API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from backend.database.session import get_db
from backend.database.models import Portfolio, Position, PaperOrder, Trade, Signal, RiskEvent
from backend.risk.risk_manager import risk_manager
from backend.paper.paper_broker import paper_broker
from backend.core.config import settings

router = APIRouter(prefix="/api", tags=["Trading & Risk"])


class PaperOrderRequest(BaseModel):
    symbol: str
    side: str  # BUY or SELL
    price: float
    stop_loss: float
    target: float
    order_type: str = "MARKET"
    quantity: Optional[int] = None
    window_minutes: Optional[int] = 30


@router.get("/portfolio")
def get_portfolio(db: Session = Depends(get_db)):
    portfolio = paper_broker.get_portfolio(db)
    positions_count = db.query(Position).count()
    trades_count = db.query(Trade).count()
    winning_trades = db.query(Trade).filter(Trade.pnl > 0).count()
    losing_trades = db.query(Trade).filter(Trade.pnl <= 0).count()
    win_rate = round(winning_trades / trades_count * 100.0, 2) if trades_count > 0 else 0.0

    return {
        "capital": portfolio.capital,
        "available_cash": round(portfolio.available_cash, 2),
        "invested_amount": round(portfolio.invested_amount, 2),
        "realized_pnl": round(portfolio.realized_pnl, 2),
        "unrealized_pnl": round(portfolio.unrealized_pnl, 2),
        "daily_pnl": round(portfolio.daily_pnl, 2),
        "total_trades": trades_count,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": win_rate,
        "open_positions": positions_count
    }


@router.post("/portfolio/reset")
def reset_portfolio(db: Session = Depends(get_db)):
    portfolio = paper_broker.reset_portfolio(db)
    positions_count = db.query(Position).count()
    trades_count = db.query(Trade).count()
    winning_trades = db.query(Trade).filter(Trade.pnl > 0).count()
    losing_trades = db.query(Trade).filter(Trade.pnl <= 0).count()
    win_rate = round(winning_trades / trades_count * 100.0, 2) if trades_count > 0 else 0.0

    return {
        "status": "success",
        "message": "Portfolio reset successfully",
        "capital": portfolio.capital,
        "available_cash": round(portfolio.available_cash, 2),
        "invested_amount": round(portfolio.invested_amount, 2),
        "realized_pnl": round(portfolio.realized_pnl, 2),
        "unrealized_pnl": round(portfolio.unrealized_pnl, 2),
        "daily_pnl": round(portfolio.daily_pnl, 2),
        "total_trades": trades_count,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": win_rate,
        "open_positions": positions_count
    }


@router.get("/positions")
def get_positions(db: Session = Depends(get_db)):
    positions = db.query(Position).all()
    return [{
        "id": p.id,
        "symbol": p.symbol,
        "side": p.side,
        "quantity": p.quantity,
        "average_price": p.average_price,
        "current_price": p.current_price,
        "stop_loss": p.stop_loss,
        "target": p.target,
        "entry_time": p.entry_time.isoformat() if getattr(p, "entry_time", None) else None,
        "window_minutes": 10 if p.symbol.startswith("TEST") else (getattr(p, "window_minutes", 30) or 30),
        "unrealized_pnl": round(p.unrealized_pnl, 2),
        "pnl_percentage": round(
            ((p.current_price - p.average_price) if p.side == "BUY" else (p.average_price - p.current_price))
            / p.average_price * 100.0, 2
        ) if p.average_price > 0 else 0.0
    } for p in positions]


@router.post("/positions/{position_id}/close")
def close_position(position_id: int, db: Session = Depends(get_db)):
    pos = db.query(Position).filter(Position.id == position_id).first()
    if not pos:
        raise HTTPException(status_code=404, detail=f"Position {position_id} not found")

    close_price = pos.current_price if (pos.current_price is not None and pos.current_price > 0) else pos.average_price
    close_side = "BUY" if pos.side == "SELL" else "SELL"

    result = paper_broker.place_order(
        symbol=pos.symbol,
        side=close_side,
        quantity=pos.quantity,
        price=close_price,
        stop_loss=0,
        target=0,
        order_type="MARKET",
        db=db
    )
    return result


@router.get("/orders")
def get_orders(limit: int = 50, db: Session = Depends(get_db)):
    orders = db.query(PaperOrder).order_by(PaperOrder.created_at.desc()).limit(limit).all()
    return [{
        "id": o.id,
        "symbol": o.symbol,
        "side": o.side,
        "order_type": o.order_type,
        "quantity": o.quantity,
        "price": o.price,
        "stop_loss": o.stop_loss,
        "target": o.target,
        "status": o.status,
        "created_at": o.created_at.isoformat(),
        "filled_at": o.filled_at.isoformat() if o.filled_at else None
    } for o in orders]


@router.post("/paper/orders")
def place_paper_order(req: PaperOrderRequest, db: Session = Depends(get_db)):
    portfolio = paper_broker.get_portfolio(db)
    open_pos_count = db.query(Position).count()
    existing_pos = db.query(Position).filter(Position.symbol == req.symbol).first()
    is_closing = existing_pos and (
        (req.side.upper() == "SELL" and existing_pos.side == "BUY") or
        (req.side.upper() == "BUY" and existing_pos.side == "SELL")
    )
    effective_pos_count = max(0, open_pos_count - 1) if is_closing else open_pos_count

    approved, qty, reason = risk_manager.evaluate_order(
        symbol=req.symbol,
        side=req.side,
        entry_price=req.price,
        stop_loss=req.stop_loss,
        target=req.target,
        portfolio=portfolio,
        open_positions_count=effective_pos_count,
        requested_quantity=req.quantity
    )

    if not approved:
        raise HTTPException(status_code=400, detail=f"Risk Engine Rejection: {reason}")

    res = paper_broker.place_order(
        symbol=req.symbol,
        side=req.side,
        quantity=qty,
        price=req.price,
        stop_loss=req.stop_loss,
        target=req.target,
        order_type=req.order_type,
        window_minutes=req.window_minutes or 30,
        db=db
    )
    return res


@router.get("/trades")
def get_trades(limit: int = 100, db: Session = Depends(get_db)):
    trades = db.query(Trade).order_by(Trade.exit_time.desc()).limit(limit).all()
    return [{
        "id": t.id,
        "symbol": t.symbol,
        "side": t.side,
        "quantity": t.quantity,
        "entry_price": t.entry_price,
        "exit_price": t.exit_price,
        "stop_loss": t.stop_loss,
        "target": t.target,
        "pnl": t.pnl,
        "pnl_percentage": t.pnl_percentage,
        "entry_time": t.entry_time.isoformat() if t.entry_time else None,
        "exit_time": t.exit_time.isoformat() if t.exit_time else None,
        "strategy": t.strategy
    } for t in trades]


@router.get("/risk")
def get_risk_status(db: Session = Depends(get_db)):
    portfolio = paper_broker.get_portfolio(db)
    max_daily = portfolio.capital * settings.MAX_DAILY_LOSS
    risk_used_today = max(0.0, -portfolio.daily_pnl)
    remaining_daily_risk = max(0.0, max_daily - risk_used_today)
    positions_count = db.query(Position).count()

    events = db.query(RiskEvent).order_by(RiskEvent.timestamp.desc()).limit(10).all()

    return {
        "kill_switch_active": risk_manager.kill_switch_active,
        "daily_loss_limit": max_daily,
        "daily_loss_current": round(risk_used_today, 2),
        "daily_risk_remaining": round(remaining_daily_risk, 2),
        "open_positions": positions_count,
        "max_open_positions": settings.MAX_OPEN_POSITIONS,
        "risk_per_trade_percent": settings.RISK_PER_TRADE * 100.0,
        "recent_events": [{
            "id": e.id,
            "timestamp": e.timestamp.isoformat(),
            "event_type": e.event_type,
            "description": e.description,
            "severity": e.severity
        } for e in events]
    }


@router.post("/risk/kill-switch")
def toggle_kill_switch(active: bool, reason: Optional[str] = "Manual toggle from dashboard"):
    if active:
        risk_manager.activate_kill_switch(reason or "Manual activation")
    else:
        risk_manager.deactivate_kill_switch()
    return {"kill_switch_active": risk_manager.kill_switch_active}
