"""Comprehensive test suite for AI Trading Assistant."""
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch
import pytest
import pandas as pd
import numpy as np
from backend.data.data_validator import validate_ohlcv_dataframe
from backend.indicators.engine import calculate_indicators
from backend.patterns.engine import detect_all_patterns
from backend.strategies.base_strategy import MomentumStrategy, BreakoutStrategy, TrendFollowingStrategy
from backend.risk.risk_manager import RiskManager, risk_manager
from backend.paper.paper_broker import PaperBroker, paper_broker
from backend.backtesting.engine import run_backtest
from backend.ai.schemas import AIAnalysisResponse, EntryZone
from backend.database.session import SessionLocal, Base, engine
from backend.database.models import Portfolio, Position, Trade, PaperOrder
from backend.main import app
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def sample_df():
    # Generate deterministic 60-candle DataFrame
    np.random.seed(123)
    prices = [3000.0]
    for _ in range(60):
        prices.append(prices[-1] * (1 + np.random.normal(0.001, 0.005)))

    data = []
    for i in range(60):
        c = prices[i + 1]
        o = prices[i]
        h = max(o, c) + 5.0
        l = min(o, c) - 5.0
        data.append({
            "timestamp": f"2026-01-01 {9 + (i // 12):02d}:{(i % 12) * 5:02d}:00",
            "symbol": "TEST",
            "open": round(o, 2),
            "high": round(h, 2),
            "low": round(l, 2),
            "close": round(c, 2),
            "volume": 100000 + (i * 1000)
        })
    return pd.DataFrame(data)


def test_csv_validation(sample_df):
    is_valid, errors, meta = validate_ohlcv_dataframe(sample_df)
    assert is_valid is True
    assert len(errors) == 0
    assert meta["total_candles"] == 60


def test_indicator_calculations(sample_df):
    df_ind = calculate_indicators(sample_df)
    assert "ema20" in df_ind.columns
    assert "ema50" in df_ind.columns
    assert "rsi" in df_ind.columns
    assert "macd" in df_ind.columns
    assert "vwap" in df_ind.columns
    assert "atr" in df_ind.columns
    assert "bb_upper" in df_ind.columns
    assert "adx" in df_ind.columns
    assert not df_ind["ema20"].isnull().all()


def test_pattern_detection(sample_df):
    df_ind = calculate_indicators(sample_df)
    patterns = detect_all_patterns(df_ind, -1)
    assert isinstance(patterns, list)


def test_strategy_evaluation(sample_df):
    df_ind = calculate_indicators(sample_df)
    strategy = MomentumStrategy()
    signal = strategy.evaluate(df_ind, -1)
    # Signal may be None or a valid dict
    if signal:
        assert signal["signal"] in ["BUY", "SELL", "HOLD"]
        assert "stop_loss" in signal
        assert "target" in signal


def test_risk_manager_rules():
    rm = RiskManager()
    dummy_portfolio = Portfolio(capital=10000.0, available_cash=10000.0, daily_pnl=0.0)

    # 1. Valid BUY Order
    approved, qty, reason = rm.evaluate_order(
        symbol="TEST",
        side="BUY",
        entry_price=1000.0,
        stop_loss=980.0,
        target=1040.0,
        portfolio=dummy_portfolio,
        open_positions_count=0
    )
    assert approved is True
    assert qty > 0
    # Risk budget = 10000 * 0.015 = 150
    assert qty * 20.0 <= 150.0
    # Max investment cap = 5000
    assert qty * 1000.0 <= 5000.0

    # 2. Invalid Stop Loss (Stop above entry for BUY)
    app_inv, _, _ = rm.evaluate_order(
        symbol="TEST",
        side="BUY",
        entry_price=1000.0,
        stop_loss=1020.0,
        target=1050.0,
        portfolio=dummy_portfolio,
        open_positions_count=0
    )
    assert app_inv is False

    # 3. Low Risk/Reward ratio
    app_rr, _, _ = rm.evaluate_order(
        symbol="TEST",
        side="BUY",
        entry_price=1000.0,
        stop_loss=980.0,
        target=1010.0,  # RR = 10/20 = 0.5 < 1.5
        portfolio=dummy_portfolio,
        open_positions_count=0
    )
    assert app_rr is False

    # 4. Max Open Positions Limit
    app_pos, _, _ = rm.evaluate_order(
        symbol="TEST",
        side="BUY",
        entry_price=1000.0,
        stop_loss=980.0,
        target=1040.0,
        portfolio=dummy_portfolio,
        open_positions_count=3  # Max is 3
    )
    assert app_pos is False

    # 5. Kill Switch
    rm.activate_kill_switch("Test kill switch")
    app_kill, _, _ = rm.evaluate_order(
        symbol="TEST",
        side="BUY",
        entry_price=1000.0,
        stop_loss=980.0,
        target=1040.0,
        portfolio=dummy_portfolio,
        open_positions_count=0
    )
    assert app_kill is False


def test_ai_response_validation():
    valid_data = {
        "signal": "BUY",
        "confidence": 0.85,
        "setup": "Breakout Setup",
        "entry_zone": {"min": 100.0, "max": 102.0},
        "stop_loss": 98.0,
        "target": 108.0,
        "risk_reward": 2.5,
        "timeframe": "5m",
        "supporting_factors": ["Volume spike"],
        "risk_factors": ["Resistance overhead"],
        "invalidation_conditions": ["Price breaks below 98"]
    }
    validated = AIAnalysisResponse(**valid_data)
    assert validated.signal == "BUY"
    assert validated.confidence == 0.85


def test_backtest_execution(sample_df):
    strat = MomentumStrategy()
    res = run_backtest(sample_df, strat, initial_capital=10000.0)
    assert "total_trades" in res
    assert "win_rate" in res
    assert "equity_curve" in res
    assert len(res["equity_curve"]) > 0


def test_paper_broker_reset_portfolio():
    db = SessionLocal()
    try:
        # Place a paper order to create a position and spend cash
        paper_broker.place_order("TEST_RESET", "BUY", 10, 100.0, db=db)
        risk_manager.activate_kill_switch("Testing reset")

        # Confirm position exists and kill switch is active
        pos = db.query(Position).filter(Position.symbol == "TEST_RESET").first()
        assert pos is not None
        assert risk_manager.kill_switch_active is True

        # Perform reset
        pf = paper_broker.reset_portfolio(db)
        assert pf.capital == 10000.0
        assert pf.available_cash == 10000.0
        assert pf.invested_amount == 0.0
        assert pf.realized_pnl == 0.0
        assert pf.unrealized_pnl == 0.0
        assert pf.daily_pnl == 0.0

        # Assert positions cleared and kill switch deactivated
        positions = db.query(Position).all()
        assert len(positions) == 0
        assert risk_manager.kill_switch_active is False
    finally:
        db.close()


def test_portfolio_reset_api():
    client = TestClient(app)
    response = client.post("/api/portfolio/reset")
    assert response.status_code == 200
    data = response.json()
    assert data["capital"] == 10000.0
    assert data["available_cash"] == 10000.0
    assert data["invested_amount"] == 0.0
    assert data["open_positions"] == 0


def test_close_position_api():
    db = SessionLocal()
    try:
        # Create a test position
        paper_broker.place_order("TEST_CLOSE", "BUY", 5, 200.0, db=db)
        pos = db.query(Position).filter(Position.symbol == "TEST_CLOSE").first()
        assert pos is not None
        pos_id = pos.id

        client = TestClient(app)
        # Close the position
        resp = client.post(f"/api/positions/{pos_id}/close")
        assert resp.status_code == 200
        result = resp.json()
        assert result["status"] == "FILLED"
        assert result["side"] == "SELL"
        assert result["symbol"] == "TEST_CLOSE"
        assert result["quantity"] == 5

        # Verify position is gone
        closed_pos = db.query(Position).filter(Position.id == pos_id).first()
        assert closed_pos is None

        # Verify 404 for nonexistent position
        err_resp = client.post("/api/positions/9999999/close")
        assert err_resp.status_code == 404
    finally:
        # Reset portfolio cleanly after test
        paper_broker.reset_portfolio(db)
        db.close()


def test_stop_loss_hit_auto_exit():
    """Verify when position opened with stop_loss=3000 and target=3100, update_market_price with 2990 triggers Stop Loss Hit and closes position."""
    db = SessionLocal()
    try:
        paper_broker.reset_portfolio(db)
        # Open position with SL=3000, Target=3100
        order_res = paper_broker.place_order(
            symbol="TEST_SL_HIT",
            side="BUY",
            quantity=10,
            price=3050.0,
            stop_loss=3000.0,
            target=3100.0,
            db=db
        )
        assert order_res["status"] == "FILLED"

        # Check position in DB
        pos = db.query(Position).filter(Position.symbol == "TEST_SL_HIT").first()
        assert pos is not None
        assert pos.stop_loss == 3000.0
        assert pos.target == 3100.0

        # Check GET /api/positions includes stop_loss and target
        client = TestClient(app)
        api_res = client.get("/api/positions")
        assert api_res.status_code == 200
        positions_data = api_res.json()
        matching = [p for p in positions_data if p["symbol"] == "TEST_SL_HIT"]
        assert len(matching) == 1
        assert matching[0]["stop_loss"] == 3000.0
        assert matching[0]["target"] == 3100.0

        # Current price falls to 2990 (<= 3000 SL)
        triggers = paper_broker.update_market_price("TEST_SL_HIT", 2990.0, db=db)
        assert len(triggers) == 1
        trig = triggers[0]
        assert trig["type"] == "AUTO_EXIT"
        assert trig["symbol"] == "TEST_SL_HIT"
        assert trig["side"] == "BUY"
        assert trig["quantity"] == 10
        assert trig["exit_price"] == 2990.0
        assert trig["stop_loss"] == 3000.0
        assert trig["target"] == 3100.0
        assert trig["reason"] == "Stop Loss Hit"
        assert trig["pnl"] == -600.0  # (2990 - 3050) * 10

        # Verify position is closed
        closed_pos = db.query(Position).filter(Position.symbol == "TEST_SL_HIT").first()
        assert closed_pos is None

        # Verify trade recorded with Bracket Auto-Exit (Stop Loss Hit)
        trade = db.query(Trade).filter(Trade.symbol == "TEST_SL_HIT").order_by(Trade.id.desc()).first()
        assert trade is not None
        assert trade.exit_price == 2990.0
        assert trade.strategy == "Bracket Auto-Exit (Stop Loss Hit)"
        assert trade.pnl == -600.0
    finally:
        paper_broker.reset_portfolio(db)
        db.close()


def test_target_hit_auto_exit():
    """Verify when position opened with target=3100, update_market_price with 3105 triggers Target Hit and closes position."""
    db = SessionLocal()
    try:
        paper_broker.reset_portfolio(db)
        # Open position with SL=3000, Target=3100
        order_res = paper_broker.place_order(
            symbol="TEST_TGT_HIT",
            side="BUY",
            quantity=5,
            price=3050.0,
            stop_loss=3000.0,
            target=3100.0,
            db=db
        )
        assert order_res["status"] == "FILLED"

        # Check position in DB
        pos = db.query(Position).filter(Position.symbol == "TEST_TGT_HIT").first()
        assert pos is not None
        assert pos.target == 3100.0

        # Current price rises to 3105 (>= 3100 Target)
        triggers = paper_broker.update_market_price("TEST_TGT_HIT", 3105.0, db=db)
        auto_exits = [t for t in triggers if t["type"] == "AUTO_EXIT"]
        assert len(auto_exits) == 1
        trig = auto_exits[0]
        assert trig["type"] == "AUTO_EXIT"
        assert trig["symbol"] == "TEST_TGT_HIT"
        assert trig["reason"] == "Target Hit"
        assert trig["exit_price"] == 3105.0
        assert trig["pnl"] == 275.0  # (3105 - 3050) * 5
        assert any(t["type"] == "BREAKEVEN_TRAILED" for t in triggers)

        # Verify position is closed
        closed_pos = db.query(Position).filter(Position.symbol == "TEST_TGT_HIT").first()
        assert closed_pos is None

        # Verify trade recorded with Bracket Auto-Exit (Target Hit)
        trade = db.query(Trade).filter(Trade.symbol == "TEST_TGT_HIT").order_by(Trade.id.desc()).first()
        assert trade is not None
        assert trade.exit_price == 3105.0
        assert trade.strategy == "Bracket Auto-Exit (Target Hit)"
        assert trade.pnl == 275.0
    finally:
        paper_broker.reset_portfolio(db)
        db.close()


@pytest.mark.asyncio
async def test_market_simulator_auto_exit_broadcast(sample_df):
    from backend.data.market_simulator import simulator
    db = SessionLocal()
    q = simulator.subscribe()
    try:
        paper_broker.reset_portfolio(db)
        first_close = float(sample_df.iloc[0]["close"])
        # Place order with SL higher than first candle close to trigger immediate SL exit
        paper_broker.place_order("TEST", "BUY", 10, first_close + 10.0, stop_loss=first_close + 5.0, target=first_close + 50.0, db=db)

        simulator.load_dataset(sample_df)

        exits = paper_broker.update_market_price("TEST", first_close, db=db)
        assert len(exits) == 1
        assert exits[0]["reason"] == "Stop Loss Hit"

        await simulator.broadcast({"type": "AUTO_EXIT_TRIGGERED", "data": exits[0]})
        msg = await asyncio.wait_for(q.get(), timeout=2.0)
        assert msg["type"] == "AUTO_EXIT_TRIGGERED"
        assert msg["data"]["reason"] == "Stop Loss Hit"
    finally:
        simulator.unsubscribe(q)
        paper_broker.reset_portfolio(db)
        db.close()


def test_investment_cap_and_risk_limits():
    """Verify ₹5,000 investment cap per trade and risk budget rules."""
    rm = RiskManager()
    portfolio = Portfolio(capital=10000.0, available_cash=10000.0, daily_pnl=0.0)

    # 1. Share price exceeds ₹5,000 limit -> Rejected
    app, qty, reason = rm.evaluate_order(
        symbol="EXPENSIVE",
        side="BUY",
        entry_price=5500.0,
        stop_loss=5400.0,
        target=5700.0,
        portfolio=portfolio,
        open_positions_count=0
    )
    assert app is False
    assert qty == 0
    assert "exceeds maximum ₹5000.00 investment limit per trade" in reason

    # 2. Risk budget allows 15 shares, but ₹5,000 cap limits to 10 shares
    app, qty, reason = rm.evaluate_order(
        symbol="CAPPED",
        side="BUY",
        entry_price=500.0,
        stop_loss=490.0,
        target=520.0,
        portfolio=portfolio,
        open_positions_count=0
    )
    assert app is True
    assert qty == 10
    assert qty * 500.0 <= 5000.0

    # 3. Risk per share exceeds risk budget and 1.5x allowance -> Rejected
    app, qty, reason = rm.evaluate_order(
        symbol="HIGH_RISK",
        side="BUY",
        entry_price=1000.0,
        stop_loss=700.0,
        target=1600.0,
        portfolio=portfolio,
        open_positions_count=0
    )
    assert app is False
    assert qty == 0
    assert "exceeds risk budget" in reason

    # 4. Single share allowed if within 1.5x risk budget
    app, qty, reason = rm.evaluate_order(
        symbol="ONE_SHARE",
        side="BUY",
        entry_price=1000.0,
        stop_loss=820.0,
        target=1400.0,
        portfolio=portfolio,
        open_positions_count=0
    )
    assert app is True
    assert qty == 1
    assert qty * 1000.0 <= 5000.0

    # 5. Insufficient cash -> Rejected
    low_cash_portfolio = Portfolio(capital=10000.0, available_cash=400.0, daily_pnl=0.0)
    app, qty, reason = rm.evaluate_order(
        symbol="NO_CASH",
        side="BUY",
        entry_price=1000.0,
        stop_loss=980.0,
        target=1040.0,
        portfolio=low_cash_portfolio,
        open_positions_count=0
    )
    assert app is False
    assert qty == 0
    assert "Insufficient cash" in reason


def test_ten_minute_window_auto_exit():
    """Verify when position reaches 10 minutes without hitting SL or Target, update_market_price auto-closes it with reason '10-Min Window Expired'."""
    db = SessionLocal()
    try:
        paper_broker.reset_portfolio(db)
        order_res = paper_broker.place_order(
            symbol="TEST_EXPIRE",
            side="BUY",
            quantity=5,
            price=100.0,
            stop_loss=90.0,
            target=120.0,
            db=db
        )
        assert order_res["status"] == "FILLED"

        pos = db.query(Position).filter(Position.symbol == "TEST_EXPIRE").first()
        assert pos is not None
        assert pos.entry_time is not None

        # Check API returns entry_time and window_minutes
        client = TestClient(app)
        api_res = client.get("/api/positions")
        assert api_res.status_code == 200
        pos_data = [p for p in api_res.json() if p["symbol"] == "TEST_EXPIRE"][0]
        assert pos_data["entry_time"] is not None
        assert pos_data["window_minutes"] == 10

        entry_t = pos.entry_time

        # 1. Check at 5 minutes: price 105 (no SL, no target hit) -> should NOT trigger exit
        triggers_5m = paper_broker.update_market_price("TEST_EXPIRE", 105.0, candle_time=entry_t + timedelta(minutes=5), db=db)
        auto_exits_5m = [t for t in triggers_5m if t["type"] == "AUTO_EXIT"]
        assert len(auto_exits_5m) == 0
        assert any(t["type"] == "BREAKEVEN_TRAILED" for t in triggers_5m)

        # Position still open
        pos_still_open = db.query(Position).filter(Position.symbol == "TEST_EXPIRE").first()
        assert pos_still_open is not None

        # 2. Check at 10 minutes: price 105 -> should trigger '10-Min Window Expired'
        triggers_10m = paper_broker.update_market_price("TEST_EXPIRE", 105.0, candle_time=entry_t + timedelta(minutes=10), db=db)
        auto_exits_10m = [t for t in triggers_10m if t["type"] == "AUTO_EXIT"]
        assert len(auto_exits_10m) == 1
        trig = auto_exits_10m[0]
        assert trig["type"] == "AUTO_EXIT"
        assert trig["symbol"] == "TEST_EXPIRE"
        assert trig["reason"] == "10-Min Window Expired"
        assert trig["exit_price"] == 105.0
        assert trig["pnl"] == 25.0  # (105 - 100) * 5

        # Verify position is closed
        closed_pos = db.query(Position).filter(Position.symbol == "TEST_EXPIRE").first()
        assert closed_pos is None

        # Verify trade recorded with Bracket Auto-Exit (10-Min Window Expired)
        trade = db.query(Trade).filter(Trade.symbol == "TEST_EXPIRE").order_by(Trade.id.desc()).first()
        assert trade is not None
        assert trade.exit_price == 105.0
        assert trade.strategy == "Bracket Auto-Exit (10-Min Window Expired)"
        assert trade.pnl == 25.0
        assert trade.entry_time == entry_t
    finally:
        paper_broker.reset_portfolio(db)
        db.close()


def test_directional_protection():
    """Verify that place_order automatically guards invalid SL and Target to prevent immediate exits."""
    db = SessionLocal()
    try:
        paper_broker.reset_portfolio(db)
        # BUY with invalid stop_loss (>= price) and invalid target (<= price)
        order_buy = paper_broker.place_order(
            symbol="TEST_GUARD_BUY",
            side="BUY",
            quantity=5,
            price=1000.0,
            stop_loss=1050.0,  # invalid (>= 1000) -> should be round(1000 * 0.985, 2) = 985.0
            target=950.0,      # invalid (<= 1000) -> should be round(1000 * 1.03, 2) = 1030.0
            db=db
        )
        assert order_buy["status"] == "FILLED"
        pos_buy = db.query(Position).filter(Position.symbol == "TEST_GUARD_BUY").first()
        assert pos_buy is not None
        assert pos_buy.stop_loss == 985.0
        assert pos_buy.target == 1030.0
        assert pos_buy.entry_time is not None

        # Verify SELL directional protection
        # Place BUY first so we have inventory to SELL
        paper_broker.place_order(
            symbol="TEST_GUARD_SELL",
            side="BUY",
            quantity=10,
            price=1000.0,
            stop_loss=950.0,
            target=1100.0,
            db=db
        )
        # Now SELL with invalid SL (<= price) and target (>= price)
        order_sell = paper_broker.place_order(
            symbol="TEST_GUARD_SELL",
            side="SELL",
            quantity=5,
            price=1000.0,
            stop_loss=900.0,   # invalid (<= 1000) -> should be round(1000 * 1.015, 2) = 1015.0
            target=1050.0,    # invalid (>= 1000) -> should be round(1000 * 0.97, 2) = 970.0
            db=db
        )
        assert order_sell["status"] == "FILLED"
        order_rec = db.query(PaperOrder).filter(PaperOrder.id == order_sell["order_id"]).first()
        assert order_rec.stop_loss == 1015.0
        assert order_rec.target == 970.0
    finally:
        paper_broker.reset_portfolio(db)
        db.close()


def test_wall_clock_window_expiry():
    """Verify that update_market_price evaluates real wall-clock elapsed time >= 600s and triggers 10-Min Window Expired."""
    db = SessionLocal()
    try:
        paper_broker.reset_portfolio(db)
        paper_broker.place_order(
            symbol="TEST_WALLCLOCK",
            side="BUY",
            quantity=2,
            price=500.0,
            stop_loss=450.0,
            target=550.0,
            db=db
        )
        pos = db.query(Position).filter(Position.symbol == "TEST_WALLCLOCK").first()
        assert pos is not None

        # Manually backdate entry_time to 601 seconds ago
        pos.entry_time = datetime.utcnow() - timedelta(seconds=601)
        db.commit()

        # Update market price with candle_time=None (pure wall clock check)
        triggers = paper_broker.update_market_price("TEST_WALLCLOCK", 505.0, candle_time=None, db=db)
        auto_exits = [t for t in triggers if t["type"] == "AUTO_EXIT"]
        assert len(auto_exits) == 1
        assert auto_exits[0]["reason"] == "10-Min Window Expired"
        assert auto_exits[0]["symbol"] == "TEST_WALLCLOCK"
        assert any(t["type"] == "BREAKEVEN_TRAILED" for t in triggers)

        closed_pos = db.query(Position).filter(Position.symbol == "TEST_WALLCLOCK").first()
        assert closed_pos is None
    finally:
        paper_broker.reset_portfolio(db)
        db.close()


def test_risk_manager_requested_quantity():
    """Verify requested_quantity parameter in RiskManager.evaluate_order."""
    rm = RiskManager()
    portfolio = Portfolio(capital=10000.0, available_cash=10000.0, daily_pnl=0.0)

    # 1. requested_quantity provided and within cap
    app, qty, reason = rm.evaluate_order(
        symbol="TEST_QTY",
        side="BUY",
        entry_price=100.0,
        stop_loss=95.0,
        target=110.0,
        portfolio=portfolio,
        open_positions_count=0,
        requested_quantity=5
    )
    assert app is True
    assert qty == 5

    # 2. requested_quantity exceeds cap (requested 80, cap is 50) -> capped to 50
    app, qty, reason = rm.evaluate_order(
        symbol="TEST_QTY",
        side="BUY",
        entry_price=100.0,
        stop_loss=95.0,
        target=110.0,
        portfolio=portfolio,
        open_positions_count=0,
        requested_quantity=80
    )
    assert app is True
    assert qty == 50

    # 3. requested_quantity is None -> calculates based on risk budget
    app, qty, reason = rm.evaluate_order(
        symbol="TEST_QTY",
        side="BUY",
        entry_price=100.0,
        stop_loss=95.0,
        target=110.0,
        portfolio=portfolio,
        open_positions_count=0,
        requested_quantity=None
    )
    assert app is True
    assert qty == 29


def test_api_paper_order_with_requested_quantity():
    """Verify POST /api/paper/orders respects requested quantity."""
    db = SessionLocal()
    try:
        paper_broker.reset_portfolio(db)
        client = TestClient(app)
        res = client.post("/api/paper/orders", json={
            "symbol": "TEST_API_QTY",
            "side": "BUY",
            "price": 200.0,
            "stop_loss": 190.0,
            "target": 220.0,
            "quantity": 7
        })
        assert res.status_code == 200
        data = res.json()
        assert data["quantity"] == 7
        assert data["symbol"] == "TEST_API_QTY"
        assert data["status"] == "FILLED"

        pos = db.query(Position).filter(Position.symbol == "TEST_API_QTY").first()
        assert pos is not None
        assert pos.quantity == 7
    finally:
        paper_broker.reset_portfolio(db)
        db.close()


def test_trailing_breakeven_buy_and_sell():
    """Verify Trailing Breakeven Auto-Lock for BUY (+0.3%) and SELL (+0.3%) positions."""
    db = SessionLocal()
    try:
        paper_broker.reset_portfolio(db)
        # 1. Test BUY trailing breakeven
        paper_broker.place_order(
            symbol="TEST_BE_BUY",
            side="BUY",
            quantity=1,
            price=1000.0,
            stop_loss=980.0,
            target=1050.0,
            db=db
        )
        pos_buy = db.query(Position).filter(Position.symbol == "TEST_BE_BUY").first()
        assert pos_buy is not None
        assert pos_buy.stop_loss == 980.0

        # Sub-threshold price increase (1002.5 < 1003.0) -> No trailing breakeven
        trigs = paper_broker.update_market_price("TEST_BE_BUY", 1002.5, db=db)
        assert len([t for t in trigs if t["type"] == "BREAKEVEN_TRAILED"]) == 0
        db.refresh(pos_buy)
        assert pos_buy.stop_loss == 980.0

        # +0.3% price increase (1003.5 >= 1003.0) -> Triggers BREAKEVEN_TRAILED
        trigs = paper_broker.update_market_price("TEST_BE_BUY", 1003.5, db=db)
        be_trigs = [t for t in trigs if t["type"] == "BREAKEVEN_TRAILED"]
        assert len(be_trigs) == 1
        assert be_trigs[0]["breakeven_price"] == 1000.0
        assert be_trigs[0]["current_price"] == 1003.5
        db.refresh(pos_buy)
        assert pos_buy.stop_loss == 1000.0

        # Further price increase (1005.0) -> No duplicate BREAKEVEN_TRAILED
        trigs = paper_broker.update_market_price("TEST_BE_BUY", 1005.0, db=db)
        assert len([t for t in trigs if t["type"] == "BREAKEVEN_TRAILED"]) == 0

        # 2. Test SELL trailing breakeven
        pos_sell = Position(
            symbol="TEST_BE_SELL",
            side="SELL",
            quantity=1,
            average_price=1000.0,
            current_price=1000.0,
            unrealized_pnl=0.0,
            stop_loss=1020.0,
            target=950.0,
            entry_time=datetime.utcnow()
        )
        db.add(pos_sell)
        db.commit()

        # Sub-threshold price drop (997.5 > 997.0) -> No trailing breakeven
        trigs = paper_broker.update_market_price("TEST_BE_SELL", 997.5, db=db)
        assert len([t for t in trigs if t["type"] == "BREAKEVEN_TRAILED"]) == 0
        db.refresh(pos_sell)
        assert pos_sell.stop_loss == 1020.0

        # +0.3% price drop for short (996.5 <= 997.0) -> Triggers BREAKEVEN_TRAILED
        trigs = paper_broker.update_market_price("TEST_BE_SELL", 996.5, db=db)
        be_trigs = [t for t in trigs if t["type"] == "BREAKEVEN_TRAILED"]
        assert len(be_trigs) == 1
        assert be_trigs[0]["breakeven_price"] == 1000.0
        assert be_trigs[0]["current_price"] == 996.5
        db.refresh(pos_sell)
        assert pos_sell.stop_loss == 1000.0
    finally:
        paper_broker.reset_portfolio(db)
        db.close()


@pytest.mark.asyncio
async def test_market_simulator_breakeven_trailed_broadcast():
    """Verify market simulator broadcasts BREAKEVEN_TRAILED event when trailing breakeven occurs."""
    from backend.data.market_simulator import simulator
    db = SessionLocal()
    q = simulator.subscribe()
    try:
        paper_broker.reset_portfolio(db)
        paper_broker.place_order(
            symbol="TEST_SIM_BE",
            side="BUY",
            quantity=1,
            price=1000.0,
            stop_loss=980.0,
            target=1050.0,
            db=db
        )

        # Trigger update_market_price that produces BREAKEVEN_TRAILED
        events = paper_broker.update_market_price("TEST_SIM_BE", 1004.0, db=db)
        be_events = [e for e in events if e.get("type") == "BREAKEVEN_TRAILED"]
        assert len(be_events) == 1

        # Broadcast event
        await simulator.broadcast({"type": "BREAKEVEN_TRAILED", "data": be_events[0]})
        msg = await asyncio.wait_for(q.get(), timeout=2.0)
        assert msg["type"] == "BREAKEVEN_TRAILED"
        assert msg["data"]["symbol"] == "TEST_SIM_BE"
        assert msg["data"]["breakeven_price"] == 1000.0
    finally:
        simulator.unsubscribe(q)
        paper_broker.reset_portfolio(db)
        db.close()


def test_bidirectional_breakout_strategy():
    """Verify BreakoutStrategy BUY and SELL signals."""
    strat = BreakoutStrategy()

    rows = []
    for i in range(30):
        rows.append({
            "symbol": "BRK_TEST",
            "timestamp": f"2026-01-01 10:{i:02d}:00",
            "open": 1000.0,
            "high": 1005.0,
            "low": 995.0,
            "close": 1000.0,
            "volume": 1000,
            "volume_sma": 1000,
            "ema20": 1000.0,
            "ema50": 995.0,
            "rsi": 55.0,
            "adx": 20.0,
            "atr": 5.0
        })

    # 1. BUY scenario: close breaks resistance (1005.0)
    df_buy = pd.DataFrame(rows)
    df_buy.loc[28, "close"] = 1002.0
    df_buy.loc[29, "close"] = 1008.0
    df_buy.loc[29, "volume"] = 1500  # > 1.2 * 1000
    df_buy.loc[29, "ema20"] = 1002.0
    df_buy.loc[29, "ema50"] = 995.0
    df_buy.loc[29, "rsi"] = 58.0
    sig_buy = strat.evaluate(df_buy, -1)
    assert sig_buy is not None
    assert sig_buy["signal"] == "BUY"
    assert sig_buy["entry_price"] == 1008.0
    assert sig_buy["stop_loss"] < 1008.0
    assert sig_buy["target"] > 1008.0
    assert sig_buy["risk_reward"] >= 0.8

    # 2. SELL scenario: close breaks support (995.0)
    df_sell = pd.DataFrame(rows)
    df_sell.loc[28, "close"] = 997.0
    df_sell.loc[29, "close"] = 992.0
    df_sell.loc[29, "volume"] = 1500  # > 1.2 * 1000
    df_sell.loc[29, "ema20"] = 995.0
    df_sell.loc[29, "ema50"] = 1005.0  # ema20 < ema50
    df_sell.loc[29, "rsi"] = 42.0     # 32 <= rsi <= 52
    sig_sell = strat.evaluate(df_sell, -1)
    assert sig_sell is not None
    assert sig_sell["signal"] == "SELL"
    assert sig_sell["entry_price"] == 992.0
    assert sig_sell["stop_loss"] > 992.0
    assert sig_sell["target"] < 992.0
    assert sig_sell["risk_reward"] >= 0.8


def test_bidirectional_momentum_strategy():
    """Verify MomentumStrategy BUY and SELL signals."""
    strat = MomentumStrategy()

    rows = []
    for i in range(30):
        rows.append({
            "symbol": "MOM_TEST",
            "timestamp": f"2026-01-01 10:{i:02d}:00",
            "open": 1000.0,
            "high": 1005.0,
            "low": 995.0,
            "close": 1000.0,
            "volume": 1000,
            "ema20": 1000.0,
            "ema50": 990.0,
            "macd": 1.0,
            "macd_signal": 0.5,
            "rsi": 58.0,
            "atr": 5.0
        })

    # 1. BUY scenario
    df_buy = pd.DataFrame(rows)
    df_buy.loc[28, "macd"] = 1.0
    df_buy.loc[28, "macd_signal"] = 0.8
    df_buy.loc[29, "macd"] = 1.5
    df_buy.loc[29, "macd_signal"] = 0.9  # expanding
    df_buy.loc[29, "rsi"] = 56.0
    df_buy.loc[29, "close"] = 1002.0
    df_buy.loc[29, "ema20"] = 1000.0
    df_buy.loc[29, "ema50"] = 990.0
    sig_buy = strat.evaluate(df_buy, -1)
    assert sig_buy is not None
    assert sig_buy["signal"] == "BUY"
    assert sig_buy["entry_price"] == 1002.0
    assert sig_buy["stop_loss"] < 1002.0
    assert sig_buy["target"] > 1002.0
    assert sig_buy["risk_reward"] >= 0.8

    # 2. SELL scenario
    df_sell = pd.DataFrame(rows)
    df_sell.loc[28, "macd"] = -1.0
    df_sell.loc[28, "macd_signal"] = -0.8
    df_sell.loc[29, "macd"] = -1.6
    df_sell.loc[29, "macd_signal"] = -0.9  # expanding downwards
    df_sell.loc[29, "rsi"] = 42.0
    df_sell.loc[29, "close"] = 998.0
    df_sell.loc[29, "ema20"] = 1000.0
    df_sell.loc[29, "ema50"] = 1010.0
    sig_sell = strat.evaluate(df_sell, -1)
    assert sig_sell is not None
    assert sig_sell["signal"] == "SELL"
    assert sig_sell["entry_price"] == 998.0
    assert sig_sell["stop_loss"] > 998.0
    assert sig_sell["target"] < 998.0
    assert sig_sell["risk_reward"] >= 0.8


def test_bidirectional_trend_following_strategy():
    """Verify TrendFollowingStrategy BUY and SELL pullback entries."""
    strat = TrendFollowingStrategy()

    rows = []
    for i in range(30):
        rows.append({
            "symbol": "TRD_TEST",
            "timestamp": f"2026-01-01 10:{i:02d}:00",
            "open": 1000.0,
            "high": 1005.0,
            "low": 995.0,
            "close": 1000.0,
            "volume": 1000,
            "ema20": 1000.0,
            "ema50": 990.0,
            "vwap": 1000.0,
            "adx": 25.0,
            "atr": 5.0
        })

    # 1. BUY scenario: close > vwap, close <= vwap * 1.008, ema20 > ema50, adx > 18, close > open
    df_buy = pd.DataFrame(rows)
    df_buy.loc[29, "vwap"] = 1000.0
    df_buy.loc[29, "open"] = 1001.0
    df_buy.loc[29, "close"] = 1004.0
    df_buy.loc[29, "ema20"] = 1002.0
    df_buy.loc[29, "ema50"] = 995.0
    df_buy.loc[29, "adx"] = 22.0
    sig_buy = strat.evaluate(df_buy, -1)
    assert sig_buy is not None
    assert sig_buy["signal"] == "BUY"
    assert sig_buy["entry_price"] == 1004.0
    assert sig_buy["stop_loss"] < 1004.0
    assert sig_buy["target"] > 1004.0
    assert sig_buy["risk_reward"] >= 0.8

    # 2. SELL scenario: close < vwap, close >= vwap * 0.992, ema20 < ema50, adx > 18, close < open
    df_sell = pd.DataFrame(rows)
    df_sell.loc[29, "vwap"] = 1000.0
    df_sell.loc[29, "open"] = 999.0
    df_sell.loc[29, "close"] = 996.0
    df_sell.loc[29, "ema20"] = 995.0
    df_sell.loc[29, "ema50"] = 1005.0
    df_sell.loc[29, "adx"] = 22.0
    sig_sell = strat.evaluate(df_sell, -1)
    assert sig_sell is not None
    assert sig_sell["signal"] == "SELL"
    assert sig_sell["entry_price"] == 996.0
    assert sig_sell["stop_loss"] > 996.0
    assert sig_sell["target"] < 996.0
    assert sig_sell["risk_reward"] >= 0.8


def test_risk_manager_min_share_sizing_for_expensive_stocks():
    """Verify ideal_quantity defaults to 1 share minimal for stocks > ₹1,000 on ₹10k capital."""
    from backend.core.config import settings
    assert settings.MIN_RISK_REWARD == 0.8

    rm = RiskManager()
    portfolio = Portfolio(capital=10000.0, available_cash=10000.0, daily_pnl=0.0)

    # 1. Stock > ₹1,000 (e.g. ₹2,500) where risk_budget / risk_per_share would be 0
    app, qty, reason = rm.evaluate_order(
        symbol="TCS",
        side="BUY",
        entry_price=2500.0,
        stop_loss=2300.0,
        target=2700.0,
        portfolio=portfolio,
        open_positions_count=0
    )
    assert app is True
    assert qty == 1
    assert "approved" in reason.lower()

    # 2. Stock <= ₹1,000 (e.g. ₹1,000) with excessive risk (> 1.5x risk budget = 225) -> Still rejected
    app_low, qty_low, reason_low = rm.evaluate_order(
        symbol="CHEAP_RISKY",
        side="BUY",
        entry_price=1000.0,
        stop_loss=700.0,
        target=1600.0,
        portfolio=portfolio,
        open_positions_count=0
    )
    assert app_low is False
    assert qty_low == 0
    assert "exceeds risk budget" in reason_low


def test_live_market_service_symbol_mapping():
    """Verify symbol mapping for Indian NSE symbols and Yahoo Finance notation."""
    from backend.data.live_market_service import to_yf_symbol, LiveMarketService
    service = LiveMarketService()

    assert to_yf_symbol("RELIANCE") == "RELIANCE.NS"
    assert to_yf_symbol("reliance") == "RELIANCE.NS"
    assert to_yf_symbol("TCS") == "TCS.NS"
    assert to_yf_symbol("INFY") == "INFY.NS"
    assert to_yf_symbol("NIFTY") == "^NSEI"
    assert to_yf_symbol("BANKNIFTY") == "^NSEBANK"
    assert to_yf_symbol("TATAMOTORS.NS") == "TATAMOTORS.NS"
    assert to_yf_symbol("^NSEI") == "^NSEI"
    assert to_yf_symbol("UNMAPPED") == "UNMAPPED.NS"
    assert service.to_yf_symbol("RELIANCE") == "RELIANCE.NS"


def test_live_market_service_candles_mocked():
    """Verify get_latest_candles calculates indicators and formats records properly with mocked yfinance."""
    from unittest.mock import MagicMock, patch
    from backend.data.live_market_service import LiveMarketService

    service = LiveMarketService()
    dates = pd.date_range("2026-09-21 09:15", periods=35, freq="5min")
    mock_df = pd.DataFrame({
        "Open": np.linspace(100, 110, 35),
        "High": np.linspace(101, 111, 35),
        "Low": np.linspace(99, 109, 35),
        "Close": np.linspace(100.5, 110.5, 35),
        "Volume": [1000] * 35,
        "Dividends": [0.0] * 35,
        "Stock Splits": [0.0] * 35
    }, index=dates)

    with patch("yfinance.Ticker") as mock_ticker_cls:
        mock_instance = MagicMock()
        mock_instance.history.return_value = mock_df
        mock_ticker_cls.return_value = mock_instance

        candles = service.get_latest_candles("RELIANCE", "5m", limit=15)
        assert len(candles) == 15
        last = candles[-1]
        assert last["symbol"] == "RELIANCE"
        assert "timestamp" in last
        assert isinstance(last["timestamp"], str)
        assert "ema20" in last
        assert "rsi" in last
        assert "vwap" in last
        assert "atr" in last
        assert "macd" in last


@pytest.mark.asyncio
async def test_live_market_service_start_stop():
    """Verify start and stop methods and mode properties."""
    from backend.data.live_market_service import LiveMarketService
    service = LiveMarketService()

    assert service.mode == "SIMULATOR"
    assert service.is_running is False

    service.start("TCS", interval="5m")
    assert service.mode == "LIVE"
    assert service.symbol == "TCS"
    assert service.interval == "5m"
    assert service.is_running is True

    service.stop()
    assert service.mode == "SIMULATOR"
    assert service.is_running is False


def test_api_market_mode_endpoint():
    """Verify GET and POST /api/market/mode endpoint functionality and switching."""
    from backend.data.live_market_service import live_service
    from backend.data.market_simulator import simulator

    client = TestClient(app)

    # 1. Initial status
    res = client.get("/api/market/mode")
    assert res.status_code == 200
    data = res.json()
    assert "mode" in data
    assert "is_running" in data
    assert "symbol" in data

    # 2. Switch to LIVE mode
    res_live = client.post("/api/market/mode?mode=LIVE&symbol=INFY")
    assert res_live.status_code == 200
    data_live = res_live.json()
    assert data_live["status"] == "success"
    assert data_live["mode"] == "LIVE"
    assert data_live["symbol"] == "INFY"
    assert data_live["is_running"] is True
    assert live_service.mode == "LIVE"
    assert live_service.symbol == "INFY"
    assert simulator.is_running is False

    # 3. GET /api/market/mode in LIVE mode
    res_get_live = client.get("/api/market/mode")
    assert res_get_live.status_code == 200
    assert res_get_live.json()["mode"] == "LIVE"
    assert res_get_live.json()["symbol"] == "INFY"

    # 4. Switch to SIMULATOR mode
    res_sim = client.post("/api/market/mode?mode=SIMULATOR")
    assert res_sim.status_code == 200
    data_sim = res_sim.json()
    assert data_sim["status"] == "success"
    assert data_sim["mode"] == "SIMULATOR"
    assert data_sim["is_running"] is False
    assert live_service.mode == "SIMULATOR"
    assert live_service.is_running is False

    # 5. Invalid mode error check
    res_invalid = client.post("/api/market/mode?mode=INVALID")
    assert res_invalid.status_code == 400

    # Ensure clean state
    live_service.stop()


@pytest.mark.asyncio
async def test_get_candles_in_live_mode():
    """Verify get_candles returns records from live_service when mode is LIVE."""
    from unittest.mock import patch
    from backend.data.live_market_service import live_service

    client = TestClient(app)
    fake_candles = [
        {"timestamp": "2026-09-21 11:30:00", "open": 200.0, "high": 205.0, "low": 199.0, "close": 204.0, "volume": 1200.0, "symbol": "RELIANCE", "ema20": 202.0}
    ]

    try:
        live_service.start("RELIANCE")
        with patch.object(live_service, "get_latest_candles", return_value=fake_candles) as mock_candles:
            res = client.get("/api/market/RELIANCE/candles?limit=50")
            assert res.status_code == 200
            data = res.json()
            assert len(data) == 1
            assert data[0]["close"] == 204.0
            assert data[0]["symbol"] == "RELIANCE"
            mock_candles.assert_called_once_with("RELIANCE", interval="5m", limit=50)
    finally:
        live_service.stop()


@pytest.mark.asyncio
async def test_live_stream_loop_broadcasts_and_triggers():
    """Verify _live_stream_loop polls data, updates broker, and broadcasts candle & triggers."""
    from unittest.mock import MagicMock, patch
    from backend.data.live_market_service import LiveMarketService
    from backend.data.market_simulator import simulator

    service = LiveMarketService()
    dates = pd.date_range("2026-09-21 09:15", periods=30, freq="5min")
    mock_df = pd.DataFrame({
        "Open": np.linspace(100, 110, 30),
        "High": np.linspace(101, 111, 30),
        "Low": np.linspace(99, 109, 30),
        "Close": np.linspace(100.5, 110.5, 30),
        "Volume": [1000] * 30,
        "Dividends": [0.0] * 30,
        "Stock Splits": [0.0] * 30
    }, index=dates)

    q = simulator.subscribe()

    with patch("yfinance.Ticker") as mock_ticker_cls, \
         patch("backend.paper.paper_broker.paper_broker.update_market_price") as mock_broker_update:

        mock_instance = MagicMock()
        mock_instance.history.return_value = mock_df
        mock_ticker_cls.return_value = mock_instance

        mock_broker_update.return_value = [
            {"type": "BREAKEVEN_TRAILED", "symbol": "RELIANCE", "breakeven_price": 100.0, "current_price": 100.3},
            {"type": "AUTO_EXIT", "symbol": "RELIANCE", "side": "BUY", "quantity": 10, "exit_price": 110.0, "reason": "Target Hit", "pnl": 100.0}
        ]

        service.poll_interval = 0.01
        service.start("RELIANCE", "5m")

        # Receive broadcasts from queue
        msg1 = await asyncio.wait_for(q.get(), timeout=2.0)
        msg2 = await asyncio.wait_for(q.get(), timeout=2.0)
        msg3 = await asyncio.wait_for(q.get(), timeout=2.0)
        service.stop()

        types = {msg1.get("type"), msg2.get("type"), msg3.get("type")}
        assert "BREAKEVEN_TRAILED" in types
        assert "AUTO_EXIT_TRIGGERED" in types
        assert "CANDLE_UPDATE" in types
        simulator.unsubscribe(q)


def test_forex_symbol_mapping():
    """Verify Forex, Crypto, Commodity symbol mapping and market categorization."""
    from backend.data.live_market_service import to_yf_symbol, get_market_category

    # Forex pairs
    assert to_yf_symbol("USDINR") == "USDINR=X"
    assert to_yf_symbol("USD/INR") == "USDINR=X"
    assert to_yf_symbol("USD INR") == "USDINR=X"
    assert to_yf_symbol("EURUSD") == "EURUSD=X"
    assert to_yf_symbol("EUR/USD") == "EURUSD=X"
    assert to_yf_symbol("GBPUSD") == "GBPUSD=X"
    assert to_yf_symbol("GBP/USD") == "GBPUSD=X"
    assert to_yf_symbol("USDJPY") == "JPY=X"
    assert to_yf_symbol("EURINR") == "EURINR=X"
    assert to_yf_symbol("GBPINR") == "GBPINR=X"
    assert to_yf_symbol("AUDUSD") == "AUDUSD=X"
    assert to_yf_symbol("GOLD") == "GC=F"
    assert to_yf_symbol("BTCUSD") == "BTC-USD"
    assert to_yf_symbol("BTC-USD") == "BTC-USD"
    assert to_yf_symbol("USDINR=X") == "USDINR=X"

    # Market classifications
    assert get_market_category("USDINR") == "FOREX"
    assert get_market_category("USD/INR") == "FOREX"
    assert get_market_category("EURUSD") == "FOREX"
    assert get_market_category("GOLD") == "FOREX"
    assert get_market_category("BTCUSD") == "FOREX"
    assert get_market_category("RELIANCE") == "NSE"
    assert get_market_category("TCS") == "NSE"
    assert get_market_category("INFY") == "NSE"


def test_live_service_get_watchlist_quotes_mocked():
    """Verify get_watchlist_quotes correctly formats multi-asset quote metrics, trade brackets, and signals."""
    from unittest.mock import MagicMock, patch
    from backend.data.live_market_service import live_service

    dates = pd.date_range("2026-09-21 09:15", periods=30, freq="5min")
    mock_df = pd.DataFrame({
        "Open": np.linspace(100, 110, 30),
        "High": np.linspace(101, 111, 30),
        "Low": np.linspace(99, 109, 30),
        "Close": np.linspace(100.5, 110.5, 30),
        "Volume": [1000] * 30,
        "Dividends": [0.0] * 30,
        "Stock Splits": [0.0] * 30
    }, index=dates)

    with patch("yfinance.Ticker") as mock_ticker_cls:
        mock_inst = MagicMock()
        mock_inst.history.return_value = mock_df
        mock_ticker_cls.return_value = mock_inst

        quotes = live_service.get_watchlist_quotes(["RELIANCE", "USD/INR"])
        assert len(quotes) == 2

        rel = next(q for q in quotes if q["symbol"] == "RELIANCE")
        assert rel["market"] == "NSE"
        assert rel["price"] > 0
        assert "change" in rel
        assert "change_percentage" in rel
        assert "high" in rel
        assert "low" in rel
        assert "volume" in rel
        assert rel["signal"] in ["BUY", "SELL", "HOLD"]
        assert rel["action"] in ["BUY", "SELL", "WAIT"]
        assert rel["quantity"] == 1
        assert rel["entry_price"] == rel["price"]
        assert rel["stop_loss"] > 0
        assert rel["target"] > 0
        assert rel["risk_reward"] > 0
        assert rel["target_profit"] > 0
        assert rel["max_risk"] > 0
        assert isinstance(rel["reason"], str) and len(rel["reason"]) > 0
        assert isinstance(rel["strategy"], str) and len(rel["strategy"]) > 0
        assert 0.0 <= rel["confidence"] <= 1.0

        usdinr = next(q for q in quotes if q["symbol"] == "USD/INR")
        assert usdinr["market"] == "FOREX"
        assert usdinr["price"] > 0
        assert usdinr["signal"] in ["BUY", "SELL", "HOLD"]
        assert usdinr["action"] in ["BUY", "SELL", "WAIT"]
        assert usdinr["quantity"] == 1
        assert usdinr["stop_loss"] > 0
        assert usdinr["target"] > 0


def test_watchlist_actionable_trade_brackets():
    """Verify watchlist quotes return complete directional brackets without invalid SL/TP inversions."""
    from unittest.mock import MagicMock, patch
    from backend.data.live_market_service import LiveMarketService

    service = LiveMarketService()
    dates = pd.date_range("2026-09-21 09:15", periods=30, freq="5min")
    mock_df = pd.DataFrame({
        "Open": np.linspace(100, 110, 30),
        "High": np.linspace(101, 111, 30),
        "Low": np.linspace(99, 109, 30),
        "Close": np.linspace(100.5, 110.5, 30),
        "Volume": [1000] * 30,
        "Dividends": [0.0] * 30,
        "Stock Splits": [0.0] * 30
    }, index=dates)

    with patch("yfinance.Ticker") as mock_ticker_cls:
        mock_inst = MagicMock()
        mock_inst.history.return_value = mock_df
        mock_ticker_cls.return_value = mock_inst

        quotes = service.get_watchlist_quotes(["RELIANCE", "USDINR"])
        assert len(quotes) == 2
        for q in quotes:
            assert q["action"] in ["BUY", "SELL", "WAIT"]
            assert q["quantity"] == 1
            assert q["entry_price"] > 0
            assert q["stop_loss"] > 0
            assert q["target"] > 0
            assert q["risk_reward"] >= 0.8
            assert q["target_profit"] > 0
            assert q["max_risk"] > 0
            assert isinstance(q["reason"], str) and len(q["reason"]) > 0
            assert isinstance(q["strategy"], str) and len(q["strategy"]) > 0
            assert 0.0 <= q["confidence"] <= 1.0

            if q["action"] == "BUY":
                assert q["stop_loss"] < q["entry_price"], f"BUY stop loss ({q['stop_loss']}) must be < entry price ({q['entry_price']})"
                assert q["target"] > q["entry_price"], f"BUY target ({q['target']}) must be > entry price ({q['entry_price']})"
            elif q["action"] == "SELL":
                assert q["stop_loss"] > q["entry_price"], f"SELL stop loss ({q['stop_loss']}) must be > entry price ({q['entry_price']})"
                assert q["target"] < q["entry_price"], f"SELL target ({q['target']}) must be < entry price ({q['entry_price']})"


def test_no_fake_signals_when_strategies_hold_and_rr_guaranteed():
    """Verify that when strategies return no signal, signal is HOLD, action is WAIT, and R:R >= 0.8."""
    from unittest.mock import MagicMock, patch
    from backend.data.live_market_service import LiveMarketService

    service = LiveMarketService()
    dates = pd.date_range("2026-09-21 09:15", periods=30, freq="5min")
    mock_df = pd.DataFrame({
        "Open": [100.0] * 30,
        "High": [100.2] * 30,
        "Low": [99.8] * 30,
        "Close": [100.0] * 30,
        "Volume": [1000] * 30,
        "Dividends": [0.0] * 30,
        "Stock Splits": [0.0] * 30
    }, index=dates)

    with patch("yfinance.Ticker") as mock_ticker_cls:
        mock_inst = MagicMock()
        mock_inst.history.return_value = mock_df
        mock_ticker_cls.return_value = mock_inst

        quotes = service.get_watchlist_quotes(["RELIANCE", "USDINR"])
        for q in quotes:
            assert q["signal"] == "HOLD"
            assert q["action"] == "WAIT"
            assert q["strategy"] == "Consolidation"
            assert q["risk_reward"] >= 0.8
            assert "Consolidation" in q["reason"]

    # Test BUY signal generation when strategy evaluates BUY
    service.clear_cache()
    with patch("yfinance.Ticker") as mock_ticker_cls:
        mock_inst = MagicMock()
        mock_inst.history.return_value = mock_df
        mock_ticker_cls.return_value = mock_inst

        with patch.object(service.strategies[0], "evaluate", return_value={"strategy": "MockStrat", "signal": "BUY", "confidence": 0.85, "reason": "Mock breakout"}):
            buy_quotes = service.get_watchlist_quotes(["RELIANCE"])
            assert len(buy_quotes) == 1
            bq = buy_quotes[0]
            assert bq["signal"] == "BUY"
            assert bq["action"] == "BUY"
            assert bq["risk_reward"] >= 0.8
            assert bq["stop_loss"] < bq["entry_price"]
            assert bq["target"] > bq["entry_price"]

    # Test SELL signal generation when strategy evaluates SELL
    service.clear_cache()
    with patch("yfinance.Ticker") as mock_ticker_cls:
        mock_inst = MagicMock()
        mock_inst.history.return_value = mock_df
        mock_ticker_cls.return_value = mock_inst

        with patch.object(service.strategies[0], "evaluate", return_value={"strategy": "MockStrat", "signal": "SELL", "confidence": 0.85, "reason": "Mock breakdown"}):
            sell_quotes = service.get_watchlist_quotes(["RELIANCE"])
            assert len(sell_quotes) == 1
            sq = sell_quotes[0]
            assert sq["signal"] == "SELL"
            assert sq["action"] == "SELL"
            assert sq["risk_reward"] >= 0.8
            assert sq["stop_loss"] > sq["entry_price"]
            assert sq["target"] < sq["entry_price"]


def test_api_market_watchlist_endpoint():
    """Verify GET /api/market/watchlist endpoint returns multi-asset quote array with trade decisions."""
    from unittest.mock import patch
    from backend.data.live_market_service import live_service

    client = TestClient(app)

    mock_quotes = [
        {
            "symbol": "RELIANCE",
            "name": "Reliance Industries",
            "price": 1240.0,
            "change": 5.0,
            "change_percentage": 0.4,
            "open": 1235.0,
            "high": 1245.0,
            "low": 1230.0,
            "volume": 100000.0,
            "signal": "BUY",
            "action": "BUY",
            "quantity": 1,
            "entry_price": 1240.0,
            "stop_loss": 1232.0,
            "target": 1246.0,
            "risk_reward": 0.75,
            "target_profit": 6.0,
            "max_risk": 8.0,
            "reason": "Bullish momentum & 20 EMA pullback test",
            "strategy": "Scalp Pullback Strategy",
            "confidence": 0.82,
            "market": "NSE",
            "timestamp": "2026-09-21 12:00:00"
        },
        {
            "symbol": "USDINR",
            "name": "USD / INR",
            "price": 95.83,
            "change": -0.01,
            "change_percentage": -0.01,
            "open": 95.84,
            "high": 95.90,
            "low": 95.70,
            "volume": 0.0,
            "signal": "HOLD",
            "action": "WAIT",
            "quantity": 1,
            "entry_price": 95.83,
            "stop_loss": 95.25,
            "target": 96.30,
            "risk_reward": 0.81,
            "target_profit": 0.47,
            "max_risk": 0.58,
            "reason": "Consolidation / neutral range; awaiting directional breakout",
            "strategy": "Consolidation",
            "confidence": 0.50,
            "market": "FOREX",
            "timestamp": "2026-09-21 12:00:00"
        }
    ]

    with patch.object(live_service, "get_watchlist_quotes", return_value=mock_quotes) as mock_fn:
        res = client.get("/api/market/watchlist?symbols=RELIANCE,USDINR")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 2
        assert data[0]["symbol"] == "RELIANCE"
        assert data[0]["market"] == "NSE"
        assert data[0]["action"] == "BUY"
        assert data[0]["quantity"] == 1
        assert data[0]["entry_price"] == 1240.0
        assert data[0]["stop_loss"] == 1232.0
        assert data[0]["target"] == 1246.0
        assert data[0]["risk_reward"] == 0.75
        assert data[0]["target_profit"] == 6.0
        assert data[0]["max_risk"] == 8.0

        assert data[1]["symbol"] == "USDINR"
        assert data[1]["market"] == "FOREX"
        assert data[1]["action"] == "WAIT"
        mock_fn.assert_called_once_with(["RELIANCE", "USDINR"])


def test_zerodha_status_api():
    """Verify /api/zerodha/status endpoint returns valid status."""
    client = TestClient(app)
    res = client.get("/api/zerodha/status")
    assert res.status_code == 200
    data = res.json()
    assert "is_connected" in data
    assert "broker" in data
    assert data["broker"] == "Zerodha Kite"


def test_zerodha_connect_validation_error():
    """Verify missing credentials returns HTTP 400."""
    client = TestClient(app)
    # Missing enctoken in ENCTOKEN mode
    res = client.post("/api/zerodha/connect", json={"mode": "ENCTOKEN", "enctoken": ""})
    assert res.status_code == 400

    # Missing keys in API_KEY mode
    res2 = client.post("/api/zerodha/connect", json={"mode": "API_KEY", "api_key": ""})
    assert res2.status_code == 400


def test_zerodha_connect_and_disconnect_enctoken_mock():
    """Verify connecting with valid enctoken switches data_source and disconnects cleanly."""
    from backend.integrations.zerodha.kite_client import zerodha_client
    from backend.data.live_market_service import live_service

    client = TestClient(app)
    with patch.object(zerodha_client, "connect_with_enctoken", return_value=(True, "Successfully connected")):
        zerodha_client.user_id = "DEMO123"
        zerodha_client.user_name = "Jane Trader"
        zerodha_client.mode = "ENCTOKEN"
        zerodha_client.is_connected = True

        res = client.post("/api/zerodha/connect", json={"mode": "ENCTOKEN", "enctoken": "mock_enctoken_abc"})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "connected"
        assert data["data_source"] == "ZERODHA"
        assert live_service.data_source == "ZERODHA"

        # Check status endpoint reflects connection
        status_res = client.get("/api/zerodha/status")
        assert status_res.status_code == 200
        assert status_res.json()["is_connected"] is True

        # Disconnect
        disc_res = client.post("/api/zerodha/disconnect")
        assert disc_res.status_code == 200
        assert disc_res.json()["status"] == "disconnected"
        assert live_service.data_source == "YFINANCE"


def test_zerodha_batch_quotes_in_watchlist():
    """Verify get_watchlist_quotes uses Zerodha 0-delay batch quotes when connected."""
    from backend.integrations.zerodha.kite_client import zerodha_client
    from backend.data.live_market_service import live_service

    live_service.data_source = "ZERODHA"
    zerodha_client.is_connected = True

    mock_z_quotes = {
        "RELIANCE": {
            "symbol": "RELIANCE",
            "price": 3050.0,
            "change": 15.0,
            "change_percentage": 0.49,
            "open": 3035.0,
            "high": 3060.0,
            "low": 3030.0,
            "close": 3035.0,
            "volume": 1200000.0,
            "timestamp": "2026-09-21T12:00:00"
        }
    }

    try:
        with patch.object(zerodha_client, "get_quotes", return_value=mock_z_quotes):
            quotes = live_service.get_watchlist_quotes(["RELIANCE"])
            assert len(quotes) == 1
            assert quotes[0]["symbol"] == "RELIANCE"
            assert quotes[0]["price"] == 3050.0
            assert quotes[0]["source"] == "ZERODHA (0-DELAY)"
            assert quotes[0]["action"] == "BUY"
            assert quotes[0]["risk_reward"] >= 0.8
    finally:
        zerodha_client.is_connected = False
        live_service.data_source = "YFINANCE"


def test_short_order_creates_position_and_reflects_in_api():
    """Verify placing a standalone SELL order creates an open short Position and reflects in /api/positions."""
    from fastapi.testclient import TestClient
    from backend.main import app
    from backend.paper.paper_broker import paper_broker
    from backend.database.session import SessionLocal
    from backend.database.models import Position

    client = TestClient(app)
    db = SessionLocal()
    try:
        paper_broker.reset_portfolio(db)

        # 1. Place a standalone SELL order via paper/orders API
        resp = client.post("/api/paper/orders", json={
            "symbol": "INFY",
            "side": "SELL",
            "quantity": 2,
            "price": 1000.0,
            "stop_loss": 1015.0,
            "target": 970.0,
            "order_type": "MARKET"
        })
        assert resp.status_code == 200
        order_data = resp.json()
        assert order_data["status"] == "FILLED"
        assert order_data["side"] == "SELL"

        # 2. Check position exists in DB with side='SELL'
        pos = db.query(Position).filter(Position.symbol == "INFY").first()
        assert pos is not None
        assert pos.side == "SELL"
        assert pos.quantity == 2
        assert pos.average_price == 1000.0

        # 3. Check position reflects in GET /api/positions
        pos_resp = client.get("/api/positions")
        assert pos_resp.status_code == 200
        positions = pos_resp.json()
        matching = [p for p in positions if p["symbol"] == "INFY"]
        assert len(matching) == 1
        assert matching[0]["side"] == "SELL"
        assert matching[0]["quantity"] == 2

        # 4. Close the short position via API
        pos_id = matching[0]["id"]
        close_resp = client.post(f"/api/positions/{pos_id}/close")
        assert close_resp.status_code == 200

        # 5. Verify position is now removed
        pos_after = db.query(Position).filter(Position.symbol == "INFY").first()
        assert pos_after is None
    finally:
        paper_broker.reset_portfolio(db)
        db.close()


def test_short_position_pnl_and_cover():
    """Verify PnL calculation on short position when price drops (profit) and when covered by BUY."""
    from backend.paper.paper_broker import paper_broker
    from backend.database.session import SessionLocal
    from backend.database.models import Position, Trade

    sym = "TEST_SHORT_TCS"
    db = SessionLocal()
    try:
        paper_broker.reset_portfolio(db)
        db.query(Trade).filter(Trade.symbol == sym).delete()
        db.commit()

        # Open short: SELL 2 @ 3000
        res = paper_broker.place_order(sym, "SELL", 2, 3000.0, stop_loss=3045.0, target=2910.0, db=db)
        assert res["status"] == "FILLED"

        # Check unrealized PnL when price drops to 2950 (profit +100 for 2 shares)
        paper_broker.update_market_price(sym, 2950.0, db=db)
        pos = db.query(Position).filter(Position.symbol == sym).first()
        assert pos is not None
        assert pos.unrealized_pnl == 100.0  # (3000 - 2950) * 2

        # Cover 1 share with BUY @ 2950
        res_cover = paper_broker.place_order(sym, "BUY", 1, 2950.0, db=db)
        assert res_cover["status"] == "FILLED"
        pos = db.query(Position).filter(Position.symbol == sym).first()
        assert pos is not None
        assert pos.quantity == 1

        trade = db.query(Trade).filter(Trade.symbol == sym).order_by(Trade.id.desc()).first()
        assert trade is not None
        assert trade.pnl == 50.0  # (3000 - 2950) * 1

        # Cover remaining 1 share with BUY @ 2900
        paper_broker.place_order(sym, "BUY", 1, 2900.0, db=db)
        pos_final = db.query(Position).filter(Position.symbol == sym).first()
        assert pos_final is None

        trade2 = db.query(Trade).filter(Trade.symbol == sym).order_by(Trade.id.desc()).first()
        assert trade2 is not None
        assert trade2.pnl == 100.0  # (3000 - 2900) * 1

        port = paper_broker.get_portfolio(db)
        assert port.realized_pnl == 150.0  # 50 + 100
    finally:
        paper_broker.reset_portfolio(db)
        db.query(Trade).filter(Trade.symbol == sym).delete()
        db.commit()
        db.close()
