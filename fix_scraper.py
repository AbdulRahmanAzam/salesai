import sys

path = r'C:\Users\azama\VS Code\PROJECTS\02 Startup Projects\sales\src\prospecting_agent\sources\web_scraper.py'
with open(path, 'rb') as f:
    raw = f.read()

idx = raw.find(b'_NAME_RE')
print("BEFORE repr:", repr(raw[idx:idx+100]))

# The broken line bytes: b"    r'\\b((?:[A-Z][a-z\\''-]+\\s+){1,2}[A-Z][a-z\\''-]+)\\b'\r"
# Replace with double-quoted raw string using only one apostrophe in char class
old_line = b"    r'\\b((?:[A-Z][a-z\\''-]+\\s+){1,2}[A-Z][a-z\\''-]+)\\b'\r"
new_line = b'    r"\\b((?:[A-Z][a-z\' -]+\\s+){1,2}[A-Z][a-z\' -]+)\\b"\r'

print("old_line in content:", old_line in raw)
raw2 = raw.replace(old_line, new_line)
print("Changed bytes:", raw != raw2)

with open(path, 'wb') as f:
    f.write(raw2)

idx2 = raw2.find(b'_NAME_RE')
print("AFTER repr:", repr(raw2[idx2:idx2+100]))
