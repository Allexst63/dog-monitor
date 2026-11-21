# Карта кода DOG Монитора

> Собрано `python3 tools/map.py` — не править руками. Смотреть сначала сюда, потом читать только нужные строки.

## index.html

index.html — 8469 строк. Разделы (строка начала) и функции раздела (имя:строка).

### Стили (CSS)

- 149: layout
- 222: home
- 413: order book
- 599: charts
- 699: wallets
- 820: sheet
- 1052: tablet and desktop
- 1756: v18: rolling digits («барабан»), sliding switches, stepped slider
- 1830: v21: smooth order book, one price, the page keeps its size

### Скрипт (JS)

- **1913: language: English only (the Russian version lives in git history, branch design-v10-ru)** — P:1918, nTitle:1925, nSum:1926, srcTr:1927, bandTr:1929, ico:1976, RM:1977
- **1982: rolling digits («барабан»): a number that changes by itself (live price, the DOG index, t…** — rollTr:1986, rollNum:1987, rollLh:1988, rollBuild:1993, rollSet:2004
- **2045: switches: the selected option's background is its own «pill» that glides to the new choic…** — slKey:2050, slBtns:2051, slPlace:2052, slScan:2078
- **2144: a list of choices (the order book's price step): the chosen row has a highlight that glid…** — vswPlace:2146, vswPick:2158
- **2221: formatting** — grp:2223, n:2224, fp:2229, dol:2238, fpd:2239, sg:2240, dir:2246, cls:2247, dcls:2248, short:2249, mdog:2250, usd:2251, usdM:2261, m1:2262, m1usd:2263, m1s:2264, toDate:2267, dtl:2281, tl:2282, dml:2283, sameDay:2284, when:2285, ago:2291, dayName:2300, isFull:2307
- **2309: owner labels** — nameTr:2311, noteTr:2350, chkTr:2374, ownName:2380, avatar:2385, kindTag:2390, whoTxt:2392
- **2394: view data** — V:2395, skelHtml:2396, topStale:2397, staleTxt:2403, topSince:2404, prevLabel:2408, biggestWall:2412, wallText:2423
- **2432: navigation** — navHtml:2433, setBadge:2439, tbSync:2440, setTab:2441
- **2563: status** — setStatus:2564
- **2593: bottom sheet** — SH:2595, isPhone:2596, sheetReset:2597, openSheet:2602, closeSheet:2616, copyBtn:2717, toast:2731
- **2738: charts** — niceTicks:2739, svgEl:2747, attachCross:2748
- **2784: price: chart data** — priceRows:2785, priceSeries:2811, pillTxt:2812
- **2813: Home: price and chart — Kraken candles by interval, as on Charts (15m · 1h · 4h · 1d · 1w)** — heroRows:2818, heroKey:2824, pxRep:2828, nowPx:2829, chg24:2830, setHero:2833, resetHero:2846, scrubHero:2847, chartLabel:2853
- **2858: price: TradingView Lightweight Charts (Apache-2.0)** — lwRedraw:2862, ut:2884, fuDM:2885, tickFmt:2886, killChart:2894, addSer:2895, heroAt:2901, heroPin:2907, hlegSet:2918, hwhatSync:2926, lastBtn:2951, toEnd:2959, hGap:2973, rClamp:2974, lastSync:2981, heroGrow:2991, hlegMargins:3008, drawLW:3012
- **3076: Home chart height: first screen shows indexes, price and the whole chart** — fitHomeChart:3078
- **3099: light tick under the finger when it moves to another candle** — haptic:3101
- **3115: Home chart by finger — like exchange apps**
- **3262: other (own SVG) charts: a sideways finger never scrolls the page** — drawPrice:3286, drawPriceSvg:3314, lineChart:3346
- **3380: moon** — moonSvg:3381
- **3394: daily summary in English, built from the same data as the report (tools/dogmon.py highlig…** — alertsEn:3395, isExK:3428, briefOf:3429
- **3445: stories** — dOf:3446, treItem:3447, buildStories:3452, sparkSvg:3504, storyKey:3513, markSeen:3514, SF:3522, openStory:3523, closeStory:3543, showSlide:3565, nextSlide:3584, prevSlide:3590, nextStory:3595, prevStory:3596, pauseStory:3597, resumeStory:3604, springStory:3612
- **3674: news** — freshNews:3675
- **3680: live price: Kraken and Gate over WebSocket (public site only)** — livePrice:3681, livePx:3683, liveChg:3684, applyLive:3685, liveSock:3716, liveMid:3735, livePush:3741, liveRest:3750, liveSoon:3762, startLive:3767
- **3798: HOME** — histDelta:3799, heroStats:3808, renderOverview:3811, refreshHomeParts:3845
- **3850: fear & greed: whole market (alternative.me, CoinMarketCap) and DOG (own index, tools/mood…** — fngZi:3853, fngCol:3854, fngName:3855, fngDay:3856, capS:3857, gaugeSvg:3858, fngMarket:3870, fngCmc:3874
- **3875: DOG index "now": read off the server's curve for today (the index as a function of DOG's …** — dogLive:3877, fngNow:3889, fngTick:3890, fngSheetLive:3895, fngHtml:3914, paintFng:3930, fngLive:3945, fngSpark:3957, fngKv:3964, FNG_SCALE:3965, fngMktChart:3969, fngMarketSheet:3976, fngCmcSheet:3988, fngDmy:4001
- **4002: index chart with price (DOG or bitcoin): tap or slide — date, index and price** — btcFmt:4005, btcNowMap:4006, pxMap:4007, fngGe:4011, fngLe:4012, fngTurns:4013, fngTurnsList:4025, ficPath:4031, fngChart:4033, ficRead:4053, ficSet:4060, ficAt:4074, fngDogSheet:4099, tile:4152, moodOf:4153, xTxt:4161, whNow:4162, whSince:4171, tilesHtml:4172, evHtml:4183, bigK:4186, bigMin:4187, bigLab:4188, stpHtml:4189, stpPaint:4196, stpSet:4204, summaryHtml:4233, briefSheet:4243, exchangesHtml:4251, mirNoteHtml:4266, monY:4271, treChart:4272, treasuryHtml:4292
- **4303: Home → DOG and meme coins: six cards for 7, 30 or 90 days. A new period re-ranks the 12 c…** — monoSpline:4310, hmSpark:4330, hmData:4337, hmKey:4351, hmX:4352, hmLine:4353, hmArea:4354, hmAria:4355, hmCard:4356, memesMiniHtml:4360, hmPaint:4369, hmSwitch:4376, hmMorph:4415, treSheet:4432, events:4450, hbarsHtml:4459, ageCardHtml:4460, exchCardHtml:4474, histLine:4487, ddSer:4497, serLine:4505, serDelta:4513, statD:4519
- **4521: "what this means" notes** — infoBtn:4522, hInfo:4523, openInfo:4599, sheetNavSync:4617, animateIntro:4621, openChecks:4647, openMore:4649
- **4671: ORDER BOOK**
- **4672: ORDER BOOK: combined book, like an exchange** — toU:4682, stepDec:4683, fpx:4684, pctOf:4685, qf:4686, usdC:4694, amtF:4700, agoS:4701
- **4703: order book data** — obFresh:4712, obPut:4713, obSeed:4736, obFetch:4746, obLoop:4765
- **4786: Kraken, Gate, MEXC and BingX live: WebSocket** — gT:4787, wsCan:4795, wsOpen:4796, wsClose:4823, wsWant:4829, wsOn:4834, wsReset:4835, wsSend:4836, wsAlive:4837, wsBook:4843, trLive:4861, krakenMsg:4870, krakenFlush:4887, gateMsg:4897, wsTrades:4906, pbRead:4916, pbStr:4927, mexcMsg:4928, bingxMsg:4955
- **4972: mirror exchange: a book that repeats another exchange (same orders twice)** — obLad:4974, obMirOf:4981, obSrc:4997, obDeep:5015, obOldDeep:5049, obHybrid:5056, obMidOf:5066, obPx:5070, obSet:5076, obFineStep:5103, obAgg:5104, obRef:5165, obCtx:5169, obRowsN:5174, obBand:5175, obHistPush:5182
- **5191: feed: big orders added, pulled, resized — while the site is open** — obDiff:5192, obEvText:5217
- **5226: view: exchanges, book, metrics** — segB:5227, obChipsHtml:5233, obNoteHtml:5242, obSepHtml:5277, obBookHtml:5283, obStatusHtml:5347, obAge:5358, obCardHtml:5363
- **5375: who is stronger near the price: plain-words book summary** — obFine:5376, obImbHtml:5377, obMetricsHtml:5396, obImbSheet:5445, obBigHtml:5446, obChgHtml:5458
- **5468: book feed** — obFeedHtml:5469
- **5478: trades: what actually executed (Kraken and Gate)** — trParse:5481, trPut:5499, trFetch:5515, tls:5524, trHtml:5525
- **5546: level details (tap a book row)** — obRowSheet:5547, obStepSheet:5587
- **5599: indicators: moving averages and RSI (Charts tab)** — taSma:5600, taEma:5601, taRsi:5609, drawDepth:5620
- **5658: each exchange** — depthRow:5659, wallList:5666, exListHtml:5680, exSheet:5692, exCardsHtml:5697, venuesHtml:5736
- **5752: Order book tab** — renderBooks:5753
- **5777: smooth repaint (v21): the new HTML is laid over the old DOM instead of replacing it («mor…** — mKey:5783, mSkip:5784, mAttrs:5785, mNode:5793, mKids:5810, morph:5828, obPaintBook:5829, obSoon:5843, obPaint:5854
- **5920: CHARTS: TradingView-style candles (RSI and MACD below), delta and correlation with bitcoin** — chIntra:5928, chSrc:5929, weekStart:5930, tvUrl:5932, tvLinkFor:5933, tvFix:5937, tvFixAll:5945, hexA:5948, chColors:5949, lwOk:5953, lwSer:5954, lwChart:5955, chKill:5968, lwPanes:5969, chWait:5970, lwFailTxt:5971
- **5973: Kraken candles** — chStored:5974, chWeekly:5978, chInstant:5990, chFresh:6000, chOhlc:6001
- **6018: deep history: Kraken keeps 720 candles, older ones come from Gate (DOG/USDT)** — pxDays:6025, chFull:6034, chKeepLost:6042, chCanMore:6050, chLoadingMore:6051, gateRows:6052, chMore:6060, chMoreDone:6096, chMoreUi:6101, chWithLive:6112, chInd:6120
- **6132: main chart** — chDrawTV:6133, chFill:6235, chGrow:6252, chPin:6268, tvLabels:6274, chLegend:6285, chRead:6297, chLive:6321
- **6331: DOG and bitcoin since DOG launch** — crSrv:6332, crBtc:6333, corrOf:6360, betaOf:6361, crCalc:6362, corrWord:6378, mvEn:6379, crDraw:6380
- **6475: DOG and meme coins (data/memes.json, tools/memes.py): change since the start of the period** — mmCol:6479, mmPct:6481, mmCalc:6482, mmTicks:6507, mmDraw:6518, mmPlot:6532, mmShow:6545, mmNote:6566, mmIdx:6573, mmNear:6574
- **6599: Charts tab** — chStatsHtml:6600
- **6607: Fear & greed: the history of all three indices. Lives right on the Charts tab (#f3s-in) a…** — f3sR:6613, f3sLinks:6614, fngChartsHtml:6619, f3sKey:6626, paintFngCharts:6627, f3sData:6636, f3Date:6659, f3Ax:6660, f3sPx:6662, f3sRead:6670, f3sPaneIn:6681, f3sPane:6694, f3sPlot:6695, f3sStats:6708, f3sBody:6718, fngAllSheet:6727, f3sPer:6735, f3sSet:6749, f3sFocus:6769, f3sShow:6787, f3sRestore:6794, f3sAt:6799, f3GoBtn:6831, renderCharts:6840, chDrawAll:6872, chLoop:6877
- **6916: WALLETS** — walletSheet:6917
- **6934: average DOG cost per wallet (data/costbasis.json, tools/costbasis.py)** — costOf:6935, curPrice:6936, vsAvg:6937, airTxt:6942, costLine:6943, costBlock:6950, holdersCost:6967
- **6977: balance sparklines (data/wallets.json)** — isEx:6978, balSeries:6979, sparkW:6985
- **7003: wallets: 24h summary** — walletsSummaryHtml:7004
- **7027: wallets: who holds DOG** — ownersData:7028, ownersHtml:7041, countTo:7050, tierState:7066, tierAnim:7072, ring1:7091, tiersData:7100, tiersHtml:7129, whSpark:7175, whalesDetail:7185, whalesCardHtml:7245, t100ChgHtml:7261, renderWallets:7269, balanceCols:7314
- **7350: NEWS** — renderNews:7351
- **7388: HISTORY** — renderHistory:7389, drawHistCharts:7405
- **7425: GUIDE** — renderHelp:7457
- **7466: shared render** — drawCharts:7467
- **7477: UPDATE NOW: fresh data straight from the page + self-check** — cachedOhlc:7498, pause:7512, num:7513, rnd:7514, sumOf:7515, median:7516, mirScore:7517, isMir:7530, pad2:7531, hmU:7532, isoS:7533, isExK2:7534, upGet:7536, prevSnap:7548
- **7556: parsing responses** — lvls:7557, parseBook:7567, firstList:7583, addrOf:7592, ohlcRows:7593
- **7604: calculation, as in tools/dogmon.py** — depthOf:7605, ladderOf:7614, wallsOf:7620, wallChanges:7625, wdKey:7656, entMap:7657, prevTopOf:7668, chartOf:7676
- **7694: live summary on top of the morning report** — buildLive:7695, sinceItems:7911
- **7955: startup** — runUpdate:7958, applyUpdate:8003, scheduleSoft:8019, softRender:8024, refreshChart:8049
- **8064: update UI** — upRowState:8065, srcListHtml:8072, chkLi:8085, updSheetHtml:8086, openUpd:8117, paintUpd:8121, autoTick:8134, isStandalone:8191, isIOS:8192, installRowHtml:8193, themeNow:8212, setTheme:8213, themeSwitch:8221
- **8227: keep the screen on: on an iPad or a computer the page can stand on the table like a clock…** — awakeOn:8231, wakeSync:8232
- **8252: visit counts: Umami Cloud — no cookies, nothing personal. Off while UMAMI_ID is empty** — track:8257, siteUrl:8279, renderAll:8296
- **8307: site data: JSON files in data/, refreshed by the scheduled update** — siteDb:8308

## tools/

- `alert.py` (99 стр.) — DOG Монитор — уведомление в Telegram при резком движении цены (GitHub Actions, каждые 15 минут).
- `build.js` (40 стр.) — 
- `costbasis.py` (329 стр.) — DOG Монитор — средняя цена DOG у кошельков топ-100 (для GitHub Actions, после tools/daily.py run).
- `daily.py` (267 стр.) — DOG Монитор — ежедневное обновление сайта без участия человека.
- `dogmon.py` (1564 стр.) — DOG Монитор — пайплайн снимка (утро и дневные обновления).
- `fetch.py` (676 стр.) — DOG Монитор — сбор данных напрямую из публичных API (для GitHub Actions).
- `livecheck.py` (55 стр.) — DOG Монитор — проверка выкладки: живой сайт отдаёт ту же сводку, что только что ушла в репозиторий.
- `map.py` (99 стр.) — DOG Монитор — карта кода (docs/MAP.md): где что лежит, чтобы не читать файлы целиком.
- `memes.py` (194 стр.) — DOG Монитор — DOG и крупнейшие мем-монеты разных сетей: дневные цены закрытия для графика сравнения на сайте.
- `mood.py` (411 стр.) — DOG Монитор — «страх и жадность»: два индекса всего рынка и свой индекс для DOG.
- `newsfeed.py` (114 стр.) — DOG Монитор — кандидаты в новости (для задачи Claude, которая отбирает и пишет их по-русски).
- `quiet.py` (35 стр.) — Runs a script from the closed part of DOG Monitor (dog-monitor/engine) inside a public GitHub Actions run.
- `selfcheck.js` (689 стр.) — DOG Монитор — автопроверка сайта в настоящем браузере (телефонный экран).
- `sitepub.py` (155 стр.) — Выкладка сводки DOG Монитора на публичный сайт.
- `siteurl.py` (80 стр.) — DOG Монитор — адрес сайта в одном месте.
- `whales.py` (292 стр.) — DOG Монитор — кошельки от 10 млн DOG: полный список, кто пришёл и кто ушёл, сверка балансов с блокчейном.

## .github/workflows/

- `alert.yml` — Сигнал о резком движении цены DOG (cron 7,22,37,52 * * * *)
- `daily.yml` — Обновление DOG Монитора (cron 41 5 * * *, 11 11 * * *, 11 16 * * *, 41 20 * * *)
- `fng.yml` — Страх и жадность (каждый час) и сторож сводки (cron 17 * * * *)
- `sitecheck.yml` — Проверка живого сайта (cron 23 */2 * * *)
