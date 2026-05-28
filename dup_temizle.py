#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dup_temizle.py — ihlaller.json'dan duplicate temizler

Çalıştır:
    python dup_temizle.py                  # kuru çalıştırma (yazar değil, raporlar)
    python dup_temizle.py --yaz            # temizlenmiş dosyayı yazar
    python dup_temizle.py --yaz --cikti temiz.json   # farklı dosyaya yazar
"""

import json, re, sys, unicodedata
from pathlib import Path
from collections import defaultdict

GIRIS = Path("ihlaller.json")

def normalize(s):
    """Başlık/URL'yi karşılaştırma için normalize et."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def anahtar(item):
    """
    Duplicate tespiti için birincil anahtar:
    1. kaynak_url varsa normalize URL
    2. yoksa normalize başlığın ilk 60 karakteri
    """
    url = (item.get("kaynak_url") or item.get("url") or "").strip().lower()
    url = re.sub(r"[?#].*$", "", url)   # query string ve fragment sil
    url = url.rstrip("/")
    if url and "google" not in url and len(url) > 10:
        return ("url", url)
    baslik = normalize(item.get("baslik") or item.get("ad") or "")[:60]
    return ("baslik", baslik)

def tercih_et(a, b):
    """
    İki duplicate kayıt arasından hangisini tutacağımızı seç.
    Daha fazla dolu alan + daha yeni tarih kazanır.
    """
    def puan(x):
        dolu = sum(1 for v in x.values() if v)
        tarih = str(x.get("tarih") or "0000")
        return (dolu, tarih)
    return a if puan(a) >= puan(b) else b

def temizle(kayitlar):
    gorulen = {}      # anahtar → seçilen kayıt
    duplar  = []      # atılan kayıtlar

    for item in kayitlar:
        k = anahtar(item)
        if not k[1]:          # anahtarı boş → her zaman tut
            gorulen[id(item)] = item
            continue
        if k in gorulen:
            kazanan = tercih_et(gorulen[k], item)
            kaybeden = item if kazanan is gorulen[k] else gorulen[k]
            gorulen[k] = kazanan
            duplar.append(kaybeden)
        else:
            gorulen[k] = item

    temiz = list(gorulen.values())
    return temiz, duplar

def main():
    yaz    = "--yaz"    in sys.argv
    cikti  = Path(sys.argv[sys.argv.index("--cikti") + 1]) if "--cikti" in sys.argv else GIRIS

    if not GIRIS.exists():
        print(f"❌ {GIRIS} bulunamadı.")
        sys.exit(1)

    veri = json.loads(GIRIS.read_text(encoding="utf-8"))
    if isinstance(veri, list):
        kayitlar = veri
        ust_level = None
    else:
        kayitlar = veri.get("ihlaller", [])
        ust_level = veri

    print(f"📂 Toplam kayıt: {len(kayitlar)}")

    temiz, duplar = temizle(kayitlar)

    print(f"✅ Temiz kayıt : {len(temiz)}")
    print(f"🗑  Duplicate   : {len(duplar)}")

    if duplar:
        print("\n── Duplicate listesi ──")
        for d in duplar[:20]:
            print(f"  [{d.get('id','')}] {(d.get('baslik') or '')[:70]}")
        if len(duplar) > 20:
            print(f"  ... ve {len(duplar)-20} tane daha")

    if yaz:
        if ust_level is not None:
            ust_level["ihlaller"] = temiz
            out = ust_level
        else:
            out = temiz
        cikti.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n💾 Yazıldı: {cikti}  ({len(temiz)} kayıt)")
    else:
        print("\n⚠  Kuru çalıştırma — dosya değiştirilmedi. Yazmak için: --yaz")

if __name__ == "__main__":
    main()
