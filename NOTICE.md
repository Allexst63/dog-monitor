# Сторонние компоненты и данные

**TradingView Lightweight Charts™** — библиотека графика цены.
Copyright © TradingView, Inc. Лицензия Apache License 2.0 (https://www.apache.org/licenses/LICENSE-2.0).
Копия пакета `lightweight-charts@5.0.8` (файл `dist/lightweight-charts.standalone.production.js`, без изменений) лежит в `vendor/` вместе с текстом лицензии и NOTICE; jsDelivr — запасной путь. На графиках показан значок TradingView — он ведёт на график DOG/USD на https://www.tradingview.com; в подвале и справке сайта — ссылка на библиотеку и на TradingView.

**Шрифт Inter** (и Inter Display) — Copyright 2016–2023 The Inter Project Authors (https://github.com/rsms/inter). Лицензия SIL Open Font License 1.1 (текст — `fonts/OFL-Inter.txt`). На сайте лежат его сокращённые до латиницы и кириллицы версии в формате WOFF (обычный, средний и полужирный, Inter Display полужирный и курсив только для знака «dog monitor»).
**Шрифты Jost и Golos Text** — Copyright 2020 The Jost Project Authors (https://github.com/indestructible-type) и 2019 The Golos Text Project Authors (https://github.com/googlefonts/golos-text), SIL Open Font License 1.1 (`fonts/OFL-Jost.txt`, `fonts/OFL-GolosText.txt`) — ими набран прежний вид сайта (`classic/`).

**Данные**
- DOG DATA (https://www.dogdata.xyz) — число холдеров, концентрация, метки кошельков, площадки, возраст монет, средняя цена покупки, аирдроп, DOG в других сетях; весь список кошельков от 10 млн DOG и профили их адресов (тип кошелька); переводы от 5 млн DOG — только чтобы найти новых кандидатов в топ-100.
- ordinals.com (официальный обозреватель ord) — балансы DOG кошельков топ-100 из индекса рун, 4 раза в день, и выборочная сверка балансов кошельков от 10 млн; Xverse (API кошелька) — второй источник тех же балансов и выборочная сверка.
- Публичные API бирж: Kraken, Gate, MEXC, BingX, DigiFinex, CoinW, Bitget — стаканы заявок и сделки (MEXC и BingX — по WebSocket); Kraken — свечи для графиков; Coinbase — цена BTC и дневные свечи BTC для сравнения с DOG (`data/btc.json`); Gate, MEXC и Kraken — дневные свечи мем-монет для сравнения с DOG (`data/memes.json`).
- C2 Blockchain — пресс-релизы о запасах DOG (ссылки на каждый релиз — в карточке компании).
- Индексы страха и жадности всего крипторынка: alternative.me (Crypto Fear & Greed Index, https://alternative.me/crypto/fear-and-greed-index/) и CoinMarketCap (CMC Crypto Fear and Greed Index, https://coinmarketcap.com/charts/fear-and-greed-index/) — показаны как есть, со ссылкой на источник; CoinGecko — место DOG среди мем-монет для индекса DOG, капитализация мем-монет и сверка их цен.

Сайт неофициальный и не связан с командой DOG•GO•TO•THE•MOON, перечисленными биржами, DOG DATA и C2 Blockchain. Информация носит справочный характер и не является инвестиционной рекомендацией.
