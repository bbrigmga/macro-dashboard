# Macro Economic Indicators Dashboard

A Streamlit dashboard that tracks macro economic indicators and market-implied signals to help assess economic conditions, positioning, and volatility regimes. Data comes from FRED (Federal Reserve Economic Data) and Yahoo Finance. The app includes interactive charts, warning signals, a growth/inflation regime quadrant, and a daily-scraped implied vs realized volatility table for 14 US equity ETFs.

## How the codebase works

### Runtime flow

```
app.py
  ├── IndicatorService.get_all_indicators()   # async fetch of all macro indicators
  ├── check_volatility_data_freshness()       # reads iv_data.db for sidebar status
  └── create_dashboard()                      # ui/dashboard.py
        ├── Regime quadrant chart             # growth/inflation proxy from Yahoo ratios
        ├── 13 indicator cards                # charts + warnings from registry metadata
        └── render_vol_table()                # built directly from iv_data.db (not service cache)
```

**Macro indicators** are fetched once at startup through `IndicatorService`, which reads configuration from `src/config/indicator_registry.py`, pulls data via `data/indicators.py` / `FredClient` / `YahooClient`, and caches results in memory + disk (`src/core/caching/cache_manager.py`).

**Volatility table data** follows a separate path. The nightly scraper writes to SQLite (`data/volatility/iv_data.db`). The dashboard always rebuilds the table from that database via `ui/vol_table.py` → `VolTableDataAssembler`, so stale indicator-service cache cannot leave historical premium columns empty.

### Indicator registry

`src/config/indicator_registry.py` is the single source of truth for indicator metadata: FRED/Yahoo series, chart type, warning text, cache TTL, and optional custom chart/status functions. Adding a new indicator typically means:

1. Add an `IndicatorConfig` entry to the registry
2. Implement fetch logic in `data/indicators.py` (if not covered by generic paths)
3. Wire display in `ui/dashboard.py` and/or add a custom chart in `visualization/`

Proxy configs for the regime quadrant live separately in `src/config/growth_proxy.py` and `src/config/inflation_proxy.py`.

### Volatility pipeline

```
scripts/scrape_iv.py  (or Windows Task Scheduler / GitHub Actions)
  └── IVScraper.scrape_daily()
        ├── Yahoo options chains → 30-day ATM IV (DTE-weighted interpolation)
        ├── RealizedVolCalculator → 30-day annualized RV from closes
        └── IVDatabase.upsert_daily() → data/volatility/iv_data.db

VolTableDataAssembler.build_table()
  └── Z-scores, percentiles, contrarian scores, historical premiums
```

## Features

- **13 macro indicator cards** plus a full-width **Growth/Inflation Regime** quadrant
- **Implied vs Realized Volatility table** for 14 sector/market ETFs with heatmap styling
- **Warning signals** and playbook text per indicator from the registry
- **Danger combination** tracking (PMI + Claims + Hours Worked)
- **Risk On / Off / Neutral** positioning from PCE + Initial Claims
- **Daily IV scrape automation** via Windows Task Scheduler and GitHub Actions
- **CSV exports** for IV/RV history and aligned macro analysis data
- **Service layer** with async parallel fetching and multi-level caching
- **Comprehensive pytest suite** under `tests/`

## Project structure

```
macro_dashboard/
├── app.py                          # Streamlit entry point
├── requirements.txt
├── pytest.ini
├── .env.example                    # FRED_API_KEY template
│
├── src/
│   ├── config/
│   │   ├── indicator_registry.py   # Single source of truth for all indicators
│   │   ├── settings.py             # API, cache, and chart settings
│   │   ├── growth_proxy.py         # Regime X-axis ratio config
│   │   └── inflation_proxy.py      # Regime Y-axis ratio config
│   ├── core/caching/
│   │   └── cache_manager.py        # Memory + disk cache with TTL
│   └── services/
│       └── indicator_service.py    # Async fetch orchestration
│
├── data/
│   ├── fred_client.py              # FRED API client
│   ├── yahoo_client.py             # Yahoo Finance prices + options
│   ├── indicators.py               # Indicator data assembly
│   ├── processing.py               # Shared transforms (MoM, YoY, etc.)
│   ├── growth_proxy.py             # Growth proxy computation
│   ├── inflation_proxy.py          # Inflation proxy computation
│   ├── market_macro_export.py      # Aligned daily macro CSV export
│   ├── iv_db.py                    # SQLite layer for IV/RV snapshots
│   ├── iv_scraper.py               # Daily options-chain scraper
│   ├── rv_calculator.py            # Realized volatility calculator
│   ├── vol_table_data.py           # Vol table assembly + signal scores
│   ├── vol_signal_backtest.py      # Contrarian signal backtest helpers
│   ├── market_utils.py             # Trading days, holidays, scrape guards
│   └── volatility/                 # iv_data.db lives here (gitignored locally)
│
├── ui/
│   ├── dashboard.py                # Page layout, status tables, card grid
│   ├── indicators.py               # Indicator card rendering
│   └── vol_table.py                # Vol heatmap table + cache helpers
│
├── visualization/
│   ├── charts.py                   # Plotly charts (regime quadrant, PSCF, etc.)
│   ├── indicators.py               # Indicator-specific chart builders
│   ├── generic_chart.py            # Registry-driven generic charts
│   └── warning_signals.py          # Bullish/bearish/neutral status logic
│
├── scripts/
│   ├── scrape_iv.py                # Daily scraper entry point (cron / Actions)
│   ├── setup_task_scheduler.ps1    # Windows scheduled task setup
│   ├── backup_iv_db.py             # Backup before git pull
│   ├── restore_iv_db.py            # Restore from backup
│   ├── iv_db_stats.py              # Collection health / SPY day count
│   ├── backfill_iv.py              # Backfill a missing trading day
│   ├── export_market_macro.py      # CLI for macro CSV export
│   └── vol_signal_backtest.py      # Vol signal backtest CLI
│
├── .github/workflows/
│   ├── scrape_iv.yml               # Weekday nightly IV scrape + DB commit
│   └── test.yml                    # CI test runner
│
└── tests/                          # pytest suite (see Testing section)
```

## Local setup

1. Clone the repository and enter the project directory.

2. Create and activate a virtual environment (recommended):
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Get a free FRED API key from [fred.stlouisfed.org/docs/api/api_key.html](https://fred.stlouisfed.org/docs/api/api_key.html).

5. Copy `.env.example` to `.env` and set your key:
   ```
   FRED_API_KEY=your_key_here
   ```

6. Run the dashboard:
   ```bash
   streamlit run app.py
   ```

The app uses the service layer by default (`IndicatorService` in `app.py`). No feature flag is required.

**Note:** Python 3.12 is recommended if you hit pandas compatibility issues on 3.13.

### Sidebar controls

When volatility data exists in the local database, the sidebar shows:

- **Reload Vol Table** — clears Streamlit caches and rebuilds from `iv_data.db` (fast; no Yahoo scrape)
- **Scrape Volatility Data** — runs a live scrape (~30–40 seconds for all 14 ETFs)
- **Export Options Data (CSV)** — downloads all stored IV/RV snapshots

## Daily IV scrape automation

The volatility table needs daily snapshots to populate historical premium and z-score columns. Two automation paths write to the same database:

| Source | When | Entry point |
|--------|------|-------------|
| **Windows Task Scheduler** | Daily ~4:30 PM local | `scripts/setup_task_scheduler.ps1` → `scripts/scrape_iv.py` |
| **GitHub Actions** | Weekdays 9 PM UTC | `.github/workflows/scrape_iv.yml` → commits `data/volatility/iv_data.db` |

### Manual scrape

```bash
python scripts/scrape_iv.py
```

The scraper skips tickers that already have today's row, backs up the DB before writing, and exits 0 even if individual tickers fail (fatal errors exit 1).

### Database operations

```bash
python scripts/backup_iv_db.py          # before git pull
python scripts/restore_iv_db.py       # if pull overwrote local history
python scripts/iv_db_stats.py           # SPY day count, date range, gaps
python scripts/backfill_iv.py --date 2026-06-02   # fill a missing day
```

**Two-writer guidance:** Local Task Scheduler is the primary source for day-to-day dashboard use. GitHub Actions is a remote backup/sync. Back up before `git pull` if you have richer local history. Actions restores the `iv-database-latest` artifact before each run and refuses to publish if SPY day-count shrinks.

### Runtime artifacts (do not commit)

- `logs/`
- `scripts/scrape_iv.log`
- `data/cache/*.csv` and `data/cache/*.pkl`

## Indicators tracked

The dashboard displays **13 indicator cards**, a **regime quadrant**, and the **volatility table**.

| Registry key | Display name | Primary source |
|--------------|--------------|----------------|
| `hours_worked` | Average Weekly Hours Worked | FRED (`AWHAETP`) |
| `core_cpi` | Core Consumer Price Index | FRED (`CPILFESL`) |
| `initial_claims` | Initial Jobless Claims | FRED (`ICSA`) |
| `pce` | Personal Consumption Expenditures | FRED (`PCE`) |
| `pmi_proxy` | Manufacturing PMI Proxy | FRED (5 series composite) |
| `new_orders` | New Orders Index | FRED (`NEWORDER`) |
| `yield_curve` | 2-10 Year Treasury Spread | FRED (`T10Y2Y`) |
| `credit_spread` | High Yield Credit Spread | FRED (`BAMLH0A0HYM2`) |
| `xlp_xly_ratio` | Staples/Discretionary Ratio | Yahoo (`XLP`, `XLY`) |
| `pscf_price` | Small Cap Financials (PSCF) | FRED (`PSCF`) |
| `usd_liquidity` | USD Liquidity | FRED (Fed balance sheet components) |
| `copper_gold_yield` | Copper/Gold vs 10Y Treasury | Yahoo + FRED |
| `korea_exports_spy_eps` | Korea Exports vs SPY EPS Growth | FRED + Yahoo |
| `regime_quadrant` | Growth/Inflation Regime | Yahoo ratio proxies |
| *(vol table)* | Implied vs Realized Volatility | Local SQLite DB |

### Manufacturing PMI proxy

Built from five FRED series with diffusion-index transforms and weighted composite:

| Component | Series | Weight |
|-----------|--------|--------|
| New Orders | `AMTMNO` | 30% |
| Production | `IPMAN` | 25% |
| Employment | `MANEMP` | 20% |
| Supplier Deliveries | `AMDMUS` | 15% |
| Inventories | `MNFCTRIMSA` | 10% |

### Growth / inflation regime quadrant

- **X-axis (growth proxy):** equal-weight z-score of 63-day log-ratio changes across CPER/GLD, XHB/IWM, EFA/SLV, CPER/FXI (`src/config/growth_proxy.py`)
- **Y-axis (inflation proxy):** equal-weight z-score of DBC/CPER and XLV/QQQ ratios with EMA smoothing (`src/config/inflation_proxy.py`)
- **Quadrants:** Reflation, Goldilocks, Stagflation, Deflation — with a 63-day AR(1)/OU projection cone (aligned with proxy momentum window)

Use **Export Macro Analysis Data (CSV)** on the regime panel to download aligned daily ETF + FRED series (`data/market_macro_export.py`).

### Key concepts

**Danger combination:** PMI below 50 + Initial Claims rising 3 weeks + Hours Worked dropping.

**Positioning:** Derived from PCE and Initial Claims status — Risk On, Risk Off, or Risk Neutral.

## Implied vs Realized Volatility table

Compares 30-day ATM implied volatility (from options) with 30-day realized volatility (from closes) across 14 ETFs.

### ETF universe

XLRE, XLF, XLE, XLC, XLK, QQQ, SPY, XLV, XLB, XLI, XLY, IWM, XLU, XLP

### Database schema

Stored in `data/volatility/iv_data.db`:

```sql
CREATE TABLE daily_iv (
    date TEXT NOT NULL,          -- YYYY-MM-DD
    ticker TEXT NOT NULL,
    close_price REAL NOT NULL,
    iv_30d REAL,                 -- annualized 30-day ATM implied vol
    rv_30d REAL,                 -- annualized 30-day realized vol
    iv_premium REAL,             -- (iv/rv - 1) * 100
    ytd_return REAL,
    UNIQUE(date, ticker)
);
```

### Calculations

**Implied volatility:** ATM call/put average from Yahoo options chains; when two expirations bracket ~30 DTE, IV is linearly interpolated by DTE distance. Quality score (0–100) reflects volume and bid-ask spread.

**Realized volatility:** `std(ln(close_t / close_{t-1}), 30 days) × √252`

**IV premium:** `((iv_30d / rv_30d) - 1) × 100`

**Z-scores:** TTM (252 trading days) and 3-year (756 days) on the IV premium series.

### Table columns (display)

The assembler (`data/vol_table_data.py`) produces columns including:

| Column | Description |
|--------|-------------|
| ETF Name / Ticker | Static identifiers |
| Vol Valuation | Options rich/cheap vs RV |
| Contrarian Signal / scores | Fear/complacency setup with trend filters |
| YTD % | Year-to-date return |
| IVOL/RVOL Current | Current IV premium % |
| IVOL/RVOL Percentile (1Y / 3Y) | Historical percentile of current premium |
| IV-RV Spread / Ratio | Absolute and relative IV vs RV |
| Prem Change (1W / 1M) | Change in premium vs prior periods |
| IVOL Prem Yesterday / 1W / 1M | Historical premium snapshots |
| TTM / 3Yr Z-Score | Relative value vs history |
| Prem Z Velocity | Rate of change in premium z-score |

Sorted by YTD % descending with heatmap conditional formatting in `ui/vol_table.py`.

### Programmatic access

```python
from data.iv_db import IVDatabase
from data.vol_table_data import VolTableDataAssembler

with IVDatabase() as db:
    assembler = VolTableDataAssembler(db)
    vol_table = assembler.build_table()
    freshness = assembler.get_data_freshness_info()
    print(f"Latest date: {freshness['latest_date']}")
```

```python
from data.iv_db import IVDatabase
from data.iv_scraper import IVScraper

db = IVDatabase()
scraper = IVScraper(db)
result = scraper.scrape_daily()
print(f"Success: {result['success']}, Failed: {result['failed']}")
```

## Testing

Run the full suite:

```bash
python -m pytest tests/ -q
```

Focused volatility checks:

```bash
python -m pytest tests/test_iv_scraper.py tests/test_vol_table_data.py tests/test_vol_table.py tests/test_vol_integration.py -v
```

Other notable test modules: `test_regime_quadrant.py`, `test_inflation_proxy.py`, `test_growth_proxy.py`, `test_market_macro_export.py`, `test_indicator_service.py`.

## Deployment on Streamlit Cloud

1. Push the repo to GitHub.
2. Create an app at [streamlit.io/cloud](https://streamlit.io/cloud) pointing to `app.py`.
3. Add `FRED_API_KEY` as a Streamlit secret.

**Volatility table on Streamlit Cloud:** The IV database must exist in the repo or be populated by GitHub Actions. Without `data/volatility/iv_data.db`, the vol table shows a prompt to run the scraper. Cloud deployments cannot scrape Yahoo on demand as reliably as a local/cron setup.

## Security

- Never commit `.env` or API keys
- `iv_data.db` is gitignored locally but force-committed by GitHub Actions for persistence
- `.gitignore` excludes cache files and logs

## Disclaimer

This dashboard is for informational purposes only and is not financial advice. Conduct your own research and consult professionals before making investment decisions.
