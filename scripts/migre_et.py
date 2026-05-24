#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
migre_et.py — Mevcut haberler.json'daki tüm kayıtlara
              haber_kategorisi alanını geriye dönük atar.

Kullanım:
    python3 migre_et.py                        # haberler.json (varsayılan)
    python3 migre_et.py --dosya /yol/haberler.json
    python3 migre_et.py --kuru-calistir        # değişiklik yazmaz, sadece raporlar
"""

import argparse
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# tarayici.py ile aynı klasörde olduğu varsayılır.
# Farklı bir yerdeyse aşağıya tam yolu ekle:
#   import sys; sys.path.insert(0, "/tam/yol/")
try:
    from tarayici import haber_kategorisi_tespit, HABER_9_KAT
except ImportError:
    # tarayici.py bulunamazsa fonksiyonu burada tekrar tanımla
    HABER_9_KAT = [
        "İklim ve Afet", "Maden ve Enerji", "Orman ve Doğa",
        "Su ve Kıyı", "Yaban Hayatı", "Direniş ve Eylemler",
        "Hukuki Süreçler", "Nöbetler ve Gözaltılar", "STK & Kampanyalar",
    ]

    def haber_kategorisi_tespit(kayit: dict) -> str:
        eylem = (kayit.get("eylem") or "").lower()
        kat   = (kayit.get("kategori") or "").lower()
        _TR  = str.maketrans("İŞĞÜÖÇ", "işğüöç")
        metin = " ".join([
            kayit.get("baslik", ""), kayit.get("ozet", ""),
            kayit.get("kategori", ""),
            " ".join(kayit.get("etiketler") or []),
        ]).translate(_TR).lower()

        if "nöbet" in metin or "gözaltı" in metin or "nöbet & gözaltı" in eylem:
            return "Nöbetler ve Gözaltılar"
        if "direniş & eylem" in eylem or any(k in metin for k in
                ["direniş", "protesto", "miting", "yürüyüş", "boykot", "oturma eylemi"]):
            return "Direniş ve Eylemler"
        if "stk & kampanya" in eylem or "stk" in kat or any(k in metin for k in
                ["greenpeace", "wwf", "tema vakfı", "doğa derneği", "350.org", "kampanya başlat"]):
            return "STK & Kampanyalar"
        if "hukuk & dava" in eylem or any(k in metin for k in
                ["dava açı", "mahkeme", "yürütmeyi durdur", "iptal kararı", "çed kararı", "itiraz"]):
            return "Hukuki Süreçler"
        if any(k in metin for k in [
                "iklim", "yangın", "sel ", "taşkın", "heyelan",
                "kuraklık", "aşırı sıcak", "afet "]):
            return "İklim ve Afet"
        if any(k in metin for k in [
                "yaban hayat", "nesli tehlike", "biyoçeşitlilik",
                "hayvan hakları", "hayvan refahı"]):
            return "Yaban Hayatı"
        if any(k in metin for k in [
                "sulak alan", "kıyı ihlal", "deniz kirliliği",
                "su kirliliği", "dere yatağı", "balık ölümü"]):
            return "Su ve Kıyı"
        if any(k in metin for k in [
                "maden", "hes ", "res ", "ges ", "termik santral", "nükleer",
                "jeotermal", "baraj", "akkuyu", "sondaj", "enerji santr", "kamulaştırma"]):
            return "Maden ve Enerji"
        if any(k in metin for k in [
                "orman", "ağaç kes", "ağaç katliamı", "habitat",
                "bitki örtüsü", "doğal sit", "milli park", "ormansızlaşma"]):
            return "Orman ve Doğa"
        if any(k in metin for k in ["kıyı", "deniz ", "göl ", "nehir", "dere "]):
            return "Su ve Kıyı"
        return ""


KOLEKSIYONLAR = ("haberler", "raporlar", "makaleler", "uluslararasi", "ekosistem")


def migre_et(dosya_yolu: str, kuru_calistir: bool = False) -> None:
    p = Path(dosya_yolu)
    if not p.exists():
        print(f"❌ Dosya bulunamadı: {p}")
        return

    print(f"📂 Okunuyor: {p}")
    veri = json.loads(p.read_text(encoding="utf-8"))

    toplam_kayit   = 0
    toplam_degisti = 0
    kat_sayac      = Counter()
    kategorisiz    = 0

    for kol in KOLEKSIYONLAR:
        liste = veri.get(kol, [])
        if not liste:
            continue

        degisti = 0
        for kayit in liste:
            eski_kat = kayit.get("haber_kategorisi", None)
            yeni_kat = haber_kategorisi_tespit(kayit)

            kayit["haber_kategorisi"] = yeni_kat

            if eski_kat != yeni_kat:
                degisti += 1

            if yeni_kat:
                kat_sayac[yeni_kat] += 1
            else:
                kategorisiz += 1

        toplam_kayit   += len(liste)
        toplam_degisti += degisti
        print(f"  {kol:15s}: {len(liste):4d} kayıt, {degisti:4d} güncellendi")

    # ── Rapor ──────────────────────────────────────────────────
    print(f"\n{'─'*48}")
    print(f"Toplam kayıt   : {toplam_kayit}")
    print(f"Güncellenen    : {toplam_degisti}")
    print(f"Kategorisiz    : {kategorisiz}")
    print(f"\nKategori dağılımı:")
    for kat in HABER_9_KAT:
        sayi = kat_sayac.get(kat, 0)
        bar  = "█" * min(sayi // max(1, toplam_kayit // 30), 30)
        print(f"  {kat:30s} {sayi:4d}  {bar}")
    print(f"  {'Kategorisiz':30s} {kategorisiz:4d}")
    print(f"{'─'*48}")

    if kuru_calistir:
        print("\n⚠  Kuru çalıştırma — dosya yazılmadı.")
        return

    # ── Yedek al ──────────────────────────────────────────────
    yedek = p.with_suffix(f".yedek_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    shutil.copy2(p, yedek)
    print(f"\n💾 Yedek: {yedek}")

    # ── meta güncelle ──────────────────────────────────────────
    if "meta" not in veri:
        veri["meta"] = {}
    veri["meta"]["haber_kategorisi_migrasyonu"] = datetime.now(timezone.utc).isoformat()

    # ── Yaz ────────────────────────────────────────────────────
    json_str = json.dumps(veri, ensure_ascii=False, indent=2)
    # Geçici dosyaya yaz, sonra yerleştir (atomik)
    tmp = p.with_suffix(".migre.tmp")
    tmp.write_text(json_str, encoding="utf-8")
    tmp.replace(p)
    print(f"✓  {p} güncellendi ({toplam_degisti} kayıt değişti)")


def main():
    parser = argparse.ArgumentParser(
        description="haberler.json'a haber_kategorisi alanını geriye dönük atar."
    )
    parser.add_argument(
        "--dosya", default="haberler.json",
        help="Hedef JSON dosyası (varsayılan: haberler.json)"
    )
    parser.add_argument(
        "--kuru-calistir", action="store_true",
        help="Sadece raporla, dosyaya yazma"
    )
    args = parser.parse_args()
    migre_et(args.dosya, args.kuru_calistir)


if __name__ == "__main__":
    main()
