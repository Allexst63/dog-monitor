# DOG Monitor · DOG Монитор

**https://allexst63.github.io/dog-monitor/** — an unofficial tracker for **DOG•GO•TO•THE•MOON** (Bitcoin rune 840000:3):
live price and full-history chart, order books from 7 exchanges, large transfers, the top 100 wallets with daily balances and
average cost, how DOG is held, C2 Blockchain holdings and news — in plain words. English by default, Russian in the “⋯” menu
(or `?lang=ru`). Updated automatically every morning by GitHub Actions.

Неофициальный монитор токена **DOG•GO•TO•THE•MOON** (руна Bitcoin 840000:3): цена и график, стаканы 7 бирж, крупные переводы, топ-100 кошельков, «как держат DOG», запасы C2 Blockchain и новости — простыми словами. Язык — английский по умолчанию, русский — в меню «⋯» или по ссылке `?lang=ru`.

## Как устроено
- `index.html` — весь сайт (одна страница, без сборки).
- `data/` — сводки в JSON. Их каждое утро кладёт автоматическое обновление (`tools/sitepub.py`); страница сама перечитывает данные раз в 5 минут.
  - `live.json` — текущая сводка, `snapshots/` — архив полных сводок (последние 60),
  - `hist.json` — история итогов, `news.json` — новости, `treasuries.json` — запасы компаний, `audit.json` — самопроверка,
  - `wallets.json` — балансы кошельков топ-100 по дням (мини-графики), `costbasis.json` — средняя цена DOG у кошельков топ-100,
    `prices.json` — цена DOG по дням с начала торгов (Kraken, раньше — Gate), для графика «Всё» и средней цены.
- `fonts/`, `icons/`, `og.jpg`, `manifest.webmanifest` — шрифты, иконки, картинка для превью ссылки, установка на экран телефона.

## Автообновление
- **Каждое утро (~05:41 UTC)** GitHub Actions (`.github/workflows/daily.yml`) сам собирает стаканы 7 бирж, свечи Kraken,
  топ-100 и переводы DOG DATA (`tools/fetch.py`), считает сводку (`tools/dogmon.py` через `tools/daily.py`) и кладёт её в `data/`.
  Затем `tools/costbasis.py` догружает новые переводы кошельков топ-100 (DOG DATA) и пересчитывает их среднюю цену.
  Запустить вручную: вкладка Actions → «Утреннее обновление DOG Монитора» → Run workflow
  (`full` — всё, `wallets` — только средние цены кошельков, `feed` — только кандидаты в новости).
- Там же собираются кандидаты в новости (`tools/newsfeed.py` → `data/feed.json`: Google News, Bing News и, если задан
  секрет `X_BEARER_TOKEN`, посты аккаунтов DOG в X). Ежедневная задача Claude отбирает из них важное, пишет по-русски
  и добавляет в `data/news.json` (`tools/daily.py news`).

## Источники и лицензии
См. `NOTICE.md`. Сайт не использует cookies и аналитику.

Информация носит справочный характер и не является инвестиционной рекомендацией.
