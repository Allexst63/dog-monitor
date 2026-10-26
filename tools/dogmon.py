#!/usr/bin/env python3
"""DOG Монитор — пайплайн снимка (утро и дневные обновления).

  python3 dogmon.py compute [утро|запрос|день|тест]   разбирает raw/*.txt, сверяет с prev/, пишет out/snapshot.json и out/report.md
                                               (запрос — полная сводка по просьбе: сравнение с последним обновлением, пишется в архив)
  python3 dogmon.py finalize                   вставляет raw/conclusion.txt в отчёт и снимок
  python3 dogmon.py newslist                   короткий список уже опубликованных новостей (prev/news)
  python3 dogmon.py news                       проверяет raw/news.json, готовит новые записи и дописывает их в out/writes.json
  python3 dogmon.py message ["статус сайта"]   короткое утреннее сообщение: только важное (out/message.md)

Версия 3.2: «Главное» — короткий список важных событий по порогам ALERT_* (крупные стенки в стаканах, балансы бирж,
переводы, крупные холдеры, топ-100, резкое движение цены); хранится в снимке (поле alerts) и идёт в утреннее сообщение.
Версия 3.1: свечи Kraken целиком (время, open, high, low, close, объём) для графика «свечи»;
казначейства компаний с DOG (meta/treasuries): команда news берёт поле "treasury" из raw/news.json.
Версия 3.0: + график цены Kraken (raw/ohlc_1d.txt, raw/ohlc_1h.txt) и «здоровье холдеров» из dogdata
(raw/dd_age.txt — возраст монет, реализованная цена, прибыль/убыток; raw/dd_airdrop.txt — аирдроп;
raw/dd_chains.txt — DOG в Solana и Stacks). Эти источники необязательные: без них сводка считается как раньше.

Каталог $DOGMON (по умолчанию /tmp/dogmon):
  raw/   ответы WebFetch дословно (+ entity_<адрес>.txt — профили адресов из dogdata)
  prev/  прошлые снимки из базы дашборда (ArtifactData out_dir)
  cfg/   config/labels.json — подписи владельцев кошельков
  out/   результат: snapshot.json, hist.json, report.md, writes.json (что записать в базу), news/*.json
"""
import datetime as dt
import glob
import hashlib
import json
import math
import os
import re
import sys
from statistics import median

VERSION = '3.2'
DASH = os.environ.get('DOGMON_DASH', 'https://claude.ai/artifact/EUA2j5NEH47wp89A51XqXn')
BASE = os.environ.get('DOGMON', '/tmp/dogmon')
RAW, PREV, OUT, CFG = (os.path.join(BASE, d) for d in ('raw', 'prev', 'out', 'cfg'))
SUPPLY = 100e9            # эмиссия DOG
WALL_MIN = 5e6            # стенка: уровень от 5 млн DOG
MOVE_MIN = 5.0            # млн DOG: отмечаем изменения балансов топ-100 от 5M
BUCKET = 0.00001          # шаг сводного стакана
LADDER = 0.30             # сводный стакан: ±30% от цены
# «Главное» в утреннем сообщении — только крупное (млн DOG; 20 млн ≈ 18 тыс. $ при цене 0,0009 $)
ALERT_WALL = 20.0         # стенка в стакане: новая, снятая, переставленная — от 20 млн
ALERT_WALL_D = 10.0       # стенка выросла или уменьшилась на 10 млн и больше (и сама от 20 млн)
ALERT_WALL_BAND = 0.30    # стенки дальше ±30% от цены не берём
ALERT_EXCH = 20.0         # баланс биржи изменился на 20 млн и больше
ALERT_FLOW = 20.0         # переводы на биржу или с биржи за сутки (сумма по бирже); один перевод между кошельками
ALERT_HOLDER = 20.0       # крупный холдер из топ-100 (не биржа) набрал или сбросил 20 млн и больше
ALERT_PRICE = 7.0         # цена за сутки изменилась на 7% и больше
SITE_URL = 'https://allexst63.github.io/dog-monitor/'
EXCHANGES = (('kraken', 'Kraken'), ('gate', 'Gate'), ('mexc', 'MEXC'), ('bingx', 'BingX'),
             ('coinw', 'CoinW'), ('digifinex', 'DigiFinex'), ('bitget', 'Bitget'))
EXN = dict(EXCHANGES)
BOOK_FILES = {'kraken': ('kraken_bids', 'kraken_asks'), 'gate': ('gate_book',), 'mexc': ('mexc_book',),
              'bingx': ('bingx_book',), 'coinw': ('coinw_book',), 'digifinex': ('digifinex_book',), 'bitget': ('bitget_book',)}
REQ_ROWS = {'kraken_bids': 200, 'kraken_asks': 120, 'gate_book': 100, 'mexc_book': 150, 'bingx_book': 150,
            'coinw_book': 20, 'digifinex_book': 150, 'bitget_book': 150}
TS_KEY = {'kraken_bids': 'maxts', 'kraken_asks': 'maxts', 'gate_book': 'current', 'mexc_book': 'ts', 'bingx_book': 'ts',
          'digifinex_book': 'date', 'bitget_book': 'ts', 'coinw_book': None}
MAX_AGE = {'stats': 780, 'holders': 780, 'conc': 780, 'whales': 120, 'markets': 120, 'btc': 60,   # холдеры dogdata обновляет ~раз в 12 ч
           'kraken_bids': 120, 'kraken_asks': 120, 'gate_book': 60, 'mexc_book': 60, 'bingx_book': 60,
           'digifinex_book': 60, 'bitget_book': 60,
           'ohlc_1d': 1560, 'ohlc_1h': 150}           # время открытия последней свечи: дневная — сегодня 00:00 UTC
SOFT_AGE = {'dd_age': 1800, 'dd_airdrop': 1800, 'dd_chains': 360}  # минут; устаревшие метрики — замечание, не ошибка
AGE_BANDS = (('до месяца', ('< 1 day', '1-7 days', '7-30 days')), ('1–6 месяцев', ('30-90 days', '90-180 days')),
             ('6–12 месяцев', ('180-365 days',)), ('больше года', ('> 365 days',)))
EXCHANGE_KINDS = ('exchange', 'custody')
NEWS_KINDS = ('листинг', 'делистинг', 'X', 'исследование', 'проект', 'новость')
NEWS_MAX_AGE = int(os.environ.get('DOGMON_NEWS_MAXAGE', '45'))   # дней; старше — не добавляем
KNOWN_EXCHANGES = {'Kraken', 'Gate', 'MEXC', 'Bitget', 'CoinEx', 'OKX', 'Binance', 'Bybit', 'BingX', 'HTX', 'KuCoin',
                   'CoinW', 'DigiFinex', 'BigONE', 'Bitrue', 'Coinbase', 'Bitfinex', 'Crypto.com'}
NOW = dt.datetime.now(dt.timezone.utc)
if os.environ.get('DOGMON_NOW'):  # только для тестов
    NOW = dt.datetime.fromisoformat(os.environ['DOGMON_NOW'].replace('Z', '+00:00'))

ADDR = r'(bc1[0-9a-z]{20,90}|[13][1-9A-HJ-NP-Za-km-z]{25,40})'
ISO = r'(\d{4}-\d\d-\d\d[T ]\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:?\d\d)?)'
NUM = r'(\d+(?:\.\d+)?(?:[eE]-?\d+)?)'
LEAD = r'^[ \t>*\-`|]*'
SEP = r'\s*[;|]\s*'
BOOK_ROW = re.compile(LEAD + r'([BA])\s*[;|,]\s*' + NUM + r'\s*[;|,]\s*' + NUM + r'(?:\s*[;|,]\s*(\d{9,13}))?', re.M)
HOLDER_ROW = re.compile(LEAD + r'(\d{1,3})' + SEP + ADDR + SEP + NUM + SEP + r'(\d+)\b', re.M)
STATS_ROW = re.compile(LEAD + r'(\d{1,2})' + SEP + ADDR + SEP + NUM, re.M)
WHALE_ROW = re.compile(ISO + SEP + NUM + SEP + r'([^;|\s]+)' + SEP + r'([^;|\s]+)(?:' + SEP + r'([0-9a-fA-F]{64}))?')
MARKET_ROW = re.compile(LEAD + r'([A-Za-z][\w .()&\'-]*?)' + SEP + r'([A-Za-z0-9()]+/[A-Za-z0-9]+)' + SEP + NUM + SEP + NUM, re.M)
OHLC_ROW = re.compile(LEAD + r'(\d{10})' + (SEP + NUM) * 6 + r'(?:' + SEP + r'(\d+))?', re.M)
WAVE_ROW = re.compile(LEAD + r'wave' + SEP + r'([^;|\n]+?)' + SEP + NUM, re.M)
SIZE_ROW = re.compile(LEAD + r'size' + SEP + r'([^;|\n]+?)' + SEP + r'(\d+)' + SEP + NUM, re.M)
CHAIN_ROW = re.compile(LEAD + r'chain' + SEP + r'([a-z]+)' + SEP + r'(\d+)' + (SEP + NUM) * 4 + r'(?:' + SEP + ISO + r')?', re.M)

checks, warns, refetch, lookup = [], [], [], []


# ---------- утилиты ----------
def chk(ok, text, src=None):
    checks.append({'ok': bool(ok), 't': text})
    if not ok and src:
        for s in ([src] if isinstance(src, str) else src):
            if s not in refetch:
                refetch.append(s)
    return bool(ok)


def raw(name):
    try:
        text = open(os.path.join(RAW, name + '.txt'), encoding='utf-8', errors='replace').read()
    except FileNotFoundError:
        return None
    if not text.strip() or text.strip().upper().startswith('UNAVAILABLE'):
        return None
    return text


def kv(text, key):
    m = re.search(r'(?<![\w.])"?' + re.escape(key) + r'"?\s*[=:]\s*"?([^;\s",}|]+)', text or '')
    return m.group(1) if m else None


def fnum(s):
    try:
        return float(str(s).replace(',', '').replace(' ', ''))
    except (TypeError, ValueError):
        return None


def dog(x):
    x = float(x)
    return x / 1e5 if x > SUPPLY else x


def parse_time(s):
    if s is None:
        return None
    s = str(s).strip().strip('"\'')
    if re.fullmatch(r'\d{9,17}(\.\d+)?', s):
        x = float(s)
        x = x / 1e6 if x > 1e14 else (x / 1e3 if x > 1e11 else x)
        return dt.datetime.fromtimestamp(x, dt.timezone.utc)
    m = re.match(r'(\d{4}-\d\d-\d\d)[T ](\d\d:\d\d:\d\d)(\.\d+)?(Z|[+-]\d\d:?\d\d)?', s)
    if not m:
        return None
    t = dt.datetime.strptime(m.group(1) + 'T' + m.group(2), '%Y-%m-%dT%H:%M:%S')
    if m.group(3):
        t += dt.timedelta(microseconds=int((m.group(3)[1:] + '000000')[:6]))
    tz = m.group(4)
    if tz and tz != 'Z':
        sign = 1 if tz[0] == '+' else -1
        t -= sign * dt.timedelta(hours=int(tz[1:3]), minutes=int(tz[-2:]))
    return t.replace(tzinfo=dt.timezone.utc)


def iso(t):
    return t.strftime('%Y-%m-%dT%H:%M:%SZ') if t else None


def hm(t):
    return t.strftime('%d.%m %H:%M UTC') if t else '—'


def fresh(src, t, label):
    a = None if t is None else (NOW - t).total_seconds() / 60
    lim = MAX_AGE[src]
    ok = a is not None and -15 <= a <= lim
    why = '' if ok else (' — нет метки времени' if a is None else f' — возраст {a:.0f} мин > {lim}')
    chk(ok, f'{label}: {hm(t)}{why}', src)
    return ok


def fp(p):
    if p is None:
        return '—'
    s = f'{p:.7f}'.rstrip('0')
    if len(s.split('.')[1]) < 6:
        s = f'{p:.6f}'
    return s


def sgn(x, d=1, unit=''):
    if x is None:
        return '—'
    r = round(x, d)
    if r == 0:
        return f'±{0:.{d}f}{unit}'
    return ('+' if r > 0 else '−') + f'{abs(r):.{d}f}{unit}'


def thou(x, d=0):
    if x is None:
        return '—'
    s = f'{abs(x):,.{d}f}'.replace(',', ' ')
    return ('−' if x < 0 else '') + s


def short(a):
    return a if len(a) <= 16 else a[:8] + '…' + a[-6:]


def r2(x, d=2):
    return None if x is None else round(x, d)


# ---------- подписи владельцев ----------
def load_labels():
    for path in (os.path.join(CFG, 'config', 'labels.json'), os.path.join(CFG, 'labels.json')):
        try:
            d = json.load(open(path, encoding='utf-8'))
            return d.get('map', d) if isinstance(d, dict) else {}
        except Exception:
            continue
    return {}


def parse_entity(text):
    info = {}
    for key in ('entity_name', 'kind', 'role', 'claim', 'first_tx', 'last_tx', 'tx_count', 'received', 'sent', 'balance'):
        v = kv(text, key)
        info[key] = None if v in (None, 'null', 'None', '') else v
    m = re.search(r'note\s*=\s*(.+)', text or '')
    note = m.group(1).strip().strip('"\'') if m else ''
    info['note'] = '' if note.lower() in ('null', 'none', '') else note[:200]
    return info


def plural(n, one, few, many):
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def ddmmyyyy(s):
    t = parse_time(s)
    return t.strftime('%d.%m.%Y') if t else None


def classify(info):
    """Профиль адреса из dogdata → {n, k, note}. Метка сущности dogdata важнее всего;
    без метки: до 500 операций — частный холдер, больше — крупный холдер (похоже на сервис)."""
    name, kind = info.get('entity_name'), (info.get('kind') or '').lower()
    if name:
        nm = {'gate.io': 'Gate', 'gate': 'Gate', 'marketplace': 'Маркетплейс'}.get(name.lower(), name)
        k = {'exchange': 'exchange', 'treasury': 'treasury', 'distributor': 'distributor', 'desk': 'mm',
             'market_maker': 'mm', 'marketplace': 'marketplace', 'custody': 'custody'}.get(kind)
        if not k:
            k = 'exchange' if nm in KNOWN_EXCHANGES else 'unknown'
        rus = {'treasury': 'Казна', 'distributor': 'Распределитель', 'mm': 'Маркет-мейкер', 'marketplace': 'Маркетплейс'}
        note = info.get('note') or ''
        m = re.search(r'Appears in ([\d.]+)% of every DOG transfer over (\d+) days', note)
        if m:
            note = f'участвует в {m.group(1)}% всех переводов DOG за {m.group(2)} дн.'
        elif note and re.search(r'[A-Za-z]{4}', note):
            note = ''
        return {'n': nm if k in ('exchange', 'custody', 'unknown') else rus.get(k, nm), 'k': k, 'note': note[:120], 'src': 'dogdata'}
    first, last, tx = info.get('first_tx'), info.get('last_tx'), fnum(info.get('tx_count'))
    if not first and tx is None:
        return None
    d0, d1 = ddmmyyyy(first), ddmmyyyy(last)
    parts = ['с аирдропа 20.04.2024' if (first or '').startswith('2024-04-20') else (f'с {d0}' if d0 else '')]
    if tx is not None:
        parts.append(f"{int(tx)} {plural(tx, 'операция', 'операции', 'операций')}")
    if d1 and d1 != d0:
        parts.append(f'последняя {d1}')
    note = ' · '.join(p for p in parts if p)
    if tx is not None and tx > 500:
        return {'n': 'Крупный холдер', 'k': 'unknown', 'note': ('много операций, похоже на сервис · ' + note)[:120], 'src': 'dogdata: без метки'}
    return {'n': 'Частный холдер', 'k': 'private', 'note': note[:120], 'src': 'dogdata: без метки'}


# ---------- прошлый снимок ----------
def load_prev(kind):
    """утро/база: прошлый утренний снимок (коллекция snapshots, старше 12 ч); день/тест: прошлое обновление (≥30 мин)."""
    docs = []
    for path in glob.glob(os.path.join(PREV, '**', '*.json'), recursive=True):
        coll = os.path.basename(os.path.dirname(path))
        if coll not in ('snapshots', 'live', 'prev'):
            continue
        try:
            d = json.load(open(path, encoding='utf-8'))
        except Exception:
            continue
        for key in ('data', 'doc', 'document', 'body'):
            if isinstance(d, dict) and isinstance(d.get(key), dict) and 'ts' in d[key]:
                d = d[key]
        if not (isinstance(d, dict) and d.get('ts') and d.get('top100')):
            continue
        t = parse_time(d['ts'])
        if t and t < NOW - dt.timedelta(minutes=30):
            docs.append((t, d, d.get('id') or os.path.splitext(os.path.basename(path))[0], coll))
    if not docs:
        return None, None
    docs.sort(key=lambda x: x[0])
    pool = docs
    if kind in ('утро', 'база'):
        old = [x for x in docs if x[0] <= NOW - dt.timedelta(hours=12)]
        pool = [x for x in old if x[3] == 'snapshots'] or old or docs
    t, d, i, c = pool[-1]
    return d, i


# ---------- стаканы ----------
def parse_book(name):
    text = raw(name)
    if text is None:
        return None
    bids, asks = [], []
    for side, p, q, ts in BOOK_ROW.findall(text):
        p, q = float(p), float(q)
        if p > 0 and q > 0:
            (bids if side == 'B' else asks).append((p, q, int(ts) if ts else None))
    bids.sort(key=lambda x: -x[0])
    asks.sort(key=lambda x: x[0])
    m = re.search(r'rows\s*=\s*(\d+)(?:\s*[ ,;/]\s*(\d+))?', text)
    decl = (int(m.group(1)), int(m.group(2)) if m.group(2) else None) if m else (None, None)
    zero_bid = re.search(r'^[ \t>*\-`|]*B\s*[;|,]\s*0(?:\.0*)?\s*[;|,]', text, re.M) is not None
    return {'text': text, 'bids': bids, 'asks': asks, 'decl': decl, 'zero_bid': zero_bid}


# ---------- график цены (Kraken) ----------
def parse_ohlc(name, label, step):
    text = raw(name)
    if text is None:
        chk(False, f'{label} — нет данных', name)
        return None
    err = kv(text, 'error')
    if err and err.strip('[]\'" '):
        chk(False, f'{label}: ошибка API {err}', name)
        return None
    rows = {}
    for ts, o, h, lo, c, vw, v, cnt in OHLC_ROW.findall(text):
        o, h, lo, c = float(o), float(h), float(lo), float(c)
        if 0 < lo <= h and 0 < c and lo <= max(o, c) + 1e-12:
            rows[int(ts)] = (int(ts), o, h, lo, c, float(v))
    rows = [rows[k] for k in sorted(rows)]
    decl = fnum(kv(text, 'rows'))
    if not rows:
        chk(False, f'{label}: свечей нет', name)
        return None
    if decl is not None and abs(decl - len(rows)) > 1:
        chk(False, f'{label}: свечей {len(rows)} из {int(decl)} — ответ обрезан', name)
    gaps = sum(1 for a, b in zip(rows, rows[1:]) if b[0] - a[0] != step)
    if gaps:
        chk(False, f'{label}: пропуски между свечами ({gaps})', name)
    fresh(name, dt.datetime.fromtimestamp(rows[-1][0], dt.timezone.utc), label)
    return rows


def build_chart(books):
    d1 = parse_ohlc('ohlc_1d', 'Kraken: свечи по дням', 86400)
    h1 = parse_ohlc('ohlc_1h', 'Kraken: свечи по часам', 3600)
    if not d1 and not h1:
        return None
    kb = books.get('kraken') or {}
    now_p = kb.get('mid') or (h1 or d1)[-1][4]

    def chg(rows, back):
        """изменение от закрытия свечи «back» назад до текущей цены Kraken"""
        if not rows or len(rows) <= back:
            return None
        base = rows[-1 - back][4]
        return r2((now_p / base - 1) * 100, 1) if base else None
    out = {'src': 'Kraken DOG/USD', 'now': round(now_p, 9), 'nowTs': kb.get('ats'),
           'd1': [[r[0], round(r[1], 7), round(r[2], 7), round(r[3], 7), round(r[4], 7), round(r[5])] for r in (d1 or [])],
           'h1': [[r[0], round(r[1], 7), round(r[2], 7), round(r[3], 7), round(r[4], 7), round(r[5])] for r in (h1 or [])],
           'chg': {'1d': chg(h1, 24), '7d': chg(h1, len(h1) - 1) if h1 else None, '30d': chg(d1, 30),
                   '90d': chg(d1, 90), '1y': chg(d1, len(d1) - 1) if d1 else None}}
    if d1:
        hi = max(d1, key=lambda r: r[2])
        lo = min(d1, key=lambda r: r[3])
        out.update({'hi': hi[2], 'hiT': hi[0], 'lo': lo[3], 'loT': lo[0], 'days': len(d1)})
    if h1:
        last24 = h1[-24:]
        out.update({'hi24': max(r[2] for r in last24), 'lo24': min(r[3] for r in last24),
                    'vol24': round(sum(r[5] for r in last24) / 1e6, 2)})   # млн DOG на Kraken за 24 ч
    out['asof'] = iso(dt.datetime.fromtimestamp(max(x[-1][0] for x in (d1, h1) if x), dt.timezone.utc))
    return out


# ---------- «здоровье холдеров» (dogdata) ----------
def soft(ok, text, src):
    if ok:
        return True
    warns.append(text)
    if src not in refetch:
        refetch.append(src)
    return False


def soft_age(src, t, label):
    a = None if t is None else (NOW - t).total_seconds() / 60
    return soft(a is not None and -15 <= a <= SOFT_AGE[src],
                f'{label}: ' + ('нет метки времени' if a is None else f'срез {hm(t)}, возраст {a / 60:.0f} ч'), src)


def build_health(mid):
    h = {}
    age = raw('dd_age')
    if age:
        g = {k: fnum(kv(age, k)) for k in ('total_utxos', 'avg_age_days', 'median_age_days', 'lth_percentage', 'sth_percentage',
                                            'realized_cap', 'market_cap', 'mvrv_ratio', 'supply_in_profit_pct',
                                            'supply_in_loss_pct', 'current_price')}
        t = parse_time(kv(age, 'last_updated'))
        waves = {lbl.strip(): float(p) for lbl, p in WAVE_ROW.findall(age)}
        sizes = [[lbl.strip(), int(c), r2(float(p), 3)] for lbl, c, p in SIZE_ROW.findall(age)]
        rc = g.get('realized_cap')
        ok = bool(rc and rc > 0 and g.get('lth_percentage') is not None and g.get('supply_in_profit_pct') is not None)
        ok = ok and abs((g['lth_percentage'] or 0) + (g['sth_percentage'] or 0) - 100) < 1.5
        ok = ok and abs((g['supply_in_profit_pct'] or 0) + (g['supply_in_loss_pct'] or 0) - 100) < 1.5
        ok = ok and (not waves or abs(sum(waves.values()) - 100) < 2)
        if soft(ok, 'dogdata: возраст монет — данные неполные или не сходятся', 'dd_age'):
            soft_age('dd_age', t, 'dogdata: возраст монет')
            bands = []
            for name, keys in AGE_BANDS:
                vals = [waves[k] for k in keys if k in waves]
                bands.append([name, r2(sum(vals), 2) if vals else None])
            h.update({'asof': iso(t), 'rc': round(rc), 'rp': round(rc / SUPPLY, 8),
                      'mvrv': r2(g.get('mvrv_ratio'), 3), 'mvrvNow': r2(mid * SUPPLY / rc, 3) if mid else None,
                      'profit': r2(g['supply_in_profit_pct'], 1), 'loss': r2(g['supply_in_loss_pct'], 1),
                      'lth': r2(g['lth_percentage'], 1), 'sth': r2(g['sth_percentage'], 1),
                      'ageAvg': round(g['avg_age_days']) if g.get('avg_age_days') else None,
                      'ageMed': round(g['median_age_days']) if g.get('median_age_days') else None,
                      'utxos': int(g['total_utxos']) if g.get('total_utxos') else None, 'ddPrice': g.get('current_price'),
                      'bands': bands, 'sizes': sizes})
            chk(True, f'dogdata: возраст монет и средняя цена — срез {hm(t)}')
    air = raw('dd_airdrop')
    if air:
        a = {k: fnum(kv(air, k)) for k in ('total_recipients', 'still_holding', 'sold_everything', 'retention_rate',
                                            'total_current_balance', 'accumulated', 'diamond_paws', 'paper_hands')}
        t = parse_time(kv(air, 'last_updated'))
        ok = bool(a.get('total_recipients') and a.get('still_holding') is not None)
        ok = ok and abs((a['still_holding'] or 0) + (a.get('sold_everything') or 0) - a['total_recipients']) <= max(5, a['total_recipients'] * 0.01)
        if soft(ok, 'dogdata: аирдроп — данные не сходятся', 'dd_airdrop'):
            soft_age('dd_airdrop', t, 'dogdata: аирдроп')
            h['air'] = {'n': int(a['total_recipients']), 'hold': int(a['still_holding']), 'sold': int(a.get('sold_everything') or 0),
                        'ret': r2(a.get('retention_rate'), 1), 'bal': r2(dog(a['total_current_balance']) / 1e6, 1) if a.get('total_current_balance') else None,
                        'acc': int(a['accumulated']) if a.get('accumulated') is not None else None, 'asof': iso(t)}
    ch = raw('dd_chains')
    if ch:
        t = parse_time(kv(ch, 'last_updated'))
        chains = []
        for c, holders, p, v, liq, sup, ct in CHAIN_ROW.findall(ch):
            chains.append({'c': c, 'h': int(holders), 'p': float(p), 'v': round(float(v)), 'liq': round(float(liq)),
                           'sup': round(float(sup))})
        if soft(bool(chains), 'dogdata: другие сети — нет строк', 'dd_chains'):
            soft_age('dd_chains', t, 'dogdata: другие сети')
            h['chains'] = sorted(chains, key=lambda x: -x['h'])
            h['chAsof'] = iso(t)
    return h or None


def depth(bids, asks, mid, full_b, full_a):
    out = {}
    for key, f in (('d2', .02), ('d5', .05), ('d10', .10), ('d25', .25)):
        lo, hi = mid * (1 - f), mid * (1 + f)
        cov_b = full_b or (bids and bids[-1][0] < lo)
        cov_a = full_a or (asks and asks[-1][0] > hi)
        out[key] = {'b': r2(sum(x[1] for x in bids if x[0] >= lo) / 1e6) if cov_b else None,
                    'a': r2(sum(x[1] for x in asks if x[0] <= hi) / 1e6) if cov_a else None}
    return out


def ladder(bids, asks, mid):
    lo, hi = mid * (1 - LADDER), mid * (1 + LADDER)
    bb, ab = {}, {}
    for p, q, _ in bids:
        if p >= lo:
            k = round(math.floor(p / BUCKET + 1e-9) * BUCKET, 5)
            bb[k] = bb.get(k, 0) + q
    for p, q, _ in asks:
        if p <= hi:
            k = round(math.ceil(p / BUCKET - 1e-9) * BUCKET, 5)
            ab[k] = ab.get(k, 0) + q
    return {'b': [{'p': k, 'q': round(v / 1e6, 3)} for k, v in sorted(bb.items(), reverse=True)],
            'a': [{'p': k, 'q': round(v / 1e6, 3)} for k, v in sorted(ab.items())]}


def walls(levels, mid, side, n=12):
    w = [x for x in levels if x[1] >= WALL_MIN and mid * 0.5 <= x[0] <= mid * 2]
    w = sorted(w, key=lambda x: -x[1])[:n]
    w.sort(key=lambda x: -x[0] if side == 'b' else x[0])
    out = []
    for p, q, ts in w:
        e = {'p': p, 'q': r2(q / 1e6)}
        if ts:
            e['o'] = int(ts if ts < 1e11 else ts / 1e3)
        out.append(e)
    return out


def wall_changes(ex, side, pbook, levels, cur_walls, full, edge, prev_t=None):
    book = {}
    for p, q, _ in levels:
        book[round(p, 9)] = book.get(round(p, 9), 0) + q
    key = 'bids' if side == 'b' else 'asks'
    pedge = ((pbook.get('edge') or {}).get(side)) if isinstance(pbook.get('edge'), dict) else None
    out, prev_ps = [], set()
    prev_list = pbook.get(key) or []
    # прошлый список стенок мог быть обрезан до 12 крупнейших: «новой» считаем только стенку крупнее самой малой из них
    q_floor = min(float(w['q']) for w in prev_list) if len(prev_list) >= 12 else 0.0
    for w in prev_list:
        p0 = round(float(w['p']), 9)
        prev_ps.add(p0)
        inside = full or edge is None or (p0 >= edge if side == 'b' else p0 <= edge)
        if not inside:
            continue
        q1 = book.get(p0, 0) / 1e6
        d = q1 - float(w['q'])
        if abs(d) >= 1.0 and abs(d) >= 0.1 * float(w['q']):
            kind = 'снята' if q1 < 0.5 else ('выросла' if d > 0 else 'уменьшилась')
            out.append({'x': ex, 's': side, 'p': w['p'], 'q0': r2(float(w['q'])), 'q1': r2(q1), 'k': kind})
    for w in cur_walls:
        p = round(w['p'], 9)
        seen = pedge is None or (p >= pedge if side == 'b' else p <= pedge)
        pm = fnum(pbook.get('mid'))
        in_window = pm is None or pm * 0.5 <= p <= pm * 2          # прошлый снимок вообще смотрел на эту цену
        older = prev_t is not None and w.get('o') and w['o'] < prev_t.timestamp()  # Kraken: уровень не менялся с прошлого снимка
        if p not in prev_ps and seen and w['q'] > q_floor and in_window and not older:
            out.append({'x': ex, 's': side, 'p': w['p'], 'q0': None, 'q1': w['q'], 'k': 'новая'})
    gone = [w for w in out if w['k'] == 'снята']
    born = [w for w in out if w['k'] == 'новая']
    for g in sorted(gone, key=lambda w: -w['q0']):
        pair = [b for b in born if abs(b['p'] / g['p'] - 1) <= 0.03 and abs(b['q1'] / g['q0'] - 1) <= 0.35]
        if pair:
            b = min(pair, key=lambda b: abs(b['p'] / g['p'] - 1))
            born.remove(b)
            out.remove(b)
            g.update({'k': 'переставлена', 'p0': g['p'], 'p': b['p'], 'q1': b['q1']})
    return [w for w in out if not (w['k'] == 'переставлена' and abs(w['p'] / w['p0'] - 1) < 0.005
                                   and abs(w['q1'] / w['q0'] - 1) < 0.10)]


# ---------- основной расчёт ----------
def compute(kind):
    os.makedirs(OUT, exist_ok=True)
    prev, prev_id = load_prev(kind)
    if prev is None:
        warns.append('нет прошлого снимка — сравнение недоступно')
    labels = load_labels()
    if not labels:
        warns.append('подписи владельцев не загружены (config/labels)')
    cache = dict((prev or {}).get('entities') or {})
    looked = {}
    for path in glob.glob(os.path.join(RAW, 'entity_*.txt')):
        a = os.path.basename(path)[7:-4]
        t = raw(os.path.basename(path)[:-4])
        if t:
            looked[a] = classify(parse_entity(t))

    def ent(a):
        if a in labels:
            e = labels[a]
            return {'n': e.get('n'), 'k': e.get('k'), 'note': e.get('note', ''), 'note_en': e.get('note_en', '')}
        if a in looked:
            return looked[a]
        if a in cache:
            return cache[a]
        return None

    # --- dogdata: statistics ---
    st = raw('stats')
    stats = {}
    if st:
        stats['holders'] = fnum(kv(st, 'total_holders'))
        stats['t'] = parse_time(kv(st, 'last_updated'))
        stats['top10'] = [(int(r), a, dog(b)) for r, a, b in STATS_ROW.findall(st)]
        fresh('stats', stats['t'], 'dogdata: статистика')
        chk(len(stats['top10']) == 10, f'dogdata: топ-10 из статистики — {len(stats["top10"])} строк', 'stats')
    else:
        chk(False, 'dogdata: статистика — нет данных', 'stats')

    # --- top-100 ---
    rows, lus = {}, {}
    for k in range(1, 5):
        t = raw(f'holders_{k}')
        if not t:
            chk(False, f'топ-100: страница {k} — нет данных', f'holders_{k}')
            continue
        got = [(int(r), a, dog(b), int(u)) for r, a, b, u in HOLDER_ROW.findall(t)]
        exp = set(range((k - 1) * 25 + 1, k * 25 + 1))
        if not ({g[0] for g in got} == exp and len(got) == 25):
            chk(False, f'топ-100: страница {k} — {len(got)} строк вместо 25', f'holders_{k}')
        lus[k] = parse_time(kv(t, 'last_updated'))
        for g in got:
            if g[0] in exp:
                rows[g[0]] = g
    top = [rows[r] for r in range(1, 101) if r in rows]
    lu_vals = [v for v in lus.values() if v]
    hold_t = max(set(lu_vals), key=lu_vals.count) if lu_vals else None
    odd = [k for k, v in lus.items() if v != hold_t]
    if odd:
        chk(False, 'топ-100: страницы из разных срезов (' + ', '.join(map(str, odd)) + ')', [f'holders_{k}' for k in odd])
    fresh('holders', hold_t, 'dogdata: топ-100')
    ok100 = len(top) == 100 and len({x[1] for x in top}) == 100
    ok100 = ok100 and all(top[i][2] >= top[i + 1][2] - 1e-6 for i in range(len(top) - 1))
    chk(ok100, f'топ-100: {len(top)} строк, места 1–100, по убыванию' if ok100 else
        f'топ-100: {len(top)} строк — порядок/полнота нарушены', None if ok100 else [f'holders_{k}' for k in range(1, 5)])
    if stats.get('top10') and len(top) >= 10:
        same_cut = stats.get('t') and hold_t and abs((stats['t'] - hold_t).total_seconds()) < 60
        mism = [r for r, a, b in stats['top10'] if r <= len(top) and (top[r - 1][1] != a or abs(top[r - 1][2] - b) > 1e4)]
        if same_cut:
            chk(not mism, 'топ-10 совпадает в двух источниках' if not mism else f'топ-10 расходится с топ-100: места {mism}',
                None if not mism else ['stats', 'holders_1'])
        elif mism:
            warns.append('топ-10 из статистики и топ-100 из разных срезов — расхождение мест ' + ', '.join(map(str, mism)))

    # --- концентрация ---
    ct = raw('conc')
    conc = {}
    if ct:
        conc = {k: fnum(kv(ct, k)) for k in ('top10_supply_pct', 'top100_supply_pct', 'top1000_supply_pct', 'gini_coefficient', 'total_holders')}
        conc['t'] = parse_time(kv(ct, 'last_updated'))
        fresh('conc', conc['t'], 'dogdata: концентрация')
    else:
        chk(False, 'dogdata: концентрация — нет данных', 'conc')
    top10pct = sum(x[2] for x in top[:10]) / SUPPLY * 100 if len(top) >= 10 else None
    top100pct = sum(x[2] for x in top) / SUPPLY * 100 if len(top) == 100 else None
    if top100pct is not None and conc.get('top100_supply_pct') is not None:
        tol = 0.2 if conc.get('t') and hold_t and abs((conc['t'] - hold_t).total_seconds()) < 5400 else 0.5
        d10 = abs(top10pct - conc['top10_supply_pct']) if conc.get('top10_supply_pct') is not None else 0
        d100 = abs(top100pct - conc['top100_supply_pct'])
        okc = d10 <= tol and d100 <= tol
        chk(okc, f'доли топ-10/топ-100 сходятся с концентрацией (±{tol} п.п.)' if okc else
            f'доли расходятся: топ-100 {top100pct:.2f}% против {conc["top100_supply_pct"]:.2f}%', None if okc else 'conc')
    holders = stats.get('holders') or conc.get('total_holders')

    # --- площадки ---
    mt = raw('markets')
    markets, venues = {}, []
    if mt:
        markets = {k: fnum(kv(mt, k)) for k in ('price', 'totalVolume', 'marketCap', 'priceChange24h')}
        markets['t'] = parse_time(kv(mt, 'last_updated'))
        for n, pair, p, v in MARKET_ROW.findall(mt):
            venues.append({'n': n.strip(), 'pair': pair, 'p': float(p), 'v': round(float(v))})
        fresh('markets', markets['t'], 'dogdata: площадки')
        chk(len(venues) >= 5, f'площадки: {len(venues)} шт', 'markets')
    else:
        chk(False, 'dogdata: площадки — нет данных', 'markets')

    # --- стаканы ---
    all_levels = {}
    for ex, files in BOOK_FILES.items():
        label = EXN[ex]
        parsed = {nm: parse_book(nm) for nm in files}
        if any(v is None for v in parsed.values()):
            chk(False, f'{label}: стакан — нет данных', list(files))
            continue
        if ex == 'kraken':
            bids, asks = parsed['kraken_bids']['bids'], parsed['kraken_asks']['asks']
        else:
            bids, asks = parsed[files[0]]['bids'], parsed[files[0]]['asks']
        if not bids or not asks:
            chk(False, f'{label}: стакан пустой', list(files))
            continue
        tss = []
        for nm, bk in parsed.items():
            if TS_KEY.get(nm):
                t = parse_time(kv(bk['text'], TS_KEY[nm]))
                fresh(nm, t, f'{label}: стакан' + (' (покупки)' if nm.endswith('_bids') else ' (продажи)' if nm.endswith('_asks') else ''))
                if t:
                    tss.append(t)
            nb, na = bk['decl']
            if ex == 'kraken':
                side = 'bids' if nm.endswith('_bids') else 'asks'
                if nb is not None and abs(nb - len(bk[side])) > 2:
                    chk(False, f'{label}: строк {len(bk[side])} из {nb} — ответ обрезан', nm)
            else:
                nzb = 1 if bk['zero_bid'] else 0
                if (nb is not None and abs(nb - len(bk['bids']) - nzb) > 2) or (na is not None and abs(na - len(bk['asks'])) > 2):
                    chk(False, f'{label}: строк {len(bk["bids"])}/{len(bk["asks"])} из {nb}/{na} — ответ обрезан', nm)
        if ex == 'kraken':
            full_b = len(bids) < REQ_ROWS['kraken_bids']
            full_a = len(asks) < REQ_ROWS['kraken_asks']
        else:
            nm = files[0]
            full_b = parsed[nm]['zero_bid'] or len(bids) < REQ_ROWS[nm] - (1 if ex == 'gate' else 0)
            full_a = len(asks) < REQ_ROWS[nm]
        all_levels[ex] = {'bids': bids, 'asks': asks, 'full_b': full_b, 'full_a': full_a,
                          'bid': bids[0][0], 'ask': asks[0][0], 't': max(tss) if tss else None}

    gt = raw('gate_ticker')
    gate_tk = {}
    if gt:
        gate_tk = {k: fnum(kv(gt, k)) for k in ('last', 'highest_bid', 'lowest_ask', 'change_percentage', 'quote_volume', 'high_24h', 'low_24h')}
        if 'gate' in all_levels and gate_tk.get('highest_bid') and gate_tk.get('lowest_ask'):
            all_levels['gate']['bid'], all_levels['gate']['ask'] = gate_tk['highest_bid'], gate_tk['lowest_ask']

    mids = {ex: (v['bid'] + v['ask']) / 2 for ex, v in all_levels.items() if v['bid'] < v['ask']}
    for ex, v in all_levels.items():
        if not v['bid'] < v['ask']:
            chk(False, f'{EXN[ex]}: лучшая покупка ≥ лучшей продажи — данные битые', list(BOOK_FILES[ex]))
    core = {ex: m for ex, m in mids.items() if ex in ('kraken', 'gate', 'mexc', 'bingx')} or mids
    mid = median(core.values()) if core else markets.get('price')
    if mids and mid:
        bad = {ex: m for ex, m in mids.items() if abs(m / mid - 1) > 0.03}
        if markets.get('price') and abs(markets['price'] / mid - 1) > 0.03:
            warns.append(f'цена dogdata {fp(markets["price"])} отличается от бирж ({fp(mid)}) больше чем на 3%')
        spread = (max(v for e, v in mids.items() if e not in bad) / min(v for e, v in mids.items() if e not in bad) - 1) * 100 \
            if len(mids) > len(bad) else 0
        chk(not bad, f'цены бирж сходятся (разброс {spread:.1f}%)' if not bad else
            'цены расходятся >3%: ' + ', '.join(EXN[e] for e in bad), None if not bad else [f for e in bad for f in BOOK_FILES[e]])
        for e in bad:
            warns.append(f'{EXN[e]}: цена {fp(mids[e])} отличается от средней {fp(mid)} — стакан этой биржи показан, но в итоги не входит')

    pw = (prev or {}).get('books', {})
    books, walls_delta = {}, []
    for ex, v in all_levels.items():
        m = mids.get(ex, mid)
        bids, asks = v['bids'], v['asks']
        wb, wa = walls(bids, m, 'b'), walls(asks, m, 'a')
        edge_b = None if v['full_b'] else bids[-1][0]
        edge_a = None if v['full_a'] else asks[-1][0]
        books[ex] = {'bid': v['bid'], 'ask': v['ask'], 'mid': round(m, 9), 'asof': hm(v['t']) if v['t'] else None,
                     'ats': int(v['t'].timestamp()) if v['t'] else None,
                     'rows': {'b': len(bids), 'a': len(asks)}, 'edge': {'b': edge_b, 'a': edge_a},
                     'bids': wb, 'asks': wa, 'ladder': ladder(bids, asks, mid or m), **depth(bids, asks, m, v['full_b'], v['full_a'])}
        if mids and mid and abs(m / mid - 1) > 0.03:
            books[ex]['off'] = 1
        books[ex]['cmp'] = bool(ex in pw and not pw[ex].get('nowalls'))
        if books[ex]['cmp']:
            prev_t = parse_time((prev or {}).get('ts'))
            walls_delta += wall_changes(ex, 'b', pw[ex], bids, wb, v['full_b'], edge_b, prev_t)
            walls_delta += wall_changes(ex, 'a', pw[ex], asks, wa, v['full_a'], edge_a, prev_t)
    if 'gate' in books and gate_tk:
        books['gate'].update({'last': gate_tk.get('last'), 'chg24': gate_tk.get('change_percentage'),
                              'vol24usd': gate_tk.get('quote_volume'), 'low24': gate_tk.get('low_24h'), 'high24': gate_tk.get('high_24h')})
    walls_delta.sort(key=lambda w: -(max(w['q0'] or 0, w['q1'] or 0) if w['k'] in ('новая', 'снята', 'переставлена') else abs(w['q1'] - w['q0'])))
    totals = {}
    for key in ('d5', 'd10', 'd25'):
        b = [bk[key]['b'] for bk in books.values() if not bk.get('off') and bk[key]['b'] is not None]
        a = [bk[key]['a'] for bk in books.values() if not bk.get('off') and bk[key]['a'] is not None]
        totals[key] = {'b': r2(sum(b)), 'a': r2(sum(a)), 'n': len(b)}

    # --- BTC ---
    bt = raw('btc')
    btc = fnum(kv(bt, 'price')) if bt else None
    bt_t = parse_time(kv(bt, 'time')) if bt else None
    if bt:
        fresh('btc', bt_t, 'BTC (Coinbase)')
        chk(btc is not None and 10000 < btc < 1000000, f'BTC {thou(btc)}$', 'btc')
    else:
        chk(False, 'BTC — нет данных', 'btc')

    # --- топ-100: владельцы и изменения ---
    prev_top = {x['a']: x for x in (prev or {}).get('top100', [])}
    entities = {}
    top100 = []
    for r, a, b, u in top:
        e = {'r': r, 'a': a, 'b': round(b / 1e6, 3), 'u': u}
        who = ent(a)
        if who:
            e['n'], e['k'] = who['n'], who['k']
            if who.get('note'):
                e['nt'] = who['note']
            if who.get('note_en'):
                e['nt_en'] = who['note_en']
            entities[a] = {'n': who['n'], 'k': who['k'], 'note': who.get('note', '')}
            if who.get('note_en'):
                entities[a]['note_en'] = who['note_en']
        else:
            e['n'], e['k'] = 'Крупный холдер', 'unknown'
            if a not in lookup:
                lookup.append(a)
        if a in prev_top:
            e['d'] = round(b / 1e6 - float(prev_top[a]['b']), 3)
            e['r0'] = prev_top[a].get('r')
        elif prev:
            e['d'] = None
            e['new'] = 1
        top100.append(e)
    cur_addrs = {x['a'] for x in top100}
    movers = {'up': [], 'down': [], 'new': [], 'out': []}

    def mini(x):
        return {'r': x['r'], 'a': x['a'], 'd': x['d'], 'n': x['n'], 'k': x['k']}
    if prev:
        ch = [x for x in top100 if x.get('d') is not None and abs(x['d']) >= MOVE_MIN]
        movers['up'] = [mini(x) for x in sorted(ch, key=lambda x: -x['d']) if x['d'] > 0][:8]
        movers['down'] = [mini(x) for x in sorted(ch, key=lambda x: x['d']) if x['d'] < 0][:8]
        movers['new'] = [{'r': x['r'], 'a': x['a'], 'b': x['b'], 'n': x['n'], 'k': x['k']} for x in top100 if x.get('new')]
        movers['out'] = [{'r0': x.get('r'), 'a': a, 'b0': x['b'], 'n': x.get('n'), 'k': x.get('k')}
                         for a, x in prev_top.items() if a not in cur_addrs]
    by = {}
    for x in top100:
        if x['k'] in EXCHANGE_KINDS:
            g = by.setdefault(x['n'], {'n': x['n'], 'k': x['k'], 'bal': 0.0, 'd': 0.0, 'cnt': 0, 'known': True})
            g['bal'] += x['b']
            g['cnt'] += 1
            if x.get('d') is not None:
                g['d'] += x['d']
            elif prev:
                g['known'] = False
    exch_by = sorted(({'n': g['n'], 'k': g['k'], 'bal': round(g['bal'], 2), 'cnt': g['cnt'],
                       'd': round(g['d'], 2) if prev and g['known'] else None} for g in by.values()), key=lambda g: -g['bal'])
    exch = {'by': exch_by, 'bal': round(sum(g['bal'] for g in exch_by), 2),
            'd': round(sum(g['d'] for g in exch_by if g['d'] is not None), 2) if prev else None,
            'pct': r2(sum(g['bal'] for g in exch_by) * 1e6 / SUPPLY * 100, 2)}

    # --- переводы от 5M ---
    wt = raw('whales')
    wt_t = None
    flows = {'toExch': None, 'fromExch': None, 'net': None, 'count': None, 'byEx': [], 'big': []}
    if wt:
        alerts = []
        for ts, q, fr, to, tx in WHALE_ROW.findall(wt):
            t = parse_time(ts)
            if t and t >= NOW - dt.timedelta(hours=24):
                alerts.append((t, dog(q), fr, to, tx))
        wt_t = parse_time(kv(wt, 'timestamp'))
        fresh('whales', wt_t, 'dogdata: переводы ≥5M')
        declared = fnum(kv(wt, 'total_alerts'))
        n_all = len(WHALE_ROW.findall(wt))
        chk(declared is None or int(declared) == n_all, f'переводы: {n_all} из {int(declared) if declared is not None else "?"}',
            None if declared is None or int(declared) == n_all else 'whales')
        rank = {x['a']: x['r'] for x in top100}
        exb = {}
        to_x = from_x = 0.0
        big = []
        for t, q, fr, to, tx in sorted(alerts, key=lambda x: -x[1]):
            fe, te = ent(fr), ent(to)
            for a, e in ((fr, fe), (to, te)):
                if e:
                    entities[a] = {'n': e['n'], 'k': e['k'], 'note': e.get('note', '')}
                elif a not in lookup and re.fullmatch(ADDR, a):
                    lookup.insert(0, a)
            fx = bool(fe and fe['k'] in EXCHANGE_KINDS)
            tx_ = bool(te and te['k'] in EXCHANGE_KINDS)
            if tx_ and not fx:
                to_x += q
                exb.setdefault(te['n'], [0.0, 0.0])[0] += q
                typ = 'на биржу'
            elif fx and not tx_:
                from_x += q
                exb.setdefault(fe['n'], [0.0, 0.0])[1] += q
                typ = 'с биржи'
            elif fx and tx_:
                typ = 'между биржами'
            else:
                typ = 'между кошельками'
            big.append({'t': t.strftime('%d.%m %H:%M'), 'ts': int(t.timestamp()), 'q': r2(q / 1e6), 'from': fr, 'to': to,
                        'fr': rank.get(fr), 'tr': rank.get(to), 'fn': fe['n'] if fe else 'Крупный холдер', 'fk': fe['k'] if fe else 'unknown',
                        'tn': te['n'] if te else 'Крупный холдер', 'tk': te['k'] if te else 'unknown', 'typ': typ, 'tx': tx or ''})
        flows = {'toExch': r2(to_x / 1e6), 'fromExch': r2(from_x / 1e6), 'net': r2((to_x - from_x) / 1e6), 'count': len(alerts),
                 'byEx': [{'n': n, 'in': r2(v[0] / 1e6), 'out': r2(v[1] / 1e6)} for n, v in sorted(exb.items(), key=lambda kv_: -(kv_[1][0] + kv_[1][1]))],
                 'big': big[:15]}
    else:
        chk(False, 'dogdata: переводы — нет данных', 'whales')

    # --- график Kraken и «здоровье холдеров» (необязательные источники) ---
    chart = build_chart(books)
    health = build_health(mid)

    # --- сборка ---
    price = {'mid': round(mid, 9) if mid else None, 'cap': r2(mid * SUPPLY / 1e6, 1) if mid else None,
             'chg24': r2(markets.get('priceChange24h') if markets.get('priceChange24h') is not None else gate_tk.get('change_percentage')),
             'vol24': markets.get('totalVolume'), 'dogdata': markets.get('price')}
    names = {EXN[ex] for ex in books}
    vol_all = sum(v['v'] for v in venues) or None
    price['cov'] = r2(sum(v['v'] for v in venues if v['n'] in names) / vol_all * 100, 0) if vol_all else None
    delta = {}
    if prev:
        pm = (prev.get('price') or {}).get('mid')
        delta = {'price': r2((mid / pm - 1) * 100, 1) if mid and pm else None,
                 'holders': int(holders - prev['holders']) if holders and prev.get('holders') else None,
                 'top100pct': r2(top100pct - prev['top100pct'], 3) if top100pct is not None and prev.get('top100pct') is not None else None,
                 'top10pct': r2(top10pct - prev['top10pct'], 3) if top10pct is not None and prev.get('top10pct') is not None else None}
    snap_id = NOW.strftime('%Y-%m-%dT%H%MZ')
    stale = [c for c in checks if not c['ok'] and not c['t'].startswith('Kraken: свечи')
             and (' — возраст ' in c['t'] or 'нет метки' in c['t'] or 'нет данных' in c['t'])]
    s = {
        'v': 4, 'id': snap_id, 'ts': iso(NOW), 'label': NOW.strftime('%d.%m · %H:%M UTC'), 'kind': kind,
        'fresh': not stale, 'pipeline': VERSION, 'btc': round(btc) if btc else None,
        'price': price, 'venues': venues, 'books': books, 'totals': totals, 'wallsDelta': walls_delta[:16],
        'holders': int(holders) if holders else None, 'holdersAsof': hm(hold_t),
        'top10pct': r2(top10pct, 3), 'top100pct': r2(top100pct, 3), 'top100Asof': hm(hold_t),
        'conc': {'top10': conc.get('top10_supply_pct'), 'top100': conc.get('top100_supply_pct'),
                 'top1000': conc.get('top1000_supply_pct'), 'gini': conc.get('gini_coefficient')},
        'top100': top100, 'movers': movers, 'exch': exch, 'flows': flows, 'delta': delta, 'entities': entities,
        'prevId': prev_id, 'prevTs': (prev or {}).get('ts'), 'prevLabel': (prev or {}).get('label'), 'prevKind': (prev or {}).get('kind'),
        'checks': checks, 'warnings': warns, 'brief': '', 'report': '', 'chart': chart, 'health': health,
        'srcTs': {'top100': iso(hold_t), 'stats': iso(stats.get('t')), 'conc': iso(conc.get('t')),
                  'markets': iso(markets.get('t')), 'whales': iso(wt_t), 'btc': iso(bt_t),
                  'ohlc': (chart or {}).get('asof'), 'health': (health or {}).get('asof')}}
    s["alerts"] = highlights(s)
    s['report'] = report(s)
    snap_path = os.path.join(OUT, 'snapshot.json')
    json.dump(s, open(snap_path, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    open(os.path.join(OUT, 'report.md'), 'w', encoding='utf-8').write(s['report'])
    # компактная строка истории
    def biggest(side, lim):
        best = None
        for ex, b in books.items():
            if b.get('off'):
                continue
            for w in b['bids' if side == 'b' else 'asks']:
                if mid and abs(w['p'] / mid - 1) <= lim and (best is None or w['q'] > best['q']):
                    best = {'x': ex, 'p': w['p'], 'q': w['q']}
        return best
    hist = {'id': snap_id, 'ts': iso(NOW), 'label': s['label'], 'kind': kind, 'fresh': s['fresh'],
            'mid': price['mid'], 'chg24': price['chg24'], 'cap': price['cap'], 'btc': s['btc'],
            'b5': totals['d5']['b'], 'a5': totals['d5']['a'], 'b10': totals['d10']['b'], 'a10': totals['d10']['a'],
            'exBal': exch['bal'], 'exD': exch['d'], 't100': s['top100pct'], 'holders': s['holders'],
            'fIn': flows.get('toExch'), 'fOut': flows.get('fromExch'), 'fCnt': flows.get('count'),
            'bw': biggest('b', 0.25), 'aw': biggest('a', 0.25), 'prevId': prev_id,
            'rp': (health or {}).get('rp'), 'mvrv': (health or {}).get('mvrvNow'),
            'profit': (health or {}).get('profit'), 'lth': (health or {}).get('lth')}
    hist_path = os.path.join(OUT, 'hist.json')
    json.dump(hist, open(hist_path, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    writes = []
    if kind in ('утро', 'база', 'запрос'):
        writes.append({'op': 'set', 'collection': 'snapshots', 'doc_id': snap_id, 'file_path': snap_path})
    writes.append({'op': 'set', 'collection': 'live', 'doc_id': 'current', 'file_path': snap_path})
    writes.append({'op': 'set', 'collection': 'hist', 'doc_id': snap_id, 'file_path': hist_path})
    json.dump(writes, open(os.path.join(OUT, 'writes.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(s['report'])
    print('\n---')
    print(f'SNAPSHOT_ID={snap_id}')
    print(f'PREV={prev_id or "нет"}')
    print('ALERTS: ' + (' | '.join(s['alerts']) if s['alerts'] else 'нет'))
    print(f'CHECKS={sum(c["ok"] for c in checks)}/{len(checks)}')
    for c in checks:
        if not c['ok']:
            print('  FAIL:', c['t'])
    for w in warns:
        print('  WARN:', w)
    print('REFETCH: ' + (' '.join(refetch) if refetch else 'нет'))
    todo = [a for a in lookup if not os.path.exists(os.path.join(RAW, f'entity_{a}.txt'))][:12]
    print('LOOKUP: ' + (' '.join(todo) if todo else 'нет'))
    print(f'WRITES: {len(writes)} → out/writes.json ({", ".join(w["collection"] + "/" + w["doc_id"] for w in writes)})')


# ---------- отчёт (личный, в пуш) ----------
def who(n, k, r=None):
    if k == 'private':
        return f"холдер{' №' + str(r) if r else ''}"
    if k == 'unknown':
        return f"крупный холдер{' №' + str(r) if r else ''}"
    return n


def report(s):
    L = []
    pr = s['price']
    status = '✅ данные свежие' if s['fresh'] else '⚠️ часть данных устарела'
    L.append(f"**DOG · {s['label']}** · {status}")
    dp = (s.get('delta') or {}).get('price')
    L.append(f"Цена **{fp(pr['mid'])}** (кап ≈{pr['cap']}M$) · 24ч {sgn(pr.get('chg24'), 1, '%')}"
             + (f" · с прошлой сводки {sgn(dp, 1, '%')}" if dp is not None else '') + f" · BTC {thou(s.get('btc'))}$")
    if s.get('brief'):
        L.append(f"**Вывод:** {s['brief']}")
    L.append('')
    L.append('| Стакан, млн DOG | Покупки | Продажи | Крупнейшая стенка |')
    L.append('|---|---|---|---|')
    for ex, name in EXCHANGES:
        b = s['books'].get(ex)
        if not b:
            L.append(f'| {name} | нет данных | — | — |')
            continue
        band, d = '±10%', b['d10']
        if d['b'] is None or d['a'] is None:
            band, d = '±5%', b['d5']
        if d['b'] is None or d['a'] is None:
            band, d = '±2%', b['d2']
        allw = [('пок.', 'b', w) for w in b['bids']] + [('прод.', 'a', w) for w in b['asks']]
        big = max(allw, key=lambda x: x[2]['q']) if allw else None
        bigs = f"{big[2]['q']:.1f} {big[0]} {fp(big[2]['p'])}" if big else 'нет ≥5M'
        if big and s.get('prevId') and b.get('cmp'):
            ch = next((w for w in s.get('wallsDelta') or [] if w['x'] == ex and w['s'] == big[1] and w['p'] == big[2]['p']), None)
            bigs += ' (=)' if ch is None else (' (новая)' if ch['k'] == 'новая' else
                                                (' (переставлена)' if ch['k'] == 'переставлена' else f" ({sgn(ch['q1'] - ch['q0'], 1)})"))
        bv = '—' if d['b'] is None else f"{d['b']:.1f}"
        av = '—' if d['a'] is None else f"{d['a']:.1f}"
        L.append(f"| {name} ({band}){' ⚠️' if b.get('off') else ''} | {bv} | {av} | {bigs} |")
    tt = (s.get('totals') or {}).get('d10') or {}
    if tt:
        L.append(f"| **Все биржи (±10%)** | **{tt.get('b') or 0:.1f}** | **{tt.get('a') or 0:.1f}** | |")
    wd = s.get('wallsDelta') or []
    if s.get('prevId'):
        if wd:
            parts = []
            for w in wd[:5]:
                nm = EXN.get(w['x'], w['x'])
                sd = 'пок.' if w['s'] == 'b' else 'прод.'
                if w['k'] == 'новая':
                    parts.append(f"{nm}: новая {w['q1']:.1f} {sd} {fp(w['p'])}")
                elif w['k'] == 'снята':
                    parts.append(f"{nm}: снята {w['q0']:.1f} {sd} {fp(w['p'])}")
                elif w['k'] == 'переставлена':
                    parts.append(f"{nm}: {w['q0']:.1f}→{w['q1']:.1f} {sd} переставили {fp(w['p0'])}→{fp(w['p'])}")
                else:
                    parts.append(f"{nm}: {fp(w['p'])} {sd} {w['q0']:.1f}→{w['q1']:.1f}")
            L.append('Стенки с прошлой сводки: ' + '; '.join(parts))
        else:
            L.append('Стенки с прошлой сводки: без заметных изменений')
    L.append('')
    ex = s.get('exch') or {}
    since = f"Δ с {s['prevLabel']}" if s.get('prevLabel') else 'Δ'
    if ex.get('by'):
        L.append(f'| DOG на биржах, млн | Баланс | {since} |')
        L.append('|---|---|---|')
        for g in ex['by']:
            L.append(f"| {g['n']} | {thou(g['bal'])} | {sgn(g.get('d'), 1)} |")
        L.append(f"| **Всего ({ex.get('pct')}% эмиссии)** | **{thou(ex.get('bal'))}** | **{sgn(ex.get('d'), 1)}** |")
    dl = s.get('delta') or {}
    L.append(f"Топ-100: {s['top100pct']:.2f}% эмиссии ({sgn(dl.get('top100pct'), 2, ' п.п.')}) · холдеры {thou(s.get('holders'))} ({sgn(dl.get('holders'), 0) if dl.get('holders') is not None else '—'})"
             if s.get('top100pct') is not None else 'Топ-100: нет данных')
    hl = s.get('health') or {}
    if hl.get('rp'):
        mid_now = (s.get('price') or {}).get('mid')
        ratio = (hl['rp'] / mid_now) if mid_now else None
        cmp_txt = '' if not ratio else (f' — цена сейчас в {ratio:.1f} раза ниже' if ratio >= 1.05 else
                                       (f' — цена сейчас в {1 / ratio:.1f} раза выше' if ratio <= 0.95 else ' — цена сейчас около неё'))
        band = next((b for b in hl.get('bands') or [] if b[0] == 'больше года'), None)
        L.append(f"Холдеры (DOG DATA, {hm(parse_time(hl.get('asof')))}): в прибыли {hl.get('profit')}% монет"
                 + (f" · лежат больше года {band[1]:.1f}%" if band and band[1] is not None else '')
                 + f" · средняя цена монет {fp(hl['rp'])}${cmp_txt}")
    if (hl.get('air') or {}).get('n'):
        a = hl['air']
        L.append(f"Аирдроп: из {thou(a['n'])} получателей держат {thou(a['hold'])} ({a.get('ret')}%)")
    chs = s.get('chart') or {}
    if chs.get('chg'):
        c = chs['chg']
        parts = [f"{k} {sgn(c.get(key), 1, '%')}" for k, key in (('24ч', '1d'), ('7д', '7d'), ('30д', '30d'), ('1г', '1y')) if c.get(key) is not None]
        line = 'Kraken: ' + ' · '.join(parts)
        if chs.get('hi'):
            line += (f" · за {chs.get('days')} дн. макс. {fp(chs['hi'])} ({dt.datetime.fromtimestamp(chs['hiT'], dt.timezone.utc):%d.%m.%y}),"
                     f" мин. {fp(chs['lo'])} ({dt.datetime.fromtimestamp(chs['loT'], dt.timezone.utc):%d.%m.%y})")
        L.append(line)
    mv = s.get('movers') or {}
    if s.get('prevId'):
        up = ', '.join(f"{who(x['n'], x['k'], x['r'])} {short(x['a'])} {sgn(x['d'], 1, 'M')}" for x in mv.get('up', [])[:4]) or 'нет'
        dn = ', '.join(f"{who(x['n'], x['k'], x['r'])} {short(x['a'])} {sgn(x['d'], 1, 'M')}" for x in mv.get('down', [])[:4]) or 'нет'
        L.append(f'Набрали ≥5M: {up} · Сбросили ≥5M: {dn}')
        if mv.get('new') or mv.get('out'):
            nw = ', '.join(f"№{x['r']} {who(x['n'], x['k'])} {short(x['a'])} {x['b']:.1f}M" for x in mv.get('new', [])[:3]) or 'нет'
            ou = ', '.join(f"{short(x['a'])} (было №{x['r0']})" for x in mv.get('out', [])[:3]) or 'нет'
            L.append(f'Новые в топ-100: {nw} · Вышли: {ou}')
    fl = s.get('flows') or {}
    if fl.get('count') is not None:
        m = (s.get('price') or {}).get('mid') or 0

        def usd(q):
            return f" (≈${q * m * 1e3:.0f}K)" if m and q else ''
        byx = ', '.join(f"{g['n']} {sgn((g['in'] or 0) - (g['out'] or 0), 1)}" for g in fl.get('byEx', [])[:4])
        line = (f"Переводы ≥5M за 24ч: {fl['count']} шт · на биржи {fl['toExch']:.1f}M{usd(fl['toExch'])} · с бирж {fl['fromExch']:.1f}M{usd(fl['fromExch'])}"
                + (f" · по биржам: {byx}" if byx else ''))
        if fl.get('big'):
            b = fl['big'][0]
            line += f" · крупнейший {b['q']:.1f}M: {who(b['fn'], b['fk'], b.get('fr'))} → {who(b['tn'], b['tk'], b.get('tr'))}"
        L.append(line)
    ok = sum(c['ok'] for c in s['checks'])
    bad = [c['t'] for c in s['checks'] if not c['ok']]
    line = f"Проверка: {ok}/{len(s['checks'])} " + ('✅' if not bad else '⚠️ ' + '; '.join(bad[:3]))
    if s.get('warnings'):
        line += ' · ' + '; '.join(s['warnings'][:2])
    L.append(line)
    if DASH:
        L.append(f'[Дашборд]({DASH})')
    return '\n'.join(L)


# ---------- «Главное»: короткое утреннее сообщение ----------
def ru(x, d=1):
    """1234.5 → «1 234,5»"""
    if x is None:
        return '—'
    s = f'{abs(x):,.{d}f}'.replace(',', ' ').replace('.', ',')
    return ('−' if x < 0 else '') + s


def rsgn(x, d=1):
    if x is None:
        return '—'
    r = round(x, d)
    return '±0' if r == 0 else ('+' if r > 0 else '−') + ru(abs(r), d)


def rprice(p):
    return '—' if p is None else fp(p).replace('.', ',') + ' $'


def rmln(q, sign=False):
    """q в млн DOG → «38,5 млн», «164 млн», «1,7 млрд»"""
    a = abs(q)
    t = ru(a / 1000, 1) + ' млрд' if a >= 1000 else ru(a, 1 if a < 100 else 0) + ' млн'
    return (('+' if q > 0 else '−') + t) if sign else t


def rusd(q, price):
    v = abs(q) * 1e6 * (price or 0)
    if not v:
        return ''
    return f'≈{ru(v / 1e6, 1)} млн $' if v >= 1e6 else f'≈{ru(v / 1e3, 0)} тыс. $'


def cap1(t):
    return t[:1].upper() + t[1:] if t else t


def highlights(s):
    """Только крупное (пороги ALERT_* в начале файла): цена, стенки, биржи, переводы, крупные холдеры, топ-100."""
    out = []
    pr = s.get('price') or {}
    mid, c24 = pr.get('mid'), pr.get('chg24')
    if c24 is not None and abs(c24) >= ALERT_PRICE:
        out.append(f"{'📈' if c24 > 0 else '📉'} Цена за сутки {rsgn(c24)}%")
    if not s.get('prevId'):
        return out
    t, prev_t = parse_time(s.get('ts')), parse_time(s.get('prevTs'))
    long_gap = bool(t and prev_t and t - prev_t > dt.timedelta(hours=30))
    side_n = {'b': 'покупку', 'a': 'продажу'}

    def dist(p):
        if not mid:
            return ''
        d = (p / mid - 1) * 100
        return ', у самой цены' if abs(d) < 0.5 else f' ({rsgn(d, 0)}% от цены)'
    # стаканы: появилась, исчезла или заметно изменилась крупная заявка
    k = 0
    for w in s.get('wallsDelta') or []:
        q0, q1, p = float(w.get('q0') or 0), float(w.get('q1') or 0), float(w['p'])
        if max(q0, q1) < ALERT_WALL or (mid and abs(p / mid - 1) > ALERT_WALL_BAND):
            continue
        if w['k'] in ('выросла', 'уменьшилась') and abs(q1 - q0) < ALERT_WALL_D:
            continue
        ex, sd = EXN.get(w['x'], w['x']), side_n.get(w['s'], '')
        if w['k'] == 'новая':
            line = f"🧱 {ex}: новая заявка на {sd} {rmln(q1)} DOG по {rprice(p)}{dist(p)}, {rusd(q1, p)}"
        elif w['k'] == 'снята':
            line = f"🧱 {ex}: снята заявка на {sd} {rmln(q0)} DOG по {rprice(p)}"
        elif w['k'] == 'переставлена':
            line = f"🧱 {ex}: заявку на {sd} {rmln(q1)} DOG переставили с {rprice(float(w.get('p0') or p))} на {rprice(p)}{dist(p)}"
        else:
            line = f"🧱 {ex}: заявка на {sd} по {rprice(p)} {'выросла' if q1 > q0 else 'уменьшилась'}: {ru(q0, 1)} → {rmln(q1)} DOG"
        out.append(line)
        k += 1
        if k >= 4:
            break
    # биржи: баланс с прошлой сводки и переводы за сутки
    fl = s.get('flows') or {}
    byf = {g['n']: g for g in fl.get('byEx') or []}
    done = set()
    for g in (s.get('exch') or {}).get('by') or []:
        d = g.get('d')
        if d is None or abs(d) < ALERT_EXCH:
            continue
        f = byf.get(g['n']) or {}
        day = (f.get('in') if d > 0 else f.get('out')) or 0
        extra = f" (за последние сутки — {rmln(day)})" if long_gap and day >= MOVE_MIN else ''
        out.append(f"🔺 {g['n']}: на биржу пришло {rmln(d)} DOG{extra}" if d > 0 else
                   f"🔻 {g['n']}: с биржи ушло {rmln(-d)} DOG{extra}")
        done.add(g['n'])
    for n, f in byf.items():
        if n in done:
            continue
        if (f.get('in') or 0) >= ALERT_FLOW:
            out.append(f"🔺 {n}: на биржу за сутки пришло {rmln(f['in'])} DOG")
        if (f.get('out') or 0) >= ALERT_FLOW:
            out.append(f"🔻 {n}: с биржи за сутки ушло {rmln(f['out'])} DOG")
    # крупные переводы между кошельками
    k = 0
    for b in fl.get('big') or []:
        if b.get('typ') == 'между кошельками' and (b.get('q') or 0) >= ALERT_FLOW:
            out.append(f"🐋 Перевод {rmln(b['q'])} DOG: {who(b['fn'], b['fk'], b.get('fr'))} → {who(b['tn'], b['tk'], b.get('tr'))}, {b['t']} UTC")
            k += 1
            if k >= 2:
                break
    # крупные холдеры (не биржи)
    mv = s.get('movers') or {}
    bal = {x['a']: x['b'] for x in s.get('top100') or []}
    k = 0
    for x in sorted((mv.get('up') or []) + (mv.get('down') or []), key=lambda x: -abs(x.get('d') or 0)):
        if x.get('k') in EXCHANGE_KINDS or x.get('d') is None or abs(x['d']) < ALERT_HOLDER:
            continue
        now = bal.get(x['a'])
        out.append(f"🐋 {cap1(who(x['n'], x['k'], x['r']))}: {'набрал' if x['d'] > 0 else 'сбросил'} {rmln(abs(x['d']))} DOG"
                   + (f", теперь {rmln(now)}" if now else ''))
        k += 1
        if k >= 3:
            break
    new, gone = mv.get('new') or [], mv.get('out') or []
    if new:
        out.append('🆕 Новые в топ-100: ' + ', '.join(f"№{x['r']} ({rmln(x['b'])})" for x in new[:3])
                   + (f" и ещё {len(new) - 3}" if len(new) > 3 else ''))
    if gone:
        out.append('🚪 Вышли из топ-100: ' + ', '.join(f"было №{x['r0']} ({rmln(x['b0'])})" for x in gone[:3] if x.get('r0'))
                   + (f" и ещё {len(gone) - 3}" if len(gone) > 3 else ''))
    return out


def message(site=None):
    """Короткое сообщение Алексею: цена, «Главное», новые новости, сайт. Пишет out/message.md."""
    s = json.load(open(os.path.join(OUT, 'snapshot.json'), encoding='utf-8'))
    pr = s.get('price') or {}
    L = [f"🐶 DOG · {s.get('label')}",
         f"{rprice(pr.get('mid'))} · за сутки {rsgn(pr.get('chg24'))}% · капитализация {ru(pr.get('cap'), 0)} млн $", '']
    al = s.get('alerts')
    if al is None:
        al = highlights(s)
    t, prev_t = parse_time(s.get('ts')), parse_time(s.get('prevTs'))
    gap = (t - prev_t) if t and prev_t else None
    since = 'за сутки' if gap is None or dt.timedelta(hours=20) <= gap <= dt.timedelta(hours=30) else f"с {prev_t:%d.%m %H:%M} UTC"
    if not s.get('prevId'):
        L.append('Первая сводка — сравнивать не с чем.')
        L += al
    elif al:
        L.append(f'Главное {since}:')
        L += al
    else:
        L.append(f'Крупного {since} не было: стенки, балансы бирж и переводы — без изменений от 20 млн DOG.')
    try:
        writes = json.load(open(os.path.join(OUT, 'writes.json'), encoding='utf-8'))
    except Exception:
        writes = []
    titles, tre = [], []
    for w in writes:
        try:
            doc = json.load(open(w['file_path'], encoding='utf-8'))
        except Exception:
            continue
        if w.get('collection') == 'news' and doc.get('title'):
            titles.append(doc['title'])
        if w.get('collection') == 'meta' and w.get('doc_id') == 'treasuries':
            for it in doc.get('items') or []:
                h = (it.get('history') or [[None, None]])[-1]
                hd = parse_time(f'{h[0]}T00:00:00Z') if h[0] else None
                if hd and NOW - hd < dt.timedelta(days=4) and h[1]:
                    tre.append(f"🏦 {it['name']}: {rmln(float(h[1]) / 1e6)} DOG (отчёт {hd:%d.%m})")
    if titles or tre:
        L.append('')
    if titles:
        L.append('📰 ' + ' · '.join(titles[:3]) + (f' (и ещё {len(titles) - 3})' if len(titles) > 3 else ''))
    L += tre
    bad = [c['t'] for c in s.get('checks') or [] if not c.get('ok')]
    if bad:
        L.append(f"⚠️ Проверка данных {len(s['checks']) - len(bad)}/{len(s['checks'])}: " + '; '.join(bad[:2]))
    L.append('')
    st = (site or '').strip()
    if st.lower() in ('ok', 'обновлён', 'обновлен'):
        L.append(f'🌐 Сайт обновлён: {SITE_URL}')
    elif st:
        L.append(st if st.startswith('⚠') else '⚠️ ' + st)
    else:
        L.append(f'🌐 Сайт: {SITE_URL}')
    text = '\n'.join(L)
    open(os.path.join(OUT, 'message.md'), 'w', encoding='utf-8').write(text)
    print(text)


def finalize():
    path = os.path.join(OUT, 'snapshot.json')
    s = json.load(open(path, encoding='utf-8'))
    c = raw('conclusion')
    b = re.sub(r'^\s*\**\s*Вывод\s*:?\**\s*', '', (c or '').strip())
    if len(b) > 700:                      # режем по концу предложения, а не посреди слова
        cut = b[:700]
        i = max(cut.rfind('. '), cut.rfind('! '), cut.rfind('? '))
        b = cut[:i + 1] if i > 200 else cut.rstrip() + '…'
    s['brief'] = b
    s['report'] = report(s)
    json.dump(s, open(path, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    open(os.path.join(OUT, 'report.md'), 'w', encoding='utf-8').write(s['report'])
    size = os.path.getsize(path)
    print(s['report'])
    print('\n---')
    print(f'SNAPSHOT_ID={s["id"]}  size={size} bytes' + ('  ⚠️ >250KB' if size > 250000 else ''))


# ---------- новости ----------
def load_news_prev():
    items = {}
    for path in glob.glob(os.path.join(PREV, 'news', '*.json')):
        try:
            d = json.load(open(path, encoding='utf-8'))
        except Exception:
            continue
        items[os.path.splitext(os.path.basename(path))[0]] = d
    return items


def newslist():
    items = sorted(load_news_prev().values(), key=lambda d: (d.get('d') or '', d.get('ts') or ''), reverse=True)
    print(f'NEWS_EXISTING={len(items)}')
    for d in items[:40]:
        print(f"{d.get('d')} | {d.get('kind')} | {d.get('title')} | {d.get('url')}")


def load_doc(base, coll, doc_id):
    for path in (os.path.join(base, coll, doc_id + '.json'), os.path.join(base, doc_id + '.json')):
        try:
            d = json.load(open(path, encoding='utf-8'))
        except Exception:
            continue
        for key in ('data', 'doc', 'document'):
            if isinstance(d, dict) and isinstance(d.get(key), dict) and 'items' in d[key]:
                d = d[key]
        if isinstance(d, dict):
            return d
    return None


def merge_treasuries(cand):
    """Поле "treasury": {"name", "dog", "d"} в новостях → документ meta/treasuries (история запасов DOG компаний).
    Возвращает путь к out/treasuries.json, если что-то изменилось, иначе None."""
    prev = load_doc(PREV, 'meta', 'treasuries') or {'items': []}
    items = {it.get('name'): it for it in prev.get('items') or [] if isinstance(it, dict) and it.get('name')}
    changed = []
    for it in cand:
        t = it.get('treasury') if isinstance(it, dict) else None
        if not isinstance(t, dict):
            continue
        name = re.sub(r'\s+', ' ', str(t.get('name') or '')).strip()[:60]
        dogv = fnum(t.get('dog'))
        d = str(t.get('d') or it.get('d') or '').strip()[:10]
        url = str(it.get('url') or '').strip()
        if not name or not dogv or dogv <= 0 or dogv > SUPPLY or not re.fullmatch(r'\d{4}-\d\d-\d\d', d):
            print(f'TREASURY skip: {name or "?"} — нет названия, числа или даты')
            continue
        e = items.setdefault(name, {'name': name, 'history': []})
        hist = e.setdefault('history', [])
        if any(h[0] == d and abs(float(h[1]) - dogv) < 1 for h in hist):
            continue
        hist[:] = [h for h in hist if h[0] != d] + [[d, round(dogv), url]]
        hist.sort(key=lambda h: h[0])
        changed.append(f'{name}: {thou(dogv)} DOG на {d}')
    if not changed:
        print('TREASURY: без изменений')
        return None
    doc = {'updated': iso(NOW), 'items': sorted(items.values(), key=lambda x: -float((x.get('history') or [[0, 0]])[-1][1]))}
    path = os.path.join(OUT, 'treasuries.json')
    json.dump(doc, open(path, 'w', encoding='utf-8'), ensure_ascii=False)
    for c in changed:
        print('TREASURY:', c)
    return path


def news():
    """raw/news.json: [{d, title, src, url, kind, sum, eng?, title_en?, sum_en?, src_en?, eng_en?, treasury?}] → out/news/<id>.json + записи в out/writes.json."""
    path = os.path.join(RAW, 'news.json')
    try:
        cand = json.load(open(path, encoding='utf-8'))
    except FileNotFoundError:
        print('NEWS: нет raw/news.json — пропуск')
        return
    except Exception as e:
        print(f'NEWS: raw/news.json не читается: {e}')
        return
    if isinstance(cand, dict):
        cand = cand.get('items') or []
    prev_items = load_news_prev()
    seen_urls = {(d.get('url') or '').rstrip('/').lower() for d in prev_items.values()}
    seen_titles = {re.sub(r'\W+', ' ', (d.get('title') or '').lower()).strip() for d in prev_items.values()}
    os.makedirs(os.path.join(OUT, 'news'), exist_ok=True)
    added, skipped = [], []
    today = NOW.date()
    for it in cand:
        if not isinstance(it, dict):
            continue
        url = str(it.get('url') or '').strip()
        title = re.sub(r'\s+', ' ', str(it.get('title') or '')).strip()
        d = str(it.get('d') or '').strip()[:10]
        kind = str(it.get('kind') or 'новость').strip()
        why = None
        if not re.match(r'https?://[^\s/]+\.[^\s]+$', url):
            why = 'нет ссылки'
        elif not title:
            why = 'нет заголовка'
        elif not re.fullmatch(r'\d{4}-\d\d-\d\d', d):
            why = 'нет даты'
        elif kind not in NEWS_KINDS:
            why = f'тип «{kind}» не из списка'
        else:
            try:
                age = (today - dt.date.fromisoformat(d)).days
            except ValueError:
                age = None
            if age is None or age < -1:
                why = 'дата в будущем'
            elif age > NEWS_MAX_AGE:
                why = f'старше {NEWS_MAX_AGE} дней'
        key_t = re.sub(r'\W+', ' ', title.lower()).strip()
        if not why and (url.rstrip('/').lower() in seen_urls or key_t in seen_titles):
            why = 'уже есть'
        if why:
            skipped.append(f'{title[:60]} — {why}')
            continue
        nid = 'n' + d.replace('-', '') + '-' + hashlib.sha1(url.encode('utf-8')).hexdigest()[:8]
        doc = {'d': d, 'title': title[:180], 'src': str(it.get('src') or '').strip()[:60], 'url': url,
               'kind': kind, 'sum': re.sub(r'\s+', ' ', str(it.get('sum') or '')).strip()[:400], 'ts': iso(NOW)}
        if it.get('eng'):
            doc['eng'] = str(it['eng'])[:60]
        # английская версия для сайта (по умолчанию сайт на английском): title_en, sum_en, src_en, eng_en
        for k, lim in (('title_en', 180), ('sum_en', 400), ('src_en', 60), ('eng_en', 60)):
            v = re.sub(r'\s+', ' ', str(it.get(k) or '')).strip()
            if v:
                doc[k] = v[:lim]
        json.dump(doc, open(os.path.join(OUT, 'news', nid + '.json'), 'w', encoding='utf-8'), ensure_ascii=False)
        seen_urls.add(url.rstrip('/').lower())
        seen_titles.add(key_t)
        added.append(nid)
    wpath = os.path.join(OUT, 'writes.json')
    try:
        writes = json.load(open(wpath, encoding='utf-8'))
    except Exception:
        writes = []
    writes = [w for w in writes if w.get('collection') != 'news']
    for nid in added[:20]:
        writes.append({'op': 'set', 'collection': 'news', 'doc_id': nid, 'file_path': os.path.join(OUT, 'news', nid + '.json')})
    tre = merge_treasuries(cand)
    writes = [w for w in writes if not (w.get('collection') == 'meta' and w.get('doc_id') == 'treasuries')]
    if tre:
        writes.append({'op': 'set', 'collection': 'meta', 'doc_id': 'treasuries', 'file_path': tre})
    json.dump(writes, open(wpath, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'NEWS: новых {len(added)}, пропущено {len(skipped)}')
    for x in skipped:
        print('  skip:', x)
    print(f'WRITES: {len(writes)} → out/writes.json')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'compute'
    if cmd == 'compute':
        compute(sys.argv[2] if len(sys.argv) > 2 else 'утро')
    elif cmd == 'finalize':
        finalize()
    elif cmd == 'news':
        news()
    elif cmd == 'newslist':
        newslist()
    elif cmd == 'message':
        message(sys.argv[2] if len(sys.argv) > 2 else None)
    else:
        sys.exit('usage: dogmon.py compute [утро|запрос|день|база|тест] | finalize | newslist | news | message ["статус сайта"]')
