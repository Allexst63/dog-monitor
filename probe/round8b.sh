#!/bin/bash
# round 8b: full run of the new top-100 balance fetch (paced, with time budgets)
set +e
O=probe/out8; mkdir -p $O
mkdir -p /tmp/dm/raw /tmp/dm/prev/live; cp probe/live_main.json /tmp/dm/prev/live/current.json
timeout 600 python3 -u probe/fetch_new.py /tmp/dm/raw stats holders_1 holders_2 holders_3 holders_4 whales ordbal
head -2 /tmp/dm/raw/ordbal.txt | cut -c1-400
echo "xverse rows: $(grep -c ';xv$' /tmp/dm/raw/ordbal.txt)  err rows: $(grep -c '^ERR' /tmp/dm/raw/ordbal.txt)  rows: $(wc -l < /tmp/dm/raw/ordbal.txt)"
cp /tmp/dm/raw/ordbal.txt $O/ordbal.txt
python3 - <<'PY'
import json
d=json.load(open('/tmp/dm/raw/json/ordbal.json')); print({k:(v if k!='failed' else list(v.values())[:6]) for k,v in d.items()})
PY
echo "== second run right away (reuse)"
timeout 300 python3 -u probe/fetch_new.py /tmp/dm/raw ordbal
head -1 /tmp/dm/raw/ordbal.txt
