"""Database table initialization script."""
from backend.database.session import engine, Base, SessionLocal
from backend.database.models import Portfolio, User
from backend.core.config import settings
from backend.core.logging import logger


def init_db():
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created.")

    # Ensure positions table has stop_loss and target columns
    with engine.connect() as conn:
        try:
            from sqlalchemy import text
            result = conn.execute(text("PRAGMA table_info(positions)")).fetchall()
            existing_cols = [row[1] for row in result]
            if "stop_loss" not in existing_cols:
                conn.execute(text("ALTER TABLE positions ADD COLUMN stop_loss FLOAT"))
            if "target" not in existing_cols:
                conn.execute(text("ALTER TABLE positions ADD COLUMN target FLOAT"))
            if "entry_time" not in existing_cols:
                conn.execute(text("ALTER TABLE positions ADD COLUMN entry_time TIMESTAMP"))
            if "window_minutes" not in existing_cols:
                conn.execute(text("ALTER TABLE positions ADD COLUMN window_minutes INTEGER DEFAULT 30"))

            orders_res = conn.execute(text("PRAGMA table_info(paper_orders)")).fetchall()
            order_cols = [row[1] for row in orders_res]
            if "window_minutes" not in order_cols:
                conn.execute(text("ALTER TABLE paper_orders ADD COLUMN window_minutes INTEGER DEFAULT 30"))

            conn.commit()
        except Exception as e:
            logger.warning("Could not verify/alter positions columns: %s", e)

    # Initialize default portfolio if not present
    db = SessionLocal()
    try:
        portfolio = db.query(Portfolio).first()
        if not portfolio:
            portfolio = Portfolio(
                capital=settings.INITIAL_CAPITAL,
                available_cash=settings.INITIAL_CAPITAL,
                invested_amount=0.0,
                realized_pnl=0.0,
                unrealized_pnl=0.0,
                daily_pnl=0.0,
            )
            db.add(portfolio)
            logger.info("Initialized default paper portfolio with capital %s", settings.INITIAL_CAPITAL)

        user = db.query(User).first()
        if not user:
            user = User(name="Default Trader")
            db.add(user)

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
