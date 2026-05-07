#!/usr/bin/env python3
"""Select 20 stratified tasks for human evaluation."""
import json, random, sys, os
random.seed(42)

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
OUT = open('/tmp/human_eval_20_result.txt', 'w')

with open('leaderboard/data/leaderboard_100_tasks.json') as f:
    tasks = json.load(f)['tasks']

ct = {}
for t in tasks:
    c = t.get('refined_category', t.get('category', '?'))
    ct.setdefault(c, []).append((t['task_id'], t.get('difficulty', '?')))

# Proportional allocation
alloc = {c: max(1, round(len(v) / 100 * 20)) for c, v in ct.items()}
while sum(alloc.values()) > 20:
    for c in sorted(alloc, key=lambda x: len(ct[x])):
        if alloc[c] > 1:
            alloc[c] -= 1
            break
while sum(alloc.values()) < 20:
    for c in sorted(ct, key=lambda x: -len(ct[x])):
        if alloc[c] < len(ct[c]):
            alloc[c] += 1
            break

final = []
for c, n in alloc.items():
    he = [(t, d) for t, d in ct[c] if d in ('hard', 'expert')]
    md = [(t, d) for t, d in ct[c] if d == 'medium']
    ch = []
    if n >= 3 and md:
        ch = [random.choice(md)]
        r = list(he)
        random.shuffle(r)
        ch += r[:n - 1]
    else:
        ch = list(he)[:n]
        if len(ch) < n:
            ch += list(md)[:n - len(ch)]
    for tid, diff in ch:
        final.append((tid, c, diff))

final.sort(key=lambda x: (x[1], x[0]))
for i, (tid, c, d) in enumerate(final, 1):
    OUT.write(f"{i:>2}. {tid:<40} {c:<28} {d}\n")

ds = {}
cs = set()
for _, c, d in final:
    ds[d] = ds.get(d, 0) + 1
    cs.add(c)
OUT.write(f"\nDifficulty: {ds}\n")
OUT.write(f"Categories: {len(cs)}/{len(ct)}\n")
OUT.write(f"Total: {len(final)}\n")
OUT.close()
