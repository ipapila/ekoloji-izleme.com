#!/usr/bin/env python3
"""
firms_yangin_tarama.py
-----------------------
NASA FIRMS (Fire Information for Resource Management System) API'sinden
Türkiye sınırları içindeki aktif yangın/ısı anomalisi noktalarını, dört
sensörün (VIIRS Suomi-NPP, VIIRS NOAA-20, VIIRS NOAA-21, MODIS) tümünden
birlikte çeker, aynı yangının farklı sensörlerde tekrar sayılmasını eler,
ekoloji-izleme.com veri modeline (tip/ad/il/koordinatlar/...) dönüştürür
ve hem JSON hem GeoJSON FeatureCollection olarak kaydeder.

KULLANIM
--------
1) Ücretsiz bir MAP_KEY al: https://firms.modaps.eosdis.nasa.gov/api/area/
   (E-posta ile anında geliyor, günlük çağrı limiti var.)
2) Ortam değişkeni olarak ver:  export FIRMS_MAP_KEY="xxxxxxxx"
   (GitHub Actions'ta repo secrets -> FIRMS_MAP_KEY)
3) Çalıştır:  python firms_yangin_tarama.py

NOT: Bu ortamda internet erişimi kapalı olduğu için script'i test amaçlı
çalıştıramadım; kendi sunucunda / GitHub Actions'ta (internet erişimi
olan ortamda) çalıştırman gerekiyor. İstersen rapor.yml gibi ayrı bir
workflow olarak (örn. saatlik) ekleyebiliriz.
"""

import os
import sys
import csv
import io
import json
import random
import string
import time
import urllib.request
from datetime import datetime, timezone

# --- Ayarlar -----------------------------------------------------------

MAP_KEY = os.environ.get("FIRMS_MAP_KEY", "").strip()

# Taranacak sensörler — hepsi aynı taramada birleştirilir.
# Sıra önemli: aynı yangın birden çok sensörde görünürse listede önce
# gelen (daha yüksek çözünürlüklü VIIRS) tutulur, geri kalanı elenir.
KAYNAK_UYDULAR = [
    "VIIRS_SNPP_NRT",     # 375m — Suomi NPP
    "VIIRS_NOAA20_NRT",   # 375m — NOAA-20
    "VIIRS_NOAA21_NRT",   # 375m — NOAA-21
    "MODIS_NRT",          # 1km  — Terra+Aqua birleşik
]

# Türkiye bounding box: west,south,east,north
TURKIYE_BBOX = "25.5,35.5,45.0,42.5"

# Kaç günlük veri (FIRMS area API: 1-10 gün arası)
GUN_ARALIGI = 1

# Güven eşiği: VIIRS için confidence "l"(low)/"n"(nominal)/"h"(high) döner.
# Küçük/başlangıç aşamasındaki yangınlar genelde düşük FRP'li olduğu için
# düşük güvenle işaretlenir — bu yüzden "l" artık ELENMİYOR, sadece
# aciklama/kayıtta "düşük güven" olarak işaretleniyor (harita tarafında
# farklı renkle gösteriliyor). Tamamen gürültü olan MODIS'in çok düşük
# sayısal güven değerleri (<MODIS_MIN_GUVEN) hâlâ elenir.
GECERLI_GUVEN = {"l", "n", "h"}
MODIS_MIN_GUVEN = 20  # önceden 50 idi — daha küçük/zayıf tespitleri de al

# Aynı yangının farklı sensörlerde tekrar sayılmasını önlemek için
# yuvarlama çözünürlüğü (derece) — ~1.1km
TEKRAR_ELEME_HASSASIYET = 3


# --- Yardımcılar ---------------------------------------------------------

def uid():
    return "r" + "".join(
        random.choices(string.ascii_lowercase + string.digits, k=9)
    ) + str(int(time.time() * 1000))


def il_bul(lat, lng):
    """Nominatim reverse geocoding ile il / ilçe / en yakın yerleşim adını çöz.
    'yerlesim' alanı köy/mahalle/beldeyi de kapsar — bu, harita bilgi
    penceresinde 'X köyü yakınında' gibi sade bir ifade kurmak içindir."""
    url = (
        f"https://nominatim.openstreetmap.org/reverse"
        f"?lat={lat}&lon={lng}&format=json&accept-language=tr&zoom=14"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "ekoloji-izleme/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8"))
        adres = data.get("address", {})
        il = adres.get("province") or adres.get("state") or ""
        ilce = adres.get("county") or adres.get("town") or adres.get("city_district") or ""
        yerlesim = (
            adres.get("village") or adres.get("hamlet") or adres.get("suburb")
            or adres.get("neighbourhood") or adres.get("municipality")
            or adres.get("town") or ""
        )
        orman = "wood" in adres or "forest" in adres or "natural" in adres
        return il, ilce, yerlesim, orman
    except Exception:
        return "", "", "", False


def firms_verisini_cek(sensor):
    if not MAP_KEY:
        print("HATA: FIRMS_MAP_KEY tanımlı değil. Ortam değişkeni olarak ekleyin.")
        sys.exit(1)

    url = (
        f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
        f"{MAP_KEY}/{sensor}/{TURKIYE_BBOX}/{GUN_ARALIGI}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "ekoloji-izleme/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        ham = r.read().decode("utf-8")

    if ham.strip().lower().startswith("invalid") or "error" in ham[:50].lower():
        print(f"  ⚠ {sensor}: FIRMS API hata döndürdü: {ham[:150]}")
        return []

    satirlar = list(csv.DictReader(io.StringIO(ham)))
    for s in satirlar:
        s["_sensor"] = sensor
    return satirlar


def tum_sensorleri_cek():
    """Listedeki tüm sensörleri sırayla tarar ve tek listede birleştirir."""
    tumu = []
    for sensor in KAYNAK_UYDULAR:
        print(f"  → {sensor} taranıyor...")
        satirlar = firms_verisini_cek(sensor)
        print(f"    {len(satirlar)} nokta bulundu")
        tumu.extend(satirlar)
        time.sleep(1)  # FIRMS MAP_KEY rate limit'e nazik davran
    return tumu


def tekrarlari_ele(satirlar):
    """Aynı yangın birden çok sensörde görünüyorsa, KAYNAK_UYDULAR sırasına
    göre ilk (en yüksek çözünürlüklü) tespiti tutar, diğerlerini eler."""
    goruldu = set()
    benzersiz = []
    for s in satirlar:
        try:
            lat = round(float(s["latitude"]), TEKRAR_ELEME_HASSASIYET)
            lng = round(float(s["longitude"]), TEKRAR_ELEME_HASSASIYET)
        except (KeyError, ValueError):
            continue
        anahtar = (lat, lng, s.get("acq_date", ""))
        if anahtar in goruldu:
            continue
        goruldu.add(anahtar)
        benzersiz.append(s)
    return benzersiz


def kayitlara_donustur(satirlar, il_ilce_coz=True, bekleme=1.0, max_geocode=150):
    kayitlar = []
    bugun = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    il_cache = {}  # (lat_yuvarlak, lng_yuvarlak) -> (il, ilce) — komşu noktalar tek istekte çözülsün
    geocode_sayaci = 0

    for s in satirlar:
        guven = str(s.get("confidence", "")).strip().lower()

        if guven.isdigit() and int(guven) < MODIS_MIN_GUVEN:
            continue
        if guven not in GECERLI_GUVEN and not guven.isdigit():
            continue  # tanınmayan/boş değer

        try:
            lat = float(s["latitude"])
            lng = float(s["longitude"])
        except (KeyError, ValueError):
            continue

        il, ilce, yerlesim, orman_yakininda = "", "", "", False
        if il_ilce_coz:
            anahtar = (round(lat, 2), round(lng, 2))  # ~1km çözünürlükte önbellek
            if anahtar in il_cache:
                il, ilce, yerlesim, orman_yakininda = il_cache[anahtar]
            elif geocode_sayaci < max_geocode:
                il, ilce, yerlesim, orman_yakininda = il_bul(lat, lng)
                il_cache[anahtar] = (il, ilce, yerlesim, orman_yakininda)
                geocode_sayaci += 1
                time.sleep(bekleme)  # Nominatim rate limit
            # max_geocode aşılırsa il/ilce boş kalır — GitHub Actions zaman
            # aşımını önlemek için; büyük yangın günlerinde koordinat yine de var.

        frp = s.get("frp", "")  # Fire Radiative Power (MW) - şiddet göstergesi
        tarih = s.get("acq_date", bugun)
        saat = s.get("acq_time", "")
        sensor = s.get("_sensor", "")
        sensor_etiket = {
            "VIIRS_SNPP_NRT": "VIIRS/Suomi-NPP",
            "VIIRS_NOAA20_NRT": "VIIRS/NOAA-20",
            "VIIRS_NOAA21_NRT": "VIIRS/NOAA-21",
            "MODIS_NRT": "MODIS",
        }.get(sensor, sensor or "bilinmiyor")

        # Herkesin anlayabileceği güven ifadesi (harita rengiyle de eşleşir)
        guven_seviye = {"h": "Yüksek", "n": "Orta", "l": "Düşük"}.get(guven)
        if guven_seviye is None and guven.isdigit():
            sayi = int(guven)
            guven_seviye = "Yüksek" if sayi >= 80 else ("Orta" if sayi >= 50 else "Düşük")
        guven_seviye = guven_seviye or "Bilinmiyor"

        # Konum ifadesi: önce en yakın yerleşim, yoksa ilçe, yoksa il
        konum_ifadesi = yerlesim or ilce or il or "bilinmeyen bir konumda"

        aciklama_sade = (
            f"Bu nokta, {konum_ifadesi}{' yakınında' if konum_ifadesi != 'bilinmeyen bir konumda' else ''} "
            f"uydu tarafından {tarih} tarihinde tespit edilen bir ısı anomalisidir. "
            f"Tespitin güvenilirlik düzeyi: {guven_seviye.lower()}. "
            "Bu tür tespitler her zaman yangın anlamına gelmez; tarım arazisi yakma, "
            "sanayi tesisi ısısı veya güneş yansıması da benzer sinyal verebilir."
        )
        if orman_yakininda:
            aciklama_sade += " Bu bölge orman/doğal alan olarak işaretli — yangın riski açısından dikkat gerektirebilir."

        teknik_detay = (
            f"Sensör: {sensor_etiket}, uydu geçiş saati: {saat[:2]}:{saat[2:]} UTC, "
            f"FRP: {frp} MW, güven: {guven}"
        )

        kayit = {
            "id": uid(),
            "tip": "İklim Olayları",
            "ad": f"Uydu Tespitli Isı Anomalisi{f' ({konum_ifadesi})' if konum_ifadesi != 'bilinmeyen bir konumda' else ''}",
            "il": il,
            "ilce": ilce,
            "yerlesim": yerlesim,
            "koordinatlar": {"lat": lat, "lng": lng},
            "alan_ha": 0,
            "durum": "Aktif",
            "belge_no": "",
            "eklenme": tarih,
            "kaynak": f"NASA FIRMS ({sensor_etiket})",
            "kaynak_link": "https://firms.modaps.eosdis.nasa.gov/map/",
            "aciklama": aciklama_sade,
            "teknik_detay": teknik_detay,
            "guven_seviye": guven_seviye,
            "alt_kategori": "",
            "kaynak_turu": "uydu",
        }
        kayitlar.append(kayit)

    return kayitlar


def geojsona_cevir(kayitlar):
    features = []
    for k in kayitlar:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [k["koordinatlar"]["lng"], k["koordinatlar"]["lat"]],
            },
            "properties": {key: v for key, v in k.items() if key != "koordinatlar"},
        })
    return {"type": "FeatureCollection", "features": features}


def main():
    print(f"FIRMS'ten Türkiye için {len(KAYNAK_UYDULAR)} sensör, son {GUN_ARALIGI} günlük veri çekiliyor...")
    satirlar = tum_sensorleri_cek()
    print(f"Toplam {len(satirlar)} ham nokta (tüm sensörler) — tekrarlar eleniyor...")

    satirlar = tekrarlari_ele(satirlar)
    print(f"{len(satirlar)} benzersiz nokta kaldı, filtreleniyor ve geocode ediliyor...")

    # NOT: Nominatim'e her nokta için reverse-geocode çok yavaş olabilir
    # (>=1sn/istek). Yoğun yangın günlerinde il_ilce_coz=False yapıp
    # sadece koordinat ile kaydetmek, sonra ayrı bir toplu geocode
    # adımı çalıştırmak daha pratik olabilir.
    kayitlar = kayitlara_donustur(satirlar, il_ilce_coz=True, bekleme=1.0)

    cikti = {
        "guncelleme": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "kayit_sayisi": len(kayitlar),
        "kayitlar": kayitlar,
    }

    with open("firms_yangin.json", "w", encoding="utf-8") as f:
        json.dump(cikti, f, ensure_ascii=False, indent=2)

    with open("firms_yangin.geojson", "w", encoding="utf-8") as f:
        json.dump(geojsona_cevir(kayitlar), f, ensure_ascii=False, indent=2)

    print(f"Tamamlandı: {len(kayitlar)} kayıt -> firms_yangin.json / firms_yangin.geojson")


if __name__ == "__main__":
    main()
