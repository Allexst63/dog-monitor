#!/usr/bin/env python3
"""DOG Монитор — «страх и жадность»: два индекса всего рынка и свой индекс для DOG.

    python3 tools/mood.py <site_dir>            посчитать и записать data/fng.json
    python3 tools/mood.py <site_dir> --offline  то же без сети (рынок, CMC и сектор — из прошлого файла)

Рынок — два готовых индекса (0 — крайний страх, 100 — крайняя жадность), берём как есть:
  alternative.me — Crypto Fear & Greed Index, обновляется у источника раз в сутки (00:00 UTC);
  CoinMarketCap  — CMC Crypto Fear and Greed Index, обновляется в течение дня (его открытый ответ
                   data-api без CORS, поэтому берём его здесь, а не в браузере).

DOG — свой индекс (версия 4 с 15.11.2026). Он про DOG, но DOG — мем-монета на биткоине и ходит вместе с рынком,
поэтому 45% — рынок и биткоин, 55% — сам DOG. Каждая часть — число от 0 (страх) до 100 (жадность):
  mkt   30%  настроение всего крипторынка: среднее индексов alternative.me и CoinMarketCap;
  btc   15%  тренд биткоина: цена BTC против средних за 30 и 90 дней и просадка от максимума за 90 дней;
  mom   25%  импульс DOG: цена против своих средних за 30 и 90 дней;
  vol   20%  падения и просадка DOG: насколько резкие падения за 30 дней против обычных (считаем только дни
             снижения — рост на 30% за день это не страх) и как далеко цена от максимума за 90 дней;
  rel   10%  DOG против биткоина: курс DOG/BTC за 30 дней.
Все части считаются по дневным ценам закрытия, поэтому каждый день истории посчитан одинаково и его можно
проверить. Сегодняшний день — по текущей (ещё не закрытой) дневной свече и текущим индексам рынка; когда день
закрывается (00:00 UTC), следующий запуск пересчитывает его по цене закрытия — и дальше он не меняется.
Холдеры и место среди мем-монет в индекс не входят (их истории за прошлые годы нет) — они в разборе «для справки».
Если части нет (источник не ответил), её вес делится между остальными.
Стакана в индексе больше нет (в версии 1 был с весом 10%): доля заявок на покупку рядом с ценой растёт ПОСЛЕ
падений — цена опускается к крупным заявкам на покупку, и они попадают в окно ±10% (за месяц сводок корреляция
с изменением цены за 3 дня −0,59), а на будущее движение цены она не указывает (корреляция около нуля).
Проверка на истории с сентября 2024: корреляция с индексами рынка 0,74 (alternative.me) и 0,83 (CoinMarketCap),
у версии 1 было 0,47 и 0,59; у рекорда цены 11.12.2024 (капитализация ≈ $1 млрд) — 83–87, крайняя жадность;
у дна в марте 2025 — 13, крайний страх. Историю до запуска версии считаем по частям, для которых есть прошлые данные
(mkt, btc, mom, vol и DOG/BTC). Это описание настроения, а не совет и не прогноз.
"""
import datetime as dt
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fetch import get  # noqa: E402

NOW = dt.datetime.now(dt.timezone.utc)
TODAY = NOW.strftime('%Y-%m-%d')
CG_ID = 'dog-go-to-the-moon-rune'
WEIGHTS = (('mkt', 30), ('btc', 15), ('mom', 25), ('vol', 20), ('rel', 10))
VER = 4
KEEP = 1100            # дней истории в файле: у DOG — вся история индекса (с 23.08.2024)
FETCH_DAYS = 1100
CURVE_N, CURVE_STEP = 48, 0.0125   # кривая «цена → индекс на сегодня»: 97 точек, шаг 1,25%
TURN = 40              # разворот индекса DOG — смена направления не меньше чем на 40 пунктов


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


def fetch(url, fixture):
    """ответ источника; MOOD_FIXTURES=<папка> — взять сохранённый ответ из файла (проверка без сети)"""
    fx = os.environ.get('MOOD_FIXTURES')
    if fx:
        return json.load(open(os.path.join(fx, fixture), encoding='utf-8'))
    return get(url, tries=2)


def clamp(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, x))


def r1(x):
    return None if x is None else round(x, 1)


def mean(a):
    a = [x for x in a if x is not None]
    return sum(a) / len(a) if a else None


def stdev(a):
    m = sum(a) / len(a)
    return math.sqrt(sum((x - m) ** 2 for x in a) / (len(a) - 1))


def day_of(ts):
    return dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).strftime('%Y-%m-%d')


def shift(day, n):
    return (dt.datetime.strptime(day, '%Y-%m-%d') - dt.timedelta(days=n)).strftime('%Y-%m-%d')


def prev_of(hist):
    """значения вчера, неделю и месяц назад от последнего дня ряда [[день, v], …]"""
    h = dict(hist or [])
    if not h:
        return {}
    last = max(h)
    return {k: h.get(shift(last, n)) for k, n in (('d1', 1), ('d7', 7), ('d30', 30))}


# ---------- рынок: alternative.me ----------
def market(old, offline):
    out = dict((old or {}).get('market') or {})
    hist = {d: v for d, v in out.get('hist') or []}
    if not offline:
        try:
            d = fetch(f'https://api.alternative.me/fng/?limit={FETCH_DAYS}&format=json', 'alt.json')
            rows = d.get('data') or []
            for r in rows:
                hist[day_of(r['timestamp'])] = int(r['value'])
            if rows:
                out.update({'v': int(rows[0]['value']), 'cls': rows[0].get('value_classification'), 'ts': int(rows[0]['timestamp']),
                            'src': 'alternative.me', 'got': NOW.strftime('%Y-%m-%dT%H:%M:%SZ')})
            print(f"MOOD alternative.me: {out.get('v')} ({len(rows)} дней)")
        except Exception as e:
            print('MOOD alternative.me ERR', e)
    days = sorted(hist)[-KEEP:]
    out['hist'] = [[d, hist[d]] for d in days]
    out['prev'] = prev_of(out['hist'])
    return out


# ---------- рынок: CoinMarketCap ----------
def cmc(old, offline):
    out = dict((old or {}).get('cmc') or {})
    hist = {d: v for d, v in out.get('hist') or []}
    if not offline:
        try:
            now = int(NOW.timestamp())
            d = fetch(f'https://api.coinmarketcap.com/data-api/v3/fear-greed/chart?start={now - FETCH_DAYS * 86400}&end={now}', 'cmc_chart.json')
            data = d.get('data') or {}
            rows = data.get('dataList') or []
            for r in rows:                       # последняя точка — текущее значение (время внутри дня)
                hist[day_of(r['timestamp'])] = int(r['score'])
            hv = data.get('historicalValues') or {}
            cur = hv.get('now') or (rows[-1] if rows else None)
            if cur:
                sc = lambda x: int(x['score']) if x and x.get('score') is not None else None  # noqa: E731
                out.update({'v': int(cur['score']), 'cls': cur.get('name'), 'ts': int(cur['timestamp']), 'src': 'CoinMarketCap',
                            'got': NOW.strftime('%Y-%m-%dT%H:%M:%SZ'),
                            'prev': {'d1': sc(hv.get('yesterday')), 'd7': sc(hv.get('lastWeek')), 'd30': sc(hv.get('lastMonth'))}})
                for k, kk in (('yearlyHigh', 'yhi'), ('yearlyLow', 'ylo')):
                    x = hv.get(k)
                    if x and x.get('score') is not None:
                        out[kk] = [int(x['score']), day_of(x['timestamp'])]
                zones = [[int(z['start']), int(z['end']), z.get('name')] for z in data.get('dialConfig') or [] if z.get('start') is not None]
                if zones:
                    out['zones'] = zones
            print(f"MOOD CoinMarketCap: {out.get('v')} ({len(rows)} точек)")
        except Exception as e:
            print('MOOD CoinMarketCap ERR', e)
    days = sorted(hist)[-KEEP:]
    out['hist'] = [[d, hist[d]] for d in days]
    if not out.get('prev'):
        out['prev'] = prev_of(out['hist'])
    return out


# ---------- мем-сектор и рейтинг: CoinGecko ----------
def sector(old, offline):
    cg = dict((old or {}).get('cg') or {})
    if offline or os.environ.get('MOOD_FIXTURES'):
        return cg
    try:
        rows = get('https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&category=meme-token&order=market_cap_desc'
                   '&per_page=100&page=1&price_change_percentage=24h,7d,30d', tries=2)
        me = next((x for x in rows if x.get('id') == CG_ID), None)
        if me is None:
            one = get(f'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids={CG_ID}&price_change_percentage=24h,7d,30d', tries=2)
            me = one[0] if one else None
        if not me:
            raise RuntimeError('DOG не найден в ответе CoinGecko')

        def beat(key):
            mine = me.get(key)
            other = [x.get(key) for x in rows if x.get('id') != CG_ID and x.get(key) is not None]
            if mine is None or len(other) < 20:
                return None, None
            other.sort()
            return sum(1 for y in other if y < mine) / len(other), other[len(other) // 2]
        b7, med7 = beat('price_change_percentage_7d_in_currency')
        b30, med30 = beat('price_change_percentage_30d_in_currency')
        idx = next((i for i, x in enumerate(rows) if x.get('id') == CG_ID), None)
        cg = {'ts': NOW.strftime('%Y-%m-%dT%H:%M:%SZ'), 'rank': me.get('market_cap_rank'),
              'memeRank': idx + 1 if idx is not None else None, 'memeN': len(rows),
              'chg7': r1(me.get('price_change_percentage_7d_in_currency')), 'chg30': r1(me.get('price_change_percentage_30d_in_currency')),
              'med7': r1(med7), 'med30': r1(med30), 'beat7': None if b7 is None else round(b7, 3), 'beat30': None if b30 is None else round(b30, 3)}
        print(f"MOOD сектор: место {cg['rank']} в общем рейтинге, {cg['memeRank']} среди мем-монет")
    except Exception as e:
        print('MOOD сектор ERR', e)
    return cg


# ---------- части по ценам, за каждый день ----------
def th(x, scale):
    """плавный перевод отклонения в шкалу 0–100: 0 → 50, +scale → ≈88, −scale → ≈12"""
    return 50 + 50 * math.tanh(x / scale)


def dog_parts(px, btc, last_close=None, only_last=False):
    """vol, mom и DOG/BTC за 30 дней — по дневным ценам закрытия DOG.
    last_close — другая цена закрытия последнего дня (для кривой «цена → индекс на сегодня»), only_last — считать только его."""
    days = sorted(d for d in px if px[d] and px[d][3] > 0)
    c = [px[d][3] for d in days]
    if last_close:
        c[-1] = last_close
    n = len(c)
    ret = [None] + [math.log(c[i] / c[i - 1]) for i in range(1, n)]
    # «падения»: разброс только дней снижения за 30 дней (полудисперсия) — резкий рост мем-монеты не считаем страхом
    dvol = [None] * n
    for i in range(max(30, n - 91) if only_last else 30, n):
        r = ret[i - 29:i + 1]
        dvol[i] = math.sqrt(sum(min(0.0, x) ** 2 for x in r) / len(r)) * math.sqrt(365)
    out = {}
    for i in range(max(120, n - 1) if only_last else 120, n):
        base = [v for v in dvol[i - 90:i] if v]
        ratio = dvol[i] / (sum(base) / len(base)) if base and sum(base) > 0 else 1.0
        dd = 1 - c[i] / max(c[i - 89:i + 1])
        m30 = c[i] / (sum(c[i - 29:i + 1]) / 30) - 1
        m90 = c[i] / (sum(c[i - 89:i + 1]) / 90) - 1
        p = {
            'vol': 0.5 * clamp(50 - (ratio - 1) * 100) + 0.5 * clamp(100 - dd / 0.5 * 100),
            'mom': 0.5 * th(m30, 0.15) + 0.5 * th(m90, 0.30),
            'rb': None,
        }
        f = {'dvol30': dvol[i], 'dvRatio': ratio, 'dd90': dd, 'm30': m30, 'm90': m90}
        if btc.get(days[i]) and btc.get(days[i - 30]):
            rb = (c[i] / btc[days[i]]) / (c[i - 30] / btc[days[i - 30]]) - 1
            p['rb'] = th(rb, 0.25)
            f['rb30'] = rb
        out[days[i]] = {'p': p, 'f': f}
    return out


def btc_parts(btc):
    """тренд биткоина: цена против средних за 30 и 90 дней, просадка от максимума за 90 дней"""
    days = sorted(d for d in btc if btc[d])
    c = [btc[d] for d in days]
    out = {}
    for i in range(90, len(c)):
        m30 = c[i] / (sum(c[i - 29:i + 1]) / 30) - 1
        m90 = c[i] / (sum(c[i - 89:i + 1]) / 90) - 1
        dd = 1 - c[i] / max(c[i - 89:i + 1])
        out[days[i]] = (0.35 * th(m30, 0.10) + 0.35 * th(m90, 0.20) + 0.30 * clamp(100 - dd / 0.30 * 100),
                        {'bPx': c[i], 'bM30': m30, 'bM90': m90, 'bDd90': dd})
    return out


def turns(series, th=TURN, exact=None):
    """развороты индекса (зигзаг): вершина жадности или дно страха, после которых индекс ушёл не меньше чем на th.
    Если одно и то же (округлённое) значение было в несколько дней, вершина — день с наибольшим точным значением,
    дно — с наименьшим; при полном совпадении — более поздний день (так же считает страница)."""
    days = sorted(series)
    out = []
    if len(days) < 2:
        return out
    ex = exact or {}
    key = lambda d: (series[d], ex.get(d, series[d]))
    hi = lo = days[0]
    mode = None
    for d in days[1:]:
        v = series[d]
        if key(d) >= key(hi):
            hi = d
        if key(d) <= key(lo):
            lo = d
        if mode in (None, 'up') and series[hi] - v >= th and (mode == 'up' or hi > lo):
            out.append([hi, series[hi], 'p'])
            mode, lo = 'down', d
        elif mode in (None, 'down') and v - series[lo] >= th and (mode == 'down' or lo > hi):
            out.append([lo, series[lo], 't'])
            mode, hi = 'up', d
    return out


def combine(parts):
    tot = sum(w for k, w in WEIGHTS if parts.get(k) is not None)
    if not tot:
        return None
    return sum(parts[k] * w for k, w in WEIGHTS if parts.get(k) is not None) / tot


def main():
    site = sys.argv[1] if len(sys.argv) > 1 else '.'
    offline = '--offline' in sys.argv
    data = os.path.join(site, 'data')
    path = os.path.join(data, 'fng.json')
    old = jload(path, {}) or {}
    px = (jload(os.path.join(data, 'prices.json'), {}) or {}).get('d') or {}
    btc = (jload(os.path.join(data, 'btc.json'), {}) or {}).get('d') or {}
    live = jload(os.path.join(data, 'live.json'), {}) or {}
    hist = sorted(jload(os.path.join(data, 'hist.json'), []) or [], key=lambda h: h.get('ts') or '')
    if len(px) < 120:
        print('MOOD: мало истории цены — пропуск')
        return 0

    mk = market(old, offline)
    cm = cmc(old, offline)
    cg = sector(old, offline)
    dp = dog_parts(px, btc)
    bp = btc_parts(btc)
    alt_h, cmc_h = dict(mk.get('hist') or []), dict(cm.get('hist') or [])
    last = max(dp)
    parts = {k: None for k, _ in WEIGHTS}
    facts = dict(dp[last]['f'])

    # рынок: среднее двух индексов (сейчас — их последние значения)
    parts['mkt'] = mean([mk.get('v'), cm.get('v')])
    if mk.get('v') is not None:
        facts['alt'] = mk['v']
    if cm.get('v') is not None:
        facts['cmc'] = cm['v']

    # биткоин
    bday = last if last in bp else (max(bp) if bp else None)
    if bday:
        parts['btc'] = bp[bday][0]
        facts.update(bp[bday][1])

    parts['mom'], parts['vol'] = dp[last]['p']['mom'], dp[last]['p']['vol']

    # DOG против биткоина
    parts['rel'] = dp[last]['p']['rb']

    # для справки (в индекс не входит — истории нет): место среди мем-монет, холдеры
    ctx = {}
    ranks = dict(old.get('ranks') or {})
    if cg.get('rank') and str(cg.get('ts', ''))[:10] == TODAY:
        ranks[TODAY] = cg['rank']
    ranks = {d: ranks[d] for d in sorted(ranks)[-KEEP:]}
    back = (NOW - dt.timedelta(days=30)).strftime('%Y-%m-%d')
    past = [d for d in ranks if d <= back]
    if past and cg.get('rank'):
        ctx['rankWas'] = ranks[past[-1]]
    profit = (live.get('health') or {}).get('profit')
    if profit is not None:
        ctx['profit'] = profit
    firstb = next((h for h in hist if h.get('exBal')), None)
    exb = (live.get('exch') or {}).get('bal')
    if firstb and exb:
        ctx['exch30'] = (exb / firstb['exBal'] - 1) * 100
        ctx['exchSince'] = str(firstb.get('ts', ''))[:10]
    first = next((h for h in hist if h.get('holders')), None)
    if first and live.get('holders'):
        span = max(1.0, (NOW - dt.datetime.strptime(first['ts'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=dt.timezone.utc)).total_seconds() / 86400)
        if span >= 7:
            ctx['holders30'] = (live['holders'] / first['holders'] - 1) * 100 * min(1.0, 30 / span)

    value = combine(parts)
    if value is None:
        print('MOOD: не хватает данных')
        return 0

    # сегодняшний индекс как функция цены DOG: страница берёт число с этой кривой по живой цене — формулы в браузере нет.
    # Цены — от −45% до +82% к цене последнего расчёта (шаг 1,25% в логарифме); рынок и биткоин — как сейчас.
    base_px = px[last][3]
    curve = {'day': last, 'pts': []}
    for k in range(-CURVE_N, CURVE_N + 1):
        P = float('%.6g' % (base_px * math.exp(k * CURVE_STEP)))
        q = dog_parts(px, btc, last_close=P, only_last=True).get(last)
        if not q:
            continue
        v = combine(dict(parts, mom=q['p']['mom'], vol=q['p']['vol'], rel=q['p']['rb']))
        if v is not None:
            curve['pts'].append([P, round(v, 2)])
    at = next((v for P, v in curve['pts'] if abs(P / base_px - 1) < 1e-5), None)
    print(f'MOOD кривая: {len(curve["pts"])} точек; в цене расчёта {at} (индекс {value:.2f})')

    # история: каждый день — по тем же частям; сегодня — текущие значения индексов рынка, раньше — дневные
    series, exact = {}, {}
    for d in sorted(dp)[-KEEP:]:
        p = {'mkt': mean([alt_h.get(d), cmc_h.get(d)]), 'btc': bp[d][0] if d in bp else None,
             'mom': dp[d]['p']['mom'], 'vol': dp[d]['p']['vol'], 'rel': dp[d]['p']['rb']}
        v = combine(p)
        if v is not None:
            series[d], exact[d] = round(v), v
    series[last], exact[last] = round(value), value
    since = min(series) if series else last

    out = {
        'updated': NOW.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'market': mk,
        'cmc': cm,
        'dog': {'v': round(value), 'day': last, 'since': since, 'ver': VER,
                'parts': [{'k': k, 'v': None if parts.get(k) is None else round(parts[k])} for k, _ in WEIGHTS],
                'facts': {k: facts[k] for k in ('alt', 'cmc') if facts.get(k) is not None},
                'now': curve,
                'ctx': {k: (round(v, 4) if isinstance(v, float) else v) for k, v in ctx.items() if v is not None},
                'prev': {'d1': series.get(shift(last, 1)), 'd7': series.get(shift(last, 7)), 'd30': series.get(shift(last, 30))},
                'hist': [[d, series[d], round(exact[d], 2)] for d in sorted(series)],
                'turns': [t + [px[t[0]][3]] for t in turns(series, exact=exact) if t[0] in px]},
        'cg': cg, 'ranks': ranks,
    }
    jdump(out, path)
    print(f"MOOD DOG: {out['dog']['v']} · " + ', '.join(f"{p['k']} {p['v']}" for p in out['dog']['parts'])
          + f" · alternative.me {mk.get('v')} · CoinMarketCap {cm.get('v')}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
