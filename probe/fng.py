import os, shutil, subprocess, json
out = 'probe/out/m1'
os.makedirs(out, exist_ok=True)
env = dict(os.environ, WHALES_ENT_BUDGET='900')
for name, cmd in (('memes', ['python3', 'tools/memes.py', '.']), ('whales', ['python3', 'tools/whales.py', '.'])):
    r = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=1500)
    open(f'{out}/log_{name}.txt', 'w').write(f'rc={r.returncode}\n' + r.stdout + '\n--- stderr ---\n' + r.stderr)
for f in ('memes.json', 'whales.json', 'whales_map.json'):
    if os.path.exists('data/' + f):
        shutil.copy('data/' + f, f'{out}/{f}')
print(open(f'{out}/log_memes.txt').read()[:3000])
print(open(f'{out}/log_whales.txt').read()[:3000])
