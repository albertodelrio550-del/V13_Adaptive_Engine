import json
from binance.client import Client

def main():
    with open('config/binance_keys.json','r', encoding='utf-8-sig') as f:
        creds=json.load(f)
    c=Client(creds['api_key'], creds['api_secret'])
    c.API_URL='https://testnet.binance.vision/api'
    c.FUTURES_URL=c.FUTURES_TESTNET_URL
    print('API_URL', c.API_URL)
    print('FUTURES_URL', c.FUTURES_URL)
    try:
        c.get_account(); print('spot ok')
    except Exception as e:
        print('spot err', e)
    try:
        r=c.futures_account(); print('fut ok', isinstance(r, dict))
    except Exception as e:
        print('fut err', e)

if __name__ == '__main__':
    main()
