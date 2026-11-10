#!/usr/bin/env python3
"""DOG Монитор — проверка выкладки: живой сайт отдаёт ту же сводку, что только что ушла в репозиторий.

    python3 tools/livecheck.py <папка сайта> <адрес сайта>

GitHub Pages публикует новую версию через 1–3 минуты после коммита. Ждём до 9 минут, пока data/version.json на сайте
совпадёт с локальным, затем проверяем, что страница, service worker, библиотека графиков и файлы данных открываются.
Код выхода 1 — сайт не обновился или что-то не открылось (GitHub пришлёт письмо о сбое задачи)."""
import json
import sys
import time
import urllib.request

UA = 'Mozilla/5.0 (compatible; DOG-Monitor/1.0; +https://allexst63.github.io/dog-monitor/)'


def get(url, timeout=25):
    req = urllib.request.Request(f'{url}{"&" if "?" in url else "?"}cb={int(time.time() * 1000)}', headers={'User-Agent': UA, 'Cache-Control': 'no-cache'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


def main(site, base):
    base = base.rstrip('/') + '/'
    want = json.load(open(f'{site}/data/version.json', encoding='utf-8'))['id']
    t0, got = time.time(), None
    while time.time() - t0 < 540:
        try:
            got = json.loads(get(base + 'data/version.json')[1].decode('utf-8')).get('id')
        except Exception as e:
            got = f'ошибка: {str(e)[:80]}'
        if got == want:
            break
        time.sleep(20)
    print(f'LIVE version: сайт {got}, репозиторий {want}, ждали {time.time() - t0:.0f} с')
    bad = [] if got == want else [f'сайт не обновился за {time.time() - t0:.0f} с (на сайте {got})']
    for f, need in (('', b'DOG Monitor'), ('sw.js', b'dogmon-'), ('vendor/lightweight-charts-5.0.8.js', b'Lightweight Charts'),
                    ('data/live.json', b'"top100"'), ('data/prices.json', b'"d"'), ('data/selfcheck.json', b'"items"'), ('manifest.webmanifest', b'"icons"')):
        try:
            st, body = get(base + f)
            if st != 200 or need not in body:
                bad.append(f'{f or "index.html"}: HTTP {st}, содержимое не то')
        except Exception as e:
            bad.append(f'{f or "index.html"}: {str(e)[:80]}')
    for b in bad:
        print('LIVE FAIL:', b)
    print('LIVE ok' if not bad else f'LIVE проблем: {len(bad)}')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
