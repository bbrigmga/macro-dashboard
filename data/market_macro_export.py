"""

Build aligned daily export of ETF prices and macro series for external analysis.

"""

from __future__ import annotations



import datetime

import logging

from typing import TYPE_CHECKING



import pandas as pd



from data.fred_client import FredClient

from data.processing import align_series_asof

from data.yahoo_client import YahooClient



if TYPE_CHECKING:

    pass



logger = logging.getLogger(__name__)



ETF_TICKERS = ['CPER', 'GLD', 'IEF', 'TIP']

GDP_SERIES_ID = 'GDP'

CPI_SERIES_ID = 'CPIAUCSL'

EXPORT_COLUMNS = ['Date', 'CPER', 'GLD', 'IEF', 'TIP', 'GDP', 'CPI']





def build_market_macro_export(

    years: int = 3,

    yahoo_client: YahooClient | None = None,

    fred_client: FredClient | None = None,

) -> pd.DataFrame:

    """

    Fetch ETF daily closes and macro series, aligned to a single Date column.



    ETF columns hold the close on each trading day. GDP (quarterly) and CPI (monthly)

    use backward as-of alignment so each row shows the last published value on or

    before that date.

    """

    end_date = datetime.datetime.now()

    start_date = end_date - datetime.timedelta(days=int(years * 365.25) + 30)

    start_str = start_date.strftime('%Y-%m-%d')

    end_str = (end_date + datetime.timedelta(days=1)).strftime('%Y-%m-%d')



    yahoo = yahoo_client or YahooClient()

    fred = fred_client or FredClient()



    etf_frames: dict[str, pd.DataFrame] = {}

    for ticker in ETF_TICKERS:

        df = yahoo.get_historical_prices(

            ticker=ticker,

            start_date=start_str,

            end_date=end_str,

            frequency='1d',

        )

        if df is None or df.empty:

            raise ValueError(f"No Yahoo data returned for {ticker}")



        frame = df[['Date', 'value']].copy()

        frame['Date'] = pd.to_datetime(frame['Date']).dt.normalize()

        frame = frame.rename(columns={'value': ticker})

        etf_frames[ticker] = frame



    merged = etf_frames[ETF_TICKERS[0]]

    for ticker in ETF_TICKERS[1:]:

        merged = pd.merge(merged, etf_frames[ticker], on='Date', how='inner')



    merged = merged.sort_values('Date').reset_index(drop=True)

    merged = merged[merged['Date'] >= pd.Timestamp(start_date)].copy()



    if merged.empty:

        return pd.DataFrame(columns=EXPORT_COLUMNS)



    gdp_df = fred.get_series(

        GDP_SERIES_ID,

        start_date=start_str,

        end_date=end_str,

        frequency='Q',

    )

    cpi_df = fred.get_series(

        CPI_SERIES_ID,

        start_date=start_str,

        end_date=end_str,

        frequency='M',

    )



    gdp_series = gdp_df.set_index('Date')[GDP_SERIES_ID] if not gdp_df.empty else pd.Series(dtype=float)

    cpi_series = cpi_df.set_index('Date')[CPI_SERIES_ID] if not cpi_df.empty else pd.Series(dtype=float)



    merged['GDP'] = align_series_asof(merged['Date'], gdp_series, 'GDP')

    merged['CPI'] = align_series_asof(merged['Date'], cpi_series, 'CPI')



    export = merged[['Date', *ETF_TICKERS, 'GDP', 'CPI']].copy()

    export['Date'] = export['Date'].dt.strftime('%Y-%m-%d')

    return export





def market_macro_export_csv_bytes(

    years: int = 3,

    yahoo_client: YahooClient | None = None,

    fred_client: FredClient | None = None,

) -> bytes:

    """Return UTF-8 CSV bytes for the aligned market/macro export."""

    df = build_market_macro_export(

        years=years,

        yahoo_client=yahoo_client,

        fred_client=fred_client,

    )

    if df.empty:

        return b""

    return df.to_csv(index=False).encode('utf-8')


