#!/bin/bash
# round 7: vendor the chart library, check the TradingView symbol, full run of the new top-100 balance fetch
set +e
O=probe/out7; mkdir -p $O
echo "== lightweight-charts"
curl -sSL -m 60 -o $O/lightweight-charts.standalone.production.js https://cdn.jsdelivr.net/npm/lightweight-charts@5.0.8/dist/lightweight-charts.standalone.production.js
curl -sSL -m 60 -o $O/LICENSE https://cdn.jsdelivr.net/npm/lightweight-charts@5.0.8/LICENSE
curl -sSL -m 60 -o $O/NOTICE https://cdn.jsdelivr.net/npm/lightweight-charts@5.0.8/NOTICE
(cd /tmp && npm pack lightweight-charts@5.0.8 >/dev/null 2>&1 && tar xzf lightweight-charts-5.0.8.tgz)
cmp /tmp/package/dist/lightweight-charts.standalone.production.js $O/lightweight-charts.standalone.production.js && echo "npm tarball == jsDelivr: identical"
sha256sum $O/lightweight-charts.standalone.production.js; wc -c $O/*
cp /tmp/package/dist/typings.d.ts $O/typings.d.ts 2>/dev/null
echo "== TradingView symbol"
UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'
for u in 'https://www.tradingview.com/symbols/DOGUSD/?exchange=KRAKEN' 'https://www.tradingview.com/chart/?symbol=KRAKEN%3ADOGUSD' 'https://www.tradingview.com/symbols/DOGUSDT/?exchange=GATEIO' 'https://www.tradingview.com/symbols/NOSUCHPAIRXYZ/?exchange=KRAKEN'; do
  curl -sS -m 30 -o /tmp/tv.html -w "%{http_code} %{size_download} %{url_effective}\n" -L -A "$UA" "$u"; grep -o '<title>[^<]*</title>' /tmp/tv.html | head -1
done
curl -sS -m 30 -A "$UA" -H 'Origin: https://www.tradingview.com' -H 'Referer: https://www.tradingview.com/' 'https://symbol-search.tradingview.com/symbol_search/v3/?text=DOGUSD&hl=0&exchange=KRAKEN&lang=en&search_type=undefined&domain=production' | head -c 1200; echo
curl -sS -m 30 -A "$UA" -H 'Origin: https://www.tradingview.com' -H 'Referer: https://www.tradingview.com/' 'https://symbol-search.tradingview.com/symbol_search/v3/?text=DOG&hl=0&exchange=KRAKEN&lang=en&domain=production' | head -c 1500; echo
echo "== coinbase btc daily"
curl -sS -m 30 "https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=86400&start=2026-10-01T00:00:00Z&end=2026-11-10T00:00:00Z" -A "$UA" | head -c 300; echo
echo "== new ordbal, full run"
mkdir -p /tmp/dm/raw /tmp/dm/prev/live; cp probe/live_main.json /tmp/dm/prev/live/current.json
python3 -u probe/fetch_new.py /tmp/dm/raw stats holders_1 holders_2 holders_3 holders_4 whales ordbal
head -3 /tmp/dm/raw/ordbal.txt | cut -c1-300
echo "xverse rows: $(grep -c ';xv$' /tmp/dm/raw/ordbal.txt)  err rows: $(grep -c '^ERR' /tmp/dm/raw/ordbal.txt)  rows: $(wc -l < /tmp/dm/raw/ordbal.txt)"
cp /tmp/dm/raw/ordbal.txt $O/ordbal.txt
python3 - <<'PY'
import json
d=json.load(open('/tmp/dm/raw/json/ordbal.json')); print({k:(v if k!='failed' else list(v.values())[:5]) for k,v in d.items()})
PY
echo "== second run right away (stability)"
python3 -u probe/fetch_new.py /tmp/dm/raw ordbal
head -1 /tmp/dm/raw/ordbal.txt
