import json, os, urllib.request, urllib.error, time
UA = 'Mozilla/5.0 (compatible; DOG-Monitor/1.0; +https://allexst63.github.io/dog-monitor/)'
out = 'probe/out/b1'; os.makedirs(out, exist_ok=True)
res = []
def get(u):
    req = urllib.request.Request(u, headers={'User-Agent': UA, 'Accept': 'application/json', 'Origin': 'https://allexst63.github.io'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            b = r.read().decode('utf-8', 'replace'); h = dict(r.headers)
            return r.status, json.loads(b), {k: v for k, v in h.items() if k.lower().startswith('access-control')}
    except urllib.error.HTTPError as e:
        return e.code, (e.read() or b'')[:300].decode('utf-8', 'replace'), {}
    except Exception as e:
        return 'ERR', str(e)[:200], {}
def summ(name, u, pick):
    st, d, cors = get(u)
    row = {'name': name, 'url': u, 'status': st, 'cors': cors}
    try:
        bids, asks = pick(d)
        bp = [float(x[0] if isinstance(x, (list, tuple)) else x.get('p') or x.get('price')) for x in bids]
        bq = [float(x[1] if isinstance(x, (list, tuple)) else x.get('s') or x.get('amount')) for x in bids]
        row.update({'nb': len(bids), 'na': len(asks), 'b0': bp[:1], 'bmin': min(bp) if bp else None, 'bigb': sorted(zip(bq, bp), reverse=True)[:5]})
    except Exception as e:
        row['err'] = str(e)[:200]; row['raw'] = str(d)[:300]
    res.append(row); time.sleep(0.4)
G = lambda d: (d['bids'], d['asks'])
for lim in (100, 200, 500, 1000):
    summ(f'gate i0 L{lim}', f'https://api.gateio.ws/api/v4/spot/order_book?currency_pair=DOG_USDT&interval=0&limit={lim}', G)
summ('gate agg1e-5 L100', 'https://api.gateio.ws/api/v4/spot/order_book?currency_pair=DOG_USDT&interval=0.00001&limit=100', G)
summ('gate agg1e-6 L100', 'https://api.gateio.ws/api/v4/spot/order_book?currency_pair=DOG_USDT&interval=0.000001&limit=100', G)
for lim in (150, 1000, 5000):
    summ(f'mexc L{lim}', f'https://api.mexc.com/api/v3/depth?symbol=DOGUSDT&limit={lim}', G)
for lim in (150, 1000):
    summ(f'bingx L{lim}', f'https://open-api.bingx.com/openApi/spot/v1/market/depth?symbol=DOG-USDT&limit={lim}', lambda d: (d['data']['bids'], d['data']['asks']))
summ('kraken 500', 'https://api.kraken.com/0/public/Depth?pair=DOGUSD&count=500', lambda d: (list(d['result'].values())[0]['bids'], list(d['result'].values())[0]['asks']))
for lim in (150, 500):
    summ(f'bitget L{lim}', f'https://api.bitget.com/api/v2/spot/market/orderbook?symbol=DOGUSDT&type=step0&limit={lim}', lambda d: (d['data']['bids'], d['data']['asks']))
json.dump(res, open(f'{out}/books.json', 'w'), indent=1)
for r in res: print(json.dumps({k: r.get(k) for k in ('name', 'status', 'nb', 'b0', 'bmin', 'bigb', 'cors', 'err')})[:600])
