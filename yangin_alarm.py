#!/usr/bin/env python3
"""
yangin_alarm.py
-----------------
firms_yangin_tarama.py'nin ürettiği firms_yangin.json'daki tespitleri,
tarayıcıdan (yangin-izleme.html, "Konumumu Kaydet" butonu) en son
kaydedilmiş konumla (son_konum.json, Plesk'te) karşılaştırır. Belirtilen
yarıçap içine düşen ve DAHA ÖNCE ALARMI ÇALINMAMIŞ her tespit için
Telegram üzerinden mesaj gönderir.

Bu script firms-tarama.yml akışının bir parçasıdır; firms_yangin_tarama.py
çalıştıktan HEMEN SONRA, aynı job içinde (firms_yangin.json diskte
zaten var) çalıştırılır — ayrıca bir HTTP isteğiyle tekrar indirmeye
gerek yok.

KONUM: "Gerçek zamanlı canlı takip" değil, "son ziyarette tarayıcının
bildirdiği konum" esas alınır (bkz. son_konum.json). Statik site +
saatlik GitHub Actions mimarisinde bunun ötesi (native arka plan konum
izni) mümkün değil.

TEKRAR ALARM ENGELLEME: Aynı fiziksel tespit her saatlik taramada YENİDEN
üretiliyor (firms_yangin_tarama.py her seferinde yeni bir rastgele "id"
atıyor), bu yüzden "id" ile tekrar kontrolü YAPILAMAZ. Bunun yerine
firms_yangin_tarama.py'nin kendi iç tekrar-eleme mantığıyla aynı anahtar
kullanılır: (yuvarlanmış lat, yuvarlanmış lng, tespit tarihi). Bu anahtar
alarm_gonderilenler.json içinde saklanır ve 3 günden eski kayıtlar
budanır (dosya sonsuza kadar büyümesin diye — bir tespit zaten birkaç
günden fazla "aktif" kalmıyor).

ORTAM DEĞİŞKENLERİ (GitHub Secrets)
------------------------------------
  TELEGRAM_BOT_TOKEN   — @BotFather'dan alınan bot token'ı
  TELEGRAM_CHAT_ID     — mesajın gideceği sohbetin chat_id'si
  SITE_URL             — diğer scriptlerle aynı (son_konum.json ve
                          alarm_gonderilenler.json buradan okunur)

KULLANIM
--------
  python yangin_alarm.py
  (firms_yangin.json'ın aynı dizinde, son_konum.json ve
   alarm_gonderilenler.json'ın da indirilmiş olması beklenir —
   bkz. firms-tarama.yml)
"""

import json
import math
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

YARICAP_KM = 25
BUDAMA_GUN = 3  # bu kadar günden eski alarm kayıtları silinir

SON_KONUM_DOSYA = "son_konum.json"
ALARM_GECMISI_DOSYA = "alarm_gonderilenler.json"
FIRMS_DOSYA = "firms_yangin.json"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()


def haversine_km(lat1, lng1, lat2, lng2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def dosya_oku(yol, varsayilan):
    if not os.path.isfile(yol):
        return varsayilan
    try:
        with open(yol, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return varsayilan


def anahtar_uret(kayit):
    lat = round(kayit["koordinatlar"]["lat"], 3)
    lng = round(kayit["koordinatlar"]["lng"], 3)
    tarih = kayit.get("eklenme", "")
    return f"{lat}_{lng}_{tarih}"


def alarm_gecmisini_budala(gecmis):
    """3 günden eski anahtarları at — dosya sınırsız büyümesin."""
    sinir = (datetime.now(timezone.utc) - timedelta(days=BUDAMA_GUN)).strftime("%Y-%m-%d")
    return {k: v for k, v in gecmis.items() if v.get("tarih", "") >= sinir}


def telegram_gonder(mesaj):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("  ⚠ TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID tanımlı değil, mesaj gönderilemedi.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    veri = json.dumps({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mesaj,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=veri, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            r.read()
        return True
    except urllib.error.URLError as e:
        print(f"  ✗ Telegram gönderim hatası: {e}")
        return False


def mesaj_metni(kayit, mesafe_km):
    konum = " / ".join(filter(None, [kayit.get("yerlesim"), kayit.get("ilce"), kayit.get("il")])) or "konum bilinmiyor"
    guven = kayit.get("guven_seviye", "bilinmiyor")
    frp = ""
    if "FRP:" in kayit.get("teknik_detay", ""):
        try:
            frp = kayit["teknik_detay"].split("FRP:")[1].split("MW")[0].strip() + " MW"
        except IndexError:
            pass
    return (
        f"🔥 <b>Yakın bölgede yangın tespiti</b>\n"
        f"Konum: {konum}\n"
        f"Kayıtlı merkezine mesafe: ~{mesafe_km:.1f} km\n"
        f"Güvenilirlik: {guven}" + (f" · FRP: {frp}" if frp else "") + "\n"
        f"Tarih: {kayit.get('eklenme', '—')}\n"
        f"Not: Isıl anomali tespiti; mutlaka yangın anlamına gelmez."
    )


def main():
    son_konum = dosya_oku(SON_KONUM_DOSYA, None)
    if not son_konum or "lat" not in son_konum or "lng" not in son_konum:
        print("son_konum.json bulunamadı/boş — kayıtlı bir konum yok, alarm kontrolü atlanıyor.")
        return

    merkez_lat, merkez_lng = son_konum["lat"], son_konum["lng"]
    print(f"Kayıtlı konum: {merkez_lat:.4f}, {merkez_lng:.4f} "
          f"(güncelleme: {son_konum.get('guncelleme', 'bilinmiyor')})")

    firms = dosya_oku(FIRMS_DOSYA, {})
    kayitlar = firms.get("kayitlar", [])
    if not kayitlar:
        print("firms_yangin.json boş ya da bulunamadı, alarm kontrolü atlanıyor.")
        return

    gecmis = dosya_oku(ALARM_GECMISI_DOSYA, {})
    gecmis = alarm_gecmisini_budala(gecmis)

    yeni_alarm_sayisi = 0
    for k in kayitlar:
        try:
            lat = k["koordinatlar"]["lat"]
            lng = k["koordinatlar"]["lng"]
        except (KeyError, TypeError):
            continue

        mesafe = haversine_km(merkez_lat, merkez_lng, lat, lng)
        if mesafe > YARICAP_KM:
            continue

        anahtar = anahtar_uret(k)
        if anahtar in gecmis:
            continue  # bu tespit için zaten alarm gönderilmiş

        if telegram_gonder(mesaj_metni(k, mesafe)):
            yeni_alarm_sayisi += 1
        gecmis[anahtar] = {"tarih": k.get("eklenme", ""), "mesafe_km": round(mesafe, 1)}

    with open(ALARM_GECMISI_DOSYA, "w", encoding="utf-8") as f:
        json.dump(gecmis, f, ensure_ascii=False, indent=2)

    print(f"Tamamlandı: {yeni_alarm_sayisi} yeni alarm gönderildi "
          f"({len(gecmis)} kayıt alarm geçmişinde tutuluyor).")


if __name__ == "__main__":
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("UYARI: TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID ortam değişkenleri tanımlı değil.")
        print("Script yine de çalışacak (alarm geçmişini günceller) ama mesaj gönderemeyecek.")
    main()
