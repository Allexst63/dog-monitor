#!/usr/bin/env python3
"""Выкладка сводки DOG Монитора на публичный сайт.

Утреннее обновление после записи в базу дашборда запускает:
    python3 tools/sitepub.py /tmp/dogmon <папка-клона-сайта>
Скрипт берёт список записей из /tmp/dogmon/out/writes.json (те же документы, что ушли в базу)
и раскладывает их в data/ сайта: live.json (+ короткий version.json), snapshots/<id>.json, hist.json,
news.json, treasuries.json, audit.json. В сеть не ходит, пишет только в папку data/ сайта.
"""
import json
import os
import re
import sys

KEEP_SNAPSHOTS = 60     # полных сводок в архиве сайта
KEEP_HIST = 400         # строк истории
KEEP_NEWS = 300         # новостей
STRIP = ('report',)     # служебный текст для Telegram-отчёта на сайте не нужен
ID_RE = re.compile(r'^[\w.:-]{1,80}$')


def jload(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def jdump(obj, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, separators=(',', ':'))
    os.replace(tmp, path)


def unwrap(d):
    """Файлы ArtifactData иногда кладут документ в поле data — достаём сам документ."""
    if isinstance(d, dict) and set(d) <= {'data', 'id', 'version', 'path'} and isinstance(d.get('data'), dict):
        return d['data']
    return d


def merge_list(path, item, key_sort, keep):
    items = jload(path) if os.path.exists(path) else []
    items = [x for x in items if isinstance(x, dict) and x.get('id') != item['id']] + [item]
    items.sort(key=key_sort, reverse=True)
    jdump(items[:keep], path)


def apply(site, coll, doc_id, data):
    data = unwrap(data)
    d = os.path.join(site, 'data')
    if not isinstance(data, dict) or not ID_RE.match(doc_id):
        return f'пропуск {coll}/{doc_id}'
    if coll == 'live' and doc_id == 'current':
        head = {k: data[k] for k in ('id', 'ts', 'kind', 'label') if k in data}
        jdump(dict(head, **{k: v for k, v in data.items() if k not in STRIP and k not in head}), os.path.join(d, 'live.json'))
        jdump({'id': data.get('id'), 'ts': data.get('ts'), 'kind': data.get('kind'), 'price': (data.get('price') or {}).get('mid')}, os.path.join(d, 'version.json'))
    elif coll == 'snapshots':
        jdump({k: v for k, v in data.items() if k not in STRIP}, os.path.join(d, 'snapshots', doc_id + '.json'))
    elif coll == 'hist':
        merge_list(os.path.join(d, 'hist.json'), dict(data, id=data.get('id') or doc_id), lambda x: str(x.get('ts') or ''), KEEP_HIST)
    elif coll == 'news':
        merge_list(os.path.join(d, 'news.json'), dict(data, id=doc_id), lambda x: (str(x.get('d') or ''), str(x.get('ts') or '')), KEEP_NEWS)
    elif coll == 'meta' and doc_id in ('treasuries', 'audit'):
        jdump(data, os.path.join(d, doc_id + '.json'))
    else:
        return f'пропуск {coll}/{doc_id}'
    return f'{coll}/{doc_id}'


def prune(site):
    sd = os.path.join(site, 'data', 'snapshots')
    if not os.path.isdir(sd):
        return 0
    live = jload(os.path.join(site, 'data', 'live.json')) if os.path.exists(os.path.join(site, 'data', 'live.json')) else {}
    files = sorted((f for f in os.listdir(sd) if f.endswith('.json')), reverse=True)
    removed = 0
    for f in files[KEEP_SNAPSHOTS:]:
        if f[:-5] != live.get('id'):
            os.remove(os.path.join(sd, f))
            removed += 1
    return removed


def main(dogmon, site):
    out = os.path.join(dogmon, 'out')
    done = []
    for w in jload(os.path.join(out, 'writes.json')):
        if w.get('op') not in (None, 'set'):
            continue
        done.append(apply(site, w['collection'], w['doc_id'], jload(w['file_path'])))
    audit = os.path.join(out, 'audit.json')
    if os.path.exists(audit):
        done.append(apply(site, 'meta', 'audit', jload(audit)))
    removed = prune(site)
    live = jload(os.path.join(site, 'data', 'live.json'))
    hist = jload(os.path.join(site, 'data', 'hist.json')) if os.path.exists(os.path.join(site, 'data', 'hist.json')) else []
    news = jload(os.path.join(site, 'data', 'news.json')) if os.path.exists(os.path.join(site, 'data', 'news.json')) else []
    print('SITE:', '; '.join(done))
    print(f'SITE_LIVE={live.get("id")} hist={len(hist)} news={len(news)} архив_удалено={removed}')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit('usage: sitepub.py /tmp/dogmon <site_dir>')
    main(sys.argv[1], sys.argv[2])
