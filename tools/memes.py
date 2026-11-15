#!/usr/bin/env python3
"""DOG Монитор — DOG и крупнейшие мем-монеты разных сетей: дневные цены закрытия для графика сравнения на сайте.

    python3 tools/memes.py <папка сайта>

Пишет data/memes.json. Для каждой монеты берём дневные свечи (UTC) сразу с трёх бирж — Gate, MEXC и Kraken — и
сверяем закрытия между собой: в файл идёт ряд с той биржи, чьи цены подтверждает другая биржа (расхождение
закрытий в медиане до 3%). Так в график не попадёт чужая монета с тем же тикером. Пропуски дней дополняются со
второй биржи. DOG — из data/prices.json (Kraken, раньше Gate): та же цена, что на всём сайте.
Капитализация и место в рейтинге — CoinGecko, одним запросом; заодно сверяем последнюю цену и с ним.
"""
import datetime as dt
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch import get  # noqa: E402  (тот же HTTP-клиент с повторами, что и для сводки)

NOW = dt.datetime.now(dt.timezone.utc)
DAYS = 400                 # сколько последних дней храним: год на графике и запас
TOL = 0.03                 # допустимое расхождение закрытий двух бирж (медиана по общим дням)
CG_TOL = 0.08              # допустимое расхождение последней цены с CoinGecko

# id, тикер, название, сеть, пара Gate, пара MEXC, пара Kraken, id CoinGecko
COINS = [
    ('dog', 'DOG', 'DOG•GO•TO•THE•MOON', 'Bitcoin', 'DOG_USDT', 'DOGUSDT', None, 'dog-go-to-the-moon-rune'),
    ('doge', 'DOGE', 'Dogecoin', 'Dogecoin', 'DOGE_USDT', 'DOGEUSDT', 'XDGUSD', 'dogecoin'),
    ('shib', 'SHIB', 'Shiba Inu', 'Ethereum', 'SHIB_USDT', 'SHIBUSDT', 'SHIBUSD', 'shiba-inu'),
    ('pepe', 'PEPE', 'Pepe', 'Ethereum', 'PEPE_USDT', 'PEPEUSDT', 'PEPEUSD', 'pepe'),
    ('pengu', 'PENGU', 'Pudgy Penguins', 'Solana', 'PENGU_USDT', 'PENGUUSDT', 'PENGUUSD', 'pudgy-penguins'),
    ('spx', 'SPX', 'SPX6900', 'Ethereum', 'SPX_USDT', 'SPXUSDT', 'SPXUSD', 'spx6900'),
    ('trump', 'TRUMP', 'Official Trump', 'Solana', 'TRUMP_USDT', 'TRUMPUSDT', 'TRUMPUSD', 'official-trump'),
    ('bonk', 'BONK', 'Bonk', 'Solana', 'BONK_USDT', 'BONKUSDT', 'BONKUSD', 'bonk'),
    ('floki', 'FLOKI', 'Floki', 'Ethereum', 'FLOKI_USDT', 'FLOKIUSDT', 'FLOKIUSD', 'floki'),
    ('wif', 'WIF', 'dogwifhat', 'Solana', 'WIF_USDT', 'WIFUSDT', 'WIFUSD', 'dogwifcoin'),
    ('fartcoin', 'FARTCOIN', 'Fartcoin', 'Solana', 'FARTCOIN_USDT', 'FARTCOINUSDT', 'FARTCOINUSD', 'fartcoin'),
    ('brett', 'BRETT', 'Brett', 'Base', 'BRETT_USDT', None, None, 'based-brett'),     # на MEXC и Kraken пары нет
]


def jload(p, default=None):
    try:
        return json.load(open(p, encoding='utf-8'))
    except Exception:
        return default


def jdump(o, p):
    tmp = p + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(o, f, ensure_ascii=False, separators=(',', ':'))
    os.replace(tmp, p)


def day(ts):
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime('%Y-%m-%d')


def sig(x, k=5):
    return float(f'{x:.{k}g}')


TODAY = NOW.strftime('%Y-%m-%d')


def gate(pair):
    d = get(f'https://api.gateio.ws/api/v4/spot/candlesticks?currency_pair={pair}&interval=1d&limit=1000', tries=2)
    if not isinstance(d, list):
        raise RuntimeError(str(d)[:120])
    return {day(int(float(r[0]))): float(r[2]) for r in d if float(r[2]) > 0 and day(int(float(r[0]))) <= TODAY}


def mexc(sym):
    d = get(f'https://api.mexc.com/api/v3/klines?symbol={sym}&interval=1d&limit=1000', tries=2)
    if not isinstance(d, list):
        raise RuntimeError(str(d)[:120])
    return {day(int(r[0]) // 1000): float(r[4]) for r in d if float(r[4]) > 0 and day(int(r[0]) // 1000) <= TODAY}


def kraken(pair):
    d = get(f'https://api.kraken.com/0/public/OHLC?pair={pair}&interval=1440', tries=2)
    if d.get('error'):
        raise RuntimeError(str(d['error'])[:120])
    res = d.get('result') or {}
    key = next((k for k in res if k != 'last'), None)
    return {day(int(r[0])): float(r[4]) for r in res.get(key) or [] if float(r[4]) > 0 and day(int(r[0])) <= TODAY}


def dev(a, b, last=90):
    """медиана относительного расхождения закрытий по общим дням (последние last дней) и число таких дней"""
    common = sorted(set(a) & set(b))[-last:]
    if len(common) < 10:
        return None, len(common)
    xs = sorted(abs(a[t] / b[t] - 1) for t in common)
    return xs[len(xs) // 2], len(common)


def main():
    site = sys.argv[1] if len(sys.argv) > 1 else '.'
    data = os.path.join(site, 'data')
    path = os.path.join(data, 'memes.json')
    old = jload(path, {}) or {}
    days = [(NOW - dt.timedelta(days=k)).strftime('%Y-%m-%d') for k in range(DAYS - 1, -1, -1)]
    dogpx = {t: v[3] for t, v in ((jload(os.path.join(data, 'prices.json'), {}) or {}).get('d') or {}).items() if v and v[3] > 0}
    old_c = {c.get('id'): c for c in old.get('coins') or []}

    # CoinGecko: капитализация, место и цена сейчас — одним запросом (необязательно)
    cg = {}
    try:
        ids = ','.join(c[7] for c in COINS)
        rows = get(f'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids={ids}&per_page=50&page=1', tries=2)
        cg = {x['id']: x for x in rows or [] if isinstance(x, dict) and x.get('id')}
        print(f'MEMES CoinGecko: {len(cg)} из {len(COINS)}')
    except Exception as e:
        print('MEMES CoinGecko ERR', str(e)[:160])

    out, problems = [], []
    for cid, sym, name, chain, gp, mp, kp, cgid in COINS:
        src = {}
        for nm, fn, arg in (('Gate', gate, gp), ('MEXC', mexc, mp), ('Kraken', kraken, kp)):
            if not arg:
                continue
            try:
                s = fn(arg)
                if len(s) >= 10:
                    src[nm] = s
                else:
                    print(f'MEMES {sym} {nm}: мало дней ({len(s)})')
            except Exception as e:
                print(f'MEMES {sym} {nm} ERR', str(e)[:120])
            time.sleep(0.25)
        if cid == 'dog' and dogpx:
            src = {'Kraken': dogpx, **{k: v for k, v in src.items() if k != 'Kraken'}}
            order = ['Kraken', 'Gate', 'MEXC']
        else:
            order = ['Gate', 'MEXC', 'Kraken']
        names = [k for k in order if k in src]
        if not names:
            problems.append(f'{sym}: ни одна биржа не ответила')
            if cid in old_c:
                out.append(old_c[cid])          # оставляем прошлый ряд — график не теряет монету из-за одного сбоя
            continue
        # сверка: у основной биржи должна быть хотя бы одна согласная; если основная расходится с двумя
        # другими, а они между собой согласны, — это другая монета с тем же тикером, берём согласных
        pair = {}
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                pair[(a, b)] = pair[(b, a)] = dev(src[a], src[b])
        agree = lambda a: [b for b in names if b != a and pair[(a, b)][0] is not None and pair[(a, b)][0] <= TOL]
        main_src = next((a for a in names if agree(a)), names[0])
        checks = [[b, round(pair[(main_src, b)][0] * 100, 2), pair[(main_src, b)][1]] for b in names if b != main_src and pair[(main_src, b)][0] is not None]
        ok2 = bool(agree(main_src))
        if not ok2 and len(names) > 1:
            problems.append(f'{sym}: биржи расходятся ' + ', '.join(f'{b} {d}%' for b, d, _ in checks))
        ser = dict(src[main_src])
        # пропуски — со согласной биржи
        for b in agree(main_src):
            for t, v in src[b].items():
                ser.setdefault(t, v)
        c = [sig(ser[t]) if t in ser else None for t in days]
        first = next((days[i] for i, v in enumerate(c) if v is not None), None)
        x = cg.get(cgid) or {}
        last = next((v for v in reversed(c) if v is not None), None)
        cgdev = abs(last / x['current_price'] - 1) if last and x.get('current_price') else None
        if cgdev is not None and cgdev > CG_TOL:
            problems.append(f'{sym}: цена {last} не сходится с CoinGecko {x["current_price"]}')
        if cgdev is not None:
            checks.append(['CoinGecko', round(cgdev * 100, 2), 1])     # цена сейчас против CoinGecko (одна точка)
            ok2 = ok2 or (len(names) == 1 and cgdev <= CG_TOL)         # одна биржа, но цену подтверждает CoinGecko
        row = {'id': cid, 'sym': sym, 'name': name, 'chain': chain, 'src': main_src, 'chk': checks, 'ok': ok2, 'c': c, 'first': first}
        if x.get('market_cap'):
            row['mc'] = round(float(x['market_cap']))
        if x.get('market_cap_rank'):
            row['rank'] = int(x['market_cap_rank'])
        if cgdev is not None:
            row['cg'] = round(cgdev * 100, 2)
        out.append(row)
        print(f'MEMES {sym}: {main_src}, {sum(1 for v in c if v is not None)} дней с {first}; сверка '
              + (', '.join(f'{b} {d}% ({n} дн.)' for b, d, n in checks) or 'нет второй биржи')
              + (f'; CoinGecko {cgdev * 100:.2f}%' if cgdev is not None else ''))
    if sum(1 for r in out if r['id'] != 'dog') < 5 or not any(r['id'] == 'dog' for r in out):
        print('MEMES: слишком мало монет — файл не меняем')
        return 1
    jdump({'v': 1, 'updated': NOW.strftime('%Y-%m-%dT%H:%M:%SZ'), 'days': days, 'coins': out, 'problems': problems,
           'src': 'дневные свечи Gate, MEXC и Kraken (UTC), закрытия сверены между биржами; DOG — Kraken, раньше Gate; капитализация — CoinGecko'},
          path)
    print(f'MEMES: {len(out)} монет, {len(days)} дней' + (f'; замечания: {"; ".join(problems)}' if problems else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
