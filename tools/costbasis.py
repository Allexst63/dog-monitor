#!/usr/bin/env python3
"""DOG Монитор — средняя цена DOG у кошельков топ-100 (для GitHub Actions, после tools/daily.py run).

    python3 tools/costbasis.py <site_dir>            посчитать и записать data/prices.json и data/costbasis.json
    python3 tools/costbasis.py <site_dir> --offline  то же без сети: только из уже сохранённых файлов (для проверки)

Как считается «средняя цена» кошелька:
  * история переводов адреса — DOG DATA (/api/address/bitcoin/<адрес>), цена DOG по дням — свечи бирж
    (Kraken DOG/USD, а до начала его истории — Gate DOG/USDT), берём цену закрытия дня;
  * каждое поступление DOG оценивается по цене дня, когда оно пришло; при отправке DOG средняя цена не меняется
    (метод средней стоимости); остаток «стоимости» делим на текущий баланс;
  * монеты из аирдропа и всё, что пришло до начала торгов (запись DOG DATA «Pre-indexed activity», блок 840 000),
    достались бесплатно — их цена 0, а доля таких монет пишется отдельно (free);
  * кошельки бирж, биржевых хранилищ и маркетплейсов не считаем: там монеты клиентов, «средняя цена» не имеет смысла;
  * история переводов кэшируется в data/costbasis.json, каждое утро догружаются только новые переводы;
  * если баланс по истории не сходится с балансом DOG DATA больше чем на 0,5% — пересчитываем с нуля; если и тогда
    не сходится — см. reconcile(): при недостающих отправках цена остаётся верной (ax='out'), иначе не показываем.
Цены DOG — только с бирж (агрегаторы цен не используются). В сеть ходит только по HTTPS к dogdata.xyz, Kraken и Gate.
"""
import bisect
import datetime as dt
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fetch import get  # noqa: E402  (тот же HTTP-клиент с повторами, что и для утренней сводки)

DD = ('https://www.dogdata.xyz', 'https://dogdata.xyz')
SKIP_KINDS = ('exchange', 'custody', 'marketplace')
MAX_TX = 1000          # DOG DATA отдаёт не больше 1000 последних операций адреса, а всё более раннее сворачивает
                       # в одну запись «Pre-indexed activity» — у таких кошельков настоящую среднюю цену не посчитать
PAGE = 500
LAUNCH = '2024-04-25'  # первый день торгов DOG на биржах (первая дневная свеча Gate)
NOW = dt.datetime.now(dt.timezone.utc)


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
    return str(ts or '')[:10]


# ---------- цена DOG по дням ----------
def fetch_prices(old):
    """{дата: [open, high, low, close]} — Kraken DOG/USD (последние ~720 дней), раньше — Gate DOG/USDT."""
    px, src = {}, {}
    today = NOW.strftime('%Y-%m-%d')
    try:
        d = get('https://api.gateio.ws/api/v4/spot/candlesticks?currency_pair=DOG_USDT&interval=1d&limit=1000')
        for r in d if isinstance(d, list) else []:
            t = dt.datetime.fromtimestamp(int(float(r[0])), dt.timezone.utc).strftime('%Y-%m-%d')
            o, h, lo, c = (float(r[i]) for i in (5, 3, 4, 2))
            if c > 0 and t <= today:      # у Gate бывает «завтрашняя» пустая свеча — её не берём
                px[t] = [o, h, lo, c]
                src[t] = 'g'
        print(f'PRICES gate: {len(px)} дней')
    except Exception as e:
        print('PRICES gate ERR', e)
    try:
        d = get('https://api.kraken.com/0/public/OHLC?pair=DOGUSD&interval=1440')
        res = d.get('result') or {}
        key = next((k for k in res if k != 'last'), None)
        n = 0
        for r in res.get(key) or []:
            t = dt.datetime.fromtimestamp(int(r[0]), dt.timezone.utc).strftime('%Y-%m-%d')
            o, h, lo, c = (float(r[i]) for i in (1, 2, 3, 4))
            if c > 0 and t <= today:
                px[t] = [o, h, lo, c]
                src[t] = 'k'
                n += 1
        print(f'PRICES kraken: {n} дней')
    except Exception as e:
        print('PRICES kraken ERR', e)
    # дни, которых нет в свежем ответе (старые), берём из прошлого файла
    for t, v in ((old or {}).get('d') or {}).items():
        if t not in px and t <= today:
            px[t] = v
            src[t] = ((old or {}).get('s') or {}).get(t, '?')
    return px, src


def price_on(px, dates, t):
    """цена закрытия дня t; если дня нет — ближайшего предыдущего"""
    if t in px:
        return px[t][3]
    i = bisect.bisect_right(dates, t) - 1
    return px[dates[i]][3] if i >= 0 else None


# ---------- история переводов кошелька ----------
def page(a, offset, limit=PAGE):
    return get([h + f'/api/address/bitcoin/{a}?limit={limit}&offset={offset}' for h in DD], tries=2)


def full_history(a, first=None):
    d = first or page(a, 0)
    total = int(d.get('tx_count') or (d.get('pagination') or {}).get('total') or 0)
    txs = list(d.get('transactions') or [])
    if total > MAX_TX:
        return d, txs, total, 'больше 1000 операций'
    while len(txs) < total:
        time.sleep(0.4)
        nd = page(a, len(txs))
        more = nd.get('transactions') or []
        if not more:
            break
        txs += more
    return d, txs, total, None


def tkey(x):
    return (int(x.get('block_height') or 0), str(x.get('timestamp') or ''), str(x.get('txid') or ''))


def apply(st, txs, px, dates):
    """st = {bal, cost, free, first}; txs — по возрастанию"""
    for x in txs:
        q = float(x.get('amount_dog') or 0)
        if q <= 0:
            continue
        t = day(x.get('timestamp'))
        pre = int(x.get('block_height') or 0) <= 840000 or t < LAUNCH
        if x.get('direction') == 'in':
            p = 0.0 if pre else (price_on(px, dates, t) or 0.0)
            st['bal'] += q
            st['cost'] += q * p
            if pre or p == 0:
                st['free'] += q
            elif not st.get('fb'):
                st['fb'] = t          # первая покупка / пополнение после аирдропа
            if not st.get('first'):
                st['first'] = t
        elif x.get('direction') == 'out' and st['bal'] > 0:
            f = min(1.0, q / st['bal'])
            st['cost'] -= st['cost'] * f
            st['free'] -= st['free'] * f
            st['bal'] = max(0.0, st['bal'] - q)
    return st


def reconcile(st, bal_now):
    """История DOG DATA бывает неполной: часть отправок (реже — поступлений) в список переводов не попадает,
    а баланс берётся из UTXO и всегда точный. При методе средней стоимости отправки не меняют среднюю цену,
    поэтому, если не хватает отправок, средняя по известным поступлениям остаётся верной — просто приводим
    остаток к настоящему балансу (approx='out'). Если не хватает поступлений до 10% — так же, но пометка 'in';
    больше — цену не показываем."""
    tol = max(1.0, bal_now * 0.005)
    if abs(st['bal'] - bal_now) <= tol:
        return st, True, None
    if st['bal'] > 0 and (st['bal'] > bal_now or st['bal'] >= 0.9 * bal_now):
        k = bal_now / st['bal']
        return ({'bal': bal_now, 'cost': st['cost'] * k, 'free': st['free'] * k, 'first': st.get('first'), 'fb': st.get('fb')}, True,
                'out' if st['bal'] > bal_now else 'in')
    return st, False, None


def main():
    site = sys.argv[1]
    offline = '--offline' in sys.argv
    data = os.path.join(site, 'data')
    live = jload(os.path.join(data, 'live.json')) or {}
    top = live.get('top100') or []
    if not top:
        sys.exit('нет data/live.json с топ-100')

    old_px = jload(os.path.join(data, 'prices.json'), {})
    if offline:
        px, src = old_px.get('d') or {}, old_px.get('s') or {}
    else:
        px, src = fetch_prices(old_px)
    if not px:
        sys.exit('нет истории цен DOG')
    dates = sorted(px)
    k_from = min((t for t, s in src.items() if s == 'k'), default=None)
    jdump({'updated': NOW.strftime('%Y-%m-%dT%H:%M:%SZ'), 'first': dates[0], 'kraken_from': k_from,
           'src': 'Kraken DOG/USD' + (f' с {k_from}' if k_from else '') + ', раньше — Gate DOG/USDT; цена закрытия дня (UTC)',
           'd': {t: [round(v, 9) for v in px[t]] for t in dates}, 's': {t: src.get(t, '?') for t in dates}},
          os.path.join(data, 'prices.json'))

    old = jload(os.path.join(data, 'costbasis.json'), {}) or {}
    cache = (old.get('c') or {}) if old.get('v') == 2 else {}   # v2: средняя цена без аирдропа — пересчёт с нуля
    out_w, out_c = {}, {}
    stat = {'ok': 0, 'skip': 0, 'err': 0, 'full': 0, 'inc': 0, 'same': 0, 'bad': 0}
    for x in top:
        a, k, bal_now = x['a'], x.get('k') or 'unknown', float(x.get('b') or 0) * 1e6
        if k in SKIP_KINDS:
            stat['skip'] += 1
            continue
        c = cache.get(a)
        if offline:
            if c:
                out_c[a] = c
            continue
        try:
            d = page(a, 0)
            total = int(d.get('tx_count') or (d.get('pagination') or {}).get('total') or 0)
            txs0 = d.get('transactions') or []
            st = None
            if total > MAX_TX:
                out_c[a] = {'n': total, 'skip': 'больше 1000 операций'}
                stat['skip'] += 1
                continue
            if c and not c.get('skip') and c.get('n') and total >= c['n']:
                new = total - c['n']
                if new == 0 and txs0 and txs0[0].get('txid') == c.get('last'):
                    st = {k2: c.get(k2) for k2 in ('bal', 'cost', 'free', 'first', 'fb')}
                    stat['same'] += 1
                elif 0 < new < len(txs0) and txs0[new].get('txid') == c.get('last'):
                    st = apply({k2: c.get(k2) for k2 in ('bal', 'cost', 'free', 'first', 'fb')}, sorted(txs0[:new], key=tkey), px, dates)
                    stat['inc'] += 1
            if st is None or abs(st['bal'] - bal_now) > max(1.0, bal_now * 0.005):
                d, txs, total, why = full_history(a, d)
                if why:
                    out_c[a] = {'n': total, 'skip': why}
                    stat['skip'] += 1
                    continue
                st = apply({'bal': 0.0, 'cost': 0.0, 'free': 0.0, 'first': None, 'fb': None}, sorted(txs, key=tkey), px, dates)
                stat['full'] += 1
                txs0 = txs
            hist_bal = st['bal']
            st, ok, approx = reconcile(st, bal_now)
            last = (txs0[0].get('txid') if txs0 else None)
            out_c[a] = {'n': total, 'last': last, 'bal': round(st['bal'], 5), 'cost': round(st['cost'], 6),
                        'free': round(max(0.0, st['free']), 5), 'first': st['first'], 'fb': st.get('fb'), 'ok': ok}
            if approx:
                out_c[a]['ax'] = approx
                stat['approx'] = stat.get('approx', 0) + 1
                print(f'COST approx({approx}) {a[:12]}…: история {hist_bal / 1e6:.2f}M, баланс {bal_now / 1e6:.2f}M')
            stat['ok' if ok else 'bad'] += 1
            if not ok:
                print(f'COST mismatch {a[:12]}…: история {hist_bal / 1e6:.2f}M, баланс {bal_now / 1e6:.2f}M')
        except Exception as e:
            stat['err'] += 1
            print(f'COST ERR {a[:12]}…: {str(e)[:160]}')
            if c:
                out_c[a] = c          # оставляем вчерашний расчёт
        time.sleep(0.4)

    for a, c in out_c.items():
        if c.get('skip') or not c.get('ok') or not c.get('bal'):
            continue
        bal, cost, free = c['bal'], c['cost'], min(c['free'], c['bal'])
        paid = bal - free
        # средняя цена — только по покупкам и пополнениям после аирдропа; монеты с аирдропа в неё не входят
        w = {'free': round(free / bal, 4), 'first': c.get('first'), 'fb': c.get('fb')}
        if paid >= max(0.02 * bal, 0.5e6):
            w['buy'] = float(f'{cost / paid:.4g}')
        if c.get('ax'):
            w['ax'] = c['ax']
        out_w[a] = w

    jdump({'v': 2, 'updated': NOW.strftime('%Y-%m-%dT%H:%M:%SZ'), 'asof': live.get('id'),
           'method': 'средняя цена покупок: пополнения после аирдропа по цене закрытия дня, отправки не меняют среднюю; монеты аирдропа не входят',
           'w': out_w, 'c': out_c}, os.path.join(data, 'costbasis.json'))
    print('COST', ' '.join(f'{k2}={v}' for k2, v in stat.items()), f'кошельков с ценой: {len(out_w)}')


if __name__ == '__main__':
    main()
