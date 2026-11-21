# Карта кода DOG Монитора

> Собрано `python3 tools/map.py` — не править руками. Смотреть сначала сюда, потом читать только нужные строки.

## index.html

index.html — 8497 строк. Разделы (строка начала) и функции раздела (имя:строка).

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

- **1917: language: English only (the Russian version lives in git history, branch design-v10-ru)** — P:1922, nTitle:1929, nSum:1930, srcTr:1931, bandTr:1933, ico:1980, RM:1981
- **1986: rolling digits («барабан»): a number that changes by itself (live price, the DOG index, t…** — rollTr:1990, rollNum:1991, rollLh:1992, rollBuild:1997, rollSet:2008
- **2049: switches: the selected option's background is its own «pill» that glides to the new choic…** — slKey:2054, slBtns:2055, slPlace:2056, slScan:2082
- **2148: a list of choices (the order book's price step): the chosen row has a highlight that glid…** — vswPlace:2150, vswPick:2162
- **2225: formatting** — grp:2227, n:2228, fp:2233, dol:2242, fpd:2243, sg:2244, dir:2250, cls:2251, dcls:2252, short:2253, mdog:2254, usd:2255, usdM:2265, m1:2266, m1usd:2267, m1s:2268, toDate:2271, dtl:2285, tl:2286, dml:2287, sameDay:2288, when:2289, ago:2295, dayName:2304, isFull:2311
- **2313: owner labels** — nameTr:2315, noteTr:2354, chkTr:2378, ownName:2384, avatar:2389, kindTag:2394, whoTxt:2396
- **2398: view data** — V:2399, skelHtml:2400, topStale:2401, staleTxt:2407, topSince:2408, prevLabel:2412, biggestWall:2416, wallText:2427
- **2436: navigation** — navHtml:2437, setBadge:2443, tbSync:2444, setTab:2445
- **2567: status** — setStatus:2568
- **2597: bottom sheet** — SH:2599, isPhone:2600, sheetReset:2601, openSheet:2606, closeSheet:2620, copyBtn:2721, toast:2735
- **2742: charts** — niceTicks:2743, svgEl:2751, attachCross:2752
- **2788: price: chart data** — priceRows:2789, priceSeries:2815, pillTxt:2816
- **2817: Home: price and chart — Kraken candles by interval, as on Charts (15m · 1h · 4h · 1d · 1w)** — heroRows:2822, heroKey:2828, pxRepOf:2832, pxRep:2833, nowPx:2834, pxSrc:2836, pxSrcSync:2838, chg24:2844, setHero:2847, resetHero:2861, scrubHero:2862, chartLabel:2868
- **2873: price: TradingView Lightweight Charts (Apache-2.0)** — lwRedraw:2877, ut:2899, fuDM:2900, tickFmt:2901, killChart:2909, addSer:2910, heroAt:2916, heroPin:2922, hlegSet:2933, hwhatSync:2941, lastBtn:2966, toEnd:2974, hGap:2988, rClamp:2989, lastSync:2996, heroGrow:3006, hlegMargins:3023, drawLW:3027
- **3091: Home chart height: first screen shows indexes, price and the whole chart** — fitHomeChart:3093
- **3114: light tick under the finger when it moves to another candle** — haptic:3116
- **3130: Home chart by finger — like exchange apps**
- **3277: other (own SVG) charts: a sideways finger never scrolls the page** — drawPrice:3301, drawPriceSvg:3329, lineChart:3361
- **3395: moon** — moonSvg:3396
- **3409: daily summary in English, built from the same data as the report (tools/dogmon.py highlig…** — alertsEn:3410, isExK:3443, briefOf:3444
- **3460: stories** — dOf:3461, treItem:3462, buildStories:3467, sparkSvg:3519, storyKey:3528, markSeen:3529, SF:3537, openStory:3538, closeStory:3558, showSlide:3580, nextSlide:3599, prevSlide:3605, nextStory:3610, prevStory:3611, pauseStory:3612, resumeStory:3619, springStory:3627
- **3689: news** — freshNews:3690
- **3695: live price: Kraken and Gate over WebSocket (public site only)** — livePrice:3696, livePx:3698, liveChg:3699, applyLive:3700, liveSock:3731, liveMid:3750, livePush:3759, liveRest:3768, liveSoon:3780, startLive:3785
- **3816: HOME** — histDelta:3817, heroStats:3826, renderOverview:3829, refreshHomeParts:3863
- **3868: fear & greed: whole market (alternative.me, CoinMarketCap) and DOG (own index, tools/mood…** — fngZi:3871, fngCol:3872, fngName:3873, fngDay:3874, capS:3875, gaugeSvg:3876, fngMarket:3888, fngCmc:3892
- **3893: DOG index "now": read off the server's curve for today (the index as a function of DOG's …** — dogLive:3895, fngNow:3907, fngTick:3908, fngSheetLive:3913, fngHtml:3932, paintFng:3948, fngLive:3963, fngSpark:3975, fngKv:3982, FNG_SCALE:3983, fngMktChart:3987, fngMarketSheet:3994, fngCmcSheet:4006, fngDmy:4019
- **4020: index chart with price (DOG or bitcoin): tap or slide — date, index and price** — btcFmt:4023, btcNowMap:4024, pxMap:4025, fngGe:4029, fngLe:4030, fngTurns:4031, fngTurnsList:4043, ficPath:4049, fngChart:4051, ficRead:4071, ficSet:4078, ficAt:4092, fngDogSheet:4117, tile:4170, moodOf:4171, xTxt:4179, whNow:4180, whSince:4189, tilesHtml:4190, evHtml:4201, bigK:4204, bigMin:4205, bigLab:4206, stpHtml:4207, stpPaint:4214, stpSet:4222, summaryHtml:4251, briefSheet:4261, exchangesHtml:4269, mirNoteHtml:4284, monY:4289, treChart:4290, treasuryHtml:4310
- **4321: Home → DOG and meme coins: six cards for 7, 30 or 90 days. A new period re-ranks the 12 c…** — monoSpline:4328, hmSpark:4348, hmData:4355, hmKey:4369, hmX:4370, hmLine:4371, hmArea:4372, hmAria:4373, hmCard:4374, memesMiniHtml:4378, hmPaint:4387, hmSwitch:4394, hmMorph:4433, treSheet:4450, events:4468, hbarsHtml:4477, ageCardHtml:4478, exchCardHtml:4492, histLine:4505, ddSer:4515, serLine:4523, serDelta:4531, statD:4537
- **4539: "what this means" notes** — infoBtn:4540, hInfo:4541, openInfo:4617, sheetNavSync:4635, animateIntro:4639, openChecks:4665, openMore:4667
- **4689: ORDER BOOK**
- **4690: ORDER BOOK: combined book, like an exchange** — toU:4700, stepDec:4701, fpx:4702, pctOf:4703, qf:4704, usdC:4712, amtF:4718, agoS:4719
- **4721: order book data** — obFresh:4730, obPut:4731, obSeed:4754, obFetch:4764, obLoop:4783
- **4804: Kraken, Gate, MEXC and BingX live: WebSocket** — gT:4805, wsCan:4813, wsOpen:4814, wsClose:4841, wsWant:4847, wsOn:4852, wsReset:4853, wsSend:4854, wsAlive:4855, wsBook:4861, trLive:4879, krakenMsg:4888, krakenFlush:4905, gateMsg:4915, wsTrades:4924, pbRead:4934, pbStr:4945, mexcMsg:4946, bingxMsg:4973
- **4990: mirror exchange: a book that repeats another exchange (same orders twice)** — obLad:4992, obMirOf:4999, obSrc:5015, obDeep:5033, obOldDeep:5067, obHybrid:5074, obMidOf:5084, obPx:5088, obSet:5096, obFineStep:5123, obAgg:5124, obRef:5185, obCtx:5189, obRowsN:5194, obBand:5195, obHistPush:5202
- **5211: feed: big orders added, pulled, resized — while the site is open** — obDiff:5212, obEvText:5237
- **5246: view: exchanges, book, metrics** — segB:5247, obChipsHtml:5253, obNoteHtml:5262, obSepHtml:5297, obBookHtml:5303, obStatusHtml:5368, obAge:5379, obCardHtml:5384
- **5396: who is stronger near the price: plain-words book summary** — obFine:5397, obImbHtml:5398, obMetricsHtml:5417, obImbSheet:5466, obBigHtml:5467, obChgHtml:5479
- **5489: book feed** — obFeedHtml:5490
- **5499: trades: what actually executed (Kraken and Gate)** — trParse:5502, trPut:5520, trFetch:5536, tls:5545, trHtml:5546
- **5567: level details (tap a book row)** — obRowSheet:5568, obStepSheet:5608
- **5620: indicators: moving averages and RSI (Charts tab)** — taSma:5621, taEma:5622, taRsi:5630, drawDepth:5641
- **5679: each exchange** — depthRow:5680, wallList:5687, exListHtml:5701, exSheet:5713, exCardsHtml:5718, venuesHtml:5757
- **5773: Order book tab** — renderBooks:5774
- **5798: smooth repaint (v21): the new HTML is laid over the old DOM instead of replacing it («mor…** — mKey:5804, mSkip:5805, mAttrs:5806, mNode:5814, mKids:5831, morph:5849, obPaintBook:5850, obSoon:5864, obPaint:5875
- **5941: CHARTS: TradingView-style candles (RSI and MACD below), delta and correlation with bitcoin** — chIntra:5949, chSrc:5950, weekStart:5951, tvUrl:5954, tvLinkFor:5955, tvFix:5959, tvFixAll:5967, hexA:5970, chColors:5971, lwOk:5975, lwSer:5976, lwChart:5977, chKill:5990, lwPanes:5991, chWait:5992, lwFailTxt:5993
- **5995: Kraken candles** — chStored:5996, chWeekly:6000, chInstant:6012, chFresh:6022, chOhlc:6023
- **6040: deep history: Kraken keeps 720 candles, older ones come from Gate (DOG/USDT)** — pxDays:6047, chFull:6056, chKeepLost:6064, chCanMore:6072, chLoadingMore:6073, gateRows:6074, chMore:6082, chMoreDone:6118, chMoreUi:6123, chWithLive:6134, chInd:6142
- **6154: main chart** — chDrawTV:6155, chFill:6257, chGrow:6274, chPin:6290, tvLabels:6296, chLegend:6307, chRead:6319, chLive:6343
- **6353: DOG and bitcoin since DOG launch** — crSrv:6354, crBtc:6355, corrOf:6382, betaOf:6383, crCalc:6384, corrWord:6400, mvEn:6401, crDraw:6402
- **6497: DOG and meme coins (data/memes.json, tools/memes.py): change since the start of the period** — mmCol:6501, mmPct:6503, mmCalc:6504, mmTicks:6529, mmDraw:6540, mmPlot:6554, mmShow:6567, mmNote:6588, mmIdx:6595, mmNear:6596
- **6621: Charts tab** — chStatsHtml:6622
- **6629: Fear & greed: the history of all three indices. Lives right on the Charts tab (#f3s-in) a…** — f3sR:6635, f3sLinks:6636, fngChartsHtml:6641, f3sKey:6648, paintFngCharts:6649, f3sData:6658, f3Date:6681, f3Ax:6682, f3sPx:6684, f3sRead:6692, f3sPaneIn:6703, f3sPane:6716, f3sPlot:6717, f3sStats:6730, f3sBody:6740, fngAllSheet:6749, f3sPer:6757, f3sSet:6771, f3sFocus:6791, f3sShow:6809, f3sRestore:6816, f3sAt:6821, f3GoBtn:6853, renderCharts:6862, chDrawAll:6894, chLoop:6899
- **6938: WALLETS** — walletSheet:6939
- **6956: average DOG cost per wallet (data/costbasis.json, tools/costbasis.py)** — costOf:6957, curPrice:6958, vsAvg:6959, airTxt:6964, costLine:6965, costBlock:6972, holdersCost:6989
- **6999: balance sparklines (data/wallets.json)** — isEx:7000, balSeries:7001, sparkW:7007
- **7025: wallets: 24h summary** — walletsSummaryHtml:7026
- **7049: wallets: who holds DOG** — ownersData:7050, ownersHtml:7063, countTo:7072, tierState:7088, tierAnim:7094, ring1:7113, tiersData:7122, tiersHtml:7151, whSpark:7197, whalesDetail:7207, whalesCardHtml:7267, t100ChgHtml:7283, renderWallets:7291, balanceCols:7336
- **7372: NEWS** — renderNews:7373
- **7410: HISTORY** — renderHistory:7411, drawHistCharts:7427
- **7447: GUIDE** — renderHelp:7479
- **7488: shared render** — drawCharts:7489
- **7499: UPDATE NOW: fresh data straight from the page + self-check** — cachedOhlc:7520, pause:7534, num:7535, rnd:7536, sumOf:7537, median:7538, mirScore:7539, isMir:7552, pad2:7553, hmU:7554, isoS:7555, isExK2:7556, upGet:7558, prevSnap:7570
- **7578: parsing responses** — lvls:7579, parseBook:7589, firstList:7605, addrOf:7614, ohlcRows:7615
- **7626: calculation, as in tools/dogmon.py** — depthOf:7627, ladderOf:7636, wallsOf:7642, wallChanges:7647, wdKey:7678, entMap:7679, prevTopOf:7690, chartOf:7698
- **7716: live summary on top of the morning report** — buildLive:7717, sinceItems:7933
- **7977: startup** — runUpdate:7980, applyUpdate:8025, scheduleSoft:8041, softRender:8046, refreshChart:8071
- **8086: update UI** — upRowState:8087, srcListHtml:8094, chkLi:8107, updSheetHtml:8108, openUpd:8139, paintUpd:8143, autoTick:8156, isStandalone:8213, isIOS:8214, installRowHtml:8215, themeNow:8234, setTheme:8235, themeSwitch:8243
- **8249: keep the screen on: on an iPad or a computer the page can stand on the table like a clock…** — awakeOn:8253, wakeSync:8254
- **8274: visit counts: Umami Cloud — no cookies, nothing personal. Off while UMAMI_ID is empty** — track:8279, siteUrl:8307, renderAll:8324
- **8335: site data: JSON files in data/, refreshed by the scheduled update** — siteDb:8336

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
- `selfcheck.js` (694 стр.) — DOG Монитор — автопроверка сайта в настоящем браузере (телефонный экран).
- `sitepub.py` (155 стр.) — Выкладка сводки DOG Монитора на публичный сайт.
- `siteurl.py` (80 стр.) — DOG Монитор — адрес сайта в одном месте.
- `whales.py` (292 стр.) — DOG Монитор — кошельки от 10 млн DOG: полный список, кто пришёл и кто ушёл, сверка балансов с блокчейном.

## .github/workflows/

- `alert.yml` — Сигнал о резком движении цены DOG (cron 7,22,37,52 * * * *)
- `daily.yml` — Обновление DOG Монитора (cron 41 5 * * *, 11 11 * * *, 11 16 * * *, 41 20 * * *)
- `fng.yml` — Страх и жадность (каждый час) и сторож сводки (cron 17 * * * *)
- `sitecheck.yml` — Проверка живого сайта (cron 23 */2 * * *)
