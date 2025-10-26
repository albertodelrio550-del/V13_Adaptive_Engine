# run_alpaca_paper.py
import time
from alpaca_feed_core import get_snapshot
from commander_v13_manual import update_prices, quick_deploy_demo

SYMBOL = "BTC/USD"
INTERVAL = 3.0

def main():
    print("V13 Manual — Live TP/SL Test\n-----------------------------")
    quick_deploy_demo()

    while True:
        quote = get_snapshot(SYMBOL)
        if quote:
            update_prices(SYMBOL, quote)
        else:
            print("No snapshot received. Check network or keys.")
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
