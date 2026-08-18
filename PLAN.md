# Trading Bot — V1 Development Plan

## 1. Project Goal

Build a fully automated stock-market analysis and paper-trading system running on a Raspberry Pi.

The first version will focus exclusively on the US stock market and will **not execute real trades**.

The system will:

1. Retrieve US stock market data from Alpaca.
2. Store historical and recent market data locally.
3. Analyze 1-hour candles.
4. Calculate technical indicators.
5. Generate BUY / SELL / HOLD signals using a deterministic strategy.
6. Simulate a portfolio starting with $10,000.
7. Persist all decisions and simulated trades.
8. Provide an API that can be triggered by Home Assistant.
9. Expose portfolio and strategy information to Home Assistant.
10. Support historical backtesting using the same strategy used by the live simulator.

The primary goal of V1 is **not to make money**.

The goal is to build a reliable infrastructure that allows us to determine whether a trading strategy has any measurable advantage.

---

# 2. Architecture

```text
                         INTERNET
                            │
                            ▼
                    ┌─────────────────┐
                    │     Alpaca      │
                    │  Market Data    │
                    └────────┬────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────┐
│                    Raspberry Pi                        │
│                                                        │
│  ┌──────────────────┐       ┌───────────────────────┐ │
│  │  Home Assistant  │──────▶│     Trading Bot       │ │
│  │                  │ HTTP  │                       │ │
│  │ Scheduler        │       │ Python                │ │
│  │ Dashboard        │◀──────│ REST API              │ │
│  └──────────────────┘       │ Strategy              │ │
│                             │ Indicators            │ │
│                             │ Portfolio             │ │
│                             │ Backtesting            │ │
│                             └───────────┬───────────┘ │
│                                         │             │
│                                         ▼             │
│                             ┌───────────────────────┐ │
│                             │     PostgreSQL         │ │
│                             └───────────────────────┘ │
│                                                        │
└────────────────────────────────────────────────────────┘
```

Home Assistant is responsible for scheduling and visualization.

The trading bot is responsible for all trading-related logic.

PostgreSQL is the persistent source of truth.

---

# 3. Technology Stack

## Runtime

* Python 3.x
* Docker
* Docker Compose

## Database

* PostgreSQL

## Market Data

* Alpaca Market Data API
* US equities
* 1-hour OHLCV bars

## API

* FastAPI
* Uvicorn

## Scheduling

Home Assistant automations will trigger the trading bot.

The trading bot itself must not depend on Home Assistant internally.

A future deployment should therefore also be possible using:

* cron
* systemd timers
* another scheduler

## Testing

* pytest

## Configuration

Environment variables loaded from `.env`.

Secrets must never be committed to Git.

---

# 4. Initial Project Structure

```text
trading-bot/
│
├── PLAN.md
├── README.md
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
│
├── app/
│   ├── main.py
│   │
│   ├── api/
│   │   └── routes.py
│   │
│   ├── config/
│   │   └── settings.py
│   │
│   ├── market/
│   │   ├── provider.py
│   │   └── alpaca.py
│   │
│   ├── indicators/
│   │   ├── trend.py
│   │   ├── momentum.py
│   │   └── volatility.py
│   │
│   ├── strategy/
│   │   └── strategy.py
│   │
│   ├── portfolio/
│   │   ├── portfolio.py
│   │   └── simulator.py
│   │
│   ├── backtest/
│   │   └── engine.py
│   │
│   └── database/
│       ├── models.py
│       └── repository.py
│
├── tests/
│   ├── indicators/
│   ├── strategy/
│   ├── portfolio/
│   └── backtest/
│
└── scripts/
    ├── download_data.py
    └── run_backtest.py
```

The exact structure may evolve during implementation, but responsibilities should remain separated.

---

# 5. Configuration

The application must be configured through environment variables.

Example:

```text
ALPACA_API_KEY=
ALPACA_API_SECRET=

DATABASE_URL=postgresql://trading:password@postgres:5432/trading

INITIAL_CAPITAL=1000

TIMEFRAME=1Hour

LOG_LEVEL=INFO
```

The actual `.env` file must not be committed.

A `.env.example` file must be provided.

---

# 6. Market Universe

V1 should use a small, explicitly configured set of US stocks.

Initial universe:

```text
AAPL
MSFT
NVDA
AMZN
GOOGL
META
TSLA
AMD
AVGO
JPM
```

The universe must be configurable without modifying Python code.

For example:

```text
SYMBOLS=AAPL,MSFT,NVDA,AMZN,GOOGL,META,TSLA,AMD,AVGO,JPM
```

Do not initially attempt to process the entire S&P 500.

The purpose is to validate the system first.

---

# 7. Market Data Layer

Create a provider abstraction.

Example interface:

```python
class MarketDataProvider:

    def get_bars(
        self,
        symbol,
        timeframe,
        start,
        end
    ):
        ...
```

Implement:

```text
AlpacaMarketDataProvider
```

The strategy must never directly call the Alpaca API.

This separation is important because another provider may be added later.

---

# 8. Market Data Storage

Store OHLCV bars in PostgreSQL.

Minimum fields:

```text
symbol
timestamp
open
high
low
close
volume
```

Add an appropriate unique constraint:

```text
(symbol, timestamp)
```

The downloader must be idempotent.

Running the downloader twice must not create duplicate candles.

---

# 9. Time Handling

All timestamps must be stored consistently.

Prefer UTC internally.

Market/session logic must use the appropriate US market timezone.

The application must not assume that the US market is always open.

The system must correctly handle:

* weekends
* US market holidays
* daylight saving time
* market open/close times

Do not hard-code Barcelona/local times into the trading engine.

---

# 10. Technical Indicators

V1 should initially implement a small number of standard indicators.

Required:

### Trend

* SMA 20
* SMA 50
* SMA 200

### Momentum

* RSI 14

### Volatility

* ATR 14

### Volume

* Volume moving average

The indicator implementation must be deterministic and independently testable.

---

# 11. Initial Strategy

V1 should deliberately use a simple deterministic strategy.

Do not use an LLM.

Do not use machine learning.

Example initial BUY conditions:

```text
SMA20 > SMA50
AND
SMA50 > SMA200
AND
RSI > 50
AND
RSI < 70
AND
Volume > Volume SMA
```

Example SELL conditions:

```text
SMA20 < SMA50
OR
RSI < 40
```

Otherwise:

```text
HOLD
```

This strategy is intentionally simple.

The purpose is to validate the infrastructure and backtesting engine, not to claim that this is a profitable strategy.

The strategy must be implemented behind an interface so that future strategies can be added.

---

# 12. Signal Model

Each strategy evaluation should produce a structured signal.

Example:

```json
{
  "symbol": "AAPL",
  "timestamp": "2026-08-13T14:00:00Z",
  "action": "BUY",
  "score": 0.75,
  "reason": [
    "SMA20 above SMA50",
    "SMA50 above SMA200",
    "RSI in bullish range",
    "Volume above average"
  ]
}
```

The reason for every signal must be persisted.

This is important for later analysis and debugging.

---

# 13. Portfolio Simulator

Start with:

```text
Initial capital: $1,000
```

The simulator must support:

* cash
* positions
* entry price
* quantity
* current market value
* realized P&L
* unrealized P&L
* total portfolio value

V1 should not use leverage.

Do not allow negative cash.

Do not allow short selling initially.

---

# 14. Position Sizing

V1 should use a simple fixed allocation model.

Example:

```text
Maximum position size: 20% of portfolio
```

Therefore:

```text
$1,000 portfolio
→ maximum $200 per position
```

The risk-management implementation must be separate from the strategy.

The strategy says:

```text
BUY
```

The risk manager decides:

```text
How much?
```

---

# 15. Transaction Costs

The simulator must support transaction costs even if V1 initially uses conservative assumptions.

At minimum support:

```text
commission
slippage
```

These should be configurable.

Example:

```text
COMMISSION=0
SLIPPAGE_BPS=5
```

The backtester must include these costs when calculating results.

This is important because a strategy that only works before transaction costs may not be useful.

---

# 16. Backtesting Engine

The backtesting engine is one of the most important components.

It must process historical candles chronologically.

Example:

```text
2022-01-03 10:00
2022-01-03 11:00
2022-01-03 12:00
...
```

At each candle:

1. Load all information available up to that timestamp.
2. Calculate indicators.
3. Generate the signal.
4. Apply risk management.
5. Simulate execution.
6. Update the portfolio.
7. Persist the result.

The system must never use future data.

---

# 17. Avoid Look-Ahead Bias

This is a hard requirement.

A strategy evaluating candle `T` must not have access to:

```text
T + 1
T + 2
...
```

For example, if a signal is generated from a candle that closes at 15:00, the simulated trade should not magically execute at the 15:00 opening price.

The execution model must reflect when the information became available.

---

# 18. Backtest Metrics

Every backtest must produce at least:

```text
Initial capital
Final capital
Total return
Annualized return
Maximum drawdown
Number of trades
Winning trades
Losing trades
Win rate
Average winning trade
Average losing trade
Profit factor
Sharpe ratio
```

Also generate an equity curve.

The result must be persisted with a unique backtest ID.

---

# 19. Backtest Comparison

The system must eventually compare the strategy against simple baselines.

At minimum:

```text
Strategy
Buy & Hold
```

For example:

```text
Strategy:       +18.4%
Buy & Hold:     +14.2%
```

A strategy that does not outperform a simple baseline after costs should not automatically be considered successful.

---

# 20. Live Simulation Mode

After backtesting works, implement a real-time simulation mode.

Every hour:

```text
Home Assistant
       │
       ▼
POST /api/run
       │
       ▼
Trading Bot
       │
       ├── fetch latest data
       ├── update database
       ├── calculate indicators
       ├── generate signals
       ├── simulate trades
       └── persist results
```

This mode uses real market data but does not send orders to a broker.

---

# 21. API

Minimum endpoints:

```text
GET  /health
POST /api/run
GET  /api/portfolio
GET  /api/positions
GET  /api/signals
GET  /api/performance
GET  /api/status
```

Example:

```text
POST /api/run
```

Triggers one complete analysis cycle.

The endpoint must be safe to call more than once for the same market candle.

---

# 22. Home Assistant Integration

Home Assistant should act as the scheduler and dashboard.

Create an automation that triggers:

```text
POST http://trading-bot:8000/api/run
```

The exact schedule should initially be conservative.

The bot itself should determine whether new market data is available.

Home Assistant should expose useful values such as:

```text
Portfolio value
Cash
Total P&L
Daily P&L
Drawdown
Open positions
Number of BUY signals
Number of SELL signals
Last execution
Last error
```

Do not put trading logic inside Home Assistant automations.

---

# 23. Logging

The application must provide structured logs.

Important events:

```text
Market data downloaded
Backtest started
Backtest completed
Signal generated
Order simulated
Portfolio updated
API request
Error
```

Every trading decision should be traceable.

Example:

```text
2026-08-13 15:00:02 INFO
AAPL BUY
price=215.42
quantity=0.92
reason="SMA20>SMA50, RSI=61.2, volume_above_average"
```

---

# 24. Error Handling

The system must tolerate:

* Alpaca API unavailable
* temporary network failure
* incomplete market data
* database unavailable
* invalid symbol
* market closed
* duplicate execution
* missing candles

A temporary API failure must not corrupt portfolio state.

A failed run must be visible from the API and Home Assistant.

---

# 25. Docker

The trading bot must run as a Docker container.

PostgreSQL must run as a separate container.

Example:

```text
docker compose up -d
```

Services:

```text
trading-bot
postgres
```

The database must use a persistent Docker volume.

The trading bot must restart automatically after a Raspberry Pi reboot.

---

# 26. Raspberry Pi Requirements

The application should be designed to run comfortably on a Raspberry Pi.

Do not assume:

* dedicated GPU
* large amount of RAM
* x86 architecture

Python dependencies must support ARM64.

The V1 system must not require a local LLM.

---

# 27. Testing Strategy

Unit tests are required for:

### Indicators

Test known input/output values.

### Strategy

Given known indicators:

```text
→ expected BUY
→ expected SELL
→ expected HOLD
```

### Portfolio

Test:

* buy
* sell
* partial allocation
* insufficient cash
* P&L
* multiple positions

### Backtesting

Use a small deterministic dataset and verify the final portfolio value exactly.

---

# 28. Development Phases

## Phase 1 — Infrastructure

* Create Git repository.
* Create Docker configuration.
* Create PostgreSQL container.
* Create Python application.
* Create configuration system.
* Create health endpoint.
* Verify deployment on Raspberry Pi.

Success criteria:

```text
docker compose up -d
```

works and:

```text
GET /health
```

returns:

```json
{
  "status": "ok"
}
```

---

## Phase 2 — Alpaca Data

* Create Alpaca provider.
* Download historical 1-hour bars.
* Store bars in PostgreSQL.
* Make downloads idempotent.
* Add data validation.

Success criteria:

Historical data for all configured symbols is stored correctly.

---

## Phase 3 — Indicators

Implement:

* SMA
* RSI
* ATR
* volume average

Add unit tests.

---

## Phase 4 — Strategy

Implement the initial deterministic strategy.

Generate structured BUY / SELL / HOLD signals.

Persist signals.

---

## Phase 5 — Portfolio Simulator

Implement:

* cash
* positions
* position sizing
* simulated orders
* slippage
* P&L

---

## Phase 6 — Backtesting

Implement the chronological backtesting engine.

Generate:

* equity curve
* performance metrics
* trade history

Compare against Buy & Hold.

---

## Phase 7 — Home Assistant

Add:

* hourly automation
* REST integration
* sensors
* dashboard

---

## Phase 8 — Real-Time Simulation

Run the strategy automatically using live market data.

No real orders.

Run this for an extended period.

---

# 29. Explicitly Out of Scope for V1

Do NOT implement these yet:

* Real trading
* Broker order execution
* Short selling
* Leverage
* Options
* Futures
* Crypto
* Machine learning
* LLM-based decisions
* News sentiment
* Fundamental analysis
* Automatic strategy optimization
* Genetic algorithms
* High-frequency trading
* Sub-minute data
* Multi-market support

These may be considered in later versions.

---

# 30. Future Architecture

Once V1 is proven, the architecture should allow:

```text
                 Market Data
                      │
       ┌──────────────┼───────────────┐
       ▼              ▼               ▼
   Technical      Fundamental      News/LLM
   Analysis        Analysis         Analysis
       │              │               │
       └──────────────┼───────────────┘
                      ▼
                Signal Engine
                      │
                      ▼
                 Risk Manager
                      │
                      ▼
              Execution Interface
                │             │
                ▼             ▼
             Simulator      Broker
```

Possible future additions:

* LLM analysis
* US + European markets
* additional data providers
* machine-learning models
* paper trading
* real broker integration
* advanced portfolio management

---

# 31. Core Principles

The following principles should be maintained throughout development:

1. **Simulation before real money.**
2. **Backtesting before live simulation.**
3. **No look-ahead bias.**
4. **Every decision must be reproducible.**
5. **Every trade must have an explanation.**
6. **Strategy and risk management must remain separate.**
7. **Market data providers must be abstracted.**
8. **Home Assistant must not contain trading logic.**
9. **All financial results must include transaction costs.**
10. **Never assume that a profitable backtest means the strategy will be profitable in reality.**
11. **Prefer simple strategies that can be measured and understood.**
12. **Do not introduce an LLM until the deterministic baseline has been validated.**

---

# 32. V1 Definition of Done

V1 is considered complete when the following workflow works end-to-end:

```text
Alpaca
   │
   ▼
Historical 1h data
   │
   ▼
PostgreSQL
   │
   ▼
Indicators
   │
   ▼
Strategy
   │
   ▼
Portfolio Simulator
   │
   ▼
Backtest
   │
   ├── Performance metrics
   ├── Trade history
   └── Equity curve
```

And:

```text
Home Assistant
      │
      ▼
POST /api/run
      │
      ▼
Latest market data
      │
      ▼
Strategy
      │
      ▼
Simulated portfolio
      │
      ▼
Home Assistant dashboard
```

At this point we have a complete experimental trading system that can be evaluated objectively without risking real money.

Only after this milestone should we consider adding an LLM, paper trading, or additional markets.
