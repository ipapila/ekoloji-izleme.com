#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tarih_duzenle.py — data.json içindeki tüm tarih alanlarını ISO formatına çevirir.

Çalıştırma:
    python scripts/tarih_duzenle.py

data.json'ı okur, tarih alanlarını düzeltir, geri yazar.
Orijinal dosyayı data.json.bak olarak yedekler.
"""

import json
import re
import shutil
from pathlib import Path
from datetime import datetime

# ─── AYARLAR ──────────────────────────────────────────────────────────
DATA_PATH = Path("data.json")          # scripti repo kökünden çalıştır
YEDEK_PATH = Path("data.json.bak")

# Hangi alanlarda tarih aranacak
TARIH_ALANLARI = ["tarih", "date", "eklenme", "guncelleme", "baslangic", "bitis"]

# Türkçe ay adları
TR_AYLAR = {
    "ocak": "01", "şubat": "02", "subat": "02", "mart": "03",
    "nisan": "04", "mayıs": "05", "mayis": "05", "haziran": "06",
    "temmuz": "07", "ağustos": "08", "agustos": "08", "eylül": "09",
    "eylul": "09", "ekim": "10", "kasım": "11", "kasim": "11",
    "aralık": "12", "aralik": "12"
}

# ─── FORMAT ALGILAMA VE DÖNÜŞTÜRME ────────────────────────────────────

def normalize_tarih(deger):
    """
    Herhangi bir tarih string'ini YYYY-MM-DD formatına çevirir.
    Tanıyamazsa orijinal değeri döndürür.
    """
    if not deger or not isinstance(deger, str):
        return deger

    d = deger.strip()

    # Zaten ISO: 2025-05-22 veya 2025-05-22T...
    if re.match(r"^\d{4}-\d{2}-\d{2}", d):
        return d[:10]  # sadece tarih kısmı

    # DD.MM.YYYY veya DD/MM/YYYY
    m = re.match(r"^(\d{1,2})[./](\d{1,2})[./](\d{4})$", d)
    if m:
        gun, ay, yil = m.groups()
        return f"{yil}-{ay.zfill(2)}-{gun.zfill(2)}"

    # YYYY.MM.DD veya YYYY/MM/DD
    m = re.match(r"^(\d{4})[./](\d{2})[./](\d{2})$", d)
    if m:
        yil, ay, gun = m.groups()
        return f"{yil}-{ay}-{gun}"

    # DD MM YYYY (boşluklu sayısal)
    m = re.match(r"^(\d{1,2})\s+(\d{1,2})\s+(\d{4})$", d)
    if m:
        gun, ay, yil = m.groups()
        return f"{yil}-{ay.zfill(2)}-{gun.zfill(2)}"

    # "22 Mayıs 2026" veya "22 mayıs 2026"
    m = re.match(r"^(\d{1,2})\s+([a-zA-ZğüşıöçĞÜŞİÖÇ]+)\s+(\d{4})$", d)
    if m:
        gun, ay_str, yil = m.groups()
        ay_no = TR_AYLAR.get(ay_str.lower().replace("ı", "i"))
        if ay_no:
            return f"{yil}-{ay_no}-{gun.zfill(2)}"

    # "Mayıs 2026" (gün yok — ayın 1'i kabul et)
    m = re.match(r"^([a-zA-ZğüşıöçĞÜŞİÖÇ]+)\s+(\d{4})$", d)
    if m:
        ay_str, yil = m.groups()
        ay_no = TR_AYLAR.get(ay_str.lower().replace("ı", "i"))
        if ay_no:
            return f"{yil}-{ay_no}-01"

    # Unix timestamp (sayısal string)
    if re.match(r"^\d{10,13}$", d):
        ts = int(d)
        if ts > 1e12:
            ts //= 1000
        return datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")

    # Tanınamadı
    return deger


def duzenle_nesne(nesne, sayac):
    """Dict içindeki tarih alanlarını düzeltir."""
    if not isinstance(nesne, dict):
        return nesne
    for alan in TARIH_ALANLARI:
        if alan in nesne and nesne[alan]:
            eski = nesne[alan]
            yeni = normalize_tarih(str(eski))
            if yeni != str(eski):
                nesne[alan] = yeni
                sayac["degisen"] += 1
                sayac["ornekler"].append(f"  '{eski}' → '{yeni}'")
    return nesne


def isle_liste(liste, sayac):
    """Liste veya iç içe yapıları gezer."""
    if isinstance(liste, list):
        return [isle_liste(e, sayac) for e in liste]
    elif isinstance(liste, dict):
        duzenle_nesne(liste, sayac)
        for v in liste.values():
            if isinstance(v, (list, dict)):
                isle_liste(v, sayac)
        return liste
    return liste


# ─── ANA AKIŞ ─────────────────────────────────────────────────────────

def main():
    if not DATA_PATH.exists():
        print(f"HATA: {DATA_PATH} bulunamadı. Scripti repo kökünden çalıştır.")
        return

    print(f"📂 {DATA_PATH} okunuyor…")
    with open(DATA_PATH, encoding="utf-8") as f:
        veri = json.load(f)

    sayac = {"degisen": 0, "ornekler": []}

    # Yapıya göre işle
    if isinstance(veri, list):
        isle_liste(veri, sayac)
    elif isinstance(veri, dict):
        for key, val in veri.items():
            if isinstance(val, (list, dict)):
                isle_liste(val, sayac)
            elif key in TARIH_ALANLARI:
                yeni = normalize_tarih(str(val))
                if yeni != str(val):
                    veri[key] = yeni
                    sayac["degisen"] += 1

    print(f"✅ {sayac['degisen']} tarih alanı düzeltildi.")
    if sayac["ornekler"]:
        print("Örnekler (ilk 20):")
        for ornek in sayac["ornekler"][:20]:
            print(ornek)

    # Yedek al
    shutil.copy(DATA_PATH, YEDEK_PATH)
    print(f"💾 Yedek: {YEDEK_PATH}")

    # Geri yaz
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)
    print(f"📝 {DATA_PATH} güncellendi.")
    print("🔁 Değişiklikleri GitHub'a push'la: git add data.json && git commit -m 'tarih standardizasyonu' && git push")


if __name__ == "__main__":
    main()
