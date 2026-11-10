# Сторонние компоненты и данные

**TradingView Lightweight Charts™** — библиотека графика цены.
Copyright © TradingView, Inc. Лицензия Apache License 2.0 (https://www.apache.org/licenses/LICENSE-2.0).
Копия пакета `lightweight-charts@5.0.8` (файл `dist/lightweight-charts.standalone.production.js`, без изменений) лежит в `vendor/` вместе с текстом лицензии и NOTICE; jsDelivr — запасной путь. На графиках показан значок TradingView — он ведёт на график DOG/USD на https://www.tradingview.com; в подвале и справке сайта — ссылка на библиотеку и на TradingView.

**Шрифт Jost** — Copyright 2020 The Jost Project Authors (https://github.com/indestructible-type).
**Шрифт Golos Text** — Copyright 2019 The Golos Text Project Authors (https://github.com/googlefonts/golos-text).
Оба шрифта распространяются по лицензии SIL Open Font License 1.1 (тексты лицензий — `fonts/OFL-Jost.txt`, `fonts/OFL-GolosText.txt`). На сайте лежат их сокращённые до латиницы и кириллицы версии в формате WOFF.

**Данные**
- DOG DATA (https://www.dogdata.xyz) — число холдеров, концентрация, метки кошельков, площадки, возраст монет, средняя цена покупки, аирдроп, DOG в других сетях; переводы от 5 млн DOG — только чтобы найти новых кандидатов в топ-100.
- ordinals.com (официальный обозреватель ord) — балансы DOG кошельков топ-100 из индекса рун, 4 раза в день; Xverse (API кошелька) — второй источник тех же балансов и выборочная сверка.
- Публичные API бирж: Kraken, Gate, MEXC, BingX, DigiFinex, CoinW, Bitget — стаканы заявок и сделки (MEXC и BingX — по WebSocket); Kraken — свечи для графиков; Coinbase — цена BTC и дневные свечи BTC для сравнения с DOG (`data/btc.json`).
- C2 Blockchain — пресс-релизы о запасах DOG (ссылки на каждый релиз — в карточке компании).

Сайт неофициальный и не связан с командой DOG•GO•TO•THE•MOON, перечисленными биржами, DOG DATA и C2 Blockchain. Информация носит справочный характер и не является инвестиционной рекомендацией.
