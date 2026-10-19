#!/usr/bin/env python3
"""DOG Монитор — кандидаты в новости (для задачи Claude, которая отбирает и пишет их по-русски).

    python3 tools/newsfeed.py <out.json> [дней=4]

Собирает свежие заголовки из Google News RSS по запросам о DOG и C2 Blockchain.
На сайт напрямую не публикуется: это только список для отбора.
"""
import datetime as dt
import email.utils
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

QUERIES = ['"DOG•GO•TO•THE•MOON"', '"DOG (Bitcoin)"', '"C2 Blockchain" DOG', 'Leonidas DOG bitcoin runes',
           '"$DOG" bitcoin rune', 'Bitcoin runes DOG exchange listing']
UA = 'Mozilla/5.0 (compatible; DOG-Monitor/1.0; +https://allexst63.github.io/dog-monitor/)'
SKIP = re.compile(r'price prediction|прогноз|predict|forecast|dogecoin|\bdoge\b|\bpets?\b|puppy|veterinar', re.I)


def rss(q, engine='google'):
    if engine == 'google':
        url = 'https://news.google.com/rss/search?' + urllib.parse.urlencode({'q': q, 'hl': 'en-US', 'gl': 'US', 'ceid': 'US:en'})
    else:
        url = 'https://www.bing.com/news/search?' + urllib.parse.urlencode({'q': q, 'format': 'rss', 'qft': 'sortbydate="1"'})
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        root = ET.fromstring(r.read())
    for it in root.iter('item'):
        src = it.find('source')
        if src is None:
            src = next((c for c in it if c.tag.endswith('}Source') or c.tag.endswith('}source')), None)
        yield {'title': (it.findtext('title') or '').strip(), 'url': (it.findtext('link') or '').strip(),
               'pub': it.findtext('pubDate'), 'src': (src.text or '').strip() if src is not None else '',
               'srcUrl': src.get('url') if src is not None else '', 'q': q}


def main(out, days=4):
    now = dt.datetime.now(dt.timezone.utc)
    seen, items, errs, stat = set(), [], [], []
    for q, engine in [(q, e) for e in ('google', 'bing') for q in QUERIES]:
        n = 0
        try:
            for x in rss(q, engine):
                n += 1
                try:
                    t = email.utils.parsedate_to_datetime(x['pub']).astimezone(dt.timezone.utc)
                except Exception:
                    continue
                key = re.sub(r'\W+', ' ', x['title'].lower()).strip()
                if now - t > dt.timedelta(days=days) or key in seen or SKIP.search(x['title']):
                    continue
                seen.add(key)
                x['d'] = t.strftime('%Y-%m-%d')
                x['ts'] = t.strftime('%Y-%m-%dT%H:%MZ')
                del x['pub']
                items.append(x)
        except Exception as e:
            errs.append(f'{engine} {q}: {e}')
        stat.append(f'{engine} {q}: {n}')
    items.sort(key=lambda x: x['ts'], reverse=True)
    json.dump({'updated': now.strftime('%Y-%m-%dT%H:%M:%SZ'), 'items': items[:60], 'errors': errs, 'stat': stat},
              open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'NEWSFEED: {len(items)} кандидатов, ошибок {len(errs)}; ' + '; '.join(stat))
    for x in items[:15]:
        print(f"  {x['ts']} | {x['src']} | {x['title'][:110]}")


if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 4)
