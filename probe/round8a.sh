#!/bin/bash
# round 8a: vendor the chart library, check the TradingView symbol
set +e
O=probe/out8; mkdir -p $O
echo "== lightweight-charts"
curl -sSL -m 60 -o $O/lightweight-charts.standalone.production.js https://cdn.jsdelivr.net/npm/lightweight-charts@5.0.8/dist/lightweight-charts.standalone.production.js
curl -sSL -m 60 -o $O/LICENSE https://cdn.jsdelivr.net/npm/lightweight-charts@5.0.8/LICENSE
curl -sSL -m 60 -o $O/NOTICE https://cdn.jsdelivr.net/npm/lightweight-charts@5.0.8/NOTICE
curl -sSL -m 60 -o $O/typings.d.ts https://cdn.jsdelivr.net/npm/lightweight-charts@5.0.8/dist/typings.d.ts
(cd /tmp && timeout 90 npm pack lightweight-charts@5.0.8 >/dev/null 2>&1 && tar xzf lightweight-charts-5.0.8.tgz)
cmp /tmp/package/dist/lightweight-charts.standalone.production.js $O/lightweight-charts.standalone.production.js && echo "npm tarball == jsDelivr: identical"
sha256sum $O/lightweight-charts.standalone.production.js; wc -c $O/*
echo "== TradingView symbol"
UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'
for u in 'https://www.tradingview.com/symbols/DOGUSD/?exchange=KRAKEN' 'https://www.tradingview.com/chart/?symbol=KRAKEN%3ADOGUSD' 'https://www.tradingview.com/symbols/DOGUSDT/?exchange=GATEIO' 'https://www.tradingview.com/symbols/NOSUCHPAIRXYZ/?exchange=KRAKEN'; do
  curl -sS -m 30 -o /tmp/tv.html -w "%{http_code} %{size_download} %{url_effective}\n" -L -A "$UA" "$u"; grep -o '<title>[^<]*</title>' /tmp/tv.html | head -1
done
curl -sS -m 30 -A "$UA" -H 'Origin: https://www.tradingview.com' -H 'Referer: https://www.tradingview.com/' 'https://symbol-search.tradingview.com/symbol_search/v3/?text=DOGUSD&hl=0&exchange=KRAKEN&lang=en&domain=production' | head -c 1200; echo
echo "== coinbase btc daily"
curl -sS -m 30 "https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=86400&start=2026-10-01T00:00:00Z&end=2026-11-10T00:00:00Z&cb=1" -A "$UA" | head -c 300; echo
