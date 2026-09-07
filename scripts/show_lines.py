import io
lines = io.open('agents/orchestrator.py', encoding='utf-8').read().splitlines()
out = []
for i, line in enumerate(lines, 1):
    if 800 <= i <= 835:
        out.append(f"{i}: {line}")
io.open('scripts/lines_800_835.txt', 'w', encoding='utf-8').write('\n'.join(out))
print('Written to scripts/lines_800_835.txt')
