import json, time, os, urllib.request, urllib.error
UA = 'Mozilla/5.0 (compatible; DOG-Monitor/1.0; +https://allexst63.github.io/dog-monitor/)'
os.makedirs('probe/out', exist_ok=True)
log = []
def get(u):
    req = urllib.request.Request(u, headers={'User-Agent': UA, 'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            b = r.read().decode('utf-8'); log.append([u, r.status, len(b)]); return json.loads(b)
    except urllib.error.HTTPError as e:
        log.append([u, e.code, (e.read() or b'')[:200].decode('utf-8', 'replace')]); return None
    except Exception as e:
        log.append([u, 'ERR', str(e)[:200]]); return None
now = int(time.time())
gate = []
start = 1713916800  # 2024-04-24
while start < now:
    end = min(now, start + 999 * 86400)
    d = get(f'https://api.gateio.ws/api/v4/spot/candlesticks?currency_pair=DOG_USDT&interval=1d&from={start}&to={end}')
    if not d: break
    gate += d; start = end + 86400
json.dump(gate, open('probe/out/gate_1d.json', 'w'))
json.dump(get('https://api.mexc.com/api/v3/klines?symbol=DOGUSDT&interval=1d&limit=1000'), open('probe/out/mexc_1d.json', 'w'))
json.dump(get('https://api.kraken.com/0/public/OHLC?pair=DOGUSD&interval=1440&since=1700000000'), open('probe/out/kraken_1d.json', 'w'))
json.dump(log, open('probe/out/log2.json', 'w'), indent=1)
print(json.dumps(log, indent=1)[:3000])
