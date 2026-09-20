"""Database table initialization script."""
from backend.database.session import engine, Base, SessionLocal
from backend.database.models import Portfolio, User
from backend.core.config import settings
from backend.core.logging import logger


def init_db():
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created.")

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
