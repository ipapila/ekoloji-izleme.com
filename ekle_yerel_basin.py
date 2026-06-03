#!/usr/bin/env python3
"""
tarayici.py'ye yerel basın kaynaklarını ekler.
Kullanim: python3 ekle_yerel_basin.py tarayici.py
"""
import sys
import importlib.util
from pathlib import Path

TARGET = sys.argv[1] if len(sys.argv) > 1 else "tarayici.py"

# yerel_basin_kaynaklari.py'yi yükle
spec = importlib.util.spec_from_file_location(
    "yerel", Path(TARGET).parent / "yerel_basin_kaynaklari.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
YEREL = mod.YEREL_BASIN_TUM

content = open(TARGET, encoding="utf-8").read()

# RSS_KAYNAKLARI listesinin sonunu bul
# "RAPOR / ANALİZ" başlığından önce ekle
EKLEME_NOKTASI = "# ══════════════════════════════════════════════════════════════════\n#  RAPOR / ANALİZ KAYNAKLARI"

if EKLEME_NOKTASI not in content:
    print("❌ Ekleme noktası bulunamadı. tarayici.py yapısı değişmiş olabilir.")
    sys.exit(1)

# Yeni kaynak bloğunu oluştur
satırlar = ["# ══════════════════════════════════════════════════════════════════\n"]
satırlar.append("#  YEREL BASIN KAYNAKLARI — 7 BÖLGE, TÜM TÜRKİYE\n")
satırlar.append("# ══════════════════════════════════════════════════════════════════\n\n")

for kaynak in YEREL:
    satırlar.append("    {\n")
    for k, v in kaynak.items():
        if isinstance(v, str):
            satırlar.append(f'     "{k}": "{v}",\n')
        else:
            satırlar.append(f'     "{k}": {v},\n')
    satırlar.append("    },\n")

yeni_blok = "".join(satırlar)

# RSS_KAYNAKLARI listesinin son elemanından sonra ekle
# "]" kapanışından önce yerel kaynakları ekle
LISTE_SONU = "]\n\n# ══════════════════════════════════════════════════════════════════\n#  RAPOR / ANALİZ KAYNAKLARI"
YENI_LISTE_SONU = "    # ── Yerel Basın ──\n" + yeni_blok + "]\n\n# ══════════════════════════════════════════════════════════════════\n#  RAPOR / ANALİZ KAYNAKLARI"

if LISTE_SONU not in content:
    print("❌ RSS_KAYNAKLARI liste sonu bulunamadı.")
    print("Manuel ekleme gerekiyor — yerel_basin_kaynaklari.py'deki YEREL_BASIN_TUM listesini")
    print("RSS_KAYNAKLARI listesinin sonuna ( ] kapanmadan önce) ekleyin.")
    sys.exit(1)

# Yedek al
import shutil
shutil.copy(TARGET, TARGET + ".bak_yerel")
print(f"✓ Yedek alındı: {TARGET}.bak_yerel")

content = content.replace(LISTE_SONU, YENI_LISTE_SONU, 1)
open(TARGET, "w", encoding="utf-8").write(content)

print(f"✓ {len(YEREL)} yerel kaynak eklendi")
print(f"✓ {TARGET} güncellendi")

# Özet
from collections import Counter
bolgeler = Counter(k["kategori"].split("/")[1].strip() if "/" in k["kategori"] else k["kategori"] for k in YEREL)
print("\nBölge dağılımı:")
for bolge, sayi in sorted(bolgeler.items()):
    print(f"  {bolge:25s}: {sayi} kaynak")
