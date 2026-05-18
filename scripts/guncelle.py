#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ekoloji-izleme.com — Otomatik Güncelleme (v2 — hassas filtre)
data.json'u GitHub'dan çeker, RSS'leri tarar, günceller.
"""

import json, requests, os, base64, datetime, re
import xml.etree.ElementTree as ET

REPO_OWNER = "ipapila"
REPO_NAME  = "ekoloji-izleme"
FILE_PATH  = "data.json"

# ─── FİLTRE SİSTEMİ ────────────────────────────────────────────────

# Tek başına yeterli — kesinlikle ekoloji haberi
YUKSEK_SINYAL = [
    "çevre ihlali", "çevre katliamı", "ÇED", "çed kararı", "çed raporu",
    "acele kamulaştırma", "taş ocağı", "taşocağı", "maden ocağı",
    "HES projesi", "RES projesi", "GES projesi", "termik santral",
    "nükleer santral", "ağaç katliamı", "ormansızlaşma", "orman tahribi",
    "sulak alan", "milli park", "doğal sit", "koruma alanı",
    "nesli tükenmekte", "nesli tehlike", "biyoçeşitlilik",
    "su kirliliği", "deniz kirliliği", "hava kirliliği", "toprak kirliliği",
    "atık depolama", "kaçak maden", "MAPEG", "EPDK kararı",
    "dere yatağı", "kıyı tahribatı", "ormana yapı",
    "resmî gazete maden", "resmî gazete çevre",
    "orman yangını", "sera gazı emisyon",
]

# Bağlam gerektiren — birden fazlası gerekir (genel kaynaklarda)
ORTA_SINYAL = [
    "çevre", "ekoloji", "orman", "maden", "baraj", "HES", "RES", "GES",
    "kamulaştırma", "doğa", "habitat", "kirlilik", "atık", "iklim",
    "yangın", "sel", "taşkın", "heyelan", "kıyı", "deniz", "göl", "dere",
    "su hakkı", "tarım arazisi", "bor", "altın maden", "jeotermal",
    "ihlal", "ruhsatsız", "izinsiz", "ağaç", "plastik kirlilik",
    "sondaj", "arama ruhsatı", "TEMA", "WWF", "Greenpeace",
    "yaban hayat", "doğal yaşam", "kuş türü", "balık türü",
]

# Güçlü negatif — varsa her zaman reddet
GUCLU_NEGATIF = [
    "faiz", "borsa", "döviz kuru", "enflasyon rakam", "bütçe açığı",
    "seçim sonuç", "cumhurbaşkanı açıkladı", "milletvekili",
    "futbol", "maç sonucu", "şampiyon", "transfer haberi", "penaltı",
    "dizi oyuncu", "film izle", "magazin", "ünlü çift", "nişanlandı",
    "moda koleksiyon", "kripto", "bitcoin fiyat", "nft",
    "müzik listesi", "konser bilet", "yeni albüm",
    "kalaşnikof", "silah eğitim", "muharebe", "hava saldırı",
    "bakanlara erdoğan", "soru kabul",   # siyasi yazışmalar
    "iran devrim",                        # uluslararası siyaset
    "liseli kız", "öğrenci kavga",        # okul olayları
]

# Genel kaynaklara özel ek negatif
GENEL_NEGATIF = [
    "ekonomi büyüme", "piyasa rallisi", "hisse senedi",
    "ihracat rekoru", "savunma sanayii", "operasyon düzenlendi",
    "turizm rekoru", "otel doluluk", "tatil fırsatı",
    "sağlık haberi", "hastane", "ameliyat",
    "üniversite sınav", "okul kayıt",
]


def ekoloji_puani(baslik: str, ozet: str = "", genel_kaynak: bool = True) -> int:
    metin = (baslik + " " + ozet).lower()

    # Güçlü negatif → 0
    if any(k.lower() in metin for k in GUCLU_NEGATIF):
        return 0
    if genel_kaynak and any(k.lower() in metin for k in GENEL_NEGATIF):
        return 0

    puan = 0
    baslik_lower = baslik.lower()

    for k in YUKSEK_SINYAL:
        if k.lower() in metin:
            puan += 3
        if k.lower() in baslik_lower:
            puan += 2  # başlıkta geçmesi ekstra

    for k in ORTA_SINYAL:
        if k.lower() in metin:
            puan += 1

    return puan


def ekoloji_mi(baslik: str, ozet: str = "", genel_kaynak: bool = True) -> bool:
    puan = ekoloji_puani(baslik, ozet, genel_kaynak)
    esik = 4 if genel_kaynak else 1
    sonuc = puan >= esik
    if not sonuc and puan > 0:
        print(f"    ✗ düşük puan [{puan}/{esik}]: {baslik[:60]}")
    return sonuc


# ─── RSS KAYNAKLARI ─────────────────────────────────────────────────

KAYNAK_RSS = [
    # Odaklı çevre kaynakları — düşük eşik (1)
    {"ad": "Bianet Çevre",  "url": "https://bianet.org/topic/cevre/feed/rss",     "etiket": "Haber",    "genel": False},
    {"ad": "İklim Haber",   "url": "https://iklimhaber.org/feed/",                 "etiket": "İklim",    "genel": False},
    {"ad": "Yeşil Gazete",  "url": "https://yesilgazete.org/feed/",                "etiket": "Haber",    "genel": False},
    {"ad": "350.org TR",    "url": "https://350.org/tr/feed/",                     "etiket": "Direniş",  "genel": False},
    # Genel haberler — yüksek eşik (4)
    {"ad": "Bianet Genel",  "url": "https://bianet.org/biamag/feed/rss",           "etiket": "Haber",    "genel": True},
    {"ad": "Gazete Duvar",  "url": "https://www.gazeteduvar.com.tr/feed",          "etiket": "Haber",    "genel": True},
]

# ─── GITHUB YARDIMCILARI ────────────────────────────────────────────

def get_sha():
    token = os.environ.get("GITHUB_TOKEN")
    url   = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    resp  = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=15)
    return resp.json().get("sha") if resp.status_code == 200 else None

def get_remote_data():
    raw = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/{FILE_PATH}"
    resp = requests.get(raw, timeout=15)
    if resp.status_code == 200:
        try:    return resp.json(), get_sha()
        except: return None, None
    return None, None

def update_remote_data(new_data, sha):
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("❌ GITHUB_TOKEN yok!")
        return
    url     = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    content = base64.b64encode(json.dumps(new_data, ensure_ascii=False, indent=2).encode()).decode()
    payload = {"message": f"otomatik güncelleme {datetime.date.today()}", "content": content}
    if sha:
        payload["sha"] = sha
    resp = requests.put(url, headers={"Authorization": f"Bearer {token}"}, json=payload, timeout=20)
    if resp.status_code in (200, 201):
        print(f"✅ GitHub güncellendi — {len(new_data.get('ihlaller',[]))} ihlal, {len(new_data.get('haberler',[]))} haber.")
    else:
        print(f"❌ Hata: {resp.status_code} — {resp.text[:300]}")

# ─── YARDIMCILAR ────────────────────────────────────────────────────

def html_temizle(text):
    if not text: return ""
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()[:600]

def tarih_normalize(ts):
    if not ts: return datetime.date.today().isoformat()
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z",
                "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ"):
        try: return datetime.datetime.strptime(ts.strip(), fmt).strftime("%Y-%m-%d")
        except: continue
    return ts[:10] if len(ts) >= 10 else datetime.date.today().isoformat()

def sonraki_id(liste):
    return max((x.get("id", 0) for x in liste), default=0) + 1 if liste else 1

# ─── RSS ÇEKİCİ ─────────────────────────────────────────────────────

def rss_cek(kaynak):
    haberler = []
    genel = kaynak.get("genel", True)
    esik  = 4 if genel else 1
    try:
        resp = requests.get(kaynak["url"], timeout=20,
                            headers={"User-Agent": "ekoloji-izleme-bot/2.0"})
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        ns   = {"atom": "http://www.w3.org/2005/Atom"}
        items = root.findall(".//item") or root.findall(".//atom:entry", ns)

        kabul = reddedilen = 0
        for item in items[:30]:
            def txt(tag):
                el = item.find(tag)
                return (el.text or "").strip() if el is not None else ""

            baslik = txt("title")
            ozet   = html_temizle(txt("description") or txt("summary") or txt("content"))
            url    = txt("link") or txt("guid")
            tarih  = tarih_normalize(txt("pubDate") or txt("published") or txt("updated"))

            if not baslik or not url:
                continue

            puan = ekoloji_puani(baslik, ozet, genel)
            if puan < esik:
                reddedilen += 1
                continue

            haberler.append({
                "baslik": baslik,
                "kaynak": kaynak["ad"],
                "tarih":  tarih,
                "etiket": kaynak["etiket"],
                "ozet":   ozet,
                "url":    url,
            })
            kabul += 1

        print(f"  📡 {kaynak['ad']}: {kabul} kabul / {reddedilen} reddedildi (eşik={esik})")
    except Exception as e:
        print(f"  ⚠️  {kaynak['ad']} hatası: {e}")
    return haberler

# ─── ANA ────────────────────────────────────────────────────────────

def main():
    print("📥 data.json çekiliyor…")
    data, sha = get_remote_data()

    if data is None:
        print("⚠️  Uzak veri alınamadı — boş yapıyla başlanıyor.")
        data = {"ihlaller": [], "haberler": [], "raporlar": [], "_meta": {}}
        sha  = None

    mevcut_haberler = data.get("haberler", [])
    mevcut_urls     = {h.get("url", "") for h in mevcut_haberler}
    print(f"  Mevcut: {len(data.get('ihlaller',[]))} ihlal, {len(mevcut_haberler)} haber")

    print("\n🔍 RSS taranıyor…")
    yeni_haberler = []
    id_sayac = sonraki_id(mevcut_haberler)

    for kaynak in KAYNAK_RSS:
        for h in rss_cek(kaynak):
            if h["url"] not in mevcut_urls:
                h["id"] = id_sayac
                id_sayac += 1
                yeni_haberler.append(h)
                mevcut_urls.add(h["url"])

    print(f"\n✅ {len(yeni_haberler)} yeni haber eklendi.")
    data["haberler"] = yeni_haberler + mevcut_haberler
    data["_meta"] = {
        "guncelleme":   datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "kaynak":       "otomatik_tarama_v2",
        "ihlal_sayisi": len(data["ihlaller"]),
        "haber_sayisi": len(data["haberler"]),
    }

    print("\n📤 GitHub'a yazılıyor…")
    update_remote_data(data, sha)

if __name__ == "__main__":
    main()
