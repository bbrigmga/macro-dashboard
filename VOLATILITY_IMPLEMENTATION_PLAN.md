# Implied vs Realized Volatility Table — Implementation Plan

> **Spec Source:** `# Implied & Realized Volatility Dashboar.md`  
> **Target Codebase:** Macro Dashboard (Streamlit + Plotly + yfinance + fredapi)  
> **Date:** 2026-03-06

---

## Recommended Model for Implementation

**Claude Sonnet 4 (or Claude Opus 4)** is the best model for this task:

| Criteria | Why Sonnet/Opus |
|----------|-----------------|
| **Multi-file coordination** | This feature touches 8+ files across data, config, service, UI, and visualization layers. Sonnet/Opus excel at maintaining context across many files simultaneously. |
| **Pattern matching** | The codebase uses a strict registry-driven pattern. The model must replicate existing conventions (IndicatorConfig, IndicatorResult, custom_chart_fn routing, cache layering) — Sonnet/Opus are strongest at inferring and following existing code patterns. |
| **SQLite + yfinance options chain** | The spec requires ATM IV calculation from options chains and SQLite schema design. These are well-represented in Sonnet/Opus training data. |
| **Financial math** | Log-return RV calculation, IV interpolation across DTE, annualization, Z-score computation — needs precise numerical reasoning. |
| **Test generation** | Must produce pytest fixtures with realistic financial data (options chains, price series) and mock yfinance responses. |

**Runner-up:** Gemini 2.5 Pro — strong on long-context multi-file edits but slightly weaker on financial domain conventions.  
**Avoid:** Smaller models (Haiku, GPT-4o-mini) — insufficient context window for 8-file coordination and too prone to hallucinating yfinance API details.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Streamlit App (app.py)                 │
│                                                             │
│  ┌────────────────┐  ┌────────────────────────────────────┐ │
│  │ Existing Cards │  │  NEW: Volatility Table Tab/Section │ │
│  │ (11 indicators)│  │  (ui/vol_table.py)                 │ │
│  └────────────────┘  └──────────────┬─────────────────────┘ │
│                                     │                       │
│                    ┌────────────────┴─────────────────┐     │
│                    │ src/services/indicator_service.py │     │
│                    │ (add vol_table route)             │     │
│                    └────────────────┬─────────────────┘     │
│                                     │                       │
│          ┌──────────────────────────┼───────────────┐       │
│          │                          │               │       │
│  ┌───────┴────────┐  ┌─────────────┴──┐  ┌────────┴─────┐ │
│  │ data/           │  │ data/           │  │ data/         │ │
│  │ iv_scraper.py   │  │ rv_calculator.py│  │ iv_db.py      │ │
│  │ (daily cron)    │  │ (on-demand)     │  │ (SQLite DAL)  │ │
│  └───────┬────────┘  └─────────────┬──┘  └────────┬─────┘ │
│          │                          │               │       │
│          └──────────┬───────────────┘               │       │
│                     │                               │       │
│              ┌──────┴──────┐                ┌───────┴─────┐ │
│              │  yfinance   │                │  iv_data.db  │ │
│              │  (options + │                │  (SQLite)    │ │
│              │   prices)   │                │              │ │
│              └─────────────┘                └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase Plan

### Phase 0: Prerequisites & Setup ✅ COMPLETE
**Goal:** Environment prep, no code changes yet.

- [x] **0.1** Install additional dependency: `pip install yfinance` (already present in requirements.txt — verify options chain support works)
- [x] **0.2** Verify yfinance options chain API availability by running a manual test:
  ```python
  import yfinance as yf
  spy = yf.Ticker("SPY")
  expirations = spy.options          # list of expiration date strings
  chain = spy.option_chain(expirations[0])  # returns (calls_df, puts_df)
  print(chain.calls[['strike', 'impliedVolatility']].head())
  ```
- [x] **0.3** Create the SQLite database directory: `data/volatility/` (keeps vol data separate from FRED cache)
- [x] **0.4** Add `iv_data.db` to `.gitignore`

---

### Phase 1: SQLite Database Layer (`data/iv_db.py`)
**Goal:** Persistent storage for daily IV/RV snapshots. All other phases depend on this.

**New file:** `data/iv_db.py`

- [ ] **1.1** Create `IVDatabase` class with `__init__(self, db_path="data/volatility/iv_data.db")`
  - Use `sqlite3` stdlib (no extra dependency)
  - Auto-create tables on first use via `_init_db()`
- [ ] **1.2** Implement schema from spec:
  ```sql
  CREATE TABLE IF NOT EXISTS daily_iv (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      date TEXT NOT NULL,
      ticker TEXT NOT NULL,
      close_price REAL NOT NULL,
      iv_30d REAL,
      rv_30d REAL,
      iv_premium REAL,
      ytd_return REAL,
      UNIQUE(date, ticker)
  );
  CREATE INDEX IF NOT EXISTS idx_daily_iv_ticker_date ON daily_iv(ticker, date);
  ```
- [ ] **1.3** Implement CRUD methods:
  - `upsert_daily(date, ticker, close_price, iv_30d, rv_30d, iv_premium, ytd_return)` — INSERT OR REPLACE
  - `get_latest(ticker) -> dict | None` — most recent row for a ticker
  - `get_history(ticker, lookback_days=252) -> pd.DataFrame` — for Z-score calculation
  - `get_all_latest() -> pd.DataFrame` — latest row per ticker (for table display)
  - `get_snapshot(date, ticker) -> dict | None` — specific date lookup (for "yesterday" / "1W ago" columns)
- [ ] **1.4** Add context manager support (`__enter__`/`__exit__`) for safe connection handling
- [ ] **1.5** Write tests: `tests/test_iv_db.py`
  - Test schema creation on fresh DB
  - Test upsert idempotency (same date+ticker → update not duplicate)
  - Test get_history returns correct date range
  - Test get_all_latest returns one row per ticker
  - Use `tmp_path` fixture for isolated test DBs

---

### Phase 2: Realized Volatility Calculator (`data/rv_calculator.py`)
**Goal:** Calculate 30-day annualized realized vol from price history.

**New file:** `data/rv_calculator.py`

- [ ] **2.1** Create `RealizedVolCalculator` class
  - Constructor takes `YahooClient` (dependency injection, matches codebase pattern)
- [ ] **2.2** Implement `calculate_rv(prices: pd.Series, window: int = 30) -> float`:
  ```python
  daily_returns = np.log(prices / prices.shift(1))
  rv = daily_returns.tail(window).std() * np.sqrt(252)
  return rv  # annualized decimal (e.g., 0.18 = 18%)
  ```
- [ ] **2.3** Implement `get_rv_for_ticker(ticker: str, window: int = 30) -> float`:
  - Fetch last `window + 5` trading days of closing prices via `YahooClient`
  - Call `calculate_rv()` on the close prices
  - Return annualized RV
- [ ] **2.4** Implement `get_rv_batch(tickers: list[str], window: int = 30) -> dict[str, float]`:
  - Loop through all tickers, return `{ticker: rv_value}` dict
  - Handle failures gracefully (return `None` for tickers that fail)
- [ ] **2.5** Write tests: `tests/test_rv_calculator.py`
  - Test with known price series (e.g., constant price → RV = 0)
  - Test with synthetic random walk (RV ≈ injected vol)
  - Test annualization factor (√252)
  - Mock `YahooClient` to avoid live API calls

---

### Phase 3: IV Scraper (`data/iv_scraper.py`)
**Goal:** Extract 30-day ATM implied volatility from yfinance options chains.

**New file:** `data/iv_scraper.py`

- [ ] **3.1** Create `IVScraper` class with constructor taking `IVDatabase` instance
- [ ] **3.2** Define ETF universe constant (from spec — 14 tickers):
  ```python
  ETF_UNIVERSE = [
      {"ticker": "XLRE", "name": "Real Estate Sector SPDR ETF"},
      {"ticker": "XLF",  "name": "Financials Sector SPDR ETF"},
      {"ticker": "XLE",  "name": "Energy Sector SPDR ETF"},
      {"ticker": "XLC",  "name": "Communication Services SPDR ETF"},
      {"ticker": "XLK",  "name": "Technology Sector SPDR ETF"},
      {"ticker": "QQQ",  "name": "Power Shares QQQ Trust ETF"},
      {"ticker": "SPY",  "name": "SPDR S&P 500 Trust"},
      {"ticker": "XLV",  "name": "Health Care Sector SPDR ETF"},
      {"ticker": "XLB",  "name": "Materials Sector SPDR ETF"},
      {"ticker": "XLI",  "name": "Industrials Sector SPDR ETF"},
      {"ticker": "XLY",  "name": "Consumer Discretionary SPDR ETF"},
      {"ticker": "IWM",  "name": "I-Shares Russell 2000"},
      {"ticker": "XLU",  "name": "Utilities Sector SPDR ETF"},
      {"ticker": "XLP",  "name": "Consumer Staples Sector SPDR ETF"},
  ]
  ```
- [ ] **3.3** Implement `_get_atm_iv(ticker: str) -> float | None`:
  1. `yf.Ticker(ticker).options` → list of expiration date strings
  2. Find the two expirations bracketing 30 DTE from today
  3. For each expiration, get `option_chain(exp_date)` → calls_df, puts_df
  4. Find current price via `yf.Ticker(ticker).info['currentPrice']` (or `.fast_info['lastPrice']`)
  5. Select ATM strike (closest to current price)
  6. Average call IV and put IV at ATM strike
  7. If two expirations bracket 30 DTE, linearly interpolate IV between them weighted by DTE proximity
  8. Return annualized 30-day ATM IV (yfinance IVs are already annualized)
  - **Edge cases:**
    - No options available → return `None`
    - Only one expiration near 30 DTE → use it directly (no interpolation)
    - ATM strike has 0 or NaN IV → widen search to ±1 strike
- [ ] **3.4** Implement `_get_ytd_return(ticker: str) -> float`:
  - Get Jan 1 close price and current close price
  - Return `(current / jan1) - 1`
- [ ] **3.5** Implement `scrape_daily() -> dict`:
  - For each ticker in `ETF_UNIVERSE`:
    1. Get ATM IV via `_get_atm_iv()`
    2. Get current close price
    3. Calculate RV via `RealizedVolCalculator`
    4. Calculate IV premium: `((iv / rv) - 1) * 100`
    5. Calculate YTD return
    6. Upsert to `IVDatabase`
  - Return summary dict with success/failure counts
  - Add logging for each ticker (consistent with codebase's logging pattern)
- [ ] **3.6** Implement `run_scraper()` standalone entry point:
  ```python
  if __name__ == "__main__":
      db = IVDatabase()
      scraper = IVScraper(db)
      result = scraper.scrape_daily()
      print(f"Scraped {result['success']} tickers, {result['failed']} failures")
  ```
  - This enables cron execution: `python -m data.iv_scraper`
- [ ] **3.7** Write tests: `tests/test_iv_scraper.py`
  - Mock `yf.Ticker` to return synthetic options chain data
  - Test ATM strike selection logic (exact match, between strikes)
  - Test DTE interpolation (two expirations, one expiration)
  - Test edge cases (no options, NaN IV)
  - Test `scrape_daily()` integration with mocked DB

---

### Phase 4: Volatility Table Data Assembly (`data/vol_table_data.py`)
**Goal:** Combine DB data into the display-ready DataFrame matching the spec's column layout.

**New file:** `data/vol_table_data.py`

- [ ] **4.1** Create `VolTableDataAssembler` class with constructor taking `IVDatabase`
- [ ] **4.2** Implement `build_table() -> pd.DataFrame` that produces the exact columns from spec:

  | Column | Source | Calculation |
  |--------|--------|-------------|
  | `etf_name` | `ETF_UNIVERSE` constant | Static lookup |
  | `ticker_display` | Derived | `f"{ticker} US EQUITY"` |
  | `ytd_pct` | `daily_iv.ytd_return` | Latest row for ticker |
  | `ivol_rvol_current` | `daily_iv.iv_premium` | Latest row: `((iv_30d / rv_30d) - 1) * 100` |
  | `ivol_prem_yesterday` | `daily_iv.iv_premium` | Row for T-1 trading day |
  | `ivol_prem_1w` | `daily_iv.iv_premium` | Row for T-5 trading days |
  | `ivol_prem_1m` | `daily_iv.iv_premium` | Row for T-21 trading days |
  | `ttm_zscore` | Calculated | Z-score of iv_premium over trailing 252 days |
  | `three_yr_zscore` | Calculated | Z-score of iv_premium over trailing 756 days |

- [ ] **4.3** Implement `_calculate_zscore(series: pd.Series, window: int) -> float`:
  ```python
  mean = series.tail(window).mean()
  std = series.tail(window).std()
  current = series.iloc[-1]
  return (current - mean) / std if std > 0 else 0.0
  ```
- [ ] **4.4** Implement `_get_historical_premium(ticker: str, days_ago: int) -> float | None`:
  - Query DB for the record closest to `today - days_ago` trading days
  - Return `iv_premium` value, or `None` if insufficient history
- [ ] **4.5** Handle insufficient history gracefully:
  - If DB has < 5 days of data → show `N/A` for "1W Ago"
  - If DB has < 21 days → show `N/A` for "1M Ago"
  - If DB has < 252 days → show `N/A` for "TTM Z-Score"
  - If DB has < 756 days → show `N/A` for "3Yr Z-Score"
- [ ] **4.6** Sort output by `ytd_pct` descending (per spec)
- [ ] **4.7** Write tests: `tests/test_vol_table_data.py`
  - Seed a test DB with synthetic 30-day history
  - Verify column names and dtypes
  - Verify sort order
  - Verify Z-score math with known inputs
  - Verify N/A handling with sparse data

---

### Phase 5: Config & Service Integration
**Goal:** Wire the volatility table into the existing registry and service patterns.

- [ ] **5.1** Update `src/config/indicator_registry.py`:
  - Add `"implied_realized_vol"` entry to `INDICATOR_REGISTRY`:
    ```python
    "implied_realized_vol": IndicatorConfig(
        key="implied_realized_vol",
        display_name="Implied vs Realized Volatility",
        emoji="📊",
        fred_series=[],
        chart_type="custom",
        value_column="ivol_rvol_current",
        periods=252,
        frequency="D",
        bullish_condition="custom",
        threshold=None,
        warning_description="IV premium > 0 means options market pricing more risk than realized...",
        chart_color="#e91e63",
        custom_chart_fn="visualization.vol_table.create_vol_table",
        custom_status_fn=None,
        yaml_series=["SPY", "QQQ", "IWM", "XLF", "XLE", "XLK", "XLV", "XLB",
                      "XLI", "XLY", "XLP", "XLU", "XLC", "XLRE"],
    )
    ```
- [ ] **5.2** Update `src/services/indicator_service.py`:
  - Import `IVDatabase` and `VolTableDataAssembler`
  - Add route in `_get_specific_indicator_data()`:
    ```python
    elif indicator_name == "implied_realized_vol":
        db = IVDatabase()
        assembler = VolTableDataAssembler(db)
        return {"data": assembler.build_table(), "table_type": "vol_heatmap"}
    ```
- [ ] **5.3** Update `src/config/settings.py`:
  - Add volatility-specific config if needed (e.g., `vol_db_path`, `scraper_enabled`)
- [ ] **5.4** Write tests: Update `tests/test_indicator_registry.py`
  - Update expected indicator count (11 → 12)
  - Verify new config fields

---

### Phase 6: Streamlit Table Component (`ui/vol_table.py`)
**Goal:** Render the styled heatmap table in Streamlit.

**New file:** `ui/vol_table.py`

- [ ] **6.1** Create `render_vol_table(data: pd.DataFrame)` function:
  - Receives the DataFrame from Phase 4's `build_table()`
  - Format columns:
    - `ytd_pct`: `"{:.1f}%"` format
    - `ivol_rvol_current`, `ivol_prem_*`: `"{:.1f}%"` format
    - `ttm_zscore`, `three_yr_zscore`: `"{:.2f}"` format
  - Rename columns for display:
    ```python
    column_map = {
        "etf_name": "ETF Name",
        "ticker_display": "Ticker",
        "ytd_pct": "YTD %",
        "ivol_rvol_current": "IVOL/RVOL Current",
        "ivol_prem_yesterday": "IVOL Prem % Yesterday",
        "ivol_prem_1w": "IVOL Prem % 1W Ago",
        "ivol_prem_1m": "IVOL Prem % 1M Ago",
        "ttm_zscore": "TTM Z-Score",
        "three_yr_zscore": "3Yr Z-Score",
    }
    ```
- [ ] **6.2** Implement conditional formatting (heatmap coloring):
  - Use `pandas.io.formats.style.Styler` with `background_gradient()`:
    ```python
    def style_vol_table(df: pd.DataFrame) -> Styler:
        numeric_cols = ["YTD %", "IVOL/RVOL Current", "IVOL Prem % Yesterday",
                        "IVOL Prem % 1W Ago", "IVOL Prem % 1M Ago"]
        zscore_cols = ["TTM Z-Score", "3Yr Z-Score"]

        styled = df.style \
            .background_gradient(subset=numeric_cols, cmap="RdYlGn", vmin=-50, vmax=50) \
            .background_gradient(subset=zscore_cols, cmap="RdYlGn", vmin=-2, vmax=2) \
            .format({col: "{:.1f}%" for col in numeric_cols}) \
            .format({col: "{:.2f}" for col in zscore_cols})
        return styled
    ```
  - Green = high positive (IV premium = fear = defensive signal)
  - Red = low/negative (IV discount = complacency)
  - Z-Score: Green = high, Red = low
- [ ] **6.3** Render with `st.dataframe()` or `st.table()`:
  - `st.dataframe(styled_df, use_container_width=True, hide_index=True)`
  - Consider `st.markdown()` with custom HTML if Styler doesn't render well in Streamlit
- [ ] **6.4** Add section header and description:
  ```python
  st.subheader("📊 Implied vs Realized Volatility")
  st.caption("30-day ATM implied vol vs 30-day realized vol across US equity sector ETFs")
  ```
- [ ] **6.5** Handle empty/sparse data:
  - If DB is empty: show info message "Run the daily scraper first: `python -m data.iv_scraper`"
  - If some tickers missing: show partial table with available data

---

### Phase 7: Dashboard Integration (`ui/dashboard.py`, `app.py`)
**Goal:** Wire the volatility table into the main dashboard layout.

- [ ] **7.1** Update `ui/dashboard.py` → `create_dashboard()`:
  - Add the volatility table section BELOW the existing indicator grid (or as a new tab):
    ```python
    # Option A: New section below indicators
    st.divider()
    if "implied_realized_vol" in indicators:
        render_vol_table(indicators["implied_realized_vol"]["data"])

    # Option B: Tabbed interface
    tab1, tab2 = st.tabs(["Macro Indicators", "Volatility Surface"])
    with tab1:
        # existing indicator cards
    with tab2:
        render_vol_table(...)
    ```
  - **Recommendation:** Option A (new section) is simpler and matches the current single-page layout
- [ ] **7.2** Update `app.py` if needed:
  - Ensure the scraper has been run at least once before displaying
  - Add a "Last scraped" timestamp display
  - Optionally add a manual "Refresh IV Data" button that triggers `scrape_daily()`
- [ ] **7.3** Add auto-scrape on app load (optional):
  ```python
  @st.cache_resource(ttl=86400)  # Run once per day
  def ensure_iv_data_fresh():
      db = IVDatabase()
      latest = db.get_all_latest()
      if latest.empty or latest['date'].max() < str(date.today()):
          scraper = IVScraper(db)
          scraper.scrape_daily()
  ```
  - **Caution:** Options chain fetching is slow (~2-3s per ticker × 14 tickers ≈ 30-40s). Use `st.spinner()` and consider running async.

---

### Phase 8: Daily Scraper Automation
**Goal:** Ensure IV data is collected daily without manual intervention.

- [ ] **8.1** Create `scripts/scrape_iv.py` as a standalone entry point:
  ```python
  """Daily IV scraper — run via cron, GitHub Actions, or scheduler."""
  from data.iv_scraper import IVScraper
  from data.iv_db import IVDatabase

  if __name__ == "__main__":
      db = IVDatabase()
      scraper = IVScraper(db)
      result = scraper.scrape_daily()
      print(f"Done: {result['success']} succeeded, {result['failed']} failed")
  ```
- [ ] **8.2** Create GitHub Actions workflow (`.github/workflows/scrape_iv.yml`):
  ```yaml
  name: Daily IV Scrape
  on:
    schedule:
      - cron: '0 21 * * 1-5'  # 9 PM UTC = 4 PM ET (after market close)
    workflow_dispatch:           # Manual trigger
  jobs:
    scrape:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - uses: actions/setup-python@v5
          with:
            python-version: '3.11'
        - run: pip install -r requirements.txt
        - run: python scripts/scrape_iv.py
        - uses: actions/upload-artifact@v4
          with:
            name: iv-database
            path: data/volatility/iv_data.db
  ```
  - **Note:** SQLite DB in GitHub Actions is ephemeral. For persistence, either:
    - Commit the DB back to the repo (simple but git-unfriendly for binary)
    - Upload as artifact + download in app deploy step
    - Use a hosted SQLite service (Turso, LiteFS) for production
- [ ] **8.3** Alternative: APScheduler integration within Streamlit:
  ```python
  # In app.py — background scheduler
  from apscheduler.schedulers.background import BackgroundScheduler
  scheduler = BackgroundScheduler()
  scheduler.add_job(scrape_daily, 'cron', hour=16, minute=30, day_of_week='mon-fri')
  scheduler.start()
  ```
  - Requires adding `apscheduler` to requirements.txt
  - Only works if Streamlit app is running continuously

---

### Phase 9: Testing & Validation
**Goal:** Comprehensive test coverage for all new components.

- [ ] **9.1** Unit tests (all with mocked external dependencies):
  - `tests/test_iv_db.py` — SQLite CRUD operations (Phase 1.5)
  - `tests/test_rv_calculator.py` — RV math (Phase 2.5)
  - `tests/test_iv_scraper.py` — Options chain parsing, ATM selection (Phase 3.7)
  - `tests/test_vol_table_data.py` — Table assembly, Z-scores (Phase 4.7)
- [ ] **9.2** Integration test:
  - `tests/test_vol_integration.py` — End-to-end with mocked yfinance
  - Seed DB → run assembler → verify styled output DataFrame
- [ ] **9.3** Manual validation:
  - Run scraper manually for 1 ticker (SPY) and verify:
    - IV value is reasonable (typically 10-40% for SPY)
    - RV calculation matches manual spreadsheet computation
    - IV premium sign is correct
  - Load dashboard and verify table renders with correct formatting
- [ ] **9.4** Update existing tests:
  - `tests/test_indicator_registry.py` — bump expected count 11 → 12
  - `tests/test_indicator_service.py` — add vol indicator routing test

---

### Phase 10: Polish & Edge Cases
**Goal:** Production readiness.

- [ ] **10.1** Handle market holidays / weekends:
  - Scraper should detect non-trading days and skip (or handle gracefully)
  - "Yesterday" column should find the previous trading day, not calendar day
- [ ] **10.2** Handle missing options data:
  - Some sector ETFs may have illiquid options → wide bid/ask spreads → unreliable IV
  - Show `N/A` or a warning icon for tickers with low options volume
- [ ] **10.3** Performance optimization:
  - Cache the assembled table DataFrame in `st.cache_data(ttl=3600)`
  - Options chain fetching is the bottleneck — consider parallel fetching with `asyncio` + `aiohttp`
- [ ] **10.4** Update `requirements.txt` if any new dependencies added
- [ ] **10.5** Update `README.md` with:
  - Volatility table feature description
  - Scraper setup instructions
  - Required yfinance version notes (options chain API stability)
- [ ] **10.6** Add logging throughout (match existing `logging.getLogger(__name__)` pattern)

---

## File Summary

| File | Action | Phase |
|------|--------|-------|
| `data/iv_db.py` | **CREATE** | 1 |
| `data/rv_calculator.py` | **CREATE** | 2 |
| `data/iv_scraper.py` | **CREATE** | 3 |
| `data/vol_table_data.py` | **CREATE** | 4 |
| `src/config/indicator_registry.py` | **EDIT** | 5 |
| `src/services/indicator_service.py` | **EDIT** | 5 |
| `src/config/settings.py` | **EDIT** (optional) | 5 |
| `ui/vol_table.py` | **CREATE** | 6 |
| `ui/dashboard.py` | **EDIT** | 7 |
| `app.py` | **EDIT** | 7 |
| `scripts/scrape_iv.py` | **CREATE** | 8 |
| `.github/workflows/scrape_iv.yml` | **CREATE** (optional) | 8 |
| `tests/test_iv_db.py` | **CREATE** | 9 |
| `tests/test_rv_calculator.py` | **CREATE** | 9 |
| `tests/test_iv_scraper.py` | **CREATE** | 9 |
| `tests/test_vol_table_data.py` | **CREATE** | 9 |
| `tests/test_vol_integration.py` | **CREATE** | 9 |
| `tests/test_indicator_registry.py` | **EDIT** | 9 |
| `requirements.txt` | **EDIT** (if needed) | 10 |
| `README.md` | **EDIT** | 10 |

---

## Dependency Order

```
Phase 0 (setup)
    │
    v
Phase 1 (iv_db.py) ─────────────────────────┐
    │                                         │
    v                                         v
Phase 2 (rv_calculator.py)              Phase 3 (iv_scraper.py)
    │                                         │
    └──────────────┬──────────────────────────┘
                   │
                   v
             Phase 4 (vol_table_data.py)
                   │
                   v
             Phase 5 (config + service integration)
                   │
                   v
             Phase 6 (ui/vol_table.py)
                   │
                   v
             Phase 7 (dashboard + app.py wiring)
                   │
            ┌──────┴──────┐
            v              v
     Phase 8 (cron)   Phase 9 (tests)
            │              │
            └──────┬───────┘
                   v
             Phase 10 (polish)
```

**Phases 2 and 3 can be done in parallel** (both depend only on Phase 1).  
**Phases 8 and 9 can be done in parallel** (both depend on Phase 7).

---

## Key Implementation Notes for the Implementing Model

1. **Follow the existing pattern exactly.** Every data fetcher in this codebase returns a `dict` with a `"data"` key containing a DataFrame. The vol table must do the same.

2. **Use `YahooClient` for price data** — don't create a parallel yfinance client. But for options chains, call `yf.Ticker()` directly since `YahooClient` doesn't support options.

3. **The SQLite layer is new to this codebase.** The existing codebase uses CSV file caching (`data/cache/*.csv`). The vol feature introduces SQLite because it needs historical time-series queries (lookback 756 days for Z-scores) that CSV doesn't support well.

4. **`st.dataframe()` supports `pandas.Styler`** — use it for heatmap colors. Don't fall back to raw HTML unless Styler breaks.

5. **yfinance options chain gotchas:**
   - `yf.Ticker(ticker).options` may be empty for some ETFs
   - `option_chain()` returns namedtuple with `.calls` and `.puts` DataFrames
   - `impliedVolatility` column is already annualized (0.20 = 20%)
   - Some strikes have `impliedVolatility = 0` — filter these out
   - Weekend/holiday calls return stale data — check `lastTradeDate`

6. **The table should work with as little as 1 day of data** (from the first scrape). Historical columns show `N/A` until enough days accumulate.

7. **Run all tests through pytest** matching the existing pattern in `pytest.ini` and `conftest.py`.
