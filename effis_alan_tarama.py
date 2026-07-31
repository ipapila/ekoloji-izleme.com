#!/usr/bin/env python3
"""
effis_alan_tarama.py
---------------------
EFFIS (European Forest Fire Information System / Copernicus) "Rapid Damage
Assessment" WFS servisinden, Türkiye sınırları içindeki yanmış alan
(burnt-area) poligonlarını çeker ve yangin-izleme.html'in beklediği
effis_yangin_alanlari.geojson dosyasını üretir.

Bu, firms_yangin_tarama.py'nin ürettiği NOKTA tespitlerinden farklıdır:
FIRMS/VIIRS-MODIS noktaları "burada ısı anomalisi var" der; EFFIS'in bu
katmanı ise uydu görüntüsünden çıkarılmış GERÇEK yanmış alan SINIRINI
(poligon) verir. EFFIS bu katmanı sadece ~30 hektar ve üzerindeki, uydu
görüntüsüyle doğrulanmış yangınlar için üretir — bu yüzden birçok gün
dosya boş bir FeatureCollection olarak kalması NORMALDİR (küçük/yeni
başlayan bir yangın henüz bu eşiği geçmemiş veya henüz işlenmemiş olabilir).

VERİ KAYNAĞI
------------
EFFIS'in resmi "Data and services" sayfasında (bkz.
https://forest-fire.emergency.copernicus.eu/applications/data-and-services)
"Download real-time updated Burnt Areas database" başlığı altında
doğrudan belgelenen WFS uç noktasını kullanıyoruz:

  https://maps.effis.emergency.copernicus.eu/effis
    ?service=WFS&version=1.1.0&request=GetFeature
    &typename=ms:modis.ba.poly
    &outputformat=geojson
    &bbox=<west,south,east,north>,EPSG:4326

Sayfada resmi örnek sadece SHAPEZIP/SPATIALITEZIP çıktısını gösteriyordu;
bu bir standart MapServer WFS olduğu için outputformat=geojson da
desteklenmesi beklenir (MapServer'ın yerleşik GeoJSON çıktı formatı).
BBOX parametresi ise vendor-özel değil, OGC WFS 1.1.0 standardının bir
parçası olduğu için güvenle kullanılabilir.

ÖNEMLİ NOT: Bu ortamda internet erişimi kapalı olduğu için bu isteği
gerçekten çalıştırıp test edemedim. İlk çalıştırmayı GitHub Actions'ta
(veya internet erişimi olan bir yerde) yapıp çıktıyı/logu kontrol etmen
gerekiyor. Aşağıdaki kod, sunucunun outputformat=geojson'ı reddetmesi ya
da beklenmedik bir yanıt dönmesi ihtimaline karşı savunmacı yazıldı:
JSON parse başarısız olursa script çökmek yerine boş ama geçerli bir
FeatureCollection yazar ve hatayı GitHub Actions logunda açıkça basar —
böylece harita bozulmaz, sadece o çalıştırmada güncellenmemiş olur.

Eğer outputformat=geojson çalışmazsa, alternatif olarak GML alıp Python
tarafında (ör. bir XML parser ile) GeoJSON'a çevirmek gerekebilir — ilk
çalıştırmanın logunu paylaşırsan gerekirse bu yedek yolu ekleriz.

DAHA HASSAS BİR ALTERNATİF (denenmedi, ileride denenebilir)
-------------------------------------------------------------
EFFIS'in "nrt.ba.poly" gibi VIIRS tabanlı, MODIS'e göre daha küçük
yangınları da (muhtemelen daha düşük hektar eşiğiyle) yakalayan bir
near-real-time katmanı olduğuna dair üçüncü parti kaynaklarda referans
var, ama resmi "Data and services" sayfasında belgelenmediği ve typename
adını doğrulayamadığım için şimdilik eklemedim.

KULLANIM
--------
python effis_alan_tarama.py
(Ortam değişkeni gerekmez — EFFIS WFS servisi anahtar/API key istemiyor.)
"""

import io
import json
import math
import socket
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

# GitHub Actions runner'larında bazen DNS IPv6 adresi döndürüyor ama
# route yok -> "Network is unreachable" hatası. firms_yangin_tarama.py'deki
# aynı düzeltme.
_orig_getaddrinfo = socket.getaddrinfo


def _ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    sonuc = _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
    return sonuc or _orig_getaddrinfo(host, port, family, type, proto, flags)


socket.getaddrinfo = _ipv4_getaddrinfo


# --- İl merkezleri (firms_yangin_tarama.py ile aynı liste) ---------------
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


# --- Ayarlar -------------------------------------------------------------

# west,south,east,north — firms_yangin_tarama.py'deki TURKIYE_BBOX ile aynı
TURKIYE_BBOX = (25.5, 35.5, 45.0, 42.5)

EFFIS_WFS_URL = (
    "https://maps.effis.emergency.copernicus.eu/effis"
    "?service=WFS&version=1.1.0&request=GetFeature"
    "&typename=ms:modis.ba.poly"
    "&outputformat=geojson"
    "&srsname=EPSG:4326"
    "&bbox={west},{south},{east},{north},EPSG:4326"
).format(
    west=TURKIYE_BBOX[0], south=TURKIYE_BBOX[1],
    east=TURKIYE_BBOX[2], north=TURKIYE_BBOX[3],
)

CIKTI_DOSYASI = "effis_yangin_alanlari.geojson"
ZAMAN_ASIMI = 60  # saniye — poligon indirmesi FIRMS'ten daha büyük olabilir


def bbox_icinde_mi(geom):
    """Geometrinin (yaklaşık) Türkiye bbox'ı ile kesişip kesişmediğini,
    tüm koordinatları tarayarak kabaca kontrol eder. Sunucu tarafı BBOX
    filtresi beklenmedik davranırsa (örn. farklı eksen sırası) diye
    istemci tarafında ikinci bir güvenlik katmanı."""
    w, s, e, n = TURKIYE_BBOX

    def koordlari_gez(c):
        if isinstance(c[0], (int, float)):
            yield c
        else:
            for alt in c:
                yield from koordlari_gez(alt)

    try:
        for lon, lat, *_ in koordlari_gez(geom["coordinates"]):
            if w - 1 <= lon <= e + 1 and s - 1 <= lat <= n + 1:
                return True
    except Exception:
        return True  # emin değilsek eleme, göstermeyi tercih et
    return False


def poligon_merkezi(geom):
    """Kaba merkez (ortalama koordinat) — il eşleştirmesi için yeterli,
    gerçek centroid hesaplamaya gerek yok."""
    toplam_lat = toplam_lon = sayac = 0

    def koordlari_gez(c):
        if isinstance(c[0], (int, float)):
            yield c
        else:
            for alt in c:
                yield from koordlari_gez(alt)

    for lon, lat, *_ in koordlari_gez(geom["coordinates"]):
        toplam_lat += lat
        toplam_lon += lon
        sayac += 1
    if sayac == 0:
        return None
    return toplam_lat / sayac, toplam_lon / sayac


def veriyi_cek():
    req = urllib.request.Request(
        EFFIS_WFS_URL,
        headers={
            "User-Agent": "ekoloji-izleme.com yangin-izleme (effis burnt-area sync)",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=ZAMAN_ASIMI) as r:
        ham = r.read()
    return ham


def bos_koleksiyon_yaz(sebep):
    print(f"UYARI: {sebep} — boş (ama geçerli) bir FeatureCollection yazılıyor "
          f"ki harita bozulmasın.", file=sys.stderr)
    with open(CIKTI_DOSYASI, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": []}, f, ensure_ascii=False)


def main():
    try:
        ham = veriyi_cek()
    except urllib.error.HTTPError as e:
        gövde = ""
        try:
            gövde = e.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            pass
        bos_koleksiyon_yaz(f"EFFIS WFS isteği HTTP {e.code} döndü. Yanıt: {gövde!r}")
        return
    except Exception as e:
        bos_koleksiyon_yaz(f"EFFIS WFS isteği başarısız: {e!r}")
        return

    try:
        veri = json.loads(ham)
    except Exception:
        # outputformat=geojson desteklenmiyor olabilir; sunucu muhtemelen
        # bir XML hata/exception raporu döndürdü. İlk 500 karakteri logla
        # ki hangi hatayı aldığımızı görüp script'i buna göre düzeltelim.
        onizleme = ham[:500].decode("utf-8", errors="replace") if isinstance(ham, bytes) else str(ham)[:500]
        bos_koleksiyon_yaz(
            "EFFIS yanıtı geçerli JSON değil — muhtemelen outputformat=geojson "
            f"desteklenmiyor. Sunucu yanıtından ilk 500 karakter: {onizleme!r}"
        )
        return

    ozellikler = veri.get("features", [])
    print(f"EFFIS WFS'ten {len(ozellikler)} poligon geldi (bbox filtresi ile).")

    filtrelenmis = []
    for f in ozellikler:
        geom = f.get("geometry")
        if not geom or not geom.get("coordinates"):
            continue
        if not bbox_icinde_mi(geom):
            continue
        ozellik = dict(f.get("properties") or {})
        merkez = poligon_merkezi(geom)
        if merkez:
            ozellik["il"] = en_yakin_il(*merkez)
        f["properties"] = ozellik
        filtrelenmis.append(f)

    print(f"Türkiye bbox'ı içinde kalan: {len(filtrelenmis)} poligon.")

    cikti = {
        "type": "FeatureCollection",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "features": filtrelenmis,
    }
    with open(CIKTI_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(cikti, f, ensure_ascii=False, indent=2)

    print(f"Tamamlandı: {len(filtrelenmis)} poligon -> {CIKTI_DOSYASI}")


if __name__ == "__main__":
    main()
