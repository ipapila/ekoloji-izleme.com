#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ekoloji-izleme.com — Otomatik Güncelleme v4
Haberler + Turkiye-katmanlar harita ihlalleri entegrasyonu.
"""

import env_yukle  # .env dosyasını os.environ'a yükler

import json, requests, os, base64, datetime, re
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

REPO_OWNER = os.environ.get("GITHUB_REPO_OWNER", "ipapila")
REPO_NAME  = os.environ.get("GITHUB_REPO_NAME",  "ekoloji-izleme.com")
FILE_PATH  = "data.json"

# Turkiye-katmanlar harita reposu
HARITA_RAW_URL = "https://raw.githubusercontent.com/ipapila/Turkiye-katmanlar/main/data.json"

# ─── KAYNAK LİSTESİ ────────────────────────────────────────────────
KAYNAK_RSS = [
    {
        "ad": "İklim Haber", "etiket": "İklim", "genel": False,
        "url": "https://iklimhaber.org/feed/",
        "web": "https://iklimhaber.org",
    },
    {
        "ad": "Google News", "etiket": "Çevre İhlali", "genel": False,
        "url": "https://news.google.com/rss/search?q=çevre+ihlali+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
        "web": "https://news.google.com",
    },
    {
        "ad": "Google News", "etiket": "Orman / Maden", "genel": False,
        "url": "https://news.google.com/rss/search?q=orman+tahribi+maden+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
        "web": "https://news.google.com",
    },
    {
        "ad": "Google News", "etiket": "HES / RES / Baraj", "genel": False,
        "url": "https://news.google.com/rss/search?q=HES+RES+baraj+çevre+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
        "web": "https://news.google.com",
    },
    {
        "ad": "Google News", "etiket": "Kamulaştırma", "genel": False,
        "url": "https://news.google.com/rss/search?q=acele+kamulaştırma+çevre+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
        "web": "https://news.google.com",
    },
    {
        "ad": "Google News", "etiket": "ÇED Kararları", "genel": False,
        "url": "https://news.google.com/rss/search?q=ÇED+maden+Türkiye+2025&hl=tr&gl=TR&ceid=TR:tr",
        "web": "https://news.google.com",
    },
    {
        "ad": "Google News", "etiket": "Orman / Maden", "genel": False,
        "url": "https://news.google.com/rss/search?q=ağaç+katliamı+orman+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
        "web": "https://news.google.com",
    },
    {
        "ad": "Google News", "etiket": "Çevre İhlali", "genel": False,
        "url": "https://news.google.com/rss/search?q=sulak+alan+milli+park+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
        "web": "https://news.google.com",
    },
    {
        "ad": "Sözcü Çevre", "etiket": "Haber", "genel": True,
        "url": "https://www.sozcu.com.tr/rss/cevre.xml",
        "web": "https://www.sozcu.com.tr/cevre/",
    },
    {
        "ad": "Gazete Duvar", "etiket": "Haber", "genel": True,
        "url": "https://www.gazeteduvar.com.tr/feed",
        "web": "https://www.gazeteduvar.com.tr",
    },
    {
        "ad": "Bianet Genel", "etiket": "Haber", "genel": True,
        "url": "https://bianet.org/biamag/feed/rss",
        "web": "https://bianet.org",
    },
]

KAYNAK_WEB = [
    {
        "ad": "Greenpeace TR", "etiket": "STK", "genel": False,
        "url": "https://www.greenpeace.org/turkey/blog/",
        "web": "https://www.greenpeace.org/turkey/",
        "secici": ".post-title a, h2 a, .article-title a",
        "ozet_secici": ".post-excerpt p, .article-excerpt",
    },
    {
        "ad": "Çevre Bakanlığı", "etiket": "Resmi", "genel": False,
        "url": "https://www.csb.gov.tr/duyurular",
        "web": "https://www.csb.gov.tr",
        "secici": ".duyuru-item a, .news-item a, h3 a",
        "ozet_secici": ".duyuru-ozet, .news-excerpt",
    },
]

# ─── FİLTRE SİSTEMİ ────────────────────────────────────────────────

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
    "orman yangını", "sera gazı emisyon", "iklim krizi",
]

ORTA_SINYAL = [
    "çevre", "ekoloji", "orman", "maden", "baraj", "HES", "RES", "GES",
    "kamulaştırma", "doğa", "habitat", "kirlilik", "atık", "iklim",
    "yangın", "sel", "taşkın", "heyelan", "kıyı", "deniz", "göl", "dere",
    "su hakkı", "tarım arazisi", "bor", "altın maden", "jeotermal",
    "ihlal", "ruhsatsız", "izinsiz", "ağaç", "plastik kirlilik",
    "sondaj", "arama ruhsatı", "TEMA", "WWF", "Greenpeace",
    "yaban hayat", "doğal yaşam", "kuş türü", "balık türü",
]

GUCLU_NEGATIF = [
    "faiz", "borsa", "döviz kuru", "enflasyon rakam", "bütçe açığı",
    "seçim sonuç", "cumhurbaşkanı açıkladı", "milletvekili",
    "futbol", "maç sonucu", "şampiyon", "transfer haberi", "penaltı",
    "dizi oyuncu", "film izle", "magazin", "ünlü çift", "nişanlandı",
    "moda koleksiyon", "kripto", "bitcoin fiyat",
    "kalaşnikof", "silah eğitim", "muharebe", "hava saldırı",
    "iran devrim", "soru kabul", "bakanlara erdoğan",
    "liseli kız", "öğrenci kavga",
]

GENEL_NEGATIF = [
    "ekonomi büyüme", "piyasa rallisi", "hisse senedi",
    "ihracat rekoru", "savunma sanayii", "operasyon düzenlendi",
    "turizm rekoru", "otel doluluk", "tatil fırsatı",
    "hastane ameliyat", "üniversite sınav", "okul kayıt",
]


def ekoloji_puani(baslik, ozet="", genel=True):
    metin = (baslik + " " + ozet).lower()
    if any(k.lower() in metin for k in GUCLU_NEGATIF):
        return 0
    if genel and any(k.lower() in metin for k in GENEL_NEGATIF):
        return 0
    puan = 0
    bl = baslik.lower()
    for k in YUKSEK_SINYAL:
        kl = k.lower()
        if kl in metin: puan += 3
        if kl in bl:    puan += 2
    for k in ORTA_SINYAL:
        if k.lower() in metin: puan += 1
    return puan


def ekoloji_mi(baslik, ozet="", genel=True):
    return ekoloji_puani(baslik, ozet, genel) >= (4 if genel else 1)


# ─── GITHUB YARDIMCILARI ────────────────────────────────────────────

def get_sha():
    token = os.environ.get("GITHUB_TOKEN")
    url   = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=15)
    return r.json().get("sha") if r.status_code == 200 else None

def get_remote_data():
    raw = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/{FILE_PATH}"
    r = requests.get(raw, timeout=15)
    if r.status_code == 200:
        try:    return r.json(), get_sha()
        except: return None, None
    return None, None

def update_remote_data(new_data, sha):
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("❌ GITHUB_TOKEN yok!")
        return
    url     = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    content = base64.b64encode(
        json.dumps(new_data, ensure_ascii=False, indent=2).encode()
    ).decode()
    payload = {
        "message": f"otomatik güncelleme {datetime.date.today()}",
        "content": content,
    }
    if sha:
        payload["sha"] = sha
    r = requests.put(url, headers={"Authorization": f"Bearer {token}"},
                     json=payload, timeout=20)
    if r.status_code in (200, 201):
        print(f"✅ GitHub güncellendi — "
              f"{len(new_data.get('ihlaller',[]))} ihlal, "
              f"{len(new_data.get('haberler',[]))} haber.")
    else:
        print(f"❌ Hata {r.status_code}: {r.text[:300]}")


# ─── HARİTA REPO İHLAL AKTARIMI ─────────────────────────────────────

def harita_ihlalleri_cek(mevcut_idler):
    """
    ipapila/Turkiye-katmanlar data.json'dan ihlalleri çeker.
    Harita modeli → ihlaller.html uyumlu modele dönüştürür.
    Zaten mevcut olanları (mevcut_idler) atlar.
    """
    print(f"\n🗺  Harita reposundan ihlaller çekiliyor…")
    try:
        r = requests.get(HARITA_RAW_URL, timeout=20,
                         headers={"User-Agent": "ekoloji-izleme-bot/3.0"})
        r.raise_for_status()
        harita_data = r.json()
    except Exception as e:
        print(f"  ⚠️  Harita verisi alınamadı: {e}")
        return []

    # data.json doğrudan liste olabilir veya dict içinde olabilir
    if isinstance(harita_data, list):
        kayitlar = harita_data
    elif isinstance(harita_data, dict):
        # Tüm olası anahtarları dene
        kayitlar = (harita_data.get("features") or
                    harita_data.get("ihlaller") or
                    harita_data.get("data") or [])
        # GeoJSON FeatureCollection ise özellikleri çıkar
        if kayitlar and isinstance(kayitlar[0], dict) and "properties" in kayitlar[0]:
            kayitlar = [f["properties"] for f in kayitlar if "properties" in f]
    else:
        kayitlar = []

    yeni = []
    atlan = 0
    for k in kayitlar:
        kid = str(k.get("id", ""))
        if kid in mevcut_idler:
            atlan += 1
            continue

        # Alan adı
        ad = k.get("ad") or k.get("name") or k.get("baslik") or ""
        if not ad:
            continue

        il    = k.get("il") or k.get("province") or ""
        ilce  = k.get("ilce") or k.get("district") or ""
        koord = k.get("koordinatlar") or {}
        lat   = koord.get("lat") if isinstance(koord, dict) else None
        lng   = koord.get("lng") if isinstance(koord, dict) else None

        # Kategori → siddet eşlemesi
        tip = k.get("tip") or k.get("kategori") or "Ekolojik İhlal"
        siddet_map = {
            "Ekolojik İhlal": "kritik",
            "Acele Kamulaştırma": "kritik",
            "Maden Ocağı": "kritik",
            "Termik Reaktör": "kritik",
            "Nükleer Enerji": "kritik",
            "HES": "orta",
            "RES": "orta",
            "GES": "orta",
            "Jeotermal": "orta",
            "Taş-Mermer Ocağı": "orta",
            "Kıyı İhlalleri": "orta",
            "İklim Olayları": "orta",
            "Orman Alanı": "takipte",
            "Sulak Alan": "takipte",
            "Milli Park": "takipte",
            "Özel Çevre Koruma Alanı": "takipte",
            "Kültür Varlığı": "takipte",
        }
        siddet = siddet_map.get(tip, "takipte")

        ihlal = {
            "id":        kid or f"h_{len(yeni)}_{datetime.date.today().strftime('%Y%m%d')}",
            "baslik":    ad,
            "ad":        ad,
            "konum":     f"{il}{', ' + ilce if ilce else ''}".strip(", "),
            "il":        il,
            "ilce":      ilce,
            "kategori":  tip,
            "tip":       tip,
            "siddet":    siddet,
            "tarih":     k.get("eklenme") or datetime.date.today().isoformat(),
            "lat":       lat,
            "lng":       lng,
            "koordinatlar": koord,
            "alan_ha":   k.get("alan_ha") or 0,
            "durum":     k.get("durum") or "Aktif",
            "belge_no":  k.get("belge_no") or "",
            "kaynak":    k.get("kaynak") or "Turkiye-katmanlar",
            "kaynak_url": k.get("kaynak_link") or "",
            "aciklama":  k.get("aciklama") or "",
            "alt_kategori": k.get("alt_kategori") or "",
            "kaynak_turu":  k.get("kaynak_turu") or "resmi",
            "foto_url":  "",
        }
        yeni.append(ihlal)

    print(f"  ✅ {len(yeni)} yeni ihlal aktarıldı, {atlan} zaten mevcut.")
    return yeni


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
        r = requests.get(kaynak["url"], timeout=20,
                         headers={"User-Agent": "ekoloji-izleme-bot/2.0"})
        r.raise_for_status()
        root  = ET.fromstring(r.content)
        ns    = {"atom": "http://www.w3.org/2005/Atom"}
        items = root.findall(".//item") or root.findall(".//atom:entry", ns)

        kabul = red = 0
        for item in items[:30]:
            def txt(tag):
                el = item.find(tag)
                return (el.text or "").strip() if el is not None else ""

            baslik = txt("title")
            ozet   = html_temizle(
                txt("description") or txt("summary") or txt("content")
            )
            url    = txt("link") or txt("guid")
            tarih  = tarih_normalize(
                txt("pubDate") or txt("published") or txt("updated")
            )

            if not baslik or not url:
                continue
            if ekoloji_puani(baslik, ozet, genel) < esik:
                red += 1
                continue

            haberler.append({
                "baslik":    baslik,
                "kaynak":    kaynak["ad"],
                "kaynak_web": kaynak["web"],
                "tarih":     tarih,
                "etiket":    kaynak["etiket"],
                "ozet":      ozet,
                "url":       url,
            })
            kabul += 1

        print(f"  📡 {kaynak['ad']}: {kabul} kabul / {red} red (eşik={esik})")
    except Exception as e:
        print(f"  ⚠️  {kaynak['ad']}: {e}")
    return haberler

# ─── WEB SCRAPING ────────────────────────────────────────────────────

def web_cek(kaynak):
    haberler = []
    genel = kaynak.get("genel", False)
    esik  = 4 if genel else 1
    try:
        r = requests.get(kaynak["url"], timeout=20,
                         headers={"User-Agent": "ekoloji-izleme-bot/2.0"})
        r.raise_for_status()
        soup  = BeautifulSoup(r.text, "html.parser")
        kabul = red = 0

        for a in soup.select(kaynak["secici"])[:20]:
            baslik = a.get_text(" ", strip=True)
            if not baslik or len(baslik) < 10:
                continue
            href = a.get("href", "")
            if not href:
                continue
            link = href if href.startswith("http") else kaynak["url"].rstrip("/") + "/" + href.lstrip("/")

            ozet = ""
            if kaynak.get("ozet_secici"):
                parent = a.find_parent(["article", "div", "li"])
                if parent:
                    el = parent.select_one(kaynak["ozet_secici"])
                    if el:
                        ozet = el.get_text(" ", strip=True)[:300]

            if ekoloji_puani(baslik, ozet, genel) < esik:
                red += 1
                continue

            haberler.append({
                "baslik":     baslik,
                "kaynak":     kaynak["ad"],
                "kaynak_web": kaynak["web"],
                "tarih":      datetime.date.today().isoformat(),
                "etiket":     kaynak["etiket"],
                "ozet":       ozet,
                "url":        link,
            })
            kabul += 1

        print(f"  🌐 {kaynak['ad']}: {kabul} kabul / {red} red (eşik={esik})")
    except Exception as e:
        print(f"  ⚠️  {kaynak['ad']}: {e}")
    return haberler

# ─── ANA FONKSİYON ─────────────────────────────────────────────────

def main():
    print("📥 data.json çekiliyor…")
    data, sha = get_remote_data()

    if data is None:
        print("⚠️  Uzak veri alınamadı — boş yapıyla başlanıyor.")
        data = {"ihlaller": [], "haberler": [], "raporlar": [], "_meta": {}}
        sha  = None

    mevcut_ihlaller = data.get("ihlaller", [])
    mevcut_haberler = data.get("haberler", [])
    mevcut_urls     = {h.get("url", "") for h in mevcut_haberler}
    mevcut_idler    = {str(i.get("id", "")) for i in mevcut_ihlaller}

    print(f"  Mevcut: {len(mevcut_ihlaller)} ihlal, {len(mevcut_haberler)} haber")

    # ── 1. Harita reposundan ihlalleri aktar ──────────────────────
    yeni_ihlaller = harita_ihlalleri_cek(mevcut_idler)
    data["ihlaller"] = yeni_ihlaller + mevcut_ihlaller

    # ── 2. Haberleri tara ────────────────────────────────────────
    print(f"\n🔍 RSS taranıyor… ({len(KAYNAK_RSS)} kaynak)")
    yeni_haberler = []
    id_sayac = sonraki_id(mevcut_haberler)
    for kaynak in KAYNAK_RSS:
        for h in rss_cek(kaynak):
            if h["url"] not in mevcut_urls:
                h["id"] = id_sayac
                id_sayac += 1
                yeni_haberler.append(h)
                mevcut_urls.add(h["url"])

    print(f"\n🌐 Web scraping… ({len(KAYNAK_WEB)} kaynak)")
    for kaynak in KAYNAK_WEB:
        for h in web_cek(kaynak):
            if h["url"] not in mevcut_urls:
                h["id"] = id_sayac
                id_sayac += 1
                yeni_haberler.append(h)
                mevcut_urls.add(h["url"])

    print(f"\n✅ {len(yeni_haberler)} yeni haber eklendi.")
    data["haberler"] = yeni_haberler + mevcut_haberler
    data["_meta"] = {
        "guncelleme":    datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "kaynak":        "otomatik_tarama_v4",
        "kaynak_sayisi": len(KAYNAK_RSS) + len(KAYNAK_WEB),
        "ihlal_sayisi":  len(data["ihlaller"]),
        "haber_sayisi":  len(data["haberler"]),
    }

    print("\n📤 GitHub'a yazılıyor…")
    update_remote_data(data, sha)


if __name__ == "__main__":
    main()
