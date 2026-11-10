#!/usr/bin/env python3
"""DOG Монитор — уведомление в Telegram при резком движении цены (GitHub Actions, каждые 15 минут).

    python3 tools/alert.py <файл состояния.json>

Цена — 15-минутные свечи Kraken DOG/USD. Сигнал, если цена изменилась на ALERT_1H % и больше за час или на ALERT_24H %
и больше за сутки. Повторно о том же не пишем: о часовом движении — не чаще раза в час, о суточном — раза в 6 часов
(раньше — только если движение развернулось в другую сторону).
Нужен секрет репозитория TELEGRAM_BOT_TOKEN (бот от @BotFather). Кому писать: секрет TELEGRAM_CHAT_ID, а если его нет —
первый человек, написавший боту в личку (запоминается в файле состояния). Без токена скрипт ничего не делает.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

A1H = float(os.environ.get('ALERT_1H') or 5)
A24 = float(os.environ.get('ALERT_24H') or 10)
SITE = 'https://allexst63.github.io/dog-monitor/'
TOKEN = (os.environ.get('TELEGRAM_BOT_TOKEN') or '').strip()
UA = 'Mozilla/5.0 (compatible; DOG-Monitor/1.0; +https://allexst63.github.io/dog-monitor/)'


def get(url, data=None):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode() if data else None, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode('utf-8'))


def tg(method, **kw):
    return get(f'https://api.telegram.org/bot{TOKEN}/{method}', kw or None)


def ru(x, d=1):
    return f'{x:,.{d}f}'.replace(',', ' ').replace('.', ',')


def price(p):
    return f'{p:.7f}'.rstrip('0').replace('.', ',') + ' $'


def main(path):
    if not TOKEN:
        print('ALERT: нет секрета TELEGRAM_BOT_TOKEN — уведомления выключены')
        return
    try:
        st = json.load(open(path, encoding='utf-8'))
    except Exception:
        st = {}
    chat = (os.environ.get('TELEGRAM_CHAT_ID') or '').strip() or st.get('chat')
    if not chat:                                  # первый, кто написал боту в личку, — получатель
        for u in tg('getUpdates').get('result') or []:
            c = ((u.get('message') or {}).get('chat') or {})
            if c.get('type') == 'private':
                chat = st['chat'] = str(c['id'])
                tg('sendMessage', chat_id=chat, disable_web_page_preview='true',
                   text=f'🐶 DOG Монитор подключён. Напишу, если цена DOG изменится на {ru(A1H, 0)}% за час или на {ru(A24, 0)}% за сутки.\n{SITE}')
                break
        if not chat:
            print('ALERT: боту ещё никто не написал — напишите ему любое сообщение')
            return
    d = get('https://api.kraken.com/0/public/OHLC?pair=DOGUSD&interval=15')
    res = d.get('result') or {}
    rows = res.get(next((k for k in res if k != 'last'), ''), [])
    now = time.time()
    if len(rows) < 100 or now - int(rows[-1][0]) > 3600:
        print('ALERT: свечи Kraken не получены или устарели')
        json.dump(st, open(path, 'w', encoding='utf-8'))
        return
    cur = float(rows[-1][4])

    def ago(secs):                                # цена закрытия свечи, шедшей столько секунд назад
        t = int(rows[-1][0]) - secs
        r = next((x for x in reversed(rows) if int(x[0]) <= t), None)
        return float(r[4]) if r else None
    out = []
    for key, base, lim, cool, span in (('h1', ago(3600), A1H, 3600, 'за час'), ('d1', ago(86400), A24, 6 * 3600, 'за сутки')):
        if not base:
            continue
        ch = (cur / base - 1) * 100
        last = st.get(key) or {}
        up = ch > 0
        if abs(ch) >= lim and (now - last.get('t', 0) >= cool or last.get('up') != up):
            out.append(f"{'🚀' if up else '🔻'} DOG {'+' if up else '−'}{ru(abs(ch))}% {span}: {price(cur)} (было {price(base)})")
            st[key] = {'t': now, 'up': up}
        print(f'ALERT {key}: {ch:+.2f}% (порог {lim}%)')
    if out:
        tg('sendMessage', chat_id=chat, disable_web_page_preview='true', text='\n'.join(out) + f'\n{SITE}')
        print('ALERT отправлено:', ' | '.join(out))
    json.dump(st, open(path, 'w', encoding='utf-8'))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'alert-state.json')
