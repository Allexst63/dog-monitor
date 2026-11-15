#!/usr/bin/env python3
"""DOG Монитор — кошельки от 10 млн DOG: полный список, кто пришёл и кто ушёл, сверка балансов с блокчейном.

    python3 tools/whales.py <папка сайта>

Список — DOG DATA (/api/dog-rune/holders: по 25 кошельков на страницу, по убыванию баланса): берём все кошельки от
10 млн DOG. Это кошельки (адреса), а не «части монет» (UTXO): у одного кошелька частей может быть тысячи.
Тип кошелька — метки топ-100 сайта, иначе профиль адреса DOG DATA (метка владельца; без метки: до 500 операций —
частный холдер, больше — не определён). Узнанный тип храним и перепроверяем раз в месяц.
Сравниваем с прошлым запуском: кто впервые набрал 10 млн, кто опустился ниже, сколько DOG прибавили или убавили
остальные. Несколько балансов сверяем с блокчейном (ordinals.com, запасной — Xverse).

Пишет data/whales.json (что показывает сайт: итоги, история, события за 35 дней, сверка)
и data/whales_map.json (весь список с типами — для сравнения в следующий раз; сайт его не загружает).
"""
import datetime as dt
import glob
import json
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch import DD, Pace, get, ord_balance, xverse_balance  # noqa: E402

NOW = dt.datetime.now(dt.timezone.utc)
THR = 10e6                 # порог: 10 млн DOG
SUPPLY = 100e9
MAX_PAGES = 120            # страховка: 3000 кошельков
ENT_BUDGET = float(os.environ.get('WHALES_ENT_BUDGET') or 150)   # секунд на профили новых адресов DOG DATA за запуск (остальные — в следующий раз)
ENT_TTL = 30               # дней до перепроверки типа кошелька
CHK_N = 12                 # сколько балансов сверять с блокчейном
EV_DAYS = 35               # сколько дней хранить события «пришёл / ушёл»
HIST_MAX = 3000
SERVICE = ('exchange', 'custody', 'marketplace', 'mm', 'distributor', 'treasury')
KNOWN_EXCHANGES = {'Kraken', 'Gate', 'MEXC', 'Bitget', 'CoinEx', 'OKX', 'Binance', 'Bybit', 'BingX', 'HTX', 'KuCoin',
                   'CoinW', 'DigiFinex', 'BigONE', 'Bitrue', 'Coinbase', 'Bitfinex', 'Crypto.com'}


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


def iso(t):
    return t.strftime('%Y-%m-%dT%H:%M:%SZ')


def iso_of(x):
    """время из ответа DOG DATA («2026-11-15T14:29:00.998Z», «…+00:00») → «2026-11-15T14:29:00Z»"""
    try:
        t = dt.datetime.fromisoformat(str(x).replace('Z', '+00:00'))
        return iso(t.astimezone(dt.timezone.utc))
    except (TypeError, ValueError):
        return None


def backfill(data):
    """история до первого запуска: число кошельков от 10 млн и их монеты из архива сводок (data/snapshots), по времени
    списка DOG DATA, на котором они посчитаны"""
    seen = {}
    for f in glob.glob(os.path.join(data, 'snapshots', '*.json')):
        t = (((jload(f, {}) or {}).get('health') or {}).get('tiers')) or {}
        k, n10 = iso_of(t.get('asof')), (t.get('n') or {}).get('10000000')
        if k and n10:
            d10 = (t.get('dog') or {}).get('10000000')
            if k not in seen or (seen[k][2] is None and d10 is not None):
                seen[k] = [k, int(n10), d10, None, None]
    return [seen[k] for k in sorted(seen)]


def holders():
    """все кошельки от порога: [(адрес, баланс DOG, частей UTXO)], время обновления списка, всего холдеров"""
    out, asof, total = [], None, None
    for k in range(1, MAX_PAGES + 1):
        d = get([h + f'/api/dog-rune/holders?page={k}&limit=25' for h in DD], tries=3)
        rows = d.get('holders') or d.get('data') or []
        if k == 1:
            asof, total = d.get('last_updated'), (d.get('pagination') or {}).get('total')
        if not rows:
            break
        for r in rows:
            b = float(r.get('total_dog') or 0)
            if b >= THR:
                out.append((r['address'], b, int(r.get('utxo_count') or 0)))
        if float(rows[-1].get('total_dog') or 0) < THR:
            break
        time.sleep(0.15)
    else:
        raise RuntimeError('список не закончился — страховка по числу страниц')
    return out, asof, total


def entity_kind(a):
    """тип кошелька по профилю адреса DOG DATA (то же правило, что в tools/dogmon.py classify)"""
    d = get([h + f'/api/address/bitcoin/{a}?limit=1' for h in DD], tries=2)
    e, st = d.get('entity') or {}, d.get('stats') or {}
    name, kind = e.get('name'), str(e.get('kind') or '').lower()
    if name:
        k = {'exchange': 'exchange', 'treasury': 'treasury', 'distributor': 'distributor', 'desk': 'mm', 'market_maker': 'mm',
             'marketplace': 'marketplace', 'custody': 'custody'}.get(kind)
        return k or ('exchange' if name in KNOWN_EXCHANGES else 'unknown'), name
    tx = d.get('tx_count', st.get('tx_count'))
    try:
        tx = float(tx)
    except (TypeError, ValueError):
        tx = None
    return ('unknown' if tx is not None and tx > 500 else 'private'), None


def main():
    site = sys.argv[1] if len(sys.argv) > 1 else '.'
    data = os.path.join(site, 'data')
    p_out, p_map = os.path.join(data, 'whales.json'), os.path.join(data, 'whales_map.json')
    old, mp = jload(p_out, {}) or {}, jload(p_map, {}) or {}
    prev = mp.get('w') or {}
    live = jload(os.path.join(data, 'live.json'), {}) or {}
    top_k = {x['a']: x.get('k') or 'unknown' for x in live.get('top100') or [] if x.get('a')}
    top_n = {x['a']: x.get('n') for x in live.get('top100') or [] if x.get('a')}

    rows, asof, total = holders()
    at = iso_of(asof) or iso(NOW)          # время списка DOG DATA: им помечаем историю и события
    if len(rows) < 100:
        print(f'WHALES: подозрительно мало кошельков ({len(rows)}) — файлы не меняем')
        return 1
    tiers_n = ((((live.get('health') or {}).get('tiers') or {}).get('n')) or {}).get('10000000')
    print(f'WHALES: {len(rows)} кошельков от 10 млн (в сводке {tiers_n}), список DOG DATA на {asof}, всего холдеров {total}')

    # типы кошельков: метки топ-100 сайта, затем сохранённые, затем профиль DOG DATA (с бюджетом времени)
    today = NOW.strftime('%Y-%m-%d')
    kinds, names, kdate, t0, asked, fails = {}, {}, {}, time.time(), 0, 0
    for a, b, u in rows:
        if a in top_k:
            kinds[a], names[a], kdate[a] = top_k[a], top_n.get(a), today
            continue
        c = prev.get(a)
        if c and len(c) >= 3 and c[1] and c[2] and (NOW - dt.datetime.strptime(c[2], '%Y-%m-%d').replace(tzinfo=dt.timezone.utc)).days < ENT_TTL:
            kinds[a], names[a], kdate[a] = c[1], (c[3] if len(c) > 3 else None), c[2]
    todo = [a for a, b, u in rows if a not in kinds]
    for a in todo:
        if time.time() - t0 > ENT_BUDGET:
            break
        try:
            kinds[a], names[a] = entity_kind(a)
            kdate[a] = today
            asked += 1
        except Exception as e:
            fails += 1
            if fails <= 3:
                print(f'WHALES профиль {a[:12]}… ERR', str(e)[:100])
        time.sleep(0.3)
    left = sum(1 for a, b, u in rows if a not in kinds)
    print(f'WHALES типы: спросили {asked}, ошибок {fails}, ещё не известны {left}')

    # сравнение с прошлым запуском (тот же порог): кто пришёл, кто ушёл, что у остальных
    cur = {a: b for a, b, u in rows}
    pb = {a: float(c[0]) * 1e6 for a, c in prev.items() if c}
    ev = [e for e in old.get('ev') or [] if e[0] >= iso(NOW - dt.timedelta(days=EV_DAYS))]
    run = None
    same = bool(mp.get('asof')) and iso_of(mp.get('asof')) == at      # DOG DATA ещё не обновил список — сравнивать нечего
    if pb and mp.get('ts') and not same:
        new = [a for a in cur if a not in pb]
        gone = [a for a in pb if a not in cur]
        stay = [a for a in cur if a in pb]
        up = sum(1 for a in stay if cur[a] - pb[a] > max(0.1e6, pb[a] * 0.001))
        down = sum(1 for a in stay if pb[a] - cur[a] > max(0.1e6, pb[a] * 0.001))
        net = sum(cur[a] - pb[a] for a in stay)
        ts = at
        ev += [[ts, '+', a, round(cur[a] / 1e6, 2), kinds.get(a) or ''] for a in new]
        ev += [[ts, '-', a, round(pb[a] / 1e6, 2), (prev.get(a) or [None, ''])[1] or ''] for a in gone]
        run = {'prev': mp.get('ts'), 'in': len(new), 'out': len(gone), 'up': up, 'down': down, 'net': round(net / 1e6, 2),
               'inDog': round(sum(cur[a] for a in new) / 1e6, 2), 'outDog': round(sum(pb[a] for a in gone) / 1e6, 2)}
        print(f"WHALES с {mp.get('ts')}: пришли {len(new)}, ушли {len(gone)}, прибавили {up}, убавили {down}, у оставшихся {net / 1e6:+.1f} млн")

    # сверка с блокчейном: кошельки у самого порога и случайные из списка
    rnd = random.Random(today)
    near = sorted(rows, key=lambda r: abs(r[1] - THR))[:4]
    rest = [r for r in rows if r not in near]
    sample = near + rnd.sample(rest, min(CHK_N - len(near), len(rest)))
    pace, stat, dl = Pace(0.4), {}, time.time() + 90
    xp = Pace(0.5)
    chk = {'n': 0, 'ok': 0, 'bad': [], 'src': {}}
    for a, b, u in sample:
        try:
            try:
                v, s = float(ord_balance(a, pace, dl, stat)), 'ordinals.com'
            except Exception:
                v, s = float(xverse_balance(a, xp, time.time() + 20)), 'Xverse'
        except Exception:
            continue
        chk['n'] += 1
        chk['src'][s] = chk['src'].get(s, 0) + 1
        if abs(v - b) <= max(0.05e6, b * 0.005):
            chk['ok'] += 1
        else:
            chk['bad'].append([a, round(b / 1e6, 3), round(v / 1e6, 3)])
    chk['ts'] = iso(NOW)
    print(f"WHALES сверка: {chk['ok']} из {chk['n']} совпали ({chk['src']})" + (f"; расходятся: {chk['bad']}" if chk['bad'] else ''))

    # итоги по типам
    by = {}
    for a, b, u in rows:
        k = kinds.get(a) or 'unknown'
        g = by.setdefault(k, [0, 0.0])
        g[0] += 1
        g[1] += b / 1e6
    svc = [sum(by[k][0] for k in by if k in SERVICE), sum(by[k][1] for k in by if k in SERVICE)]
    dog = sum(b for a, b, u in rows) / 1e6
    hist = [h for h in old.get('hist') or [] if isinstance(h, list) and len(h) >= 5] or backfill(data)
    hist = [h for h in hist if h[0] < at] + [[at, len(rows), round(dog, 1), svc[0], round(svc[1], 1)]]
    hist = hist[-HIST_MAX:]
    ev_from = old.get('evFrom') or (iso_of(mp.get('asof')) or mp.get('ts') if run is not None else None)
    big = sorted(rows, key=lambda r: -r[1])
    out = {
        'v': 1, 'updated': iso(NOW), 'asof': asof, 'holders': total, 'thr': THR,
        'n': len(rows), 'dog': round(dog, 1), 'pct': round(dog * 1e6 / SUPPLY * 100, 2),
        'svc': [svc[0], round(svc[1], 1)], 'kinds': {k: [v[0], round(v[1], 1)] for k, v in sorted(by.items())},
        'known': len(rows) - left, 'tiersN': tiers_n,
        'min': round(big[-1][1] / 1e6, 2), 'med': round(big[len(big) // 2][1] / 1e6, 2),
        'utxo': sum(u for a, b, u in rows),
        'run': run, 'chk': chk, 'hist': hist, 'ev': ev[-400:], 'evFrom': ev_from,
        'src': 'DOG DATA — список холдеров (все кошельки от 10 млн DOG), профили адресов; сверка балансов — ordinals.com, запасной — Xverse',
    }
    jdump(out, p_out)
    jdump({'v': 1, 'ts': iso(NOW), 'asof': asof,
           'w': {a: [round(b / 1e6, 3), kinds.get(a) or '', kdate.get(a), names.get(a)] for a, b, u in rows}}, p_map)
    print(f"WHALES: {len(rows)} кошельков, {dog / 1e3:.2f} млрд DOG ({out['pct']}%), биржи и сервисы {svc[0]} / {svc[1] / 1e3:.2f} млрд")
    return 0


if __name__ == '__main__':
    sys.exit(main())
