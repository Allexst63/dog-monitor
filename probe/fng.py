import json, time, os, re, urllib.request, urllib.error
UA = 'Mozilla/5.0 (compatible; DOG-Monitor/1.0; +https://allexst63.github.io/dog-monitor/)'
os.makedirs('probe/out3', exist_ok=True)
log = []
def get(u, raw=False):
    req = urllib.request.Request(u, headers={'User-Agent': UA, 'Accept': '*/*' if raw else 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            b = r.read().decode('utf-8', 'replace'); log.append([u, r.status, len(b)])
            return b if raw else json.loads(b)
    except urllib.error.HTTPError as e:
        log.append([u, e.code, (e.read() or b'')[:200].decode('utf-8', 'replace')]); return None
    except Exception as e:
        log.append([u, 'ERR', str(e)[:200]]); return None
DD = 'https://www.dogdata.xyz'
# 1) holder list around the 10M threshold
out = {}
for lim, pages in ((100, (1, 8, 9, 10)), (25, (33, 34, 35, 36))):
    for pg in pages:
        d = get(f'{DD}/api/dog-rune/holders?page={pg}&limit={lim}')
        out[f'{lim}:{pg}'] = d
        time.sleep(0.3)
json.dump(out, open('probe/out3/holders.json', 'w'))
# 2) metrics endpoints
for ep in ('/api/metrics/utxo-age', '/api/metrics/holder-concentration', '/api/dog-rune/stats', '/api/multichain/stats'):
    json.dump(get(DD + ep), open('probe/out3/' + ep.strip('/').replace('/', '_') + '.json', 'w'))
# 3) discover API endpoints from the site's JS
html = get(DD + '/', raw=True) or ''
srcs = sorted(set(re.findall(r'(/_next/static/[^"\']+\.js)', html)))
eps = set()
for s in srcs[:60]:
    js = get(DD + s, raw=True) or ''
    for m in re.findall(r'["\'`](/api/[A-Za-z0-9_\-/{}$.?=&]+)', js):
        eps.add(m)
    time.sleep(0.1)
json.dump({'scripts': srcs, 'endpoints': sorted(eps)}, open('probe/out3/endpoints.json', 'w'), indent=1)
# 4) Kraken asset pairs for memecoins
ap = get('https://api.kraken.com/0/public/AssetPairs')
want = ('XDG', 'DOGE', 'SHIB', 'PEPE', 'BONK', 'WIF', 'FLOKI', 'TRUMP', 'PENGU', 'SPX', 'FARTCOIN', 'BRETT', 'POPCAT', 'MOODENG', 'MEW', 'TURBO', 'NEIRO', 'PNUT', 'GIGA', 'MOG')
pairs = {k: {'alt': v.get('altname'), 'ws': v.get('wsname'), 'base': v.get('base'), 'quote': v.get('quote')} for k, v in ((ap or {}).get('result') or {}).items() if v.get('quote') in ('ZUSD', 'USD') and any(v.get('base', '').upper().startswith(w) or (v.get('altname') or '').upper().startswith(w) for w in want)}
json.dump(pairs, open('probe/out3/kraken_meme_pairs.json', 'w'), indent=1)
# 5) CoinGecko ids for the memecoins (top meme category)
cg = get('https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&category=meme-token&order=market_cap_desc&per_page=40&page=1')
json.dump([{k: x.get(k) for k in ('id', 'symbol', 'name', 'market_cap_rank', 'current_price', 'market_cap')} for x in (cg or [])], open('probe/out3/cg_memes.json', 'w'), indent=1)
json.dump(log, open('probe/out3/log.json', 'w'), indent=1)
print(json.dumps(log, indent=1)[:4000])
