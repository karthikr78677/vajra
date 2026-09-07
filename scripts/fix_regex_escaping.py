"""Fix the double-escaped regex backslashes in the OCR intent detection block."""
import io, re

path = 'agents/orchestrator.py'
content = io.open(path, encoding='utf-8').read()

# The broken line has 4 backslashes: \\\\b - fix to 2: \\b
broken_ocr  = r"r'\\\\b(extract text|ocr|read text|get text|text from|transcribe|text in)\\\\b'"
fixed_ocr   = r"r'\b(extract text|ocr|read text|get text|text from|transcribe|text in)\b'"

broken_ques = r"r'(?:what|describe|identify|find|analyse|analyze|tell me|explain)\\\\s+(.+)'"
fixed_ques  = r"r'(?:what|describe|identify|find|analyse|analyze|tell me|explain)\s+(.+)'"

content = content.replace(broken_ocr, fixed_ocr)
content = content.replace(broken_ques, fixed_ques)

io.open(path, 'w', encoding='utf-8').write(content)

# Verify
if fixed_ocr in content and fixed_ques in content:
    print("SUCCESS: Regex backslashes fixed.")
else:
    print("FAILED: something went wrong.")
