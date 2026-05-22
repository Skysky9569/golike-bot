import re
with open('golikefb_sele.py', 'r', encoding='utf-8') as f:
    text = f.read()
text = re.sub(r'CURRENT_VERSION\s*=\s*\"1\.8\.\d+\".*', 'CURRENT_VERSION = "1.8.8" # v1.8.8: Fixed updater recursive folder sync', text)
with open('golikefb_sele.py', 'w', encoding='utf-8') as f:
    f.write(text)
