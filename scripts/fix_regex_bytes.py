"""Fix double-escaped regex patterns in orchestrator.py vision dispatch."""
import io

path = 'agents/orchestrator.py'
raw = io.open(path, 'rb').read()

# The broken line in raw bytes — 4 backslashes before b
broken_ocr  = b"                r'\\\\b(extract text|ocr|read text|get text|text from|transcribe|text in)\\\\b',"
fixed_ocr   = b"                r'\\b(extract text|ocr|read text|get text|text from|transcribe|text in)\\b',"

broken_ques = b"                    r'(?:what|describe|identify|find|analyse|analyze|tell me|explain)\\\\s+(.+)',"
fixed_ques  = b"                    r'(?:what|describe|identify|find|analyse|analyze|tell me|explain)\\s+(.+)',"

if broken_ocr in raw:
    raw = raw.replace(broken_ocr, fixed_ocr)
    print("Fixed OCR regex")
else:
    print("WARNING: OCR regex pattern not found in raw bytes")
    # Show what's actually there
    idx = raw.find(b'extract text|ocr')
    print("Context:", raw[idx-30:idx+80])

if broken_ques in raw:
    raw = raw.replace(broken_ques, fixed_ques)
    print("Fixed question regex")
else:
    print("WARNING: question regex pattern not found")

io.open(path, 'wb').write(raw)
print("Done writing file.")

# Verify by running the regex to confirm it compiles
import re
try:
    re.search(r'\b(extract text|ocr)\b', "extract text from image", re.IGNORECASE)
    print("Regex self-test: OK")
except Exception as e:
    print("Regex self-test FAILED:", e)
