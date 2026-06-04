#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
arsiv_goc.py — Mevcut JSON dosyalarındaki tüm verileri aya göre arşivler.
Tek seferlik çalıştırılır. Mevcut arsiv/ dosyalarına dokunmaz.

Kullanim: python3 arsiv_goc.py
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

ARSIV_DIR = Path("arsiv")
ARSIV_DIR.mkdir(exist_ok=True)

# Kaynak dosyalar → arşiv adı → JSON anahtarı
KAYNAKLAR = [
    ("haberler.json",  "haberler",  "haberler"),
    ("ihlaller.json",  "ihlaller",  "ihlaller"),
    ("raporlar.json",  "raporlar",  "raporlar"),
    ("makaleler.json", "makaleler", "makaleler"),
    ("kuresel.json",   "kuresel",   "kuresel"),
    ("ekosistem.json", "ekosistem", "ekosistem"),
]

def tarih_ay(tarih_str):
    """'2026-05-14T...' → '2026-05'"""
    if not tarih_str:
        return None
    try:
        return str(tarih_str)[:7]
    except Exception:
        return None

toplam_arsivlenen = 0
toplam_dosya = 0

for dosya_adi, arsiv_adi, json_anahtari in KAYNAKLAR:
    p = Path(dosya_adi)
    if not p.exists():
        print(f"⚠  {dosya_adi} bulunamadı, atlanıyor")
        continue

    try:
        veri = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"⚠  {dosya_adi} okunamadı: {e}")
        continue

    liste = veri.get(json_anahtari, [])
    if not liste:
        print(f"ℹ  {dosya_adi} boş, atlanıyor")
        continue

    # Aya göre grupla
    aylar = defaultdict(list)
    tarihsiz = 0
    for item in liste:
        ay = tarih_ay(item.get("tarih", ""))
        if ay:
            aylar[ay].append(item)
        else:
            tarihsiz += 1

    print(f"\n📂 {dosya_adi} → {len(aylar)} ay, {len(liste)} kayıt ({tarihsiz} tarihsiz)")

    for ay, kayitlar in sorted(aylar.items()):
        arsiv_dosya = ARSIV_DIR / f"{arsiv_adi}-{ay}.json"

        if arsiv_dosya.exists():
            print(f"   ⏭  {arsiv_dosya.name} zaten var, atlanıyor")
            continue

        cikti = {
            "meta": {
                "arsiv_ay": ay,
                "koleksiyon": arsiv_adi,
                "toplam": len(kayitlar),
                "olusturulma": datetime.now(timezone.utc).isoformat(),
                "kaynak": "arsiv_goc.py (tek seferlik göç)",
            },
            arsiv_adi: sorted(kayitlar, key=lambda x: x.get("tarih") or "", reverse=True),
        }

        arsiv_dosya.write_text(
            json.dumps(cikti, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        boy_kb = round(arsiv_dosya.stat().st_size / 1024, 1)
        print(f"   ✓  {arsiv_dosya.name}: {len(kayitlar)} kayıt ({boy_kb} KB)")
        toplam_arsivlenen += len(kayitlar)
        toplam_dosya += 1

print(f"\n{'═'*50}")
print(f"✓ Tamamlandı: {toplam_dosya} arşiv dosyası, {toplam_arsivlenen} kayıt")
print(f"✓ Arşiv klasörü: {ARSIV_DIR.resolve()}")

# Arşiv özeti
print(f"\nOluşturulan dosyalar:")
for f in sorted(ARSIV_DIR.iterdir()):
    if f.suffix == ".json":
        boy_kb = round(f.stat().st_size / 1024, 1)
        print(f"  {f.name:<40} {boy_kb:>8} KB")
