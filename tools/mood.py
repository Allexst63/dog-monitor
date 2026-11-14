#!/usr/bin/env python3
"""DOG Монитор — «страх и жадность»: индекс всего рынка и такой же по смыслу индекс для одного DOG.

    python3 tools/mood.py <site_dir>            посчитать и записать data/fng.json
    python3 tools/mood.py <site_dir> --offline  то же без сети (рынок и сектор — из прошлого файла)

Рынок — готовый Crypto Fear & Greed Index сайта alternative.me (0 — крайний страх, 100 — крайняя жадность),
берём как есть, раз в день он обновляется у источника.

DOG — тот же подход, но только по данным DOG. Каждая часть — число от 0 (страх) до 100 (жадность):
  vol   25%  волатильность и просадка: колебания цены за 30 дней против обычных за прошлые 90 дней и падение
             от максимума за 90 дней — чем они больше, тем ближе к страху (как у alternative.me);
  mom   25%  импульс: цена относительно своих средних за 30 и 90 дней;
  btc   15%  сила против биткоина: как изменился курс DOG/BTC за 30 дней (аналог «доминирования» у alternative.me);
  sec   15%  место среди мем-монет: скольких из 100 крупнейших мем-монет DOG обогнал за 7 и 30 дней
             и как сдвинулся в общем рейтинге по капитализации за 30 дней (CoinGecko);
  book  10%  стакан: доля заявок на покупку среди всех заявок в пределах 10% от цены — сама по себе
             и против обычной для DOG за последний месяц (сводки сайта);
  hold  10%  холдеры: число кошельков за 30 дней, запас DOG на биржах за 30 дней, доля монет в прибыли.
Если части нет (источник не ответил), её вес делится между остальными. Историю до запуска индекса считаем
только по цене (vol, mom, btc): стаканов и рейтинга за прошлые дни нет.
Это описание настроения, а не совет и не прогноз.
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
WEIGHTS = (('vol', 25), ('mom', 25), ('btc', 15), ('sec', 15), ('book', 10), ('hold', 10))
KEEP = 400


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


# ---------- рынок: alternative.me ----------
def market(old, offline):
    out = dict((old or {}).get('market') or {})
    hist = {d: v for d, v in out.get('hist') or []}
    if not offline:
        try:
            d = get('https://api.alternative.me/fng/?limit=120&format=json')
            rows = d.get('data') or []
            for r in rows:
                day = dt.datetime.fromtimestamp(int(r['timestamp']), dt.timezone.utc).strftime('%Y-%m-%d')
                hist[day] = int(r['value'])
            if rows:
                out.update({'v': int(rows[0]['value']), 'cls': rows[0].get('value_classification'), 'ts': int(rows[0]['timestamp']), 'src': 'alternative.me', 'got': NOW.strftime('%Y-%m-%dT%H:%M:%SZ')})
            print(f"MOOD рынок: {out.get('v')} ({len(rows)} дней)")
        except Exception as e:
            print('MOOD рынок ERR', e)
    days = sorted(hist)[-KEEP:]
    out['hist'] = [[d, hist[d]] for d in days]
    return out


# ---------- мем-сектор и рейтинг: CoinGecko ----------
def sector(old, offline):
    cg = dict((old or {}).get('cg') or {})
    if offline:
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


# ---------- DOG: части индекса по цене, за каждый день ----------
def th(x, scale):
    """плавный перевод отклонения в шкалу 0–100: 0 → 50, +scale → ≈88, −scale → ≈12"""
    return 50 + 50 * math.tanh(x / scale)


def price_parts(px, btc):
    days = sorted(d for d in px if px[d] and px[d][3] > 0)
    c = [px[d][3] for d in days]
    n = len(c)
    ret = [None] + [math.log(c[i] / c[i - 1]) for i in range(1, n)]
    vol = [None] * n
    for i in range(30, n):
        vol[i] = stdev(ret[i - 29:i + 1]) * math.sqrt(365)
    out = {}
    for i in range(n):
        p = {'vol': None, 'mom': None, 'btc': None}
        f = {}
        if i >= 120:
            base = [v for v in vol[i - 90:i] if v is not None]
            ratio = vol[i] / (sum(base) / len(base))
            dd = 1 - c[i] / max(c[i - 89:i + 1])
            # спокойный рынок — это ещё не жадность: за тишину не больше 60 из 100
            p['vol'] = 0.5 * min(60.0, clamp(50 - (ratio - 1) * 100)) + 0.5 * clamp(100 - dd / 0.5 * 100)
            m30 = c[i] / (sum(c[i - 29:i + 1]) / 30) - 1
            m90 = c[i] / (sum(c[i - 89:i + 1]) / 90) - 1
            p['mom'] = 0.5 * th(m30, 0.15) + 0.5 * th(m90, 0.30)
            f.update({'vol30': vol[i], 'volRatio': ratio, 'dd90': dd, 'm30': m30, 'm90': m90})
            if btc.get(days[i]) and btc.get(days[i - 30]):
                rb = (c[i] / btc[days[i]]) / (c[i - 30] / btc[days[i - 30]]) - 1
                p['btc'] = th(rb, 0.25)
                f['rb30'] = rb
        out[days[i]] = {'p': p, 'f': f}
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
    cg = sector(old, offline)
    pp = price_parts(px, btc)
    last = max(pp)
    parts, facts = dict(pp[last]['p']), dict(pp[last]['f'])

    # место среди мем-монет и в общем рейтинге
    ranks = dict(old.get('ranks') or {})
    if cg.get('rank') and str(cg.get('ts', ''))[:10] == TODAY:
        ranks[TODAY] = cg['rank']
    ranks = {d: ranks[d] for d in sorted(ranks)[-KEEP:]}
    fresh_cg = bool(cg.get('ts')) and (NOW - dt.datetime.strptime(cg['ts'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=dt.timezone.utc)) < dt.timedelta(days=3)
    if fresh_cg and (cg.get('beat7') is not None or cg.get('beat30') is not None):
        perf = 100 * mean([cg.get('beat7'), cg.get('beat30')])
        back = (NOW - dt.timedelta(days=30)).strftime('%Y-%m-%d')
        past = [d for d in ranks if d <= back]
        ref = ranks[past[-1]] if past else (ranks[min(ranks)] if len(ranks) > 1 else None)
        if ref and cg.get('rank'):
            facts['rankWas'] = ref
            parts['sec'] = 0.7 * perf + 0.3 * clamp(50 + (ref - cg['rank']) * 2)
        else:
            parts['sec'] = perf
    else:
        parts['sec'] = None

    # стакан: доля покупок в пределах 10% от цены. У DOG заявок на покупку обычно больше, чем на продажу,
    # поэтому половина оценки — сравнение с обычной для DOG долей за последний месяц
    d10 = (live.get('totals') or {}).get('d10') or {}
    share = d10['b'] / (d10['b'] + d10['a']) if d10.get('b') is not None and d10.get('a') is not None and d10['b'] + d10['a'] > 0 else None
    sh = sorted(h['b10'] / (h['b10'] + h['a10']) for h in hist if h.get('b10') and h.get('a10'))
    if share is not None:
        facts['bidShare'] = share
        absolute = clamp((share - 0.2) / 0.6 * 100)
        if len(sh) >= 10:
            usual = sh[len(sh) // 2]
            facts['bidUsual'] = usual
            parts['book'] = 0.5 * absolute + 0.5 * clamp(50 + (share - usual) * 250)
        else:
            parts['book'] = absolute
    else:
        parts['book'] = None

    # холдеры: число кошельков и запас на биржах за 30 дней, доля монет в прибыли
    hp = []
    first = next((h for h in hist if h.get('holders')), None)
    if first and live.get('holders'):
        span = max(1.0, (NOW - dt.datetime.strptime(first['ts'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=dt.timezone.utc)).total_seconds() / 86400)
        if span >= 7:
            chg = (live['holders'] / first['holders'] - 1) * 100 * min(1.0, 30 / span)
            facts['holders30'] = chg
            hp.append((0.4, clamp(50 + chg * 50)))
    profit = (live.get('health') or {}).get('profit')
    if profit is not None:
        facts['profit'] = profit
        hp.append((0.4, clamp(profit)))
    firstb = next((h for h in hist if h.get('exBal')), None)
    exb = (live.get('exch') or {}).get('bal')
    if firstb and exb:
        chg = (exb / firstb['exBal'] - 1) * 100
        facts['exch30'] = chg
        hp.append((0.2, th(-chg, 8)))
    parts['hold'] = sum(w * v for w, v in hp) / sum(w for w, _ in hp) if hp else None

    value = combine(parts)
    if value is None:
        print('MOOD: не хватает данных')
        return 0

    # история: сохранённые дни не пересчитываем, прошлые дни до запуска — только по цене
    saved = {d: v for d, v in (old.get('dog') or {}).get('hist') or []}
    series = {}
    for d in sorted(pp)[-KEEP:]:
        if d in saved and d != last and (old.get('dog') or {}).get('since', '9999') <= d:
            series[d] = saved[d]
        else:
            v = combine(pp[d]['p'])
            if v is not None:
                series[d] = round(v)
    series[last] = round(value)
    since = (old.get('dog') or {}).get('since') or last

    def ago(hh, n):
        d = (dt.datetime.strptime(last, '%Y-%m-%d') - dt.timedelta(days=n)).strftime('%Y-%m-%d')
        return hh.get(d)
    mh = {d: v for d, v in mk.get('hist') or []}
    if mk.get('v') is not None and mh:
        mday = max(mh)
        mk['prev'] = {k: mh.get((dt.datetime.strptime(mday, '%Y-%m-%d') - dt.timedelta(days=n)).strftime('%Y-%m-%d')) for k, n in (('d1', 1), ('d7', 7), ('d30', 30))}
    out = {
        'updated': NOW.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'market': mk,
        'dog': {'v': round(value), 'day': last, 'since': since,
                'parts': [{'k': k, 'w': w, 'v': None if parts.get(k) is None else round(parts[k])} for k, w in WEIGHTS],
                'facts': {k: (round(v, 4) if isinstance(v, float) else v) for k, v in facts.items() if v is not None},
                'prev': {'d1': ago(series, 1), 'd7': ago(series, 7), 'd30': ago(series, 30)},
                'hist': [[d, series[d]] for d in sorted(series)]},
        'cg': cg, 'ranks': ranks,
    }
    jdump(out, path)
    print(f"MOOD DOG: {out['dog']['v']} · " + ', '.join(f"{p['k']} {p['v']}" for p in out['dog']['parts']) + f" · рынок {mk.get('v')}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
