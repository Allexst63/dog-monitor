#!/usr/bin/env bash
# Разовая проверка (временная): библиотека графиков для локальных тестов
set -u
O=probe/out2; mkdir -p $O
curl -s -m 60 -o $O/lwc.js https://cdn.jsdelivr.net/npm/lightweight-charts@5.0.8/dist/lightweight-charts.standalone.production.js
echo "lwc $(wc -c < $O/lwc.js)" >> $O/log.txt
curl -s -m 30 -o $O/mexc_aggtrades.json "https://api.mexc.com/api/v3/aggTrades?symbol=DOGUSDT&limit=20"
echo done >> $O/log.txt
