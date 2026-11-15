import json, time, os, urllib.request, urllib.error
UA = 'Mozilla/5.0 (compatible; DOG-Monitor/1.0; +https://allexst63.github.io/dog-monitor/)'
os.makedirs('probe/out', exist_ok=True)
log = []
def get(u, raw=False):
    req = urllib.request.Request(u, headers={'User-Agent': UA, 'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            b = r.read().decode('utf-8')
            log.append([u, r.status, len(b), r.headers.get('access-control-allow-origin')])
            return json.loads(b)
    except urllib.error.HTTPError as e:
        log.append([u, e.code, (e.read() or b'')[:300].decode('utf-8', 'replace'), None]); return None
    except Exception as e:
        log.append([u, 'ERR', str(e)[:300], None]); return None
now = int(time.time())
alt = get('https://api.alternative.me/fng/?limit=0&format=json')
json.dump(alt, open('probe/out/alt.json', 'w'))
cmc = get(f'https://api.coinmarketcap.com/data-api/v3/fear-greed/chart?start=1367193600&end={now}')
json.dump(cmc, open('probe/out/cmc_chart.json', 'w'))
for u in ['https://api.coinmarketcap.com/data-api/v3/fear-greed/latest',
          'https://api.coinmarketcap.com/data-api/v3/fear-greed/chart?start=%d&end=%d' % (now - 3 * 86400, now),
          'https://api.coinmarketcap.com/data-api/v3/global-metrics/quotes/latest']:
    d = get(u)
    json.dump(d, open('probe/out/' + u.split('/v3/')[1].split('?')[0].replace('/', '_') + ('_3d' if 'chart' in u else '') + '.json', 'w'))
cg = get('https://api.coingecko.com/api/v3/coins/dog-go-to-the-moon-rune/market_chart?vs_currency=usd&days=365&interval=daily')
json.dump(cg, open('probe/out/cg_dog_365.json', 'w'))
time.sleep(3)
cgb = get('https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=365&interval=daily')
json.dump(cgb, open('probe/out/cg_btc_365.json', 'w'))
json.dump(log, open('probe/out/log.json', 'w'), indent=1)
print(json.dumps(log, indent=1)[:4000])
