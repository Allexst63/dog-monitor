#!/usr/bin/env python3
"""DOG Монитор — карта кода (docs/MAP.md): где что лежит, чтобы не читать файлы целиком.

    python3 tools/map.py [папка сайта]      пересобрать docs/MAP.md (быстро, без сети)

Идея как у graphify (граф кода вместо чтения всего подряд), только под этот проект: сайт — один index.html (~8 тыс. строк,
разметка + стили + скрипт), его разделы помечены комментариями «// ---------- … ----------» и «/* ---------- … */».
Карта перечисляет разделы скрипта и стилей со строками, функции каждого раздела (имя:строка), а также скрипты tools/
и задачи .github/workflows. Сначала смотрим карту, потом читаем только нужный кусок: sed -n 'A,Bp' index.html.
Пересобирать после правок (номера строк сдвигаются); проверка в tools/selfcheck.js не нужна — карта для разработки.
"""
import os
import re
import sys

SITE = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else '.')
SEC_JS = re.compile(r'^\s*// -{6,}\s*(.+?)\s*(-{3,}.*)?$')
SEC_CSS = re.compile(r'^\s*/\*\s*-{6,}\s*(.+?)\s*-{3,}')
FN = re.compile(r'^\s*(?:async\s+)?function\s+([A-Za-z0-9_$]+)\s*\(|^\s*const\s+([A-Za-z0-9_$]+)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z0-9_$]+)\s*=>')


def clip(t, n=110):
    t = re.sub(r'\s+', ' ', t).strip()
    return t if len(t) <= n else t[:n - 1] + '…'


def html_map(path):
    lines = open(path, encoding='utf-8').read().split('\n')
    out, in_script, in_style = [], False, False
    secs = []          # [kind, title, start, [fn:line]]
    for i, ln in enumerate(lines, 1):
        if '<script' in ln and 'src=' not in ln and len(ln) < 400:
            in_script = True
        if '<style' in ln:
            in_style = True
        if '</style>' in ln:
            in_style = False
        if '</script>' in ln:
            in_script = False
        if in_style:
            m = SEC_CSS.match(ln)
            if m:
                secs.append(['css', clip(m.group(1), 90), i, []])
            continue
        if not in_script:
            continue
        m = SEC_JS.match(ln)
        if m:
            secs.append(['js', clip(m.group(1), 90), i, []])
            continue
        f = FN.match(ln)
        if f and secs and secs[-1][0] == 'js' and re.match(r'^  \S', ln):
            secs[-1][3].append(f'{f.group(1) or f.group(2)}:{i}')
    out.append(f'index.html — {len(lines)} строк. Разделы (строка начала) и функции раздела (имя:строка).\n')
    out.append('### Стили (CSS)\n')
    for k, t, s, _ in secs:
        if k == 'css':
            out.append(f'- {s}: {t}')
    out.append('\n### Скрипт (JS)\n')
    for k, t, s, fns in secs:
        if k == 'js':
            out.append(f'- **{s}: {t}**' + (f' — {", ".join(fns)}' if fns else ''))
    return '\n'.join(out)


def doc_of(path):
    try:
        src = open(path, encoding='utf-8').read()
    except Exception:
        return ''
    m = re.search(r'^(?:#!.*\n)?\s*(?:"""|/\*)\s*(.+?)\n', src)
    return clip(m.group(1), 120) if m else ''


def main():
    parts = ['# Карта кода DOG Монитора', '',
             '> Собрано `python3 tools/map.py` — не править руками. Смотреть сначала сюда, потом читать только нужные строки.', '',
             '## index.html', '', html_map(os.path.join(SITE, 'index.html')), '', '## tools/', '']
    td = os.path.join(SITE, 'tools')
    for f in sorted(os.listdir(td)):
        p = os.path.join(td, f)
        if os.path.isfile(p) and f.endswith(('.py', '.js')):
            n = sum(1 for _ in open(p, encoding='utf-8'))
            parts.append(f'- `{f}` ({n} стр.) — {doc_of(p)}')
    parts += ['', '## .github/workflows/', '']
    wd = os.path.join(SITE, '.github', 'workflows')
    for f in sorted(os.listdir(wd)):
        src = open(os.path.join(wd, f), encoding='utf-8').read()
        name = re.search(r'^name:\s*(.+)$', src, re.M)
        crons = re.findall(r"cron:\s*'([^']+)'", src)
        parts.append(f'- `{f}` — {name.group(1).strip() if name else ""}' + (f' (cron {", ".join(crons)})' if crons else ''))
    os.makedirs(os.path.join(SITE, 'docs'), exist_ok=True)
    out = os.path.join(SITE, 'docs', 'MAP.md')
    open(out, 'w', encoding='utf-8').write('\n'.join(parts) + '\n')
    print(f'MAP → {out} ({os.path.getsize(out)} байт)')


if __name__ == '__main__':
    main()
