"""
Tests for market utilities module.

Tests trading day calculations, holiday detection, and market hour validation.
"""
import pytest
import datetime as dt
from unittest.mock import patch

from data.market_utils import (
    is_trading_day, 
    get_previous_trading_day,
    get_next_trading_day, 
    get_trading_days_between,
    should_skip_scraping,
    get_approximate_trading_day,
    is_market_hours_et,
    is_trading_day_fast
)


class TestTradingDayDetection:
    """Test trading day vs non-trading day detection."""
    
    def test_weekdays_are_trading_days(self):
        """Test that weekdays are trading days (when not holidays)."""
        # Monday, March 4, 2026 (not a holiday)
        monday = dt.date(2026, 3, 2)
        assert is_trading_day(monday)
        
        # Tuesday, March 3, 2026
        tuesday = dt.date(2026, 3, 3)
        assert is_trading_day(tuesday)
        
        # Friday, March 6, 2026
        friday = dt.date(2026, 3, 6)
        assert is_trading_day(friday)
    
    def test_weekends_are_not_trading_days(self):
        """Test that weekends are not trading days."""
        # Saturday, March 1, 2026
        saturday = dt.date(2026, 2, 28)
        assert not is_trading_day(saturday)
        
        # Sunday, March 2, 2026  
        sunday = dt.date(2026, 3, 1)
        assert not is_trading_day(sunday)
    
    def test_holidays_are_not_trading_days(self):
        """Test that market holidays are not trading days."""
        # New Year's Day 2026
        new_years = dt.date(2026, 1, 1)
        assert not is_trading_day(new_years)
        
        # Christmas Day 2025
        christmas = dt.date(2025, 12, 25)
        assert not is_trading_day(christmas)
        
        # Independence Day 2026 (observed on July 3rd since July 4th is Saturday)
        july_4th_observed = dt.date(2026, 7, 3)
        assert not is_trading_day(july_4th_observed)
    
    def test_fast_trading_day_matches_regular(self):
        """Test that fast version matches regular version."""
        test_dates = [
            dt.date(2026, 3, 3),   # Weekday
            dt.date(2026, 3, 1),   # Weekend  
            dt.date(2026, 1, 1),   # Holiday
            dt.date(2026, 7, 4),   # July 4th (Saturday)
            dt.date(2026, 7, 3),   # July 4th observed (Friday)
        ]
        
        for test_date in test_dates:
            assert is_trading_day(test_date) == is_trading_day_fast(test_date)


class TestPreviousTradingDay:
    """Test previous trading day calculations."""
    
    def test_previous_trading_day_from_tuesday(self):
        """Test getting previous trading day from Tuesday (should be Monday)."""
        # Tuesday, March 4, 2026
        tuesday = dt.date(2026, 3, 4)
        prev_day = get_previous_trading_day(tuesday, 1)
        
        # Should be Monday, March 3, 2026
        assert prev_day == dt.date(2026, 3, 3)
        assert is_trading_day(prev_day)
    
    def test_previous_trading_day_from_monday(self):
        """Test getting previous trading day from Monday (should skip weekend to Friday)."""
        # Monday, March 2, 2026
        monday = dt.date(2026, 3, 2)
        prev_day = get_previous_trading_day(monday, 1)
        
        # Should be Friday, February 27, 2026 (skipping weekend - Feb 28 is Saturday)
        expected_friday = dt.date(2026, 2, 27)
        assert prev_day == expected_friday
        assert is_trading_day(prev_day)
    
    def test_multiple_days_back(self):
        """Test getting multiple trading days back."""
        # Start from Friday, March 6, 2026
        friday = dt.date(2026, 3, 6)
        
        # 1 day back should be Thursday
        one_back = get_previous_trading_day(friday, 1)
        assert one_back == dt.date(2026, 3, 5)
        
        # 5 days back should be previous Friday (skipping weekend)
        five_back = get_previous_trading_day(friday, 5)
        assert five_back == dt.date(2026, 2, 27)  # Feb 27 is Friday, Feb 28 is Saturday
        assert is_trading_day(five_back)
    
    def test_skip_holidays(self):
        """Test that previous trading day skips holidays."""
        # Day after New Year's Day 2026 (January 2, 2026 is Thursday)
        jan_2 = dt.date(2026, 1, 2)
        prev_day = get_previous_trading_day(jan_2, 1)
        
        # Should skip New Year's Day (Jan 1) and go to Dec 31, 2025
        # But Dec 31, 2025 is Wednesday, so that should be the result
        assert prev_day == dt.date(2025, 12, 31)
        assert is_trading_day(prev_day)


class TestNextTradingDay:
    """Test next trading day calculations."""
    
    def test_next_trading_day_from_friday(self):
        """Test getting next trading day from Friday (should skip weekend to Monday)."""
        # Friday, February 27, 2026 
        friday = dt.date(2026, 2, 27)
        next_day = get_next_trading_day(friday)
        
        # Should be Monday, March 2, 2026 (skipping weekend)
        assert next_day == dt.date(2026, 3, 2)
        assert is_trading_day(next_day)
    
    def test_next_trading_day_from_tuesday(self):
        """Test getting next trading day from Tuesday (should be Wednesday)."""
        # Tuesday, March 3, 2026
        tuesday = dt.date(2026, 3, 3)
        next_day = get_next_trading_day(tuesday)
        
        # Should be Wednesday, March 4, 2026
        assert next_day == dt.date(2026, 3, 4)
        assert is_trading_day(next_day)


class TestTradingDaysBetween:
    """Test trading days between date ranges."""
    
    def test_trading_days_same_week(self):
        """Test trading days in same week."""
        # Monday to Friday, March 2-6, 2026 (March 7 is Saturday)
        monday = dt.date(2026, 3, 2)
        friday = dt.date(2026, 3, 6)
        
        trading_days = get_trading_days_between(monday, friday)
        
        # Should be 5 days: Mon, Tue, Wed, Thu, Fri
        assert len(trading_days) == 5
        assert all(is_trading_day(day) for day in trading_days)
        assert trading_days[0] == monday
        assert trading_days[-1] == friday
    
    def test_trading_days_across_weekend(self):
        """Test trading days across weekend."""  
        # Friday to next Tuesday
        friday = dt.date(2026, 2, 27)  # Friday
        tuesday = dt.date(2026, 3, 3)   # Tuesday
        
        trading_days = get_trading_days_between(friday, tuesday)
        
        # Should be 3 days: Fri, Mon, Tue (skip Sat/Sun which are Feb 28/Mar 1)
        assert len(trading_days) == 3
        expected = [dt.date(2026, 2, 27), dt.date(2026, 3, 2), dt.date(2026, 3, 3)]
        assert trading_days == expected
    
    def test_trading_days_with_holiday(self):
        """Test trading days that include a holiday."""
        # Dec 24-26, 2025 (Christmas Day is Dec 25)
        dec_24 = dt.date(2025, 12, 24)
        dec_26 = dt.date(2025, 12, 26)
        
        trading_days = get_trading_days_between(dec_24, dec_26)
        
        # Should only include Dec 24 and 26 (Dec 25 Christmas is holiday)
        # Actually, let me check the 2025 holidays... Christmas is on a Wednesday
        # So Dec 24 (Tue) and Dec 26 (Thu) should be trading days
        expected_days = [dt.date(2025, 12, 24), dt.date(2025, 12, 26)]
        assert len(trading_days) == 2
        assert all(is_trading_day(day) for day in trading_days)


class TestScrapingSkipLogic:
    """Test scraping skip logic for holidays and weekends."""
    
    def test_skip_on_weekend(self):
        """Test that scraping is skipped on weekends."""  
        # Saturday
        saturday = dt.date(2026, 2, 28)
        should_skip, reason = should_skip_scraping(saturday)
        assert should_skip
        assert "weekend" in reason.lower()
        
        # Sunday  
        sunday = dt.date(2026, 3, 1)
        should_skip, reason = should_skip_scraping(sunday)
        assert should_skip
        assert "weekend" in reason.lower()
    
    def test_skip_on_holiday(self):
        """Test that scraping is skipped on holidays."""
        # New Year's Day
        new_years = dt.date(2026, 1, 1) 
        should_skip, reason = should_skip_scraping(new_years)
        assert should_skip
        assert "holiday" in reason.lower()
        
        # Christmas
        christmas = dt.date(2025, 12, 25)
        should_skip, reason = should_skip_scraping(christmas)
        assert should_skip
        assert "holiday" in reason.lower()
    
    def test_no_skip_on_trading_day(self):
        """Test that scraping is not skipped on trading days."""
        # Regular Tuesday
        tuesday = dt.date(2026, 3, 3)
        should_skip, reason = should_skip_scraping(tuesday)
        assert not should_skip
        assert "open" in reason.lower()


class TestApproximateTradingDay:
    """Test approximate trading day calculation for database lookups."""
    
    def test_approximate_trading_day_calculation(self):
        """Test approximate trading day with buffer calculation."""
        today = dt.date(2026, 3, 6)  # Friday
        
        # 1 day back with buffer
        approx_1d = get_approximate_trading_day(today, 1)
        # Should go back ~1.4 days + 2 days buffer = ~3 days
        # So around March 3 (Tuesday) or March 2 (Monday)
        assert approx_1d <= dt.date(2026, 3, 4)
        assert approx_1d >= dt.date(2026, 3, 1)
        
        # 5 days back with buffer  
        approx_5d = get_approximate_trading_day(today, 5)
        # Should go back ~7+2=9 days, so around Feb 25-27
        assert approx_5d <= dt.date(2026, 2, 28)
        assert approx_5d >= dt.date(2026, 2, 24)
    
    def test_approximate_avoids_weekend(self):
        """Test that approximate trading day avoids landing on weekends."""
        # Test multiple scenarios to ensure we don't land on weekends
        for days_back in [1, 5, 10, 21]:
            for start_day in range(7):  # Test all weekdays
                test_date = dt.date(2026, 3, 3) + dt.timedelta(days=start_day)
                approx_date = get_approximate_trading_day(test_date, days_back)
                
                # Should not land on weekend
                assert approx_date.weekday() < 5, f"Landed on weekend: {approx_date} (weekday {approx_date.weekday()})"


class TestMarketHours:
    """Test market hours detection."""
    
    def test_market_hours_detection(self):
        """Test market hours ET detection."""
        # Market hours: 9:30 AM - 4:00 PM ET (we use 9-16 for buffer)
        assert is_market_hours_et(10)  # 10 AM ET
        assert is_market_hours_et(15)  # 3 PM ET
        assert is_market_hours_et(9)   # 9 AM ET (early but allowed)
        assert is_market_hours_et(16)  # 4 PM ET (late but allowed)
        
        # Outside market hours
        assert not is_market_hours_et(8)   # 8 AM ET (too early)
        assert not is_market_hours_et(17)  # 5 PM ET (too late)  
        assert not is_market_hours_et(22)  # 10 PM ET
        assert not is_market_hours_et(2)   # 2 AM ET
    
    def test_market_hours_current_time_simple(self):
        """Test market hours function can be called without error."""
        # Simple test - just verify the function can be called
        result = is_market_hours_et()
        assert isinstance(result, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])