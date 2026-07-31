#!/usr/bin/env python3
"""
firms_arsiv_doldur.py
----------------------
firms_yangin_tarama.py ile AYNI dönüştürme mantığını (tekrar eleme,
il/ilçe çözümleme, güven kodu, kayıt şeması) kullanarak NASA FIRMS'ten
geçmişe dönük veri çeker ve arsiv/YYYY-MM-DD.json dosyalarını üretir.

Bu script hourly (saatlik) firms-tarama.yml akışının bir parçası DEĞİLDİR;
tek seferlik geriye dönük dolgu için elle ya da ayrı bir workflow_dispatch
workflow'u (firms-arsiv-doldur.yml) ile çalıştırılır.

KULLANIM
--------
  export FIRMS_MAP_KEY="xxxxxxxx"
  python firms_arsiv_doldur.py            # son 10 gün (bugün dahil)
  python firms_arsiv_doldur.py 20         # son 20 gün

NOT: FIRMS Area API tek istekte en fazla 10 günlük aralık veriyor
(DAY_RANGE 1-10), bu yüzden 10'dan büyük istekler otomatik olarak
10'ar günlük parçalara bölünür.

NOT (geocoding): Çok günlük/çok noktalı taramalarda Nominatim'e nokta
başına ~1sn istek atmak workflow'u çok uzatabileceği için bu script
varsayılan olarak il/ilçe/yerleşim çözümlemesini KAPALI tutar; sadece
çevrimdışı en-yakın-il (haversine) yedeğini kullanır — bu yüzden
popup'larda ilçe/yerleşim adı boş, il adı dolu gelir. Tam adres
çözümlemesi istenirse --geocode ile açılabilir (çok daha yavaştır).
"""

import os
import sys
import time
import json
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import firms_yangin_tarama as ft  # aynı dizindeki asıl script — şema/mantık burada tanımlı


def firms_verisini_cek_tarihli(sensor, baslangic_tarih, gun_araligi):
    """firms_yangin_tarama.firms_verisini_cek ile aynı yeniden-deneme /
    yedek-sunucu mantığı, ama isteğe [DATE] ekleyerek geçmişe dönük sorgu
    yapar: /api/area/csv/[MAP_KEY]/[SOURCE]/[BBOX]/[DAY_RANGE]/[DATE]
    DATE..DATE+gun_araligi-1 aralığını döndürür."""
    import urllib.request
    import urllib.error
    import csv
    import io

    if not ft.MAP_KEY:
        print("HATA: FIRMS_MAP_KEY tanımlı değil.")
        sys.exit(1)

    sunucular = [
        "https://firms.modaps.eosdis.nasa.gov",
        "https://firms2.modaps.eosdis.nasa.gov",
    ]

    ham = None
    son_hata = None
    for sunucu_index, taban_url in enumerate(sunucular):
        url = (
            f"{taban_url}/api/area/csv/{ft.MAP_KEY}/{sensor}/{ft.TURKIYE_BBOX}"
            f"/{gun_araligi}/{baslangic_tarih}"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "ekoloji-izleme/1.0"})
        for deneme in range(1, 4):
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    ham = r.read().decode("utf-8")
                break
            except (OSError, urllib.error.URLError) as e:
                son_hata = e
                if deneme < 3:
                    bekleme = 5 * deneme
                    print(f"  ⚠ {sensor} ({taban_url}): bağlantı hatası ({e}), {bekleme}sn sonra {deneme + 1}. deneme...")
                    time.sleep(bekleme)
        if ham is not None:
            break

    if ham is None:
        print(f"  ✗ {sensor}: hem ana hem yedek sunucu başarısız oldu: {son_hata}")
        return []

    if ham.strip().lower().startswith("invalid") or "error" in ham[:50].lower():
        print(f"  ⚠ {sensor}: FIRMS API hata döndürdü: {ham[:150]}")
        return []

    satirlar = list(csv.DictReader(io.StringIO(ham)))
    for s in satirlar:
        s["_sensor"] = sensor
    return satirlar


def parcalari_hesapla(toplam_gun):
    """toplam_gun kadar geçmişi, her biri en fazla 10 günlük parçalara böler.
    Döner: [(baslangic_tarih_str, bu_parcanin_gun_sayisi), ...] — en eskiden
    en yeniye doğru sıralı."""
    bugun = datetime.now(timezone.utc).date()
    en_eski_baslangic = bugun - timedelta(days=toplam_gun - 1)
    parcalar = []
    imlec = en_eski_baslangic
    while imlec <= bugun:
        kalan = (bugun - imlec).days + 1
        parca_gun = min(10, kalan)
        parcalar.append((imlec.strftime("%Y-%m-%d"), parca_gun))
        imlec += timedelta(days=parca_gun)
    return parcalar


def main():
    toplam_gun = 10
    geocode_ac = "--geocode" in sys.argv
    sayisal_argumanlar = [a for a in sys.argv[1:] if a.isdigit()]
    if sayisal_argumanlar:
        toplam_gun = int(sayisal_argumanlar[0])

    print(f"Son {toplam_gun} gün için geçmişe dönük FIRMS taraması başlıyor "
          f"(geocode: {'açık' if geocode_ac else 'kapalı, sadece en-yakın-il'})...")

    tum_satirlar = []
    for baslangic, gun_sayisi in parcalari_hesapla(toplam_gun):
        print(f"→ {baslangic} ile başlayan {gun_sayisi} günlük parça:")
        for sensor in ft.KAYNAK_UYDULAR:
            print(f"    → {sensor} taranıyor...")
            satirlar = firms_verisini_cek_tarihli(sensor, baslangic, gun_sayisi)
            print(f"      {len(satirlar)} nokta bulundu")
            tum_satirlar.extend(satirlar)
            time.sleep(1)

    print(f"Toplam {len(tum_satirlar)} ham nokta — tekrarlar eleniyor...")
    benzersiz = ft.tekrarlari_ele(tum_satirlar)
    print(f"{len(benzersiz)} benzersiz nokta kaldı, kayıtlara dönüştürülüyor...")

    kayitlar = ft.kayitlara_donustur(
        benzersiz,
        il_ilce_coz=geocode_ac,
        bekleme=1.0,
        max_geocode=1000 if geocode_ac else 0,
    )

    yazilanlar = ft.arsive_yaz(kayitlar)
    print(f"Tamamlandı: {len(kayitlar)} kayıt, {len(yazilanlar)} arşiv dosyası yazıldı:")
    for y in sorted(yazilanlar):
        print(f"  {y}")


if __name__ == "__main__":
    main()
