"""Apply OCR intent detection fix to agents/orchestrator.py vision dispatch."""

path = 'agents/orchestrator.py'
lines = open(path, encoding='utf-8').read().splitlines(keepends=True)

# Find the block: lines 788-796 (0-indexed: 787-795)
# We'll identify them by content so it's line-number independent
start_marker = '        else:\r\n'
intent_marker = '            # Detect intent'
old_block_lines = []
start_idx = None

for i, line in enumerate(lines):
    if line == start_marker or line == '        else:\n':
        # Check next line is the Detect intent comment
        if i + 1 < len(lines) and '# Detect intent' in lines[i + 1]:
            start_idx = i
            break

if start_idx is None:
    print("ERROR: Could not find the 'else: # Detect intent' block")
    exit(1)

# Find end of block = first line at same indent level that is NOT inside this else
end_idx = start_idx + 1
while end_idx < len(lines):
    stripped = lines[end_idx].rstrip()
    # The block ends when we hit the next top-level block at 8-space indent
    # that is NOT indented further (i.e. starts new statement at 8 spaces)
    if stripped and not stripped.startswith('            ') and stripped.startswith('        ') and not stripped.startswith('        else'):
        break
    end_idx += 1

print(f"Replacing lines {start_idx+1} to {end_idx} (1-indexed)")
print("OLD BLOCK:")
for l in lines[start_idx:end_idx]:
    print(repr(l), end='')

eol = '\r\n' if '\r\n' in lines[0] else '\n'
new_block = (
    f'        else:{eol}'
    f'            # Detect OCR intent: "extract text", "ocr", "read text" etc. -> use Tesseract OCR{eol}'
    f'            ocr_intent = re.search({eol}'
    f"                r'\\\\b(extract text|ocr|read text|get text|text from|transcribe|text in)\\\\b',{eol}"
    f'                query, re.IGNORECASE{eol}'
    f'            ){eol}'
    f'            if ocr_intent:{eol}'
    f'                result = extract_text(filepath){eol}'
    f'                action = "extract_text"{eol}'
    f'            else:{eol}'
    f'                # Detect if user asks a specific question about the image{eol}'
    f'                question_match = re.search({eol}'
    f"                    r'(?:what|describe|identify|find|analyse|analyze|tell me|explain)\\\\s+(.+)',{eol}"
    f'                    query, re.IGNORECASE{eol}'
    f'                ){eol}'
    f'                question = question_match.group(0) if question_match else "Describe this image in detail."{eol}'
    f'                result = analyze_image(filepath, question=question){eol}'
    f'                action = "analyze_image"{eol}'
)

new_content = ''.join(lines[:start_idx]) + new_block + ''.join(lines[end_idx:])
open(path, 'w', encoding='utf-8').write(new_content)
print("\nSUCCESS: OCR intent detection applied.")
