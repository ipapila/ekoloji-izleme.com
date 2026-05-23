#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ekoloji-izleme.com — Otomatik Güncelleme v6
v6 YENİLİKLERİ:
  - 4 koleksiyon desteği: haberler | raporlar | makaleler | uluslararasi
  - RAPOR_RSS, MAKALE_RSS, ULUSLARARASI_RSS kaynak listeleri eklendi
  - SSL bypass (verify=False), fallback selector, timeout=12
  - icerik_tipi ve dil alanları
"""

import env_yukle

import json, requests, os, base64, datetime, re
import urllib3
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

REPO_OWNER = os.environ.get("GITHUB_REPO_OWNER", "ipapila")
REPO_NAME  = os.environ.get("GITHUB_REPO_NAME",  "ekoloji-izleme.com")
FILE_PATH  = "data.json"

HARITA_KAYNAKLARI = {"harita","OGM","DKMP","BSGM","harita_import","harita_verisi"}
SSL_NO_VERIFY_HOSTS = {"mapeg.gov.tr", "ilan.gov.tr"}
FALLBACK_SELECTOR = "article h2 a, article h3 a, .post-title a, .entry-title a, h2.title a, h3.title a, [class*='title'] a"

# ── Rapor/analiz sinyalleri ─────────────────────────────────────
RAPOR_SINYAL = ["rapor","araştırma","analiz","inceleme","değerlendirme","politika","strateji",
                "report","analysis","research","assessment","policy","findings"]
KOSE_SINYAL  = ["köşe","görüş","yorum","perspektif","opinion","commentary","column"]

# ══════════════════════════════════════════════════════════════════
#  KAYNAK LİSTELERİ
# ══════════════════════════════════════════════════════════════════

KAYNAK_RSS = [
    {"ad": "İklim Haber",    "etiket": "İklim",         "genel": False, "hedef": "haberler", "dil": "tr",
     "url": "https://iklimhaber.org/feed/",              "web": "https://iklimhaber.org"},
    {"ad": "Google News",    "etiket": "Çevre İhlali",  "genel": False, "hedef": "haberler", "dil": "tr",
     "url": "https://news.google.com/rss/search?q=çevre+ihlali+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "web": "https://news.google.com"},
    {"ad": "Google News",    "etiket": "Orman / Maden", "genel": False, "hedef": "haberler", "dil": "tr",
     "url": "https://news.google.com/rss/search?q=orman+tahribi+maden+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "web": "https://news.google.com"},
    {"ad": "Google News",    "etiket": "HES / RES",     "genel": False, "hedef": "haberler", "dil": "tr",
     "url": "https://news.google.com/rss/search?q=HES+RES+baraj+çevre+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "web": "https://news.google.com"},
    {"ad": "Google News",    "etiket": "Kamulaştırma",  "genel": False, "hedef": "haberler", "dil": "tr",
     "url": "https://news.google.com/rss/search?q=acele+kamulaştırma+çevre+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "web": "https://news.google.com"},
    {"ad": "Google News",    "etiket": "ÇED",           "genel": False, "hedef": "haberler", "dil": "tr",
     "url": "https://news.google.com/rss/search?q=ÇED+maden+Türkiye+2025&hl=tr&gl=TR&ceid=TR:tr", "web": "https://news.google.com"},
    {"ad": "Google News",    "etiket": "Orman / Maden", "genel": False, "hedef": "haberler", "dil": "tr",
     "url": "https://news.google.com/rss/search?q=ağaç+katliamı+orman+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "web": "https://news.google.com"},
    {"ad": "Google News",    "etiket": "Çevre İhlali",  "genel": False, "hedef": "haberler", "dil": "tr",
     "url": "https://news.google.com/rss/search?q=sulak+alan+milli+park+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "web": "https://news.google.com"},
    {"ad": "Sözcü Çevre",    "etiket": "Haber",         "genel": True,  "hedef": "haberler", "dil": "tr",
     "url": "https://www.sozcu.com.tr/rss/cevre.xml",    "web": "https://www.sozcu.com.tr/cevre/"},
    {"ad": "Gazete Duvar",   "etiket": "Haber",         "genel": True,  "hedef": "haberler", "dil": "tr",
     "url": "https://www.gazeteduvar.com.tr/feed",       "web": "https://www.gazeteduvar.com.tr"},
    {"ad": "Bianet Genel",   "etiket": "Haber",         "genel": True,  "hedef": "haberler", "dil": "tr",
     "url": "https://bianet.org/biamag/feed/rss",        "web": "https://bianet.org"},
]

RAPOR_RSS = [
    {"ad": "WWF Türkiye",    "etiket": "STK Raporu",    "genel": False, "hedef": "raporlar", "dil": "tr",
     "url": "https://news.google.com/rss/search?q=site:wwf.org.tr+rapor+OR+arastirma&hl=tr&gl=TR&ceid=TR:tr", "web": "https://wwf.org.tr"},
    {"ad": "TEMA",           "etiket": "STK Raporu",    "genel": False, "hedef": "raporlar", "dil": "tr",
     "url": "https://news.google.com/rss/search?q=site:tema.org.tr+rapor&hl=tr&gl=TR&ceid=TR:tr", "web": "https://tema.org.tr"},
    {"ad": "Google News",    "etiket": "İklim Raporu",  "genel": False, "hedef": "raporlar", "dil": "tr",
     "url": "https://news.google.com/rss/search?q=iklim+raporu+Türkiye+2025&hl=tr&gl=TR&ceid=TR:tr", "web": "https://news.google.com"},
    {"ad": "Google News",    "etiket": "Politika Analizi","genel": False,"hedef": "raporlar","dil": "tr",
     "url": "https://news.google.com/rss/search?q=ekoloji+politika+değerlendirme+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "web": "https://news.google.com"},
    {"ad": "SHURA Enerji",   "etiket": "Enerji Politikası","genel": False,"hedef": "raporlar","dil": "tr",
     "url": "https://news.google.com/rss/search?q=site:shura-enerji.com&hl=tr&gl=TR&ceid=TR:tr", "web": "https://shura-enerji.com"},
]

MAKALE_RSS = [
    {"ad": "Bianet",         "etiket": "Köşe / Yorum",  "genel": False, "hedef": "makaleler", "dil": "tr",
     "url": "https://bianet.org/bianet/feed/rss",        "web": "https://bianet.org"},
    {"ad": "Google News",    "etiket": "Köşe / Görüş",  "genel": False, "hedef": "makaleler", "dil": "tr",
     "url": "https://news.google.com/rss/search?q=çevre+ekoloji+köşe+yorum+görüş+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "web": "https://news.google.com"},
    {"ad": "Google News",    "etiket": "Yorum",          "genel": False, "hedef": "makaleler", "dil": "tr",
     "url": "https://news.google.com/rss/search?q=iklim+krizi+yorum+değerlendirme+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "web": "https://news.google.com"},
]

ULUSLARARASI_RSS = [
    {"ad": "Carbon Brief",   "etiket": "Uluslararası Analiz", "genel": False, "hedef": "uluslararasi", "dil": "en",
     "url": "https://www.carbonbrief.org/feed",           "web": "https://carbonbrief.org"},
    {"ad": "Climate Home",   "etiket": "Uluslararası Haber",  "genel": False, "hedef": "uluslararasi", "dil": "en",
     "url": "https://www.climatechangenews.com/feed/",    "web": "https://climatechangenews.com"},
    {"ad": "Mongabay",       "etiket": "Uluslararası Haber",  "genel": False, "hedef": "uluslararasi", "dil": "en",
     "url": "https://news.mongabay.com/feed/",            "web": "https://mongabay.com"},
    {"ad": "The Guardian",   "etiket": "Uluslararası Haber",  "genel": True,  "hedef": "uluslararasi", "dil": "en",
     "url": "https://www.theguardian.com/environment/rss","web": "https://theguardian.com"},
    {"ad": "350.org",        "etiket": "İklim Hareketi",      "genel": False, "hedef": "uluslararasi", "dil": "en",
     "url": "https://350.org/feed/",                      "web": "https://350.org"},
    {"ad": "Google News EN", "etiket": "Türkiye / Uluslararası","genel": False,"hedef": "uluslararasi","dil": "en",
     "url": "https://news.google.com/rss/search?q=Turkey+environment+mining+ecology&hl=en&gl=US&ceid=US:en", "web": "https://news.google.com"},
    {"ad": "Google News EN", "etiket": "Türkiye / İklim",     "genel": False, "hedef": "uluslararasi", "dil": "en",
     "url": "https://news.google.com/rss/search?q=Turkey+climate+deforestation+coal&hl=en&gl=US&ceid=US:en", "web": "https://news.google.com"},
]

EKOSISTEM_RSS = [
    # turler
    {"ad": "Google News",  "etiket": "Nesli Tehlike Türler",   "genel": False, "hedef": "ekosistem", "bolum": "turler",         "dil": "tr",
     "url": "https://news.google.com/rss/search?q=nesli+tehlike+tür+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "web": "https://news.google.com"},
    # yaban
    {"ad": "Google News",  "etiket": "Yaban Hayatı",           "genel": False, "hedef": "ekosistem", "bolum": "yaban",          "dil": "tr",
     "url": "https://news.google.com/rss/search?q=yaban+hayatı+izleme+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "web": "https://news.google.com"},
    {"ad": "Doğa Derneği", "etiket": "Yaban Hayatı",           "genel": False, "hedef": "ekosistem", "bolum": "yaban",          "dil": "tr",
     "url": "https://news.google.com/rss/search?q=site:dogadernegi.org&hl=tr&gl=TR&ceid=TR:tr", "web": "https://dogadernegi.org"},
    # su-canlilari
    {"ad": "Google News",  "etiket": "Su Canlıları",            "genel": False, "hedef": "ekosistem", "bolum": "su-canlilari",   "dil": "tr",
     "url": "https://news.google.com/rss/search?q=balık+ölümü+su+kirliliği+deniz+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "web": "https://news.google.com"},
    # hayvan-haklari
    {"ad": "Google News",  "etiket": "Hayvan Hakları",          "genel": False, "hedef": "ekosistem", "bolum": "hayvan-haklari", "dil": "tr",
     "url": "https://news.google.com/rss/search?q=hayvan+hakları+istismar+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "web": "https://news.google.com"},
    # ciftci
    {"ad": "Google News",  "etiket": "Çiftçi & Köylü",         "genel": False, "hedef": "ekosistem", "bolum": "ciftci",         "dil": "tr",
     "url": "https://news.google.com/rss/search?q=çiftçi+köylü+tarım+maden+kamulaştırma+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "web": "https://news.google.com"},
    # balikci
    {"ad": "Google News",  "etiket": "Balıkçı Toplulukları",   "genel": False, "hedef": "ekosistem", "bolum": "balikci",        "dil": "tr",
     "url": "https://news.google.com/rss/search?q=balıkçı+deniz+kirliliği+av+yasağı+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "web": "https://news.google.com"},
    # yerli
    {"ad": "Google News",  "etiket": "Yerli & Yerel Haklar",   "genel": False, "hedef": "ekosistem", "bolum": "yerli",          "dil": "tr",
     "url": "https://news.google.com/rss/search?q=yerel+halk+maden+HES+RES+direniş+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "web": "https://news.google.com"},
    # kadinlar
    {"ad": "Google News",  "etiket": "Kadınlar & Ekoloji",     "genel": False, "hedef": "ekosistem", "bolum": "kadinlar",       "dil": "tr",
     "url": "https://news.google.com/rss/search?q=kadın+çevre+ekoloji+maden+HES+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "web": "https://news.google.com"},
    # genclik
    {"ad": "Google News",  "etiket": "Gençlik & Ekoloji",      "genel": False, "hedef": "ekosistem", "bolum": "genclik",        "dil": "tr",
     "url": "https://news.google.com/rss/search?q=iklim+gençlik+Türkiye+genç+aktivist&hl=tr&gl=TR&ceid=TR:tr", "web": "https://news.google.com"},
    # kentsel
    {"ad": "Google News",  "etiket": "Kentsel Çevre",          "genel": False, "hedef": "ekosistem", "bolum": "kentsel",        "dil": "tr",
     "url": "https://news.google.com/rss/search?q=yeşil+alan+kentsel+dönüşüm+hava+kirliliği+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "web": "https://news.google.com"},
    # esitsizlik
    {"ad": "Google News",  "etiket": "Ekolojik Eşitsizlik",    "genel": False, "hedef": "ekosistem", "bolum": "esitsizlik",     "dil": "tr",
     "url": "https://news.google.com/rss/search?q=çevre+adaleti+ekolojik+eşitsizlik+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "web": "https://news.google.com"},
    # goc
    {"ad": "Google News",  "etiket": "İklim Göçü",             "genel": False, "hedef": "ekosistem", "bolum": "goc",            "dil": "tr",
     "url": "https://news.google.com/rss/search?q=iklim+göçü+yerinden+edilme+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "web": "https://news.google.com"},
    # savas
    {"ad": "Google News",  "etiket": "Savaş & Ekoloji",        "genel": False, "hedef": "ekosistem", "bolum": "savas",          "dil": "tr",
     "url": "https://news.google.com/rss/search?q=savaş+çevre+ekoloji+kirlilik&hl=tr&gl=TR&ceid=TR:tr", "web": "https://news.google.com"},
]

KAYNAK_WEB = [
    {"ad": "Greenpeace TR",   "etiket": "STK", "genel": False, "hedef": "haberler",
     "url": "https://www.greenpeace.org/turkey/blog/", "web": "https://www.greenpeace.org/turkey/",
     "secici": ".post-title a, h2 a, h3 a, [class*='title'] a",
     "ozet_secici": ".post-excerpt p, [class*='excerpt'], p"},
    {"ad": "Çevre Bakanlığı", "etiket": "Resmi", "genel": False, "hedef": "haberler",
     "url": "https://www.csb.gov.tr/duyurular",         "web": "https://www.csb.gov.tr",
     "secici": ".duyuru-item a, .news-item a, h3 a, h4 a, li a",
     "ozet_secici": ".duyuru-ozet, .news-excerpt, p"},
]

# ══════════════════════════════════════════════════════════════════
#  FİLTRE SİSTEMİ
# ══════════════════════════════════════════════════════════════════

YUKSEK_SINYAL = [
    "çevre ihlali","çevre katliamı","ÇED","acele kamulaştırma","taş ocağı","maden ocağı",
    "HES projesi","RES projesi","GES projesi","termik santral","nükleer santral",
    "ağaç katliamı","ormansızlaşma","orman tahribi","sulak alan","milli park","doğal sit",
    "nesli tükenmekte","biyoçeşitlilik","su kirliliği","deniz kirliliği","hava kirliliği",
    "atık depolama","kaçak maden","MAPEG","EPDK kararı","dere yatağı","kıyı tahribatı",
    "orman yangını","iklim krizi","rapor","araştırma","analiz",
    "mining","deforestation","climate","biodiversity","pollution","carbon","emissions",
]
ORTA_SINYAL = [
    "çevre","ekoloji","orman","maden","baraj","HES","RES","GES","kamulaştırma",
    "doğa","habitat","kirlilik","atık","iklim","yangın","sel","kıyı","deniz","göl","dere",
    "TEMA","WWF","Greenpeace","yaban hayat","değerlendirme","yorum","görüş",
    "environment","ecology","forest","energy","renewable","Turkey","Akkuyu",
]
GUCLU_NEGATIF = [
    "faiz","borsa","döviz","kur","enflasyon","futbol","maç sonucu","şampiyon","transfer",
    "dizi","film","oyuncu","magazin","nişan","düğün","moda","kripto","bitcoin",
]
GENEL_NEGATIF = [
    "ekonomi büyüme","piyasa rallisi","hisse senedi","ihracat rekoru",
    "savunma sanayii","operasyon düzenlendi","turizm rekoru","otel doluluk",
    "hastane ameliyat","üniversite sınav","okul kayıt",
]

def ekoloji_puani(baslik, ozet="", genel=True, hedef="haberler"):
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
    if hedef in ("raporlar","makaleler","uluslararasi") and puan == 0:
        if any(k.lower() in metin for k in RAPOR_SINYAL + KOSE_SINYAL):
            puan = 2
    return puan

def icerik_tipi_tespit(baslik, ozet, hedef):
    if hedef == "uluslararasi": return "uluslararasi"
    metin = (baslik + " " + ozet).lower()
    if hedef == "raporlar" or any(k in metin for k in RAPOR_SINYAL): return "rapor"
    if hedef == "makaleler" or any(k in metin for k in KOSE_SINYAL):  return "kose"
    return "haber"

# ══════════════════════════════════════════════════════════════════
#  GITHUB YARDIMCILARI
# ══════════════════════════════════════════════════════════════════

def get_remote_data():
    token = os.environ.get("GITHUB_TOKEN")
    url   = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    r = requests.get(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }, timeout=20)
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
    json_str = json.dumps(new_data, ensure_ascii=False, indent=2)
    try:
        json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"❌ JSON geçersiz — yazma iptal: {e}")
        return
    content = base64.b64encode(json_str.encode("utf-8")).decode()
    payload = {"message": f"otomatik güncelleme {datetime.date.today()}", "content": content}
    if sha: payload["sha"] = sha
    r = requests.put(url, headers={"Authorization": f"Bearer {token}"},
                     json=payload, timeout=20)
    if r.status_code in (200, 201):
        print(f"✅ GitHub güncellendi — "
              f"{len(new_data.get('ihlaller',[]))} ihlal | "
              f"{len(new_data.get('haberler',[]))} haber | "
              f"{len(new_data.get('raporlar',[]))} rapor | "
              f"{len(new_data.get('makaleler',[]))} makale | "
              f"{len(new_data.get('uluslararasi',[]))} uluslararası")
    else:
        print(f"❌ Hata {r.status_code}: {r.text[:300]}")

# ══════════════════════════════════════════════════════════════════
#  YARDIMCILAR
# ══════════════════════════════════════════════════════════════════

def html_temizle(text):
    if not text: return ""
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()[:600]

def tarih_normalize(ts):
    if not ts: return datetime.date.today().isoformat()
    for fmt in ("%a, %d %b %Y %H:%M:%S %z","%a, %d %b %Y %H:%M:%S %Z",
                "%Y-%m-%dT%H:%M:%S%z","%Y-%m-%dT%H:%M:%SZ"):
        try: return datetime.datetime.strptime(ts.strip(), fmt).strftime("%Y-%m-%d")
        except: continue
    return ts[:10] if len(ts) >= 10 else datetime.date.today().isoformat()

def sonraki_id(liste):
  return max((x.get("id") or 0 for x in liste), default=0) + 1 if liste else 1

# ══════════════════════════════════════════════════════════════════
#  RSS ÇEKİCİ (tüm koleksiyonlar)
# ══════════════════════════════════════════════════════════════════

def rss_cek(kaynak):
    haberler = []
    genel  = kaynak.get("genel", True)
    hedef  = kaynak.get("hedef", "haberler")
    dil    = kaynak.get("dil", "tr")
    esik   = 4 if genel else 1
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/17.0 Safari/605.1.15",
        "ekoloji-izleme-bot/2.0 (+https://ekoloji-izleme.com)",
    ]
    r = None
    for ua in user_agents:
        try:
            r = requests.get(kaynak["url"], timeout=12, headers={
                "User-Agent": ua, "Accept": "application/rss+xml,application/xml,*/*",
                "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
            })
            if r.status_code == 200: break
            r = None
        except Exception: continue
    if r is None or r.status_code != 200:
        status = r.status_code if r is not None else "bağlantı hatası"
        print(f"  ⚠️  {kaynak['ad']} [{hedef}]: HTTP {status} — atlanıyor")
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
            ozet   = html_temizle(txt("description") or txt("summary") or txt("content"))
            url    = txt("link") or txt("guid")
            tarih  = tarih_normalize(txt("pubDate") or txt("published") or txt("updated"))
            if not baslik or not url: continue
            if ekoloji_puani(baslik, ozet, genel, hedef) < esik:
                red += 1; continue
            haberler.append({
                "baslik": baslik, "kaynak": kaynak["ad"], "kaynak_web": kaynak["web"],
                "tarih": tarih, "etiket": kaynak["etiket"], "ozet": ozet, "url": url,
                "icerik_tipi": icerik_tipi_tespit(baslik, ozet, hedef),
                "dil": dil, "_hedef": hedef,
            })
            # ekosistem kaynakları bolum alanı taşır
            if "bolum" in kaynak:
                haberler[-1]["bolum"] = kaynak["bolum"]
            kabul += 1
        print(f"  📡 {kaynak['ad']} [{hedef}]: {kabul} kabul / {red} red (eşik={esik})")
    except Exception as e:
        print(f"  ⚠️  {kaynak['ad']}: parse hatası — {e}")
    return haberler

# ══════════════════════════════════════════════════════════════════
#  WEB SCRAPING
# ══════════════════════════════════════════════════════════════════

def web_cek(kaynak):
    haberler = []
    genel = kaynak.get("genel", False)
    hedef = kaynak.get("hedef", "haberler")
    esik  = 4 if genel else 1
    url_str = kaynak["url"]
    verify  = not any(h in url_str for h in SSL_NO_VERIFY_HOSTS)
    if not verify:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    try:
        r = requests.get(url_str, timeout=15, verify=verify, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,*/*", "Accept-Language": "tr-TR,tr;q=0.9",
            "Accept-Encoding": "gzip, deflate, br", "DNT": "1",
        })
        r.raise_for_status()
        soup  = BeautifulSoup(r.text, "html.parser")
        kabul = red = 0
        linkler = soup.select(kaynak["secici"])[:20]
        if not linkler:
            linkler = soup.select(FALLBACK_SELECTOR)[:20]
        for a in linkler:
            baslik = a.get_text(" ", strip=True)
            if not baslik or len(baslik) < 10: continue
            href = a.get("href","")
            if not href: continue
            link = href if href.startswith("http") else kaynak["url"].rstrip("/") + "/" + href.lstrip("/")
            ozet = ""
            if kaynak.get("ozet_secici"):
                parent = a.find_parent(["article","div","li"])
                if parent:
                    el = parent.select_one(kaynak["ozet_secici"])
                    if el: ozet = el.get_text(" ", strip=True)[:300]
            if ekoloji_puani(baslik, ozet, genel, hedef) < esik:
                red += 1; continue
            haberler.append({
                "baslik": baslik, "kaynak": kaynak["ad"], "kaynak_web": kaynak["web"],
                "tarih": datetime.date.today().isoformat(), "etiket": kaynak["etiket"],
                "ozet": ozet, "url": link,
                "icerik_tipi": icerik_tipi_tespit(baslik, ozet, hedef),
                "dil": "tr", "_hedef": hedef,
            })
            kabul += 1
        print(f"  🌐 {kaynak['ad']} [{hedef}]: {kabul} kabul / {red} red (eşik={esik})")
    except requests.exceptions.SSLError:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        try:
            r = requests.get(url_str, timeout=15, verify=False,
                             headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            linkler = soup.select(kaynak["secici"])[:20] or soup.select(FALLBACK_SELECTOR)[:20]
            kabul = red = 0
            for a in linkler:
                baslik = a.get_text(" ", strip=True)
                if not baslik or len(baslik) < 10: continue
                href = a.get("href","")
                if not href: continue
                link = href if href.startswith("http") else url_str.rstrip("/") + "/" + href.lstrip("/")
                if ekoloji_puani(baslik, "", genel, hedef) < esik: red += 1; continue
                haberler.append({
                    "baslik": baslik, "kaynak": kaynak["ad"], "kaynak_web": kaynak["web"],
                    "tarih": datetime.date.today().isoformat(), "etiket": kaynak["etiket"],
                    "ozet": "", "url": link,
                    "icerik_tipi": icerik_tipi_tespit(baslik, "", hedef),
                    "dil": "tr", "_hedef": hedef,
                })
                kabul += 1
            print(f"  🌐 {kaynak['ad']} [{hedef}]: {kabul} kabul / {red} red (SSL atlandı)")
        except Exception as e2:
            print(f"  ⚠️  {kaynak['ad']}: {e2}")
    except Exception as e:
        print(f"  ⚠️  {kaynak['ad']}: {e}")
    return haberler

# ══════════════════════════════════════════════════════════════════
#  ANA FONKSİYON
# ══════════════════════════════════════════════════════════════════

def main():
    print("📥 data.json çekiliyor (GitHub API)…")
    data, sha = get_remote_data()
    if data is None:
        print("⚠️  Uzak veri alınamadı — boş yapıyla başlanıyor.")
        data = {"ihlaller":[],"haberler":[],"raporlar":[],"makaleler":[],
                "uluslararasi":[],"ekosistem":[],"_meta":{}}
        sha = None

    for col in ("raporlar","makaleler","uluslararasi","ekosistem","direnis"):
        if col not in data: data[col] = []

    # Harita kayıtlarını temizle
    onceki = len(data.get("ihlaller",[]))
    data["ihlaller"] = [i for i in data.get("ihlaller",[])
                        if i.get("kaynak","") not in HARITA_KAYNAKLARI]
    silinen = onceki - len(data["ihlaller"])
    if silinen: print(f"🧹 {silinen} harita kaydı temizlendi")

    # ── Global görülmüş kümeler (tüm koleksiyonlar) ──
    mevcut_urls = set()
    mevcut_basliklar = set()
    for kol in ("haberler","raporlar","makaleler","uluslararasi","ekosistem"):
        for h in data.get(kol,[]):
            mevcut_urls.add(h.get("url",""))
            if h.get("baslik"):
                mevcut_basliklar.add(re.sub(r"\s+","",h["baslik"]).strip().lower())

    print(f"  Mevcut: {len(data.get('ihlaller',[]))} ihlal | "
          f"{len(data.get('haberler',[]))} haber | "
          f"{len(data.get('raporlar',[]))} rapor | "
          f"{len(data.get('makaleler',[]))} makale | "
          f"{len(data.get('uluslararasi',[]))} uluslararası | "
          f"{len(data.get('ekosistem',[]))} ekosistem")

    # ── Tüm kaynakları tara ──
    tum_kaynaklar = KAYNAK_RSS + RAPOR_RSS + MAKALE_RSS + ULUSLARARASI_RSS + EKOSISTEM_RSS
    print(f"\n🔍 RSS taranıyor… ({len(tum_kaynaklar)} kaynak)")
    yeni_hedefler: dict = {"haberler":[],"raporlar":[],"makaleler":[],"uluslararasi":[],"ekosistem":[]}
    id_sayaclar = {kol: sonraki_id(data.get(kol,[])) for kol in yeni_hedefler}

    for kaynak in tum_kaynaklar:
        for h in rss_cek(kaynak):
            hedef = h.pop("_hedef", "haberler")
            bn = re.sub(r"\s+","",h.get("baslik","")).strip().lower()
            if h["url"] not in mevcut_urls and bn not in mevcut_basliklar:
                h["id"] = id_sayaclar[hedef]
                id_sayaclar[hedef] += 1
                yeni_hedefler[hedef].append(h)
                mevcut_urls.add(h["url"])
                if bn: mevcut_basliklar.add(bn)

    print(f"\n🌐 Web scraping… ({len(KAYNAK_WEB)} kaynak)")
    for kaynak in KAYNAK_WEB:
        for h in web_cek(kaynak):
            hedef = h.pop("_hedef", "haberler")
            bn = re.sub(r"\s+","",h.get("baslik","")).strip().lower()
            if h["url"] not in mevcut_urls and bn not in mevcut_basliklar:
                h["id"] = id_sayaclar[hedef]
                id_sayaclar[hedef] += 1
                yeni_hedefler[hedef].append(h)
                mevcut_urls.add(h["url"])
                if bn: mevcut_basliklar.add(bn)

    # ── Koleksiyonları güncelle ──
    for kol, yeni in yeni_hedefler.items():
        data[kol] = yeni + data.get(kol,[])
        print(f"  ✅ {kol:15s}: +{len(yeni)} yeni → toplam {len(data[kol])}")

    data["_meta"] = {
        "guncelleme":    datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "kaynak":        "otomatik_tarama_v6",
        "ihlal_sayisi":  len(data.get("ihlaller",[])),
        "haber_sayisi":  len(data.get("haberler",[])),
        "rapor_sayisi":  len(data.get("raporlar",[])),
        "makale_sayisi": len(data.get("makaleler",[])),
        "ulus_sayisi":   len(data.get("uluslararasi",[])),
        "ekosistem_sayisi": len(data.get("ekosistem",[])),
    }

    print("\n📤 GitHub'a yazılıyor (API)…")
    update_remote_data(data, sha)

if __name__ == "__main__":
    main()
