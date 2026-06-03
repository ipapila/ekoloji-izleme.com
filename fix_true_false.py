#!/usr/bin/env python3
"""
tarayici.py'deki JSON-style true/false değerlerini Python True/False'a çevirir.
Kullanim: python3 fix_true_false.py tarayici.py
"""
import sys, shutil, re

TARGET = sys.argv[1] if len(sys.argv) > 1 else "tarayici.py"
content = open(TARGET, encoding="utf-8").read()

# "genel": true  →  "genel": True
# "genel": false →  "genel": False
# Sadece dict value olarak kullanılan true/false (string içindeki değil)

once = content.count('"genel": true') + content.count('"genel": false')

content = re.sub(r'("genel":\s*)true\b', r'\1True', content)
content = re.sub(r'("genel":\s*)false\b', r'\1False', content)

sonra = content.count('"genel": true') + content.count('"genel": false')

print(f"✓ {once - sonra} adet true/false → True/False dönüştürüldü")

# Syntax kontrolü
try:
    compile(content, TARGET, 'exec')
    print("✓ Syntax kontrolü geçti")
except SyntaxError as e:
    print(f"❌ Syntax hatası: {e}")
    sys.exit(1)

shutil.copy(TARGET, TARGET + ".bak_tf")
open(TARGET, "w", encoding="utf-8").write(content)
print(f"✓ {TARGET} güncellendi")
