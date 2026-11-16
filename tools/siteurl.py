#!/usr/bin/env python3
"""DOG Монитор — адрес сайта в одном месте.

Адрес зависит от того, где лежит репозиторий: Allexst63/dog-monitor → https://allexst63.github.io/dog-monitor/,
а после переноса в организацию dog-monitor с именем dog-monitor.github.io → https://dog-monitor.github.io/.
Скрипты берут адрес отсюда (site_url()), поэтому после переноса ничего править руками не нужно.

    python3 tools/siteurl.py <папка сайта>

Запускается в GitHub Actions перед выкладкой: считает адрес по имени репозитория (GITHUB_REPOSITORY) и, если он
поменялся, записывает его в data/site.json и в ссылки превью в index.html (og:url, og:image, hreflang)."""
import json
import os
import re
import sys

DEFAULT = 'https://allexst63.github.io/dog-monitor/'
HERE = os.path.dirname(os.path.abspath(__file__))


def from_repo(repo):
    """'Owner/name' → адрес GitHub Pages (сайт организации — если репозиторий называется <owner>.github.io)."""
    if not repo or '/' not in repo:
        return None
    owner, name = repo.split('/', 1)
    host = owner.lower() + '.github.io'
    return f'https://{host}/' if name.lower() == host else f'https://{host}/{name}/'


def site_url(site_dir=None):
    u = os.environ.get('SITE_URL') or from_repo(os.environ.get('GITHUB_REPOSITORY'))
    if u:
        return u.rstrip('/') + '/'
    try:
        with open(os.path.join(site_dir or os.path.join(HERE, '..'), 'data', 'site.json'), encoding='utf-8') as f:
            u = json.load(f).get('url')
        if u:
            return u.rstrip('/') + '/'
    except Exception:
        pass
    return DEFAULT


def main(site):
    url = site_url(site)
    changed = []
    p = os.path.join(site, 'data', 'site.json')
    try:
        with open(p, encoding='utf-8') as f:
            old = json.load(f).get('url')
    except Exception:
        old = None
    if old != url:
        with open(p, 'w', encoding='utf-8') as f:
            json.dump({'url': url}, f, ensure_ascii=False)
        changed.append('data/site.json')
    # ссылки превью в <head>: заменяем только адреса github.io, остальное не трогаем
    ip = os.path.join(site, 'index.html')
    with open(ip, encoding='utf-8') as f:
        html = f.read()
    head_end = html.find('</head>')
    head, rest = html[:head_end], html[head_end:]
    new_head = re.sub(r'https://[A-Za-z0-9-]+\.github\.io/(?:[A-Za-z0-9._-]+/)?(?=[?"o])', url, head)
    if new_head != head:
        with open(ip, 'w', encoding='utf-8') as f:
            f.write(new_head + rest)
        changed.append('index.html')
    print(f'SITE_URL {url}' + (f' — обновлено: {", ".join(changed)}' if changed else ' — без изменений'))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '.')
