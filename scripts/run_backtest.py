import argparse
import logging
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.backtest.engine import BacktestEngine
from app.config.settings import get_settings
from app.database.db import SessionLocal, init_db
from app.database.repository import BarRepository
from app.strategy.strategy import SmaRsiStrategy

logger = logging.getLogger("run_backtest")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a backtest against locally stored bars and persist the result."
    )
    parser.add_argument(
        "--symbols",
        type=str,
        default=None,
        help="Comma-separated symbol list override. Default: configured universe.",
    )
    parser.add_argument(
        "--days-back",
        type=int,
        default=365,
        help="Only use bars within this many days of the latest bar. Default: 365.",
    )
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    args = parse_args()
    settings = get_settings()

    symbols = (
        [s.strip() for s in args.symbols.split(",") if s.strip()]
        if args.symbols
        else settings.symbol_list
    )

    init_db()

    logger.info("backtest started symbols=%s", symbols)

    session = SessionLocal()
    try:
        repository = BarRepository(session)
        bars_by_symbol: dict[str, list] = {}
        for symbol in symbols:
            latest = repository.get_latest_bar(symbol)
            if latest is None:
                logger.warning("no data for symbol=%s, skipping", symbol)
                continue
            start = latest.timestamp - timedelta(days=args.days_back)
            bars = repository.get_bars(symbol, start=start)
            if bars:
                bars_by_symbol[symbol] = bars
                logger.info("symbol=%s bars=%d", symbol, len(bars))

        if not bars_by_symbol:
            logger.error("no data available to backtest")
            return 1

        engine = BacktestEngine(
            strategy=SmaRsiStrategy(),
            initial_capital=settings.initial_capital,
            commission=settings.commission,
            slippage_bps=settings.slippage_bps,
            symbols=symbols,
        )
        result = engine.run(bars_by_symbol)
        repository.save_backtest_result(result)
        repository.session.commit()

        metrics = result.metrics
        logger.info(
            "backtest id=%s start=%s end=%s",
            result.backtest_id,
            result.params.start,
            result.params.end,
        )
        logger.info("final=%s total_return=%.2f%% annualized=%.2f%%",
                    round(metrics.final_capital, 2),
                    metrics.total_return * 100,
                    metrics.annualized_return * 100)
        logger.info("max_drawdown=%.2f%% sharpe=%.2f trades=%d win_rate=%.1f%%",
                    metrics.max_drawdown * 100,
                    metrics.sharpe_ratio,
                    metrics.num_trades,
                    metrics.win_rate * 100)
        logger.info("profit_factor=%s buy_and_hold_return=%.2f%%",
                    metrics.profit_factor,
                    result.buy_and_hold_return * 100)
    finally:
        session.close()

    logger.info("backtest completed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
