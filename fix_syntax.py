import re

with open('vuln_pipeline.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the multiline f-string
old = '''    user_content = f"{prompt}

--- DECOMPILED PSEUDO-C START ---

{pseudo_c}

--- DECOMPILED PSEUDO-C END ---"'''

new = '    user_content = f"{prompt}\\n\\n--- DECOMPILED PSEUDO-C START ---\\n\\n{pseudo_c}\\n\\n--- DECOMPILED PSEUDO-C END ---"'

if old in content:
    content = content.replace(old, new)
    with open('vuln_pipeline.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK')
else:
    print('NOT FOUND')
