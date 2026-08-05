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
import socket
import sys
import csv
import io
import json
import math
import random
import string
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

# GitHub Actions runner'larında bazen DNS, FIRMS/Nominatim için IPv6
# adresi döndürüyor ama runner'da IPv6 route yok; bu da
# "OSError: [Errno 101] Network is unreachable" hatasına yol açıyor.
# Çözümlemeyi sadece IPv4 adresleriyle sınırlayarak bunu önlüyoruz.
_orig_getaddrinfo = socket.getaddrinfo


def _ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    sonuc = _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
    return sonuc or _orig_getaddrinfo(host, port, family, type, proto, flags)


socket.getaddrinfo = _ipv4_getaddrinfo


# --- Çevrimdışı en-yakın-il yedeği ---------------------------------------
# Nominatim reverse-geocoding ağ isteği başarısız olur ya da max_geocode
# sınırı aşılırsa, en azından il adı boş kalmasın diye 81 il merkezine
# olan mesafeyi (haversine) hesaplayıp en yakınını döndürüyoruz. Ağ
# gerektirmez, anında çalışır — böylece popup'ta "Konum bilgisi yok"
# yerine en azından il adı her zaman görünür.
IL_MERKEZLERI = {
    "Adana": (37.0000, 35.3213), "Adıyaman": (37.7648, 38.2786),
    "Afyonkarahisar": (38.7507, 30.5567), "Ağrı": (39.7191, 43.0503),
    "Amasya": (40.6499, 35.8353), "Ankara": (39.9334, 32.8597),
    "Antalya": (36.8969, 30.7133), "Artvin": (41.1828, 41.8183),
    "Aydın": (37.8560, 27.8416), "Balıkesir": (39.6484, 27.8826),
    "Bilecik": (40.1451, 29.9798), "Bingöl": (38.8855, 40.4989),
    "Bitlis": (38.4006, 42.1095), "Bolu": (40.7392, 31.6089),
    "Burdur": (37.7203, 30.2908), "Bursa": (40.1826, 29.0665),
    "Çanakkale": (40.1553, 26.4142), "Çankırı": (40.6013, 33.6134),
    "Çorum": (40.5506, 34.9556), "Denizli": (37.7765, 29.0864),
    "Diyarbakır": (37.9144, 40.2306), "Edirne": (41.6771, 26.5557),
    "Elazığ": (38.6810, 39.2264), "Erzincan": (39.7500, 39.5000),
    "Erzurum": (39.9000, 41.2700), "Eskişehir": (39.7767, 30.5206),
    "Gaziantep": (37.0662, 37.3833), "Giresun": (40.9128, 38.3895),
    "Gümüşhane": (40.4602, 39.4813), "Hakkari": (37.5744, 43.7408),
    "Hatay": (36.4018, 36.3498), "Isparta": (37.7648, 30.5566),
    "Mersin": (36.8000, 34.6333), "İstanbul": (41.0082, 28.9784),
    "İzmir": (38.4237, 27.1428), "Kars": (40.6013, 43.0975),
    "Kastamonu": (41.3887, 33.7827), "Kayseri": (38.7312, 35.4787),
    "Kırklareli": (41.7333, 27.2167), "Kırşehir": (39.1425, 34.1709),
    "Kocaeli": (40.8533, 29.8815), "Konya": (37.8746, 32.4932),
    "Kütahya": (39.4242, 29.9833), "Malatya": (38.3552, 38.3095),
    "Manisa": (38.6191, 27.4289), "Kahramanmaraş": (37.5753, 36.9228),
    "Mardin": (37.3212, 40.7245), "Muğla": (37.2153, 28.3636),
    "Muş": (38.9462, 41.7539), "Nevşehir": (38.6939, 34.6857),
    "Niğde": (37.9667, 34.6833), "Ordu": (40.9839, 37.8764),
    "Rize": (41.0201, 40.5234), "Sakarya": (40.6940, 30.4358),
    "Samsun": (41.2867, 36.3300), "Siirt": (37.9333, 41.9500),
    "Sinop": (42.0231, 35.1531), "Sivas": (39.7477, 37.0179),
    "Tekirdağ": (40.9833, 27.5167), "Tokat": (40.3167, 36.5500),
    "Trabzon": (41.0027, 39.7168), "Tunceli": (39.3074, 39.4388),
    "Şanlıurfa": (37.1591, 38.7969), "Uşak": (38.6823, 29.4082),
    "Van": (38.4891, 43.4089), "Yozgat": (39.8181, 34.8147),
    "Zonguldak": (41.4564, 31.7987), "Aksaray": (38.3687, 34.0370),
    "Bayburt": (40.2552, 40.2249), "Karaman": (37.1759, 33.2287),
    "Kırıkkale": (39.8468, 33.5153), "Batman": (37.8812, 41.1351),
    "Şırnak": (37.4187, 42.4918), "Bartın": (41.5811, 32.4610),
    "Ardahan": (41.1105, 42.7022), "Iğdır": (39.9167, 44.0333),
    "Yalova": (40.6500, 29.2667), "Karabük": (41.2061, 32.6204),
    "Kilis": (36.7184, 37.1212), "Osmaniye": (37.0742, 36.2478),
    "Düzce": (40.8438, 31.1565),
}


def en_yakin_il(lat, lng):
    """Haversine ile 81 il merkezinden en yakınını bulur. Ağ gerektirmez."""
    R = 6371.0
    lat1 = math.radians(lat)
    en_yakin, en_kucuk_mesafe = "", float("inf")
    for il, (il_lat, il_lng) in IL_MERKEZLERI.items():
        lat2 = math.radians(il_lat)
        dlat = math.radians(il_lat - lat)
        dlng = math.radians(il_lng - lng)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
        )
        mesafe = 2 * R * math.asin(math.sqrt(a))
        if mesafe < en_kucuk_mesafe:
            en_kucuk_mesafe, en_yakin = mesafe, il
    return en_yakin

# --- Haberle doğrulama ----------------------------------------------------
# FIRMS tek başına "yangın" demiyor, sadece ısı anomalisi tespit ediyor
# (bkz. yukarıdaki modül dokümanı). Bir noktanın gerçekten aktif bir
# orman yangını olduğunu, sitenin zaten scraper'la (tarayici.py) topladığı
# haber verisiyle eşleştirerek doğruluyoruz: haberin başlığı/özeti "yangın"
# geçiyor mu ve haberin tarihi + metni, bu FIRMS noktasının tarihi ve
# çözümlenmiş il/ilçe/yerleşim adıyla örtüşüyor mu?
#
# Not: haber verisinde koordinat YOK (bkz. haberler.json şeması), bu yüzden
# coğrafi mesafeyle değil, yer adı metin eşleşmesiyle doğruluyoruz —
# FIRMS noktasının Nominatim'den çözdüğü il/ilçe/yerleşim adı, haberin
# metninde geçiyorsa eşleşme sayılır.
FIRE_ANAHTAR_KELIMELER = ("yangın", "yangını", "yangınlar", "alevler")
DOGRULAMA_GUN_TOLERANSI = 2  # haber tarihi ile tespit tarihi arasındaki azami fark

# Türkçe büyük harfleri, standart Unicode str.lower()'ın yanlış sonuç
# verdiği (İ -> 'i̇' iki karakter, I -> 'i' değil 'ı' olmalı) noktalarda
# doğru küçük harfe çeviren yardımcı. guven_kod karşılaştırmasında
# yaşanan aynı Unicode normalizasyon sorununun metin eşleşmesine de
# sessizce sızmasını önlemek için kullanılıyor.
_TR_KUCUK_HARF = str.maketrans({"İ": "i", "I": "ı", "Ğ": "ğ", "Ü": "ü", "Ş": "ş", "Ö": "ö", "Ç": "ç"})


def tr_kucuk(s):
    return (s or "").translate(_TR_KUCUK_HARF).lower()


def _haber_tarihini_coz(tarih_str):
    """'2026-08-04T16:30:47+03:00' veya '2026-08-04' formatlarını, saat
    dilimi bilgisini atarak karşılaştırılabilir bir date'e çevirir."""
    if not tarih_str:
        return None
    try:
        temiz = tarih_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(temiz)
        return dt.date()
    except ValueError:
        try:
            return datetime.strptime(tarih_str[:10], "%Y-%m-%d").date()
        except ValueError:
            return None


def _yangin_haberlerini_yukle():
    """Repo kökündeki mevcut haber/ihlal JSON dosyalarından 'yangın'
    anahtar kelimesi geçenleri toplar. Ağ isteği yapmaz — dagitici.py
    tarafından zaten üretilmiş dosyaları okur."""
    KAYNAK_DOSYALAR = (
        ("haberler.json", "haberler"),
        ("haberler-iklim.json", "haberler"),
        ("haberler-orman.json", "haberler"),
        ("haberler-direnis.json", "haberler"),
        ("ihlaller.json", "ihlaller"),
    )
    haberler = []
    gorulen_id = set()
    for dosya, anahtar in KAYNAK_DOSYALAR:
        if not os.path.exists(dosya):
            continue
        try:
            with open(dosya, encoding="utf-8") as f:
                veri = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        for h in veri.get(anahtar, []) or []:
            hid = h.get("id") or h.get("url")
            if hid and hid in gorulen_id:
                continue
            metin = tr_kucuk(f"{h.get('baslik', '')} {h.get('ozet', '')}")
            if not any(kw in metin for kw in FIRE_ANAHTAR_KELIMELER):
                continue
            if hid:
                gorulen_id.add(hid)
            haberler.append(h)
    return haberler


def haberle_dogrula(kayitlar):
    """Her FIRMS kaydı için: yer adı (yerleşim/ilçe/il) haberin
    başlık+özetinde geçiyor mu ve tarihler DOGRULAMA_GUN_TOLERANSI
    içinde mi diye bakar; eşleşirse kaydı haber kaynağıyla işaretler."""
    haberler = _yangin_haberlerini_yukle()
    if not haberler:
        return kayitlar

    on_hesap = []
    for h in haberler:
        tarih = _haber_tarihini_coz(h.get("tarih", ""))
        metin = tr_kucuk(f"{h.get('baslik', '')} {h.get('ozet', '')}")
        on_hesap.append((h, tarih, metin))

    for k in kayitlar:
        adaylar = [x for x in (k.get("yerlesim"), k.get("ilce"), k.get("il")) if x]
        if not adaylar:
            continue
        tespit_tarihi = _haber_tarihini_coz(k.get("eklenme", ""))

        for h, haber_tarihi, metin in on_hesap:
            if tespit_tarihi and haber_tarihi:
                if abs((haber_tarihi - tespit_tarihi).days) > DOGRULAMA_GUN_TOLERANSI:
                    continue
            eslesen_yer = next((a for a in adaylar if tr_kucuk(a) in metin), None)
            if not eslesen_yer:
                continue
            k["dogrulanmis"] = True
            k["dogrulama_kaynagi"] = h.get("kaynak", "")
            k["dogrulama_baslik"] = h.get("baslik", "")
            k["dogrulama_url"] = h.get("url", "")
            k["dogrulama_yer"] = eslesen_yer
            break

    return kayitlar


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

    # NASA'nın resmi FIRMS API sunucuları: ana sunucu (firms) ve bakım/arıza
    # durumlarında kullanılması önerilen ayna sunucu (firms2). Ana sunucu
    # 3 denemede de zaman aşımına uğrarsa (bağlantı hatası — API'nin kendisi
    # bir hata mesajıyla YANIT VERMİŞ olması değil), otomatik olarak firms2'ye
    # geçiyoruz. Kaynak: NASA FIRMS bakım duyuruları
    # (https://www.earthdata.nasa.gov/data/alerts-outages) — "ana sunucuda
    # sorun olursa firms2.modaps.eosdis.nasa.gov'u kullanın" tavsiyesi.
    sunucular = [
        "https://firms.modaps.eosdis.nasa.gov",
        "https://firms2.modaps.eosdis.nasa.gov",
    ]

    for sunucu_index, taban_url in enumerate(sunucular):
        url = f"{taban_url}/api/area/csv/{MAP_KEY}/{sensor}/{TURKIYE_BBOX}/{GUN_ARALIGI}"
        req = urllib.request.Request(url, headers={"User-Agent": "ekoloji-izleme/1.0"})

        ham = None
        son_hata = None
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
            if sunucu_index > 0:
                print(f"  ℹ {sensor}: ana sunucu yanıt vermedi, yedek sunucudan ({taban_url}) veri alındı.")
            break

        if sunucu_index == 0:
            print(f"  ⚠ {sensor}: ana sunucu (firms) 3 denemede de başarısız oldu ({son_hata}), yedek sunucu (firms2) deneniyor...")
        else:
            print(f"  ✗ {sensor}: hem ana hem yedek sunucu (firms/firms2) 3'er denemede de başarısız oldu: {son_hata}")

    if ham is None:
        return []

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

        # Nominatim çağrısı hiç yapılmadıysa (max_geocode aşıldı) ya da
        # yapıldı ama sonuç boş döndüyse (ağ hatası, rate limit, vs.),
        # popup'ta "Konum bilgisi yok" görünmesin diye en azından il adını
        # çevrimdışı hesapla — bu her zaman çalışır, ağ gerektirmez.
        if not il and not ilce and not yerlesim:
            il = en_yakin_il(lat, lng)

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

        # Harita rengi bu koda göre belirlenir: sabit, dile bağlı olmayan
        # tek harf (h/n/l). guven_seviye ise SADECE ekranda gösterilecek
        # Türkçe metin içindir — renk mantığı asla bu metne bakmamalı,
        # çünkü Türkçe karakter karşılaştırması (ü, ş) Unicode normalizasyon
        # farklarında sessizce yanlış sonuç verebilir (bu yüzden önceden
        # yüksek/orta noktalar haritada gri/"düşük" görünüyordu).
        if guven in GECERLI_GUVEN:
            guven_kod = guven  # zaten h/n/l
        elif guven.isdigit():
            sayi = int(guven)
            guven_kod = "h" if sayi >= 80 else ("n" if sayi >= 50 else "l")
        else:
            guven_kod = "l"

        guven_seviye = {"h": "Yüksek", "n": "Orta", "l": "Düşük"}[guven_kod]

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
            f"FRP: {frp} MW, güvenilirlik kodu: {guven}"
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
            "guven_kod": guven_kod,
            "alt_kategori": "",
            "kaynak_turu": "uydu",
        }
        kayitlar.append(kayit)

    return kayitlar


def arsive_yaz(kayitlar):
    """Kayıtları 'eklenme' (acq_date) alanına göre gruplar ve her tarih için
    arsiv/YYYY-MM-DD.json dosyasını tam olarak o günün kayıtlarıyla üretir.

    GUN_ARALIGI=1 olduğundan pratikte tek grup (bugünkü UTC tarihi) oluşur;
    script saatlik çalıştığı için bu dosya gün boyunca defalarca baştan
    yazılır ve günün kümülatif tespitlerini taşır. Gece yarısı UTC sınırında
    bazı geç saatlerdeki taramaların birkaç dakika farkla bir önceki güne
    ait kayıt döndürmesi ihtimaline karşı gruplama tek bir sabit tarihe
    güvenmek yerine kayıtların kendi 'eklenme' alanına bakar.
    """
    os.makedirs("arsiv", exist_ok=True)
    gruplar = {}
    for k in kayitlar:
        tarih = k.get("eklenme") or "bilinmeyen"
        gruplar.setdefault(tarih, []).append(k)

    yazilanlar = []
    for tarih, grup in gruplar.items():
        if tarih == "bilinmeyen":
            continue
        cikti = {
            "guncelleme": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "kayit_sayisi": len(grup),
            "kayitlar": grup,
        }
        yol = os.path.join("arsiv", f"{tarih}.json")
        with open(yol, "w", encoding="utf-8") as f:
            json.dump(cikti, f, ensure_ascii=False, indent=2)
        yazilanlar.append(yol)
    return yazilanlar


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

    kayitlar = haberle_dogrula(kayitlar)
    dogrulanan_sayisi = sum(1 for k in kayitlar if k.get("dogrulanmis"))
    print(f"{dogrulanan_sayisi} kayıt haber kaynağıyla doğrulandı.")

    cikti = {
        "guncelleme": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "kayit_sayisi": len(kayitlar),
        "kayitlar": kayitlar,
    }

    with open("firms_yangin.json", "w", encoding="utf-8") as f:
        json.dump(cikti, f, ensure_ascii=False, indent=2)

    with open("firms_yangin.geojson", "w", encoding="utf-8") as f:
        json.dump(geojsona_cevir(kayitlar), f, ensure_ascii=False, indent=2)

    arsiv_dosyalari = arsive_yaz(kayitlar)

    print(f"Tamamlandı: {len(kayitlar)} kayıt -> firms_yangin.json / firms_yangin.geojson")
    if arsiv_dosyalari:
        print(f"Arşiv güncellendi: {', '.join(arsiv_dosyalari)}")


if __name__ == "__main__":
    main()
