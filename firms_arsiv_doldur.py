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

NOT: FIRMS Area API dokümantasyonu DAY_RANGE için 1-10 aralığından
bahseder, ama bazı MAP_KEY/kaynak kombinasyonlarında sunucu bunu daha
dar tutabiliyor (bu projede gözlemlenen: 1-5). Script varsayılan olarak
5 günlük parçalar halinde ister; sunucu farklı bir üst sınır bildirirse
(ör. "Expects [1..N]") o isteği otomatik olarak N ile tekrar dener.

NOT (geocoding): Çok günlük/çok noktalı taramalarda Nominatim'e nokta
başına ~1sn istek atmak workflow'u çok uzatabileceği için bu script
varsayılan olarak il/ilçe/yerleşim çözümlemesini KAPALI tutar; sadece
çevrimdışı en-yakın-il (haversine) yedeğini kullanır — bu yüzden
popup'larda ilçe/yerleşim adı boş, il adı dolu gelir. Tam adres
çözümlemesi istenirse --geocode ile açılabilir (çok daha yavaştır).
"""

import os
import re
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
        print(f"    URL: {url}")
        for deneme in range(1, 4):
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    ham = r.read().decode("utf-8")
                break
            except urllib.error.HTTPError as e:
                gövde = ""
                try:
                    gövde = e.read().decode("utf-8", errors="replace")[:300]
                except Exception:
                    pass
                son_hata = f"HTTP {e.code}: {gövde or e.reason}"
                print(f"  ⚠ {sensor} ({taban_url}): {son_hata}")

                # FIRMS bazı MAP_KEY'lerde DAY_RANGE'i dokümantasyondaki
                # 1-10 aralığından daha dar tutuyor (bu projede gözlemlenen:
                # 1-5). Hata mesajı "Expects [X..Y]" formatındaysa Y'yi
                # ayrıştırıp, istenen gun_araligi bundan büyükse aynı
                # isteği tek seferde izin verilen üst sınırla tekrar dene.
                uyum = re.search(r"Expects \[\d+\.\.(\d+)\]", gövde)
                if uyum and int(uyum.group(1)) < gun_araligi:
                    yeni_araligi = int(uyum.group(1))
                    print(f"    ↳ İzin verilen azami DAY_RANGE {yeni_araligi} — {yeni_araligi} ile tekrar deneniyor...")
                    url = (
                        f"{taban_url}/api/area/csv/{ft.MAP_KEY}/{sensor}/{ft.TURKIYE_BBOX}"
                        f"/{yeni_araligi}/{baslangic_tarih}"
                    )
                    req = urllib.request.Request(url, headers={"User-Agent": "ekoloji-izleme/1.0"})
                    try:
                        with urllib.request.urlopen(req, timeout=30) as r:
                            ham = r.read().decode("utf-8")
                        break
                    except Exception as e2:
                        son_hata = str(e2)
                        print(f"    ✗ tekrar deneme de başarısız: {e2}")

                if 400 <= e.code < 500:
                    # İstemci hatası (kötü MAP_KEY, geçersiz parametre vb.) —
                    # aynı isteği tekrar etmek sonucu değiştirmez, hemen vazgeç.
                    break
                if deneme < 3:
                    bekleme = 5 * deneme
                    time.sleep(bekleme)
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


def parcalari_hesapla(toplam_gun, azami_parca=5):
    """toplam_gun kadar geçmişi, her biri en fazla azami_parca günlük
    parçalara böler. FIRMS Area API dokümantasyonu DAY_RANGE için 1-10
    aralığından bahsetse de, bazı MAP_KEY/kaynak kombinasyonlarında
    sunucu "Invalid day range. Expects [1..5]." diyerek 5 ile
    sınırlıyor — bu yüzden varsayılanı güvenli tarafta (5) tutuyoruz.
    Döner: [(baslangic_tarih_str, bu_parcanin_gun_sayisi), ...] — en
    eskiden en yeniye doğru sıralı."""
    bugun = datetime.now(timezone.utc).date()
    en_eski_baslangic = bugun - timedelta(days=toplam_gun - 1)
    parcalar = []
    imlec = en_eski_baslangic
    while imlec <= bugun:
        kalan = (bugun - imlec).days + 1
        parca_gun = min(azami_parca, kalan)
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
