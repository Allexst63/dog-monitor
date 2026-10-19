#!/usr/bin/env python3
"""DOG Монитор — сбор данных напрямую из публичных API (для GitHub Actions).

    python3 tools/fetch.py <raw_dir> [имя ...]            все источники или только названные
    python3 tools/fetch.py <raw_dir> --entity <адрес> ...  профили адресов dogdata

Пишет raw/<имя>.txt в том же текстовом виде, который разбирает tools/dogmon.py
(раньше эти файлы готовил WebFetch). Сырые ответы JSON кладёт в raw/json/ — для отладки.
Цены DOG — только с бирж и dogdata.xyz.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

UA = 'Mozilla/5.0 (compatible; DOG-Monitor/1.0; +https://allexst63.github.io/dog-monitor/)'
DD = ('https://www.dogdata.xyz', 'https://dogdata.xyz')
LAST = [None]


def get(urls, tries=3):
    if isinstance(urls, str):
        urls = [urls]
    last = None
    for i in range(tries):
        for u in urls:
            sep = '&' if '?' in u else '?'
            full = f'{u}{sep}cb={int(time.time() * 1000)}'
            try:
                req = urllib.request.Request(full, headers={'User-Agent': UA, 'Accept': 'application/json'})
                with urllib.request.urlopen(req, timeout=30) as r:
                    LAST[0] = json.loads(r.read().decode('utf-8'))
                    return LAST[0]
            except (urllib.error.URLError, ValueError, TimeoutError, OSError) as e:
                last = f'{u}: {e}'
        time.sleep(2 + 3 * i)
    raise RuntimeError(last)


def s(x):
    """точная строка значения, как в JSON"""
    if x is None:
        return 'null'
    if isinstance(x, float):
        return repr(x)
    return str(x)


def lvl(rows):
    """[[p, q, ...]] или [{price, amount|qty|quantity|size}] → [(p, q, ts?)]"""
    out = []
    for r in rows or []:
        if isinstance(r, dict):
            p = r.get('price', r.get('p'))
            q = next((r[k] for k in ('amount', 'qty', 'quantity', 'size', 'volume', 'q') if k in r), None)
            out.append((p, q, None))
        elif isinstance(r, (list, tuple)) and len(r) >= 2:
            out.append((r[0], r[1], r[2] if len(r) > 2 else None))
    return out


def book_text(head, bids, asks):
    L = [head]
    L += [f'B;{s(p)};{s(q)}' for p, q, _ in bids]
    L += [f'A;{s(p)};{s(q)}' for p, q, _ in asks]
    L.append(f'rows={len(bids)} {len(asks)}')
    return '\n'.join(L)


def first_list(d, need):
    """первый список словарей с ключом need (на любой глубине)"""
    if isinstance(d, list):
        if d and isinstance(d[0], dict) and need in d[0]:
            return d
        for x in d:
            r = first_list(x, need)
            if r:
                return r
    elif isinstance(d, dict):
        for v in d.values():
            r = first_list(v, need)
            if r:
                return r
    return []


def g(d, *path):
    for k in path:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def dk(d, key):
    """значение ключа на любой глубине (первое найденное)"""
    if isinstance(d, dict):
        if key in d:
            return d[key]
        for v in d.values():
            r = dk(v, key)
            if r is not None:
                return r
    elif isinstance(d, list):
        for v in d[:3]:
            r = dk(v, key)
            if r is not None:
                return r
    return None


def items(x, name_keys):
    """список [{...}] или словарь {имя: значение|{...}} → [(имя, dict)]"""
    out = []
    if isinstance(x, dict):
        for k, v in x.items():
            out.append((k, v if isinstance(v, dict) else {'percentage': v}))
    for v in x if isinstance(x, list) else []:
        if isinstance(v, dict):
            out.append((next((v[k] for k in name_keys if k in v), None), v))
    return out


def shape(d, depth=0):
    if depth > 3:
        return '…'
    if isinstance(d, dict):
        return '{' + ', '.join(f'{k}: {shape(v, depth + 1)}' for k, v in list(d.items())[:14]) + '}'
    if isinstance(d, list):
        return f'[{len(d)}× ' + (shape(d[0], depth + 1) if d else '') + ']'
    return type(d).__name__


def addr(x):
    if isinstance(x, str):
        return x
    if isinstance(x, dict):
        return x.get('address') or x.get('addr') or x.get('label') or x.get('name') or 'null'
    if isinstance(x, list) and x:
        return addr(x[0])
    return 'null'


# ---------- источники ----------
def f_stats():
    d = get([h + '/api/dog-rune/stats' for h in DD])
    top = first_list(d.get('top10_holders') or d, 'address')
    L = [f"total_holders={s(d.get('total_holders'))}", f"last_updated={s(d.get('last_updated'))}"]
    L += [f"{s(h.get('rank'))};{h.get('address')};{s(h.get('total_dog'))}" for h in top]
    return d, '\n'.join(L)


def f_holders(k):
    def run():
        d = get([h + f'/api/dog-rune/holders?page={k}&limit=25' for h in DD])
        rows = first_list(d, 'address')
        L = [f"last_updated={s(d.get('last_updated'))}", f"total={s(g(d, 'pagination', 'total'))}"]
        L += [f"{s(h.get('rank'))};{h.get('address')};{s(h.get('total_dog'))};{s(h.get('utxo_count'))}" for h in rows]
        return d, '\n'.join(L)
    return run


def f_conc():
    d = get([h + '/api/metrics/holder-concentration' for h in DD])
    keys = ('top10_supply_pct', 'top100_supply_pct', 'top1000_supply_pct', 'gini_coefficient', 'total_holders', 'last_updated')
    return d, '\n'.join(f'{k}={s(d.get(k, g(d, "data", k)))}' for k in keys)


def f_whales():
    d = get([h + '/api/whale-alerts?threshold=5000000&limit=200' for h in DD])
    al = first_list(d, 'txid') or first_list(d, 'total_dog_moved')
    L = [f"timestamp={s(d.get('timestamp'))}", f"total_alerts={s(d.get('total_alerts'))}"]
    L += [f"{s(a.get('timestamp'))};{s(a.get('total_dog_moved'))};{addr(a.get('from'))};{addr(a.get('to'))};{s(a.get('txid'))}" for a in al]
    return d, '\n'.join(L)


def f_markets():
    d = get([h + '/api/markets' for h in DD])
    tk = first_list(d, 'market') or first_list(d, 'pair')
    L = [f"last_updated={s(dk(d, 'last_updated'))}; price={s(dk(d, 'price') if not isinstance(dk(d, 'price'), (dict, list)) else None)}; "
         f"totalVolume={s(dk(d, 'totalVolume'))}; marketCap={s(dk(d, 'marketCap'))}; priceChange24h={s(dk(d, 'priceChange24h'))}"]
    L += [f"{t.get('market')};{t.get('pair')};{s(t.get('price'))};{s(t.get('volumeUsd'))}" for t in tk]
    return d, '\n'.join(L)


def kraken_book(side, count):
    def run():
        d = get(f'https://api.kraken.com/0/public/Depth?pair=DOGUSD&count={count}')
        key = next(iter(d.get('result') or {}), None)
        rows = ((d.get('result') or {}).get(key) or {}).get(side) or []
        ts = max((int(float(r[2])) for r in rows), default=0)
        L = [f"pair={key}; error={json.dumps(d.get('error'))}; maxts={ts}"]
        L += [f"{'B' if side == 'bids' else 'A'};{r[0]};{r[1]};{int(float(r[2]))}" for r in rows]
        L.append(f'rows={len(rows)}')
        return d, '\n'.join(L)
    return run


def f_gate_book():
    d = get(['https://api.gateio.ws/api/v4/spot/order_book?currency_pair=DOG_USDT&interval=0.00001&limit=100',
             'https://api.gate.io/api/v4/spot/order_book?currency_pair=DOG_USDT&interval=0.00001&limit=100'])
    return d, book_text(f"current={s(d.get('current'))}; update={s(d.get('update'))}", lvl(d.get('bids')), lvl(d.get('asks')))


def f_gate_ticker():
    d = get(['https://api.gateio.ws/api/v4/spot/tickers?currency_pair=DOG_USDT',
             'https://api.gate.io/api/v4/spot/tickers?currency_pair=DOG_USDT'])
    t = d[0] if isinstance(d, list) and d else d
    keys = ('last', 'highest_bid', 'lowest_ask', 'change_percentage', 'quote_volume', 'high_24h', 'low_24h')
    return d, '; '.join(f'{k}={s(t.get(k))}' for k in keys)


def f_mexc():
    t0 = int(time.time() * 1000)
    d = get('https://api.mexc.com/api/v3/depth?symbol=DOGUSDT&limit=150')
    ts = d.get('timestamp') or t0      # MEXC не всегда отдаёт время — стакан живой, берём время запроса
    return d, book_text(f"id={s(d.get('lastUpdateId'))}; ts={s(ts)}", lvl(d.get('bids')), lvl(d.get('asks')))


def f_bingx():
    t0 = int(time.time() * 1000)
    d = get('https://open-api.bingx.com/openApi/spot/v1/market/depth?symbol=DOG-USDT&limit=150')
    x = d.get('data') or {}
    ts = x.get('ts') or d.get('timestamp') or t0
    return d, book_text(f"code={s(d.get('code'))}; ts={s(ts)}", lvl(x.get('bids')), lvl(x.get('asks')))


def f_bitget():
    d = get('https://api.bitget.com/api/v2/spot/market/orderbook?symbol=DOGUSDT&type=step0&limit=150')
    x = d.get('data') or {}
    return d, book_text(f"code={s(d.get('code'))}; ts={s(x.get('ts') or d.get('requestTime'))}", lvl(x.get('bids')), lvl(x.get('asks')))


def f_digifinex():
    d = get('https://openapi.digifinex.com/v3/order_book?symbol=dog_usdt&limit=150')
    return d, book_text(f"code={s(d.get('code'))}; date={s(d.get('date'))}", lvl(d.get('bids')), lvl(d.get('asks')))


def f_coinw():
    d = get('https://api.coinw.com/api/v1/public?command=returnOrderBook&symbol=DOG(RUNE)_USDT&size=100')
    x = d.get('data') if isinstance(d.get('data'), dict) else d
    return d, book_text(f"code={s(d.get('code'))}", lvl(x.get('bids')), lvl(x.get('asks')))


def f_btc():
    d = get('https://api.exchange.coinbase.com/products/BTC-USD/ticker')
    return d, f"price={s(d.get('price'))}; time={s(d.get('time'))}"


def ohlc(interval, back):
    def run():
        since = int(time.time()) - back
        d = get(f'https://api.kraken.com/0/public/OHLC?pair=DOGUSD&interval={interval}&since={since}')
        res = d.get('result') or {}
        key = next((k for k in res if k != 'last'), None)
        rows = res.get(key) or []
        L = [f"pair={key}; error={json.dumps(d.get('error'))}; last={s(res.get('last'))}"]
        L += [';'.join(str(v) for v in r[:8]) for r in rows]
        L.append(f'rows={len(rows)}')
        return d, '\n'.join(L)
    return run


def f_age():
    d = get([h + '/api/metrics/utxo-age' for h in DD])
    keys = ('last_updated', 'total_utxos', 'total_supply', 'avg_age_days', 'median_age_days', 'lth_percentage', 'sth_percentage',
            'realized_cap', 'market_cap', 'mvrv_ratio', 'supply_in_profit_pct', 'supply_in_loss_pct', 'current_price')
    L = [f'{k}={s(dk(d, k))}' for k in keys]
    for name, w in items(dk(d, 'hodl_waves'), ('range', 'label', 'name', 'age')):
        L.append(f"wave;{name};{s(w.get('percentage', w.get('pct')))}")
    for name, b in items(dk(d, 'size_distribution'), ('bucket', 'name', 'label', 'range', 'size')):
        L.append(f"size;{name};{s(b.get('count'))};{s(b.get('percentage', b.get('pct')))}")
    return d, '\n'.join(L)


def f_airdrop():
    d = get([h + '/api/airdrop/summary' for h in DD])
    keys = ('last_updated', 'total_recipients', 'still_holding', 'sold_everything', 'retention_rate', 'total_current_balance', 'accumulated')
    L = [f'{k}={s(d.get(k))}' for k in keys]
    L += [f"diamond_paws={s(g(d, 'accumulator_breakdown', 'diamond_paws'))}", f"paper_hands={s(g(d, 'accumulator_breakdown', 'paper_hands'))}"]
    return d, '\n'.join(L)


def f_chains():
    d = get([h + '/api/multichain/stats' for h in DD])
    L = [f"last_updated={s(d.get('last_updated'))}; total_holders={s(d.get('total_holders'))}"]
    for c in d.get('chains') or []:
        L.append('chain;' + ';'.join(s(c.get(k)) for k in ('chain', 'holder_count', 'price_usd', 'volume_24h_usd',
                                                         'liquidity_usd', 'total_supply', 'last_updated')))
    return d, '\n'.join(L)


def f_entity(a):
    d = get([h + f'/api/address/bitcoin/{a}?limit=1' for h in DD], tries=2)
    e, st = d.get('entity') or {}, d.get('stats') or {}
    return d, (f"entity_name={s(e.get('name'))}; kind={s(e.get('kind'))}; role={s(e.get('role'))}; claim={s(e.get('claim'))}; "
               f"first_tx={s(st.get('first_tx_timestamp'))}; last_tx={s(st.get('last_tx_timestamp'))}; tx_count={s(d.get('tx_count', st.get('tx_count')))}; "
               f"received={s(st.get('total_received_dog'))}; sent={s(st.get('total_sent_dog'))}; note={s(e.get('evidence_note'))}")


SOURCES = {
    'stats': f_stats, 'holders_1': f_holders(1), 'holders_2': f_holders(2), 'holders_3': f_holders(3), 'holders_4': f_holders(4),
    'conc': f_conc, 'whales': f_whales, 'markets': f_markets,
    'kraken_bids': kraken_book('bids', 200), 'kraken_asks': kraken_book('asks', 120),
    'gate_book': f_gate_book, 'gate_ticker': f_gate_ticker, 'mexc_book': f_mexc, 'bingx_book': f_bingx,
    'bitget_book': f_bitget, 'digifinex_book': f_digifinex, 'coinw_book': f_coinw, 'btc': f_btc,
    'ohlc_1d': ohlc(1440, 365 * 86400), 'ohlc_1h': ohlc(60, 7 * 86400),
    'dd_age': f_age, 'dd_airdrop': f_airdrop, 'dd_chains': f_chains,
}


def save(raw, name, fn):
    os.makedirs(os.path.join(raw, 'json'), exist_ok=True)
    LAST[0] = None
    try:
        d, text = fn()
        json.dump(d, open(os.path.join(raw, 'json', name + '.json'), 'w', encoding='utf-8'), ensure_ascii=False)
        ok = True
    except Exception as e:
        text, ok = f'UNAVAILABLE: {e}', False
        try:
            print(f'SHAPE {name}:', shape(LAST[0]))
        except Exception:
            pass
    open(os.path.join(raw, name + '.txt'), 'w', encoding='utf-8').write(text + '\n')
    if name in os.environ.get('DOGMON_SHAPE', '').split(','):
        print(f'SHAPE {name}:', shape(LAST[0])[:1500])
    print(f"FETCH {'ok ' if ok else 'ERR'} {name}: {text.splitlines()[0][:140] if text else ''}")
    return ok


def main():
    raw = sys.argv[1]
    os.makedirs(raw, exist_ok=True)
    args = sys.argv[2:]
    if args and args[0] == '--entity':
        for a in args[1:]:
            save(raw, 'entity_' + a, lambda a=a: f_entity(a))
            time.sleep(0.3)
        return
    names = args or list(SOURCES)
    bad = [n for n in names if n in SOURCES and not save(raw, n, SOURCES[n])]
    print(f'FETCH_DONE ok={len(names) - len(bad)}/{len(names)}' + (' failed=' + ','.join(bad) if bad else ''))


if __name__ == '__main__':
    main()
