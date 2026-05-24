import os
import sys

def check_file(path):
    # Vietnamese characters
    vi_chars = set('àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ'
                   'ÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ'
                   ' \t\r\n.,;:!?"\'()[]{}-_+=<>/*&^%$#@~`|\\')

    with open(path, 'r', encoding='utf-8') as f:
        try:
            lines = f.readlines()
        except UnicodeDecodeError:
            return
            
    for i, line in enumerate(lines):
        for char in line:
            # Check if char is outside standard ASCII and not in standard Vietnamese
            if ord(char) > 127 and char not in vi_chars:
                if ord(char) > 10000:
                    continue
                out_lines.append(f"{path}:{i+1}: Found weird character {repr(char)} (U+{ord(char):04X}) in: {line.strip()}\\n")
                break

out_lines = []
for root, dirs, files in os.walk('.'):
    for file in files:
        if file.endswith('.py') or file.endswith('.json') or file.endswith('.md'):
            check_file(os.path.join(root, file))

with open('scan_results.txt', 'w', encoding='utf-8') as f:
    f.writelines(out_lines)
