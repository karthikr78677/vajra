import re

path = 'agents/orchestrator.py'
content = open(path, encoding='utf-8').read()

new_block = """        else:
            # Detect OCR intent: "extract text", "ocr", "read text" etc. -> use Tesseract OCR
            ocr_intent = re.search(
                r'\\b(extract text|ocr|read text|get text|text from|transcribe|text in)\\b',
                query, re.IGNORECASE
            )
            if ocr_intent:
                result = extract_text(filepath)
                action = "extract_text"
            else:
                # Detect if user asks a specific question about the image
                question_match = re.search(
                    r'(?:what|describe|identify|find|analyse|analyze|tell me|explain)\\s+(.+)',
                    query, re.IGNORECASE
                )
                question = question_match.group(0) if question_match else "Describe this image in detail."
                result = analyze_image(filepath, question=question)
                action = "analyze_image\""""

pattern = re.compile(r'        else:\n\s*# Detect intent.*?action = "analyze_image"', re.DOTALL)
match = pattern.search(content)
if match:
    # Use replace to avoid sub escape issues
    content = content.replace(match.group(0), new_block)
    open(path, 'w', encoding='utf-8').write(content)
    print('SUCCESS: Patched vision dispatch!')
else:
    print('FAILED to match block.')
