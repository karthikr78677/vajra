"""Debug: show the exact bytes of lines 809-813."""
import io
lines = io.open('agents/orchestrator.py', encoding='utf-8').read().splitlines()
for i, line in enumerate(lines, 1):
    if 808 <= i <= 825:
        io.open('scripts/exact_lines.txt', 'a', encoding='utf-8').write(f"{i}: {repr(line)}\n")

txt = io.open('scripts/exact_lines.txt', encoding='utf-8').read()
print(txt)
