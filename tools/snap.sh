#!/usr/bin/env bash
# Разовый снимок рынка (BTC, DOG, EUR/USD, ставки) — временный, для анализа
set -u
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
NOW=$(date +%s)
O=mk5; mkdir -p $O
get() { curl -s -m 45 -A "$UA" -H "Accept: application/json,text/csv,text/html,*/*" -o "$O/$1" -w "$1 %{http_code} %{size_download}\n" "$2" >> $O/log.txt || echo "$1 ERR" >> $O/log.txt; sleep 0.7; }
d() { date -u -d @$1 +%FT%TZ; }
# --- BTC spot / history
get btc_ticker.json "https://api.exchange.coinbase.com/products/BTC-USD/ticker"
get btc_d1a.json "https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=86400"
get btc_d1b.json "https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=86400&start=$(d $((NOW-600*86400)))&end=$(d $((NOW-300*86400)))"
get btc_d1c.json "https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=86400&start=$(d $((NOW-900*86400)))&end=$(d $((NOW-600*86400)))"
get btc_h6.json "https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=21600"
get btc_h1.json "https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=3600"
get eth_d1.json "https://api.exchange.coinbase.com/products/ETH-USD/candles?granularity=86400"
get kraken_btc_d1.json "https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=1440"
get cb_usdt_eur.json "https://api.exchange.coinbase.com/products/USDT-EUR/ticker"
get cb_usdc_eur.json "https://api.exchange.coinbase.com/products/USDC-EUR/ticker"
# --- derivatives
get dvol.json "https://www.deribit.com/api/v2/public/get_volatility_index_data?currency=BTC&start_timestamp=$(( (NOW-200*86400)*1000 ))&end_timestamp=$((NOW*1000))&resolution=86400"
get deribit_opts.json "https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency=BTC&kind=option"
get deribit_fut.json "https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency=BTC&kind=future"
get deribit_index.json "https://www.deribit.com/api/v2/public/get_index_price?index_name=btc_usd"
get deribit_funding.json "https://www.deribit.com/api/v2/public/get_funding_rate_history?instrument_name=BTC-PERPETUAL&start_timestamp=$(( (NOW-20*86400)*1000 ))&end_timestamp=$((NOW*1000))"
get okx_funding.json "https://www.okx.com/api/v5/public/funding-rate-history?instId=BTC-USDT-SWAP&limit=100"
get okx_oi.json "https://www.okx.com/api/v5/rubik/stat/contracts/open-interest-volume?ccy=BTC&period=1D"
get okx_ls.json "https://www.okx.com/api/v5/rubik/stat/contracts/long-short-account-ratio?ccy=BTC&period=1D"
get okx_taker.json "https://www.okx.com/api/v5/rubik/stat/taker-volume?ccy=BTC&instType=CONTRACTS&period=1D"
curl -s -m 40 -X POST -H "Content-Type: application/json" -d '{"type":"metaAndAssetCtxs"}' https://api.hyperliquid.xyz/info -o $O/hl_ctx.json -w "hl_ctx %{http_code} %{size_download}\n" >> $O/log.txt
get fng.json "https://api.alternative.me/fng/?limit=200"
get cm_btc.json "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets=btc&metrics=CapRealUSD,SplyCur,CapMVRVCur,PriceUSD&frequency=1d&start_time=2024-01-01&page_size=10000"
# --- macro / FX (Yahoo)
for t in "%5EGSPC" "%5EIXIC" "DX-Y.NYB" "%5ETNX" "%5EIRX" "GC%3DF" "CL%3DF" "%5EVIX" "BTC-USD" "IBIT" "MSTR" "COIN" "EURUSD%3DX" "6E%3DF" "EURRUB%3DX" "RUB%3DX"; do get "yf_$(echo $t | tr -dc 'A-Za-z0-9').json" "https://query1.finance.yahoo.com/v8/finance/chart/$t?range=2y&interval=1d"; done
get yf_EURUSD_h1.json "https://query1.finance.yahoo.com/v8/finance/chart/EURUSD%3DX?range=1mo&interval=60m"
get kr_fx.json "https://api.kraken.com/0/public/Ticker?pair=EURUSD,USDTEUR,USDTUSD,USDCEUR,XBTEUR,USDCUSD"
get kr_eurusd_d1.json "https://api.kraken.com/0/public/OHLC?pair=EURUSD&interval=1440"
get kr_usdteur_d1.json "https://api.kraken.com/0/public/OHLC?pair=USDTEUR&interval=1440"
# --- rates (FRED, ECB)
for s in DGS2 DGS10 DFF ECBDFR DEXUSEU T10YIE; do get "fred_$s.csv" "https://fred.stlouisfed.org/graph/fredgraph.csv?id=$s&cosd=2024-06-01"; done
get ecb_exr.csv "https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A?format=csvdata&lastNObservations=700"
get ecb_yc2y.csv "https://data-api.ecb.europa.eu/service/data/YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y?format=csvdata&lastNObservations=500"
get ecb_yc10y.csv "https://data-api.ecb.europa.eu/service/data/YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y?format=csvdata&lastNObservations=500"
get ecb_estr.csv "https://data-api.ecb.europa.eu/service/data/EST/B.EU000A2X2A25.WT?format=csvdata&lastNObservations=300"
get cftc_eur.json "https://publicreporting.cftc.gov/resource/6dca-aqww.json?market_and_exchange_names=EURO%20FX%20-%20CHICAGO%20MERCANTILE%20EXCHANGE&\$order=report_date_as_yyyy_mm_dd%20DESC&\$limit=80"
get cftc_btc.json "https://publicreporting.cftc.gov/resource/6dca-aqww.json?market_and_exchange_names=BITCOIN%20-%20CHICAGO%20MERCANTILE%20EXCHANGE&\$order=report_date_as_yyyy_mm_dd%20DESC&\$limit=80"
get kalshi_fed.json "https://api.elections.kalshi.com/trade-api/v2/markets?series_ticker=KXFED&status=open&limit=200"
get kalshi_feddec.json "https://api.elections.kalshi.com/trade-api/v2/markets?series_ticker=KXFEDDECISION&status=open&limit=200"
get poly_fed.json "https://gamma-api.polymarket.com/public-search?q=fed%20december&limit_per_type=20"
# --- DOG order books / candles / trades
get dog_kraken_depth.json "https://api.kraken.com/0/public/Depth?pair=DOGUSD&count=500"
get dog_kraken_ticker.json "https://api.kraken.com/0/public/Ticker?pair=DOGUSD,DOGEUR"
get dog_kraken_h1.json "https://api.kraken.com/0/public/OHLC?pair=DOGUSD&interval=60&since=$((NOW-12*86400))"
get dog_kraken_d1.json "https://api.kraken.com/0/public/OHLC?pair=DOGUSD&interval=1440"
get dog_kraken_trades.json "https://api.kraken.com/0/public/Trades?pair=DOGUSD&since=$(( (NOW-3*86400) ))000000000&count=1000"
get dog_gate_book.json "https://api.gateio.ws/api/v4/spot/order_book?currency_pair=DOG_USDT&interval=0.00001&limit=100"
get dog_gate_raw.json "https://api.gateio.ws/api/v4/spot/order_book?currency_pair=DOG_USDT&limit=1000"
get dog_gate_ticker.json "https://api.gateio.ws/api/v4/spot/tickers?currency_pair=DOG_USDT"
get dog_gate_d1.json "https://api.gateio.ws/api/v4/spot/candlesticks?currency_pair=DOG_USDT&interval=1d&limit=1000"
get dog_gate_h1.json "https://api.gateio.ws/api/v4/spot/candlesticks?currency_pair=DOG_USDT&interval=1h&limit=400"
get dog_gate_trades.json "https://api.gateio.ws/api/v4/spot/trades?currency_pair=DOG_USDT&limit=1000"
get dog_mexc.json "https://api.mexc.com/api/v3/depth?symbol=DOGUSDT&limit=1000"
get dog_mexc_trades.json "https://api.mexc.com/api/v3/trades?symbol=DOGUSDT&limit=1000"
get dog_bingx.json "https://open-api.bingx.com/openApi/spot/v1/market/depth?symbol=DOG-USDT&limit=1000"
get dog_digifinex.json "https://openapi.digifinex.com/v3/order_book?symbol=dog_usdt&limit=150"
get dog_coinw.json "https://api.coinw.com/api/v1/public?command=returnOrderBook&symbol=DOG"
get dog_okx.json "https://www.okx.com/api/v5/market/books?instId=DOG-USDT&sz=400"
# --- DOG DATA (on-chain)
get dd_whales.json "https://www.dogdata.xyz/api/whale-alerts?threshold=5000000&limit=300"
get dd_top100.json "https://www.dogdata.xyz/api/top-holders?limit=100"
get dd_health.json "https://www.dogdata.xyz/api/health"
get dd_gate.json "https://www.dogdata.xyz/api/address/bitcoin/bc1pk8g4rztfkxs2q9c40g6keeknjw6aadx3kzu4suzlll0remfw7xxs5x9ctv?limit=60"
get dd_kraken.json "https://www.dogdata.xyz/api/address/bitcoin/bc1plzs2lltvv29k603w5m0aqma5e8w0n3pc77dt89l5w9hurmdfgd0swdhspn?limit=80"
cat $O/log.txt
