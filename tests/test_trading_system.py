"""Comprehensive test suite for AI Trading Assistant."""
import asyncio
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
from backend.database.models import Portfolio, Position, Trade
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
        assert len(triggers) == 1
        trig = triggers[0]
        assert trig["type"] == "AUTO_EXIT"
        assert trig["symbol"] == "TEST_TGT_HIT"
        assert trig["reason"] == "Target Hit"
        assert trig["exit_price"] == 3105.0
        assert trig["pnl"] == 275.0  # (3105 - 3050) * 5

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




