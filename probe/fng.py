import json, os, urllib.request, time
UA = 'Mozilla/5.0 (compatible; DOG-Monitor/1.0; +https://allexst63.github.io/dog-monitor/)'
out = 'probe/out/b2'; os.makedirs(out, exist_ok=True)
U = {
 'gate_full': 'https://api.gateio.ws/api/v4/spot/order_book?currency_pair=DOG_USDT&interval=0&limit=1000',
 'gate_100': 'https://api.gateio.ws/api/v4/spot/order_book?currency_pair=DOG_USDT&interval=0&limit=100',
 'gate_tk': 'https://api.gateio.ws/api/v4/spot/tickers?currency_pair=DOG_USDT',
 'kraken': 'https://api.kraken.com/0/public/Depth?pair=DOGUSD&count=500',
 'digifinex': 'https://openapi.digifinex.com/v3/order_book?symbol=dog_usdt&limit=150',
 'coinw': 'https://api.coinw.com/api/v1/public?command=returnOrderBook&symbol=DOG(RUNE)_USDT&size=100',
 'gate_trades': 'https://api.gateio.ws/api/v4/spot/trades?currency_pair=DOG_USDT&limit=300',
 'kraken_trades': 'https://api.kraken.com/0/public/Trades?pair=DOGUSD',
}
for k, u in U.items():
    try:
        req = urllib.request.Request(u, headers={'User-Agent': UA, 'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=30) as r:
            open(f'{out}/{k}.json', 'w').write(r.read().decode('utf-8'))
        print(k, 'ok')
    except Exception as e:
        print(k, 'ERR', e)
    time.sleep(0.3)
