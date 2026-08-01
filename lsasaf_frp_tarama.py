#!/usr/bin/env python3
"""
LSA SAF FRP-PIXEL (MSG) HDF5 İndirici ve Dönüştürücü
Kullanım: python lsasaf_frp_tarama.py [--inspect]
"""

import os
import sys
import json
import h5py
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta
import time
import re
import math

# ---------------------------- KONFIGURASYON ----------------------------
BASE_URL = "https://datalsasaf.lsasvcs.ipma.pt/PRODUCTS/MSG/FRP-PIXEL/HDF5"
USER = os.environ.get('LSA_USER')
PASS = os.environ.get('LSA_PASS')
MAX_RETRIES = 3
RETRY_DELAYS = [5, 10, 15]  # saniye

# ---------------------------- YARDIMCI FONKSİYONLAR ----------------------------
def auth_get(url, retry_count=0):
    """Basic Auth ile GET isteği gönder, 401'de otomatik dene."""
    if not USER or not PASS:
        print("✗ HATA: LSA_USER veya LSA_PASS environment değişkenleri tanımlı değil!")
        sys.exit(1)

    auth = HTTPBasicAuth(USER, PASS)
    try:
        resp = requests.get(url, auth=auth, timeout=30)
        if resp.status_code == 401:
            raise requests.exceptions.HTTPError("401 Unauthorized")
        resp.raise_for_status()
        return resp
    except requests.exceptions.HTTPError as e:
        if retry_count < MAX_RETRIES and "401" in str(e):
            delay = RETRY_DELAYS[retry_count] if retry_count < len(RETRY_DELAYS) else 5
            print(f"  ⚠ bağlantı hatası ({e}), {delay}sn sonra {retry_count+2}. deneme...")
            time.sleep(delay)
            return auth_get(url, retry_count + 1)
        else:
            raise

def list_directory(date_path):
    """
    Verilen tarih klasörünün (YYYY/MM/DD) Apache/nginx dizin listesini
    çeker ve içindeki dosya adlarını döndürür. LSA SAF sunucusu bu
    klasörlere GET ile gidildiğinde standart bir HTML index sayfası
    döndürüyor; BeautifulSoup gibi ek bağımlılık gerekmesin diye href'leri
    basit bir regex ile ayıklıyoruz.
    """
    url = f"{BASE_URL}/{date_path}/"
    try:
        resp = auth_get(url)
    except Exception:
        return []
    hrefs = re.findall(r'href="([^"?]+)"', resp.text)
    # "../" gibi üst dizin linklerini ve alt klasörleri (sonu / ile bitenleri) ele
    return [h for h in hrefs if h and not h.endswith('/') and h not in ('..',)]

# Gerçek piksel verisini içeren dosya adı deseni:
#   HDF5_LSASAF_MSG_FRP-PIXEL[-ListProduct]_MSG-Disk_YYYYMMDDHHMM (+.bz2 olabilir)
# NOT: Önceki sürümde "-ListProduct" ekli dosyaların YANLIŞ dosya olduğu
# varsayılmıştı — bu YANLIŞ çıktı. Kanıt: o dosya başarıyla indi (141 KB,
# geçerli HDF5) ve sadece içindeki dataset isimleri beklenenle eşleşmedi;
# yani "ListProduct" muhtemelen bu ürün için TEK/DOĞRU dosya varyantı.
# Bu yüzden desen artık "-ListProduct" ekini de kabul ediyor — asıl sorun
# process_hdf5()'teki dataset isim eşleştirmesi (bkz. aşağıdaki --inspect notu).
FRP_DOSYA_DESENI = re.compile(r'^HDF5_LSASAF_MSG_FRP-PIXEL(?:-\w+)?_MSG-Disk_(\d{12})(?:\.\w+)?$')

def find_latest_file():
    """Son birkaç saat içindeki klasörleri tarayıp en güncel GERÇEK
    FRP-PIXEL veri dosyasının URL'sini döndürür (ListProduct dosyaları
    hariç tutularak)."""
    now = datetime.utcnow()
    en_iyi = None  # (timestamp_str, url)

    # Son 4 saatin klasörlerini kontrol et (gün sınırını geçen saatler için
    # date_path değişebileceğinden, aynı date_path'i tekrar tekrar
    # sorgulamamak için cache'liyoruz).
    kontrol_edilen_klasorler = set()
    for hour_offset in range(0, 4):
        dt = now - timedelta(hours=hour_offset)
        date_path = dt.strftime("%Y/%m/%d")
        if date_path in kontrol_edilen_klasorler:
            continue
        kontrol_edilen_klasorler.add(date_path)

        dosyalar = list_directory(date_path)
        if not dosyalar:
            continue

        for dosya_adi in dosyalar:
            eslesme = FRP_DOSYA_DESENI.match(dosya_adi)
            if not eslesme:
                continue
            zaman_str = eslesme.group(1)
            try:
                dosya_zamani = datetime.strptime(zaman_str, "%Y%m%d%H%M")
            except ValueError:
                continue
            if dosya_zamani > now:
                continue  # gelecekteki bir zaman damgası olamaz
            if en_iyi is None or zaman_str > en_iyi[0]:
                en_iyi = (zaman_str, f"{BASE_URL}/{date_path}/{dosya_adi}")

        # En güncel saatin klasöründe zaten bir eşleşme bulduysak daha eski
        # saatlere bakmaya gerek yok.
        if en_iyi is not None:
            break

    if en_iyi is None:
        raise FileNotFoundError(
            "Son 4 saat içinde FRP-PIXEL_MSG-Disk desenine uyan bir dosya bulunamadı. "
            "Sunucudaki dosya adlandırma deseni değişmiş olabilir — bir klasörü elle "
            "(tarayıcıdan ya da curl ile) kontrol edin."
        )

    print(f"→ Bulunan dosya: {en_iyi[1]}")
    return en_iyi[1]

def download_hdf5(url, local_path="temp.h5"):
    """Verilen URL'den HDF5 dosyasını indir. Dosya .bz2 ile sıkıştırılmış
    geldiyse (bazı LSA SAF ürünlerinde olduğu gibi) otomatik açar."""
    print(f"↓ İndiriliyor: {url}")
    resp = auth_get(url)
    icerik = resp.content
    total_size = len(icerik)

    if url.endswith('.bz2'):
        import bz2
        icerik = bz2.decompress(icerik)
        print(f"  ↳ .bz2 açıldı ({total_size // 1024} KB → {len(icerik) // 1024} KB)")

    with open(local_path, 'wb') as f:
        f.write(icerik)
    print(f"✓ İndirme tamamlandı ({total_size // 1024} KB)")
    return local_path

# ---------------------------- HDF5 İŞLEME ----------------------------
def inspect_hdf5(file_path):
    """HDF5 içindeki tüm dataset/grup yapısını ekrana basar."""
    print(f"\n🔍 HDF5 Yapısı İnceleniyor: {file_path}")
    with h5py.File(file_path, 'r') as f:
        def print_structure(name, obj):
            if isinstance(obj, h5py.Dataset):
                print(f"  📊 Dataset : {name} → shape: {obj.shape}, dtype: {obj.dtype}")
            elif isinstance(obj, h5py.Group):
                print(f"  📁 Group   : {name}")
        f.visititems(print_structure)

def _yapi_dokumu_bas(f):
    """inspect_hdf5 ile aynı çıktıyı üretir — dataset bulunamadığında
    --inspect'i ayrıca çalıştırmaya gerek kalmadan aynı bilgiyi log'a basar."""
    print("  ── HDF5 yapısı ──")
    def yaz(name, obj):
        if isinstance(obj, h5py.Dataset):
            alanlar = f" alanlar: {obj.dtype.names}" if obj.dtype.names else ""
            print(f"    📊 {name} → shape:{obj.shape} dtype:{obj.dtype}{alanlar}")
        elif isinstance(obj, h5py.Group):
            print(f"    📁 {name}")
    f.visititems(yaz)
    print("  ── kök öznitelikler (attrs) ──")
    for k, v in f.attrs.items():
        print(f"    {k}: {v}")


def _tum_datasetleri_topla(f):
    """Dosyanın TAMAMINI (her derinlikteki grubu) tarayıp yol→dataset eşlemi döndürür."""
    datasetler = {}
    def topla(name, obj):
        if isinstance(obj, h5py.Dataset):
            datasetler[name] = obj
    f.visititems(topla)
    return datasetler


def _dataset_bul(datasetler, tam_adaylar, alt_dize_adaylar):
    """
    Üç aşamalı arama:
      1) Herhangi bir derinlikteki dataset'in adı (son path segmenti)
         tam_adaylar'dan biriyle case-insensitive eşleşiyor mu?
      2) Compound (structured) dtype'lı bir dataset içinde, alanlardan
         biri tam_adaylar'dan biriyle eşleşiyor mu? (LSA SAF "List
         Product" dosyaları FRP/LAT/LON'u ayrı dataset yerine TEK bir
         tablo dataset'inin alanları olarak tutuyor olabilir.)
      3) Son çare: dataset adında alt_dize_adaylar'dan biri geçiyor mu?
    Döndürür: (numpy_array, bulunan_yol_bilgisi) ya da (None, None)
    """
    tam_kucuk = [a.lower() for a in tam_adaylar]

    for yol, ds in datasetler.items():
        basename = yol.rsplit('/', 1)[-1]
        if basename.lower() in tam_kucuk:
            return ds[:], yol

    for yol, ds in datasetler.items():
        if ds.dtype.names:
            for alan in ds.dtype.names:
                if alan.lower() in tam_kucuk:
                    return ds[alan][:], f"{yol}[{alan}]"

    for yol, ds in datasetler.items():
        basename = yol.rsplit('/', 1)[-1].lower()
        if any(sub in basename for sub in alt_dize_adaylar):
            return ds[:], yol
        if ds.dtype.names:
            for alan in ds.dtype.names:
                if any(sub in alan.lower() for sub in alt_dize_adaylar):
                    return ds[alan][:], f"{yol}[{alan}]"

    return None, None


def process_hdf5(file_path):
    """
    HDF5'ten FRP, Lat, Lon, Time verilerini oku, 
    JSON ve GeoJSON üret.
    """
    print(f"\n⚙ Veri işleniyor: {file_path}")
    data = {
        "type": "FeatureCollection",
        "features": []
    }
    
    with h5py.File(file_path, 'r') as f:
        datasetler = _tum_datasetleri_topla(f)

        frp_data, frp_yol = _dataset_bul(
            datasetler, ["FRP", "frp", "FRP_MW", "FRP_PIXEL"], ["frp"]
        )
        lat_data, lat_yol = _dataset_bul(
            datasetler, ["Latitude", "LATITUDE", "Lat", "LAT", "PIXEL_LATITUDE"], ["lat"]
        )
        lon_data, lon_yol = _dataset_bul(
            datasetler, ["Longitude", "LONGITUDE", "Lon", "LON", "PIXEL_LONGITUDE"], ["lon", "long"]
        )
        time_data, time_yol = _dataset_bul(
            datasetler,
            ["Time", "TIME", "AcqTime", "ACQTIME", "ACQUISITION_TIME", "OBSERVATION_TIME"],
            ["time"]
        )

        if frp_data is None or lat_data is None or lon_data is None:
            print("✗ Gerekli dataset'ler (FRP, Lat, Lon) bulunamadı!")
            print(f"  frp:{'bulundu → ' + frp_yol if frp_data is not None else 'BULUNAMADI'}")
            print(f"  lat:{'bulundu → ' + lat_yol if lat_data is not None else 'BULUNAMADI'}")
            print(f"  lon:{'bulundu → ' + lon_yol if lon_data is not None else 'BULUNAMADI'}")
            _yapi_dokumu_bas(f)
            sys.exit(1)

        print(f"  ✓ frp:{frp_yol}  lat:{lat_yol}  lon:{lon_yol}  time:{time_yol or '(yok)'}")

        # Verileri düzleştir (1D olmayabilir)
        frp_flat = frp_data.flatten()
        lat_flat = lat_data.flatten()
        lon_flat = lon_data.flatten()
        
        # Zaman varsa onu da düzleştir
        if time_data is not None:
            time_flat = time_data.flatten()
        else:
            time_flat = [None] * len(frp_flat)

        # GeoJSON oluştur
        for i in range(len(frp_flat)):
            frp_val = float(frp_flat[i])
            if math.isnan(frp_val) or frp_val <= 0:
                continue  # Sadece pozitif FRP değerlerini al (yangın var)
            
            lat = float(lat_flat[i])
            lon = float(lon_flat[i])
            if lat < -90 or lat > 90 or lon < -180 or lon > 180:
                continue

            prop = {
                "frp": round(frp_val, 2),
                "latitude": lat,
                "longitude": lon
            }
            if time_flat[i] is not None:
                # Zaman genelde sayısal (UTC saniye veya julian gün)
                try:
                    if time_flat[i] > 1e6:  # Unix timestamp (saniye)
                        dt_obj = datetime.utcfromtimestamp(float(time_flat[i]))
                        prop["time"] = dt_obj.isoformat()
                    else:
                        prop["time"] = str(time_flat[i])
                except:
                    prop["time"] = str(time_flat[i])

            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [lon, lat]
                },
                "properties": prop
            }
            data["features"].append(feature)

    print(f"✓ {len(data['features'])} adet yangın pikseli bulundu.")
    
    # JSON olarak kaydet
    with open("lsasaf_frp.json", "w", encoding="utf-8") as jf:
        json.dump(data, jf, indent=2, ensure_ascii=False)
    print("✓ lsasaf_frp.json oluşturuldu.")

    # GeoJSON olarak kaydet (zaten aynı formatta)
    with open("lsasaf_frp.geojson", "w", encoding="utf-8") as gf:
        json.dump(data, gf, indent=2, ensure_ascii=False)
    print("✓ lsasaf_frp.geojson oluşturuldu.")

# ---------------------------- ANA FONKSİYON ----------------------------
def main():
    inspect_mode = "--inspect" in sys.argv

    try:
        # 1. En son dosyayı bul
        file_url = find_latest_file()
        
        # 2. Dosyayı indir
        local_file = download_hdf5(file_url)
        
        # 3. İnceleme veya işleme
        if inspect_mode:
            inspect_hdf5(local_file)
        else:
            process_hdf5(local_file)
            
        # 4. Temizlik
        if os.path.exists(local_file):
            os.remove(local_file)
            print("🧹 Geçici dosya silindi.")
            
    except Exception as e:
        print(f"✗ Kritik hata: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
