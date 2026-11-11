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


def f_tiers():
    """сколько кошельков держит от 10 млн, 5 млн и 1 млн DOG и сколько у них монет в сумме: список холдеров DOG DATA
    отсортирован по балансу, поэтому место последнего кошелька с балансом не ниже порога и есть их число — ищем его
    делением пополам по страницам; затем проходим все страницы до порога 1 млн и складываем балансы (до 3 минут;
    не успели или не сошлось — остаются только числа кошельков)"""
    cache = {}
    ps = [25]

    def page(k):
        if k not in cache:
            d = get([h + f'/api/dog-rune/holders?page={k}&limit={ps[0]}' for h in DD], tries=2)
            cache[k] = (first_list(d, 'address'), d)
            time.sleep(0.15)
        return cache[k]
    try:                                       # страницы по 100 — вчетверо меньше запросов, если сервер так умеет
        d = get([h + '/api/dog-rune/holders?page=1&limit=100' for h in DD], tries=1)
        r = first_list(d, 'address')
        if len(r) == 100 and int(g(d, 'pagination', 'total_pages') or 0) >= 10:
            ps[0] = 100
            cache[1] = (r, d)
    except Exception:
        pass
    rows, d0 = page(1)
    pages = int(g(d0, 'pagination', 'total_pages') or 0)
    if not rows or pages < 10:
        raise RuntimeError('нет списка холдеров')
    bal = lambda x: float(x.get('total_dog') or 0)
    L = [f"last_updated={s(d0.get('last_updated'))}; total={s(g(d0, 'pagination', 'total'))}"]
    cnt, last = {}, 1
    for thr in (10e6, 5e6, 1e6):
        lo, hi = 1, pages                      # первая страница, где последний кошелёк уже ниже порога
        while lo < hi:
            mid = (lo + hi) // 2
            r = page(mid)[0]
            if r and bal(r[-1]) >= thr:
                lo = mid + 1
            else:
                hi = mid
        r = page(lo)[0]
        cnt[thr] = (lo - 1) * ps[0] + sum(1 for x in r if bal(x) >= thr)
        last = max(last, lo)
    sums, seen, top1000, t0 = {}, 0, 0.0, time.time()
    try:
        tot = {thr: 0.0 for thr in cnt}
        for k in range(1, last + 1):
            if time.time() - t0 > 180:
                raise RuntimeError('не успели')
            for x in page(k)[0]:
                b = bal(x)
                if seen < 1000:
                    top1000 += b
                seen += 1
                for thr in tot:
                    if b >= thr:
                        tot[thr] += b
        if seen >= cnt[1e6]:
            sums = tot
    except Exception as e:
        L[0] += f'; sums=нет ({e})'
    for thr in (10e6, 5e6, 1e6):
        L.append(f'tier;{int(thr)};{cnt[thr]}' + (f';{sums[thr]:.0f}' if sums else ''))
    if sums and seen >= 1000:
        L.append(f'top1000={top1000:.0f}')
    return {'pages': pages, 'page_size': ps[0], 'asked': len(cache)}, '\n'.join(L)


def f_chains():
    d = get([h + '/api/multichain/stats' for h in DD])
    L = [f"last_updated={s(d.get('last_updated'))}; total_holders={s(d.get('total_holders'))}"]
    for c in d.get('chains') or []:
        L.append('chain;' + ';'.join(s(c.get(k)) for k in ('chain', 'holder_count', 'price_usd', 'volume_24h_usd',
                                                         'liquidity_usd', 'total_supply', 'last_updated')))
    return d, '\n'.join(L)


# ---------- свежие балансы топ-кошельков из блокчейна ----------
# DOG DATA иногда днями не обновляет топ-100 (/api/dog-rune/holders). Поэтому балансы DOG берём прямо из индекса рун
# ordinals.com (официальный обозреватель ord): /address/<адрес> с Accept: application/json отдаёт runes_balances.
# ordinals.com стоит за балансировщиком, и больше половины его серверов отвечают «406 JSON API disabled» — это не лимит
# и не ошибка адреса: тот же запрос через долю секунды попадает на другой сервер и проходит. Поэтому спрашиваем до 16 раз.
# Если адрес так и не ответил — второй независимый источник: API кошелька Xverse (rune-balance). Им же сверяем
# несколько адресов, чтобы убедиться, что балансы настоящие (строка xcheck).
# Кандидаты в топ-100: вчерашний топ-100 сайта, места 1–150 и топ-10 DOG DATA, участники переводов от 5 млн DOG.
# Чтобы войти в топ-100, нужны десятки миллионов DOG — такой приход виден в переводах от 5 млн.
RUNE = 'DOG•GO•TO•THE•MOON'
RUNE_ID = '840000:3'
RAWDIR = [None]
ORD_TRIES = 10          # попыток на адрес: отвечает примерно каждая третья-восьмая (остальные серверы — «406»)
ORD_GAP = 0.4           # секунд между запросами к ordinals.com (все потоки вместе) — чтобы не упереться в лимит
ORD_BUDGET = 150        # секунд на опрос ordinals.com (сначала самые крупные); кто не успел — спрашиваем у Xverse
XV_GAP = 0.5
XV_BUDGET = 120
REUSE_MIN = 20          # повторный запуск в той же сводке: балансы моложе стольких минут заново не спрашиваем


class Pace:
    """общий для всех потоков интервал между запросами и общая пауза, если сервер просит притормозить"""

    def __init__(self, gap):
        import threading
        self.gap, self.next, self.lock = gap, 0.0, threading.Lock()

    def wait(self):
        with self.lock:
            now = time.time()
            t = max(now, self.next)
            self.next = t + self.gap
        if t > now:
            time.sleep(t - now)

    def hold(self, secs):
        with self.lock:
            self.next = max(self.next, time.time() + secs)


def ord_balance(a, pace=None, deadline=None, stat=None, tries=ORD_TRIES):
    last = None
    stat = stat if stat is not None else {}
    for i in range(tries):
        if stat.get('blocked') or (deadline and time.time() > deadline):
            raise RuntimeError('ordinals.com: ' + ('лимит запросов' if stat.get('blocked') else 'не успел за отведённое время'))
        if pace:
            pace.wait()
        stat['req'] = stat.get('req', 0) + 1
        try:
            req = urllib.request.Request(f'https://ordinals.com/address/{a}', headers={'User-Agent': UA, 'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read().decode('utf-8'))
            rb = d.get('runes_balances') if isinstance(d, dict) else None
            if rb is None:
                raise ValueError('нет runes_balances')
            for row in rb:
                if isinstance(row, (list, tuple)) and len(row) >= 2 and row[0] == RUNE:
                    return str(row[1])
            return '0'
        except urllib.error.HTTPError as e:
            last = f'HTTP {e.code}'
            if e.code == 406:                       # попали на сервер без JSON — следующий запрос уйдёт на другой
                stat['n406'] = stat.get('n406', 0) + 1
                continue
            if e.code in (403, 429, 503):           # просят притормозить: общая пауза; повторяется — уходим к запасному источнику
                stat['limit'] = stat.get('limit', 0) + 1
                if stat['limit'] >= 10:
                    stat['blocked'] = True
                if pace:
                    pace.hold(8)
                continue
            time.sleep(1)
        except (urllib.error.URLError, ValueError, TimeoutError, OSError) as e:
            last = str(e)[:80]
            time.sleep(1)
    raise RuntimeError(f'ordinals.com: {last}')


def xverse_balance(a, pace=None, deadline=None, tries=2):
    """баланс DOG адреса по данным кошелька Xverse (второй независимый индекс рун)"""
    from decimal import Decimal
    last = None
    for i in range(tries):
        if deadline and time.time() > deadline:
            raise RuntimeError('xverse: не успел за отведённое время')
        if pace:
            pace.wait()
        try:
            req = urllib.request.Request(f'https://api-3.xverse.app/v2/address/{a}/rune-balance?includeUnconfirmed=false',
                                         headers={'User-Agent': UA, 'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=20) as r:
                d = json.loads(r.read().decode('utf-8'))
            if not isinstance(d, list):
                raise ValueError('ответ не список')
            for row in d:
                if isinstance(row, dict) and (row.get('id') == RUNE_ID or row.get('runeName') == RUNE):
                    return format(Decimal(int(row['amount'])).scaleb(-int(row.get('divisibility', 5))), 'f')
            return '0'
        except urllib.error.HTTPError as e:
            last = f'HTTP {e.code}'
            if e.code in (403, 429) and pace:
                pace.hold(6)
        except (urllib.error.URLError, ValueError, TypeError, KeyError, TimeoutError, OSError) as e:
            last = str(e)[:80]
            time.sleep(1)
    raise RuntimeError(f'xverse: {last}')


def f_ordbal():
    import concurrent.futures as cf
    raw = RAWDIR[0]

    def text(name):
        try:
            t = open(os.path.join(raw, name + '.txt'), encoding='utf-8').read()
            return '' if t.startswith('UNAVAILABLE') else t
        except OSError:
            return ''
    cand = {}

    def add(a, why, b=None):
        if isinstance(a, str) and (a.startswith('bc1') or a[:1] in '13') and 25 <= len(a) <= 90:
            c = cand.setdefault(a, {'why': set(), 'b': None})
            c['why'].add(why)
            if b is not None:
                c['b'] = max(c['b'] or 0, b)
    for k in range(1, 5):
        for ln in text(f'holders_{k}').splitlines():
            p = ln.split(';')
            if len(p) >= 3 and p[0].isdigit():
                add(p[1], 'dd', float(p[2]) if p[2] not in ('', 'null') else None)
    for k in (5, 6):                      # места 101–150 DOG DATA: соседи по границе топ-100 (необязательно)
        try:
            d = get([h + f'/api/dog-rune/holders?page={k}&limit=25' for h in DD], tries=2)
            for h in first_list(d, 'address'):
                add(h.get('address'), 'dd150', float(h['total_dog']) if h.get('total_dog') is not None else None)
        except Exception as e:
            print(f'ORDBAL кандидаты, страница {k}: {str(e)[:120]}')
    for ln in text('stats').splitlines():
        p = ln.split(';')
        if len(p) >= 3 and p[0].isdigit():
            add(p[1], 'top10', float(p[2]) if p[2] not in ('', 'null') else None)
    for ln in text('whales').splitlines():
        p = ln.split(';')
        if len(p) >= 4 and p[0][:2] == '20':
            add(p[2], 'whale')
            add(p[3], 'whale')
    prev = os.path.join(os.path.dirname(os.path.abspath(raw)), 'prev', 'live', 'current.json')
    try:
        for x in json.load(open(prev, encoding='utf-8')).get('top100') or []:
            add(x.get('a'), 'prev', float(x['b']) * 1e6 if x.get('b') is not None else None)
    except (OSError, ValueError):
        pass
    if len(cand) < 100:
        raise RuntimeError(f'мало кандидатов: {len(cand)}')
    t0 = time.time()
    res, src, err = {}, {}, {}
    # повторный запрос в той же сводке: уже полученные несколько минут назад балансы заново не спрашиваем
    old = text('ordbal')
    if old:
        import re
        m = re.search(r'ts=(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)', old)
        try:
            age = time.time() - __import__('calendar').timegm(time.strptime(m.group(1), '%Y-%m-%dT%H:%M:%SZ')) if m else 1e9
        except ValueError:
            age = 1e9
        if 0 <= age < REUSE_MIN * 60:
            for ln in old.splitlines():
                p = ln.split(';')
                if len(p) >= 2 and p[0] in cand:
                    try:
                        float(p[1])
                    except ValueError:
                        continue
                    res[p[0]], src[p[0]] = p[1], (p[3] if len(p) > 3 and p[3] in ('ord', 'xv') else 'ord')
    reused = len(res)
    todo = [a for a in cand if a not in res]
    # сначала те, кто важнее для топ-100 (по последнему известному балансу), — если время выйдет, не ответят только мелкие
    todo.sort(key=lambda a: -(cand[a]['b'] or 0))
    stat = {}
    pace, dl = Pace(ORD_GAP), time.time() + ORD_BUDGET

    def one(a):
        return a, ord_balance(a, pace, dl, stat)
    miss = {}
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        futs = {ex.submit(one, a): a for a in todo}
        for f in cf.as_completed(futs):
            try:
                a, b = f.result()
                res[a], src[a] = b, 'ord'
            except Exception as e:
                miss[futs[f]] = str(e)[:120]
    t_ord = time.time() - t0
    # кто не ответил — спрашиваем у второго источника
    xp, xdl = Pace(XV_GAP), time.time() + XV_BUDGET
    for a in sorted(miss, key=lambda a: -(cand[a]['b'] or 0)):
        try:
            res[a], src[a] = xverse_balance(a, xp, xdl), 'xv'
        except Exception as e:
            err[a] = f'{miss[a]}; {str(e)[:100]}'
    # сверка со вторым источником: 6 адресов с разных мест списка, расхождение до 0,5% (или 1 млн DOG) — норма
    ranked = sorted((a for a in res if src[a] == 'ord' and float(res[a]) > 0), key=lambda a: -float(res[a]))
    xc_ok, xc_bad, xc_err = 0, [], 0
    for a in ranked[10:100:15][:6]:
        try:
            xb, ob = float(xverse_balance(a, xp, time.time() + 25, tries=1)), float(res[a])
            if abs(xb - ob) <= max(1e6, ob * 0.005):
                xc_ok += 1
            else:
                xc_bad.append(f'{a[:10]}… {ob / 1e6:.2f}M/{xb / 1e6:.2f}M')
        except Exception:
            xc_err += 1
    ts = dt_iso(time.time())
    n_xv = sum(1 for v in src.values() if v == 'xv')
    L = [f'ts={ts}; asked={len(cand)}; ok={len(res)}; failed={len(err)}; xverse={n_xv}; '
         f'xcheck={xc_ok}/{xc_ok + len(xc_bad)}; xcheck_err={xc_err}; reused={reused}; requests={stat.get("req", 0)}; '
         f'no_json={stat.get("n406", 0)}; limited={stat.get("limit", 0)}; secs_ord={t_ord:.0f}; secs={time.time() - t0:.0f}']
    if xc_bad:
        L.append('XBAD;' + ' | '.join(xc_bad))
    L += [f'{a};{b};{",".join(sorted(cand[a]["why"]))};{src[a]}' for a, b in sorted(res.items(), key=lambda kv: -float(kv[1]))]
    L += [f'ERR;{a};{cand.get(a, {}).get("b") or 0}' for a in err]
    return {'asked': len(cand), 'ok': len(res), 'xverse': n_xv, 'failed': err, 'stat': stat, 'xcheck': [xc_ok, xc_bad, xc_err]}, '\n'.join(L)


def dt_iso(t):
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(t))


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
    'dd_age': f_age, 'dd_airdrop': f_airdrop, 'dd_chains': f_chains, 'dd_tiers': f_tiers,
    'ordbal': f_ordbal,           # после holders_*, stats и whales: берёт из них кандидатов
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
    RAWDIR[0] = raw
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
