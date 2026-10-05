import os
import re

file_map = {}
for root, dirs, files in os.walk('src'):
    for f in files:
        full_path = os.path.join(root, f).replace('\\\\', '/')
        file_map[full_path.lower()] = full_path

import_re = re.compile(r'import\s+.*?\s+from\s+[\'"](\.[^\'"]+)[\'"]')
for root, dirs, files in os.walk('src'):
    for f in files:
        if f.endswith(('.js', '.jsx')):
            file_path = os.path.join(root, f).replace('\\\\', '/')
            with open(file_path, 'r', encoding='utf-8') as file_obj:
                try:
                    content = file_obj.read()
                    for match in import_re.finditer(content):
                        imp_path = match.group(1)
                        if imp_path.startswith('.'):
                            base_dir = os.path.dirname(file_path)
                            parts = imp_path.split('/')
                            for p in parts:
                                if p == '.': continue
                                elif p == '..': base_dir = os.path.dirname(base_dir)
                                else: base_dir = base_dir + '/' + p
                            
                            for ext in ['', '.js', '.jsx', '/index.js', '/index.jsx']:
                                test_path = base_dir + ext
                                test_lower = test_path.lower()
                                if test_lower in file_map and test_path != file_map[test_lower]:
                                    print(f'Mismatch in {file_path}: imported {imp_path} -> expected {file_map[test_lower]}')
                except Exception:
                    pass
