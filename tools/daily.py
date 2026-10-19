#!/usr/bin/env python3
"""DOG Монитор — ежедневное обновление сайта без участия человека.

    python3 tools/daily.py run  <site_dir>              сбор данных → расчёт → data/ сайта (GitHub Actions, каждое утро)
    python3 tools/daily.py news <site_dir> <news.json>  добавить новости (их отбирает задача Claude) в data/news.json
    python3 tools/daily.py message <site_dir> [статус]  короткое сообщение по текущей сводке сайта

Рабочая папка — $DOGMON (по умолчанию /tmp/dogmon). Прошлые сводки берутся из data/ сайта.
"""
import datetime as dt
import glob
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get('DOGMON', '/tmp/dogmon')
RAW, PREV, OUT, CFG = (os.path.join(BASE, d) for d in ('raw', 'prev', 'out', 'cfg'))
NOW = dt.datetime.now(dt.timezone.utc)


def jload(p, default=None):
    try:
        return json.load(open(p, encoding='utf-8'))
    except Exception:
        return default


def jdump(o, p):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(o, open(p, 'w', encoding='utf-8'), ensure_ascii=False)


def sh(*args):
    r = subprocess.run([sys.executable, *args], capture_output=True, text=True, env=dict(os.environ, DOGMON=BASE))
    if r.returncode:
        print(r.stdout[-3000:], r.stderr[-3000:])
        raise SystemExit(f'ошибка: {" ".join(args[:2])}')
    return r.stdout


def line(out, key):
    m = re.search(rf'^{key}:? ?(.*)$', out, re.M)
    v = (m.group(1).strip() if m else '').lstrip('=').strip()
    return [] if v in ('', 'нет') else v.split()


def prepare(site):
    shutil.rmtree(BASE, ignore_errors=True)
    for d in (RAW, PREV, OUT, os.path.join(CFG, 'config')):
        os.makedirs(d, exist_ok=True)
    shutil.copy(os.path.join(HERE, 'dogmon.py'), os.path.join(BASE, 'dogmon.py'))
    shutil.copy(os.path.join(HERE, 'labels.json'), os.path.join(CFG, 'config', 'labels.json'))
    data = os.path.join(site, 'data')
    snaps = sorted(glob.glob(os.path.join(data, 'snapshots', '*.json')), reverse=True)[:3]
    os.makedirs(os.path.join(PREV, 'snapshots'), exist_ok=True)
    for p in snaps:
        shutil.copy(p, os.path.join(PREV, 'snapshots', os.path.basename(p)))
    if os.path.exists(os.path.join(data, 'live.json')):
        os.makedirs(os.path.join(PREV, 'live'), exist_ok=True)
        shutil.copy(os.path.join(data, 'live.json'), os.path.join(PREV, 'live', 'current.json'))
    for n in jload(os.path.join(data, 'news.json'), []) or []:
        if isinstance(n, dict) and n.get('id'):
            jdump(n, os.path.join(PREV, 'news', n['id'] + '.json'))
    for doc in ('treasuries', 'audit'):
        if os.path.exists(os.path.join(data, doc + '.json')):
            os.makedirs(os.path.join(PREV, 'meta'), exist_ok=True)
            shutil.copy(os.path.join(data, doc + '.json'), os.path.join(PREV, 'meta', doc + '.json'))


# ---------- вывод простыми словами (из цифр сводки, без советов и прогнозов) ----------
def ru(x, d=1):
    return f'{x:,.{d}f}'.replace(',', ' ').replace('.', ',')


def pct(x):
    if x is None:
        return None
    r = round(x, 1)
    return 'почти без изменений' if abs(r) < 0.5 else f"{'+' if r > 0 else '−'}{ru(abs(r))}%"


def brief(s):
    pr, ch = s.get('price') or {}, ((s.get('chart') or {}).get('chg') or {})
    mid = pr.get('mid')
    parts = []
    if mid:
        p = f"Цена DOG — около {ru(mid, 6)} $"
        bits = [f'за сутки {pct(pr.get("chg24"))}' if pr.get('chg24') is not None else None,
                f'за неделю {pct(ch.get("7d"))}' if ch.get('7d') is not None else None]
        bits = [b for b in bits if b]
        parts.append(p + (': ' + ', '.join(bits) if bits else '') + '.')
    bal = (s.get('exch') or {}).get('bal')
    if bal:
        parts.append(f"На кошельках бирж лежит {ru(bal / 1000, 1)} млрд DOG." if bal >= 1000 else f"На кошельках бирж лежит {ru(bal, 0)} млн DOG.")
    al = [re.sub(r'^\W+\s*', '', a).strip() for a in (s.get('alerts') or [])]
    if al:
        parts.append('Главное за сутки: ' + '; '.join(al[:3]) + '.')
    elif s.get('prevId'):
        parts.append('Крупных изменений за сутки не было: заявки в стаканах, балансы бирж и переводы — без сдвигов от 20 млн DOG.')
    txt = ' '.join(parts)
    return txt if len(txt) <= 680 else txt[:680].rsplit(';', 1)[0] + '.'


def audit(s, fetch_ok, fetch_all, failed, looked, refetched):
    ch = s.get('checks') or []
    ok = sum(1 for c in ch if c.get('ok'))
    books = s.get('books') or {}
    names = {'kraken': 'Kraken', 'gate': 'Gate', 'mexc': 'MEXC', 'bingx': 'BingX', 'coinw': 'CoinW', 'digifinex': 'DigiFinex', 'bitget': 'Bitget'}
    items = [f'Автоматическое утреннее обновление: проверка данных {ok} из {len(ch)}',
             f'Источники: получено {fetch_ok} из {fetch_all}' + (f' (повторно запрошено: {len(refetched)})' if refetched else ''),
             f"Стаканы {len(books)} из 7 бирж: " + ', '.join(names.get(k, k) for k in books)]
    miss = [names[k] for k in names if k not in books]
    if miss:
        items.append('Не удалось получить стакан: ' + ', '.join(miss) + ' — в итоги не вошли')
    if looked:
        items.append(f'Проверены владельцы {looked} кошельков по данным DOG DATA')
    bad = [c['t'] for c in ch if not c.get('ok')]
    items += [f'Замечание: {t}' for t in bad[:3]]
    todo = [f'Перепроверить: {t}' for t in bad[:5]]
    if failed:
        todo.append('Не ответили источники: ' + ', '.join(failed))
    return {'ts': NOW.strftime('%Y-%m-%dT%H:%M:%SZ'), 'items': items[:8], 'todo': todo[:5]}


def fetch(names=None, entity=None):
    args = [os.path.join(HERE, 'fetch.py'), RAW] + (['--entity'] + entity if entity else (names or []))
    out = sh(*args)
    print(out.strip())
    m = re.search(r'FETCH_DONE ok=(\d+)/(\d+)(?: failed=(\S+))?', out)
    return (int(m.group(1)), int(m.group(2)), (m.group(3) or '').split(',') if m and m.group(3) else []) if m else (0, 0, [])


def run(site):
    prepare(site)
    ok, total, failed = fetch()
    dm = os.path.join(BASE, 'dogmon.py')
    out = sh(dm, 'compute', 'утро')
    refetched, looked = [], 0
    for _ in range(2):                      # повторные запросы источников, которые не прошли проверку
        rf = [x for x in line(out, 'REFETCH') if not x.startswith('entity_')]
        lk = line(out, 'LOOKUP')
        if not rf and not lk:
            break
        if rf:
            refetched += rf
            fetch(rf)
        if lk:
            looked += len(lk)
            fetch(entity=lk)
        out = sh(dm, 'compute', 'утро')
    failed = [n for n in failed if open(os.path.join(RAW, n + '.txt'), encoding='utf-8').read().startswith('UNAVAILABLE')]
    print(out[-2500:])
    s = jload(os.path.join(OUT, 'snapshot.json'))
    open(os.path.join(RAW, 'conclusion.txt'), 'w', encoding='utf-8').write(brief(s))
    sh(dm, 'finalize')
    s = jload(os.path.join(OUT, 'snapshot.json'))
    jdump(audit(s, total - len(failed), total, failed, looked, sorted(set(refetched))), os.path.join(OUT, 'audit.json'))
    print(sh(os.path.join(HERE, 'sitepub.py'), BASE, site).strip())
    print('BRIEF:', s.get('brief'))
    print(f'SNAPSHOT_ID={s.get("id")}')


def news(site, path):
    prepare(site)
    shutil.copy(path, os.path.join(RAW, 'news.json'))
    jdump([], os.path.join(OUT, 'writes.json'))
    print(sh(os.path.join(BASE, 'dogmon.py'), 'news').strip())
    writes = [w for w in jload(os.path.join(OUT, 'writes.json'), []) if w.get('collection') in ('news', 'meta')]
    jdump(writes, os.path.join(OUT, 'writes.json'))
    if writes:
        print(sh(os.path.join(HERE, 'sitepub.py'), BASE, site).strip())
    print(f'NEWS_ADDED={sum(1 for w in writes if w["collection"] == "news")}')


def message(site, status=None):
    prepare(site)
    shutil.copy(os.path.join(site, 'data', 'live.json'), os.path.join(OUT, 'snapshot.json'))
    jdump([], os.path.join(OUT, 'writes.json'))
    print(sh(os.path.join(BASE, 'dogmon.py'), 'message', *([status] if status else [])).strip())


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'run' and len(sys.argv) == 3:
        run(sys.argv[2])
    elif cmd == 'news' and len(sys.argv) == 4:
        news(sys.argv[2], sys.argv[3])
    elif cmd == 'message' and len(sys.argv) in (3, 4):
        message(sys.argv[2], sys.argv[3] if len(sys.argv) == 4 else None)
    else:
        sys.exit(__doc__)
