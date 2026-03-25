import os
import logging
import sys
from data.fred_client import FredClient
from src.config.settings import Settings

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def check_fred():
    print("-" * 30)
    print("FRED API Diagnostic Tool")
    print("-" * 30)
    
    # 1. Check Environment Variable
    api_key_env = os.environ.get('FRED_API_KEY')
    print(f"Environment Variable FRED_API_KEY: {'[SET]' if api_key_env else '[NOT SET]'}")
    
    # 2. Check Settings/Client
    try:
        client = FredClient()
        # FredClient doesn't store api_key directly, it passes it to self.fred
        has_fred = hasattr(client, 'fred')
        print(f"FredClient Initialized: {has_fred}")
        
        # 3. Test Connection
        print("Attempting to fetch 'SP500' series...")
        try:
            # SP500 is a standard FRED series
            # Note: fredapi Fred object has a get_series method
            data = client.fred.get_series('SP500')
            if data is not None and not data.empty:
                print("SUCCESS: Connection established and data retrieved.")
                print(f"Latest value date: {data.index[-1]}")
                print(f"Latest value: {data.iloc[-1]}")
            else:
                print("WARNING: Request completed but returned empty data.")
        except Exception as e:
            error_msg = str(e)
            print(f"CRITICAL ERROR: {error_msg}")
            if '403' in error_msg or 'api_key' in error_msg.lower() or 'unauthorized' in error_msg.lower():
                print("DIAGNOSIS: This looks like an invalid or unauthorized API key.")
            elif '429' in error_msg:
                print("DIAGNOSIS: Rate limit exceeded.")
            else:
                print("DIAGNOSIS: API error. Check if the series 'SP500' exists or if there's a network issue.")
                
    except Exception as e:
        print(f"Initialization Error: {e}")

if __name__ == "__main__":
    check_fred()
