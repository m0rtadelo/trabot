import argparse
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config.settings import get_settings
from app.database.db import SessionLocal, init_db
from app.database.repository import BarRepository
from app.market.alpaca import AlpacaMarketDataProvider
from app.market.timeframe import drop_incomplete_bars
from app.market.validation import BarValidationError, validate_bars

logger = logging.getLogger("download_data")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download historical OHLCV bars from Alpaca into PostgreSQL."
    )
    parser.add_argument(
        "--start",
        type=str,
        default=None,
        help="Start date/time (ISO 8601, UTC). Default: --days-back ago.",
    )
    parser.add_argument(
        "--end",
        type=str,
        default=None,
        help="End date/time (ISO 8601, UTC). Default: now.",
    )
    parser.add_argument(
        "--days-back",
        type=int,
        default=365,
        help="How many days of history to fetch when --start is not given. Default: 365.",
    )
    parser.add_argument(
        "--symbols",
        type=str,
        default=None,
        help="Comma-separated symbol list override. Default: configured universe.",
    )
    args = parser.parse_args()

    if args.start is None:
        args.start = datetime.now(timezone.utc) - timedelta(days=args.days_back)
    else:
        args.start = datetime.fromisoformat(args.start)
        if args.start.tzinfo is None:
            args.start = args.start.replace(tzinfo=timezone.utc)

    if args.end is None:
        args.end = datetime.now(timezone.utc)
    else:
        args.end = datetime.fromisoformat(args.end)
        if args.end.tzinfo is None:
            args.end = args.end.replace(tzinfo=timezone.utc)

    return args


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

    logger.info("download started symbols=%s start=%s end=%s", symbols, args.start, args.end)

    init_db()

    try:
        provider = AlpacaMarketDataProvider(
            api_key=settings.alpaca_api_key,
            api_secret=settings.alpaca_api_secret,
            data_feed=settings.alpaca_data_feed,
        )
    except ValueError as exc:
        logger.error("failed to create provider: %s", exc)
        return 1

    session = SessionLocal()
    try:
        repository = BarRepository(session)
        for symbol in symbols:
            try:
                bars = provider.get_bars(
                    symbol=symbol,
                    timeframe=settings.timeframe,
                    start=args.start,
                    end=args.end,
                )
            except Exception as exc:
                logger.error("fetch failed symbol=%s error=%s", symbol, exc)
                continue

            bars = drop_incomplete_bars(bars, settings.timeframe, args.end)

            try:
                validate_bars(bars)
            except BarValidationError as exc:
                logger.error("invalid data symbol=%s error=%s", symbol, exc)
                continue

            inserted = repository.save_bars(bars)
            total = repository.count_bars(symbol)
            logger.info(
                "symbol=%s fetched=%d inserted=%d total=%d",
                symbol,
                len(bars),
                inserted,
                total,
            )
    finally:
        session.close()

    logger.info("download completed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
