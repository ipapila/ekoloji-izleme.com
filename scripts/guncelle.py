#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ekoloji-izleme.com — Otomatik Güncelleme v5
DÜZELTME: get_remote_data() artık GitHub API kullanır (CDN cache sorununu çözer)
DÜZELTME: harita kaynaklı eski ihlalleri temizleme seçeneği
"""

import env_yukle  # .env dosyasını os.environ'a yükler

import json, requests, os, base64, datetime, re
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

REPO_OWNER = os.environ.get("GITHUB_REPO_OWNER", "ipapila")
REPO_NAME  = os.environ.get("GITHUB_REPO_NAME",  "ekoloji-izleme.com")
FILE_PATH  = "data.json"

# Harita kaynaklı ihlalleri temizlemek için kaynak listesi
# Bu kaynaklar eski harita importlarından geldi, guncelle.py artık bunları eklemez.
# HARITA_TEMIZLE = True yapılırsa bir kez çalıştırıp False'a geri çevirin.
HARITA_TEMIZLE = False
HARITA_KAYNAKLARI = {"OGM", "DKMP", "BSGM", "harita_import", "harita_verisi"}


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

def get_remote_data():
    """
    ÖNEMLİ: raw CDN yerine GitHub API kullanıyoruz.
    raw.githubusercontent.com 5-10 dakika cache yapar;
    veriYaz() yeni veri yazdıktan hemen sonra guncelle.py çalışırsa
    CDN eski veriyi döner ve üstüne yazar → rapor/makale/uluslararası kaybolur.
    API her zaman güncel veriyi döner.
    """
    token = os.environ.get("GITHUB_TOKEN")
    url   = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    r = requests.get(url, headers=headers, timeout=20)
    if r.status_code == 200:
        d = r.json()
        try:
            content = base64.b64decode(d["content"].replace("\n","")).decode("utf-8")
            return json.loads(content), d["sha"]
        except Exception as e:
            print(f"❌ data.json parse hatası: {e}")
            return None, None
    print(f"❌ GitHub API: HTTP {r.status_code}")
    return None, None


def update_remote_data(new_data, sha):
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("❌ GITHUB_TOKEN yok!")
        return
    url     = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    content = base64.b64encode(
        json.dumps(new_data, ensure_ascii=False, indent=2).encode("utf-8")
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

    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "ekoloji-izleme-bot/2.0 (+https://ekoloji-izleme.com)",
    ]

    r = None
    for ua in user_agents:
        try:
            r = requests.get(kaynak["url"], timeout=20,
                             headers={"User-Agent": ua,
                                      "Accept": "application/rss+xml,application/xml,text/xml,*/*"})
            if r.status_code == 200:
                break
            r = None
        except Exception:
            continue

    if r is None or r.status_code != 200:
        status = r.status_code if r is not None else "bağlantı hatası"
        print(f"  ⚠️  {kaynak['ad']}: HTTP {status} — atlanıyor")
        return haberler

    try:
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
        print(f"  ⚠️  {kaynak['ad']}: parse hatası — {e}")
    return haberler

# ─── WEB SCRAPING ────────────────────────────────────────────────────

def web_cek(kaynak):
    haberler = []
    genel = kaynak.get("genel", False)
    esik  = 4 if genel else 1
    try:
        r = requests.get(kaynak["url"], timeout=20,
                         headers={
                             "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                             "Accept": "text/html,application/xhtml+xml,*/*",
                             "Accept-Language": "tr-TR,tr;q=0.9",
                         })
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
    print("📥 data.json çekiliyor (GitHub API)…")
    data, sha = get_remote_data()

    if data is None:
        print("⚠️  Uzak veri alınamadı — boş yapıyla başlanıyor.")
        data = {"ihlaller": [], "haberler": [], "raporlar": [],
                "makaleler": [], "uluslararasi": [], "_meta": {}}
        sha  = None

    # Eksik koleksiyon anahtarlarını ekle (eski data.json için)
    for col in ("raporlar", "makaleler", "uluslararasi"):
        if col not in data:
            data[col] = []

    # ── Eski harita kayıtlarını temizle (bir kez çalıştır, sonra False'a çevir) ──
    if HARITA_TEMIZLE:
        onceki = len(data.get("ihlaller", []))
        data["ihlaller"] = [
            i for i in data.get("ihlaller", [])
            if i.get("kaynak", "") not in HARITA_KAYNAKLARI
        ]
        silinen = onceki - len(data["ihlaller"])
        if silinen:
            print(f"🧹 {silinen} harita kaydı temizlendi (kaynak: {HARITA_KAYNAKLARI})")

    mevcut_haberler  = data.get("haberler", [])
    mevcut_urls      = {h.get("url", "") for h in mevcut_haberler}
    mevcut_basliklar = {
        re.sub(r"\s+", " ", h.get("baslik", "")).strip().lower()
        for h in mevcut_haberler if h.get("baslik")
    }

    print(f"  Mevcut: {len(data.get('ihlaller',[]))} ihlal, {len(mevcut_haberler)} haber")

    # ── Haberleri tara ──────────────────────────────────────────
    print(f"\n🔍 RSS taranıyor… ({len(KAYNAK_RSS)} kaynak)")
    yeni_haberler = []
    id_sayac = sonraki_id(mevcut_haberler)
    for kaynak in KAYNAK_RSS:
        for h in rss_cek(kaynak):
            bn = re.sub(r"\s+", " ", h.get("baslik", "")).strip().lower()
            if h["url"] not in mevcut_urls and bn not in mevcut_basliklar:
                h["id"] = id_sayac; id_sayac += 1
                yeni_haberler.append(h)
                mevcut_urls.add(h["url"])
                if bn: mevcut_basliklar.add(bn)

    print(f"\n🌐 Web scraping… ({len(KAYNAK_WEB)} kaynak)")
    for kaynak in KAYNAK_WEB:
        for h in web_cek(kaynak):
            bn = re.sub(r"\s+", " ", h.get("baslik", "")).strip().lower()
            if h["url"] not in mevcut_urls and bn not in mevcut_basliklar:
                h["id"] = id_sayac; id_sayac += 1
                yeni_haberler.append(h)
                mevcut_urls.add(h["url"])
                if bn: mevcut_basliklar.add(bn)

    print(f"\n✅ {len(yeni_haberler)} yeni haber eklendi.")
    data["haberler"] = yeni_haberler + mevcut_haberler
    data["_meta"] = {
        "guncelleme":    datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "kaynak":        "otomatik_tarama_v5",
        "kaynak_sayisi": len(KAYNAK_RSS) + len(KAYNAK_WEB),
        "ihlal_sayisi":  len(data.get("ihlaller",    [])),
        "haber_sayisi":  len(data.get("haberler",    [])),
        "rapor_sayisi":  len(data.get("raporlar",    [])),
        "makale_sayisi": len(data.get("makaleler",   [])),
        "ulus_sayisi":   len(data.get("uluslararasi",[])),
    }

    print("\n📤 GitHub'a yazılıyor (API)…")
    update_remote_data(data, sha)


if __name__ == "__main__":
    main()
