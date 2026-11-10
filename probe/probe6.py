#!/usr/bin/env python3
"""Временная диагностика источников (ветка probe): печатает ответы API в журнал GitHub Actions."""
import json
import sys
import time
import urllib.error
import urllib.request

UA = 'Mozilla/5.0 (compatible; DOG-Monitor/1.0; +https://allexst63.github.io/dog-monitor/)'


def req(url, headers=None, timeout=40):
    h = {'User-Agent': UA, 'Accept': 'application/json'}
    h.update(headers or {})
    t0 = time.time()
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout)
        return r.status, dict(r.headers), r.read(), time.time() - t0
    except urllib.error.HTTPError as e:
        try:
            body = e.read()[:1500]
        except Exception:
            body = b''
        return e.code, dict(e.headers), body, time.time() - t0
    except Exception as e:
        return None, {}, repr(e).encode(), time.time() - t0


def shape(d, depth=0):
    if depth > 4:
        return '…'
    if isinstance(d, dict):
        return '{' + ', '.join(f'{k}: {shape(v, depth + 1)}' for k, v in list(d.items())[:30]) + '}'
    if isinstance(d, list):
        return f'[{len(d)}× ' + (shape(d[0], depth + 1) if d else '') + ']'
    if isinstance(d, str):
        return 'str(' + d[:40] + ')'
    return repr(d)[:40]


def show(name, url, headers=None, n=700, hdr=False):
    st, hd, body, dt = req(url, headers)
    print(f'\n=== {name}: HTTP {st} {dt:.1f}s {len(body)}b :: {url[:150]}')
    if hdr or (st != 200):
        print('   headers:', {k: v for k, v in hd.items() if k.lower() in ('retry-after', 'server', 'cf-ray', 'cf-cache-status', 'x-ratelimit-limit', 'x-ratelimit-remaining', 'x-ratelimit-reset', 'ratelimit-limit', 'ratelimit-remaining', 'ratelimit-reset', 'content-type', 'via', 'x-cache', 'age', 'cache-control')})
    try:
        d = json.loads(body.decode('utf-8'))
        print('   shape:', shape(d)[:n])
        return d
    except Exception:
        print('   body:', body[:300])
        return None


live = json.load(open('data/live.json', encoding='utf-8'))
top = [x['a'] for x in live['top100']]
A0, A1 = top[0], top[50]
what = sys.argv[1] if len(sys.argv) > 1 else 'all'

if what in ('all', 'api'):
    show('hiro holders (name)', 'https://api.hiro.so/runes/v1/etchings/DOGGOTOTHEMOON/holders?limit=60&offset=0', n=500)
    d = show('hiro holders (id)', 'https://api.hiro.so/runes/v1/etchings/840000:3/holders?limit=60&offset=0', n=500, hdr=True)
    if d and d.get('results'):
        print('   first:', d['results'][:3], 'total:', d.get('total'))
        d2 = show('hiro holders p2', 'https://api.hiro.so/runes/v1/etchings/840000:3/holders?limit=60&offset=60', n=200)
        if d2 and d2.get('results'):
            print('   #61:', d2['results'][0], '#120:', d2['results'][-1])
    show('hiro address', f'https://api.hiro.so/runes/v1/addresses/{A1}/balances?limit=20', n=600)
    show('hiro etching', 'https://api.hiro.so/runes/v1/etchings/840000:3', n=700)
    d = show('dogdata address', f'https://www.dogdata.xyz/api/address/bitcoin/{A1}?limit=1', n=2500)
    if isinstance(d, dict):
        for k, v in d.items():
            if k != 'transactions':
                print('   ', k, '=', json.dumps(v, ensure_ascii=False)[:600])
    d = show('dogdata top-holders', 'https://www.dogdata.xyz/api/dog-rune/top-holders?limit=100', n=900)
    if isinstance(d, dict):
        print('   keys:', {k: (v if not isinstance(v, (list, dict)) else type(v).__name__) for k, v in d.items()})
    d = show('dogdata holders limit=100', 'https://www.dogdata.xyz/api/dog-rune/holders?page=1&limit=100', n=500)
    if isinstance(d, dict):
        print('   keys:', {k: (v if not isinstance(v, (list, dict)) else type(v).__name__) for k, v in d.items()})
    d = show('dogdata health', 'https://www.dogdata.xyz/api/health', n=1500)
    print('   ', json.dumps(d, ensure_ascii=False)[:1500] if d else '')
    d = show('dogdata stats', 'https://www.dogdata.xyz/api/dog-rune/stats', n=900)
    show('magiceden balance', f'https://api-mainnet.magiceden.dev/v2/ord/btc/runes/wallet/balances/{A1}/DOGGOTOTHEMOON', n=600, hdr=True)
    show('magiceden rune info', 'https://api-mainnet.magiceden.dev/v2/ord/btc/runes/market/DOGGOTOTHEMOON/info', n=600)
    show('unisat nokey', f'https://open-api.unisat.io/v1/indexer/address/{A1}/runes/840000%3A3/balance', n=400)
    show('unisat holders nokey', 'https://open-api.unisat.io/v1/indexer/runes/840000%3A3/holders?start=0&limit=20', n=400)
    show('xverse', f'https://api-3.xverse.app/v2/address/{A1}/rune-balance?includeUnconfirmed=false', n=600)
    show('bestinslot nokey', 'https://api.bestinslot.xyz/v3/runes/holders?rune_id=840000:3&sort_by=balance&order=desc&offset=0&count=20', n=400)
    show('geniidata nokey', 'https://api.geniidata.com/api/1/runes/840000:3/holders?limit=20&offset=0', n=400)
    show('okx nokey', f'https://www.okx.com/api/v5/explorer/btc/address-balance-list?address={A1}&symbol=runes', n=400)
    show('ordiscan nokey', f'https://api.ordiscan.com/v1/address/{A1}/runes', n=400)
    show('ord rune', 'https://ordinals.com/rune/DOG%E2%80%A2GO%E2%80%A2TO%E2%80%A2THE%E2%80%A2MOON', n=900, hdr=True)
    d = show('kraken 1w', 'https://api.kraken.com/0/public/OHLC?pair=DOGUSD&interval=10080', n=300)
    if d and d.get('result'):
        k = next(x for x in d['result'] if x != 'last')
        rows = d['result'][k]
        print('   weekly rows:', len(rows), 'first', rows[0][:5], time.strftime('%a %Y-%m-%d', time.gmtime(rows[0][0])), 'last', rows[-1][:5], time.strftime('%a %Y-%m-%d', time.gmtime(rows[-1][0])))
    d = show('kraken 1d', 'https://api.kraken.com/0/public/OHLC?pair=DOGUSD&interval=1440', n=200)
    if d and d.get('result'):
        k = next(x for x in d['result'] if x != 'last')
        rows = d['result'][k]
        print('   daily rows:', len(rows), 'first', time.strftime('%a %Y-%m-%d', time.gmtime(rows[0][0])), 'last', time.strftime('%a %Y-%m-%d', time.gmtime(rows[-1][0])))

if what in ('all', 'ord'):
    def ord_one(a):
        st, hd, body, dt = req(f'https://ordinals.com/address/{a}', timeout=60)
        bal = None
        if st == 200:
            try:
                d = json.loads(body.decode())
                bal = next((r[1] for r in d.get('runes_balances') or [] if r[0] == 'DOG•GO•TO•THE•MOON'), '0')
            except Exception as e:
                bal = 'parse:' + repr(e)[:60]
        return st, hd, body, dt, bal
    print('\n##### ordinals.com: 14 запросов подряд без пауз')
    first_err = True
    for i, a in enumerate(top[:14]):
        st, hd, body, dt, bal = ord_one(a)
        print(f'  {i:2d} HTTP {st} {dt:5.1f}s {len(body):7d}b bal={bal}')
        if st != 200 and first_err:
            first_err = False
            print('   headers:', hd)
            print('   body:', body[:400])
    print('##### пауза 25 с, затем 14 запросов с шагом 2 с')
    time.sleep(25)
    for i, a in enumerate(top[14:28]):
        st, hd, body, dt, bal = ord_one(a)
        print(f'  {i:2d} HTTP {st} {dt:5.1f}s {len(body):7d}b bal={bal}')
        if st != 200:
            print('   headers:', {k: v for k, v in hd.items() if k.lower() in ('retry-after', 'server', 'cf-ray', 'content-type')}, body[:200])
        time.sleep(2)
    print('##### самые тяжёлые адреса (биржи): размер ответа')
    for a in top[:3]:
        st, hd, body, dt, bal = ord_one(a)
        print(f'  {a[:14]} HTTP {st} {dt:5.1f}s {len(body)}b bal={bal}')
        time.sleep(2)
