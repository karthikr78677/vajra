path = 'agents/orchestrator.py'
content = open(path, encoding='utf-8').read()

# The comment line uses an em-dash (U+2014) in the original file
EMDASH = '\u2014'

old = (
    '        else:\n'
    '            # Detect intent ' + EMDASH + ' if user asks a specific question, pass it; else use general preset\n'
    '            question_match = re.search(\n'
    "                r'(?:what|describe|identify|find|analyse|analyze|tell me|explain)\\s+(.+)',\n"
    '                query, re.IGNORECASE\n'
    '            )\n'
    '            question = question_match.group(0) if question_match else "Describe this image in detail."\n'
    '            result = analyze_image(filepath, question=question)\n'
    '            action = "analyze_image"'
)

new = (
    '        else:\n'
    '            # Detect OCR intent: extract text, ocr, read text -> use Tesseract OCR\n'
    '            ocr_intent = re.search(\n'
    '                r"\\b(extract text|ocr|read text|get text|text from|transcribe|text in)\\b",\n'
    '                query, re.IGNORECASE\n'
    '            )\n'
    '            if ocr_intent:\n'
    '                result = extract_text(filepath)\n'
    '                action = "extract_text"\n'
    '            else:\n'
    '                # Detect if user asks a specific question about the image\n'
    '                question_match = re.search(\n'
    '                    r"(?:what|describe|identify|find|analyse|analyze|tell me|explain)\\s+(.+)",\n'
    '                    query, re.IGNORECASE\n'
    '                )\n'
    '                question = question_match.group(0) if question_match else "Describe this image in detail."\n'
    '                result = analyze_image(filepath, question=question)\n'
    '                action = "analyze_image"'
)

if old in content:
    content = content.replace(old, new, 1)
    open(path, 'w', encoding='utf-8').write(content)
    print('SUCCESS: OCR intent detection patched.')
else:
    print('NOT FOUND. Raw bytes around "Detect intent":')
    idx = content.find('Detect intent')
    print(repr(content[idx-20:idx+400]))
