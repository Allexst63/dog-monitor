#!/usr/bin/env bash
# Разовая проверка источников данных (временная)
set -u
O=probe/out; mkdir -p $O
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
get() {
  local n=$1 u=$2; shift 2
  curl -s -m 30 -A "$UA" -H "Origin: https://allexst63.github.io" -D "$O/$n.h" -o "$O/$n.body" "$@" "$u"
  echo "$n | $(head -1 $O/$n.h 2>/dev/null | tr -d '\r') | $(grep -i '^access-control-allow-origin' $O/$n.h 2>/dev/null | tr -d '\r') | $(wc -c < $O/$n.body 2>/dev/null)B | $u" >> $O/log.txt
  sleep 0.6
}
NOW=$(date +%s)
get dd_health https://www.dogdata.xyz/api/health
get dd_stats https://www.dogdata.xyz/api/dog-rune/stats
get dd_conc https://www.dogdata.xyz/api/metrics/holder-concentration
get dd_top "https://www.dogdata.xyz/api/dog-rune/top-holders?limit=100"
get dd_holders1 "https://www.dogdata.xyz/api/dog-rune/holders?page=1&limit=25"
get dd_markets https://www.dogdata.xyz/api/markets
get dd_home https://www.dogdata.xyz/
get dd_home2 https://dogdata.xyz/
get ord_kraken https://ordinals.com/address/bc1plzs2lltvv29k603w5m0aqma5e8w0n3pc77dt89l5w9hurmdfgd0swdhspn -H "Accept: application/json"
get ord_rune "https://ordinals.com/rune/DOG%E2%80%A2GO%E2%80%A2TO%E2%80%A2THE%E2%80%A2MOON" -H "Accept: application/json"
get ord_status https://ordinals.com/status -H "Accept: application/json"
get hiro_holders "https://api.hiro.so/runes/v1/etchings/840000:3/holders?limit=5"
get me_rune "https://api-mainnet.magiceden.dev/v2/ord/btc/runes/market/DOGGOTOTHEMOON/info"
get unisat "https://open-api.unisat.io/v1/indexer/runes/840000:3/holders?start=0&limit=5"
get ordiscan "https://api.ordiscan.com/v1/rune/DOGGOTOTHEMOON"
get mempool_tip https://mempool.space/api/blocks/tip/height
get mexc_depth "https://api.mexc.com/api/v3/depth?symbol=DOGUSDT&limit=100"
get mexc_trades "https://api.mexc.com/api/v3/trades?symbol=DOGUSDT&limit=50"
get bingx_depth "https://open-api.bingx.com/openApi/spot/v1/market/depth?symbol=DOG-USDT&limit=100"
get cb_candles "https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=86400&start=2024-04-20T00:00:00Z&end=2025-02-14T00:00:00Z"
get gate_tr_from "https://api.gateio.ws/api/v4/spot/trades?currency_pair=DOG_USDT&limit=100&from=$((NOW-900))"
# какие адреса API использует сам сайт dogdata.xyz
for f in dd_home dd_home2; do grep -oE '(src|href)="[^"]+\.js[^"]*"' $O/$f.body 2>/dev/null; done | sort -u | head -60 > $O/dd_scripts.txt
i=0
for s in $(grep -oE '"[^"]+\.js[^"]*"' $O/dd_scripts.txt | tr -d '"' | sort -u | head -40); do
  case "$s" in http*) u="$s";; //*) u="https:$s";; /*) u="https://www.dogdata.xyz$s";; *) u="https://www.dogdata.xyz/$s";; esac
  i=$((i+1)); curl -s -m 20 -A "$UA" "$u" -o "$O/js_$i.js"; echo "$i $u $(wc -c < $O/js_$i.js)" >> $O/dd_js_list.txt
done
cat $O/js_*.js 2>/dev/null | grep -oE '(https?://[a-zA-Z0-9._-]+(supabase|dogdata|api)[a-zA-Z0-9._/-]*|"/api/[a-zA-Z0-9/_?=&.-]+"|`/api/[^`]{1,80}`|supabase[a-zA-Z0-9._-]{0,40}|from\("[a-z_]+"\)|\.rpc\("[a-z_]+")' | sort | uniq -c | sort -rn | head -150 > $O/dd_api_refs.txt
rm -f $O/js_*.js
echo done >> $O/log.txt
