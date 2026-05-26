#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ekoloji-izleme.com — Otomatik Güncelleme v7
v7 YENİLİKLERİ:
  - İhlal tarama eklendi (IHLAL_RSS kaynakları)
  - Koordinat tahmini (il bazlı)
  - Kategori otomatik tespiti
  - Şiddet skoru
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

RAPOR_SINYAL = ["rapor","araştırma","analiz","inceleme","değerlendirme","politika","strateji",
                "report","analysis","research","assessment","policy","findings"]
KOSE_SINYAL  = ["köşe","görüş","yorum","perspektif","opinion","commentary","column"]

# ══════════════════════════════════════════════════════════════════
#  İL KOORDİNATLARI
# ══════════════════════════════════════════════════════════════════

IL_KOORD = {
    "adana":(37.0000,35.3213),"adıyaman":(37.7648,38.2786),"afyon":(38.7507,30.5567),
    "ağrı":(39.7191,43.0503),"amasya":(40.6499,35.8353),"ankara":(39.9208,32.8541),
    "antalya":(36.8841,30.7056),"artvin":(41.1828,41.8183),"aydın":(37.8560,27.8416),
    "balıkesir":(39.6484,27.8826),"bilecik":(40.1506,29.9792),"bingöl":(38.8854,40.4981),
    "bitlis":(38.4006,42.1095),"bolu":(40.7396,31.6061),"burdur":(37.7265,30.2906),
    "bursa":(40.1826,29.0665),"çanakkale":(40.1553,26.4142),"çankırı":(40.6013,33.6134),
    "çorum":(40.5506,34.9556),"denizli":(37.7765,29.0864),"diyarbakır":(37.9144,40.2306),
    "edirne":(41.6818,26.5623),"elazığ":(38.6810,39.2264),"erzincan":(39.7500,39.5000),
    "erzurum":(39.9043,41.2679),"eskişehir":(39.7767,30.5206),"gaziantep":(37.0662,37.3833),
    "giresun":(40.9128,38.3895),"gümüşhane":(40.4386,39.4814),"hakkari":(37.5744,43.7408),
    "hatay":(36.4018,36.3498),"ısparta":(37.7648,30.5566),"içel":(36.8000,34.6333),
    "mersin":(36.8000,34.6333),"istanbul":(41.0082,28.9784),"izmir":(38.4192,27.1287),
    "kars":(40.6013,43.0975),"kastamonu":(41.3887,33.7827),"kayseri":(38.7312,35.4787),
    "kırklareli":(41.7333,27.2167),"kırşehir":(39.1425,34.1709),"kocaeli":(40.8533,29.8815),
    "konya":(37.8746,32.4932),"kütahya":(39.4167,29.9833),"malatya":(38.3552,38.3095),
    "manisa":(38.6191,27.4289),"kahramanmaraş":(37.5858,36.9371),"mardin":(37.3212,40.7245),
    "muğla":(37.2153,28.3636),"muş":(38.9462,41.7539),"nevşehir":(38.6939,34.6857),
    "niğde":(37.9667,34.6833),"ordu":(40.9860,37.8797),"rize":(41.0201,40.5234),
    "sakarya":(40.6940,30.4358),"samsun":(41.2867,36.3300),"siirt":(37.9333,41.9500),
    "sinop":(42.0231,35.1531),"sivas":(39.7477,37.0179),"tekirdağ":(40.9781,27.5115),
    "tokat":(40.3167,36.5500),"trabzon":(41.0015,39.7178),"tunceli":(39.1079,39.5480),
    "şanlıurfa":(37.1591,38.7969),"uşak":(38.6823,29.4082),"van":(38.4891,43.4089),
    "yozgat":(39.8181,34.8147),"zonguldak":(41.4564,31.7987),"aksaray":(38.3687,34.0370),
    "bayburt":(40.2552,40.2249),"karaman":(37.1759,33.2287),"kırıkkale":(39.8468,33.5153),
    "batman":(37.8812,41.1351),"şırnak":(37.5164,42.4611),"bartın":(41.6344,32.3375),
    "ardahan":(41.1105,42.7022),"iğdır":(39.9167,44.0333),"yalova":(40.6500,29.2667),
    "karabük":(41.2061,32.6204),"kilis":(36.7184,37.1212),"osmaniye":(37.0742,36.2462),
    "düzce":(40.8438,31.1565),
}

def il_koord_bul(metin):
    """Metinden il adı bulup koordinat döndür."""
    metin_lower = metin.lower()
    for il, koord in IL_KOORD.items():
        if il in metin_lower:
            return koord
    return None

# ══════════════════════════════════════════════════════════════════
#  KATEGORİ TESPİTİ
# ══════════════════════════════════════════════════════════════════

KATEGORI_ESLEME = [
    (["acele kamulaştırma","kamulaştırma kararı"],                     "Acele Kamulaştırma"),
    (["maden ocağı","maden izni","madencilik","taş ocağı","kireç ocağı","granit"],"Maden Ocağı"),
    (["taş ocağı","mermer ocağı","kireçtaşı","taş-mermer"],            "Taş-Mermer Ocağı"),
    (["hes","hidroelektrik","baraj","nehir","dere","çay"],              "HES"),
    (["res","rüzgar enerji","rüzgar türbin","enerji santrali"],         "RES"),
    (["ges","güneş enerji","solar"],                                    "GES"),
    (["termik","kömür santral","fosil"],                                "Termik Reaktör"),
    (["nükleer","akkuyu","atom"],                                       "Nükleer Enerji"),
    (["jeotermal"],                                                     "Jeotermal"),
    (["orman","ağaç kes","ağaç katli","ormansız"],                     "Orman Alanı"),
    (["sulak alan","bataklık","göl","lagün"],                          "Sulak Alan"),
    (["milli park","tabiat parkı","doğal sit","koruma alanı"],         "Milli Park"),
    (["kıyı","sahil","deniz tahrib","plaj"],                           "Kıyı İhlalleri"),
    (["atık","çöp","depolama","döküm","kirlilik"],                     "Atık & Depolama"),
    (["kaçak yapı","kaçak inşaat","imar ihlal"],                       "Kaçak Yapılaşma"),
    (["iklim","sera gazı","karbon","emisyon"],                         "İklim Olayları"),
    (["yaban hayat","nesli tüken","nesli tehlike","tür yok"],          "Yaban Hayatı"),
    (["çiftçi","köylü","tarım arazi"],                                 "Tarım Arazisi İhlali"),
    (["su hakkı","içme suyu","su kaynak"],                             "Su Hakkı"),
    (["sanayi bölge","osb","fabrika","tesis"],                         "Sanayi Bölgesi"),
]

def kategori_tespit(baslik, ozet=""):
    metin = (baslik + " " + ozet).lower()
    for anahtar_listesi, kategori in KATEGORI_ESLEME:
        if any(k in metin for k in anahtar_listesi):
            return kategori
    return "Ekolojik İhlal"

# ══════════════════════════════════════════════════════════════════
#  ŞİDDET SKORU
# ══════════════════════════════════════════════════════════════════

def siddet_tespit(baslik, ozet=""):
    metin = (baslik + " " + ozet).lower()
    kritik = ["acele kamulaştırma","nükleer","termik","kömür","katliamı","yıkım","ÇED geçti",
              "ruhsat verildi","ihale","inşaat başladı","tahribat","yok edildi"]
    orta   = ["maden","hes","res","ges","baraj","orman","kamulaştırma","ruhsat",
              "izin","proje","risk","tehdit","kirlilik"]
    if any(k in metin for k in kritik): return "kritik"
    if any(k in metin for k in orta):   return "orta"
    return "takipte"

# ══════════════════════════════════════════════════════════════════
#  İHLAL RSS KAYNAKLARI
# ══════════════════════════════════════════════════════════════════

IHLAL_RSS = [
    {"ad": "Google News",  "etiket": "Acele Kamulaştırma",
     "url": "https://news.google.com/rss/search?q=acele+kamulaştırma+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "web": "https://news.google.com"},
    {"ad": "Google News",  "etiket": "Maden Ocağı",
     "url": "https://news.google.com/rss/search?q=maden+ocağı+ruhsat+çevre+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "web": "https://news.google.com"},
    {"ad": "Google News",  "etiket": "HES",
     "url": "https://news.google.com/rss/search?q=HES+baraj+dere+ihlal+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "web": "https://news.google.com"},
    {"ad": "Google News",  "etiket": "RES",
     "url": "https://news.google.com/rss/search?q=rüzgar+enerji+RES+çevre+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "web": "https://news.google.com"},
    {"ad": "Google News",  "etiket": "Orman Alanı",
     "url": "https://news.google.com/rss/search?q=orman+tahribi+ağaç+katliamı+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "web": "https://news.google.com"},
    {"ad": "Google News",  "etiket": "Kıyı İhlalleri",
     "url": "https://news.google.com/rss/search?q=kıyı+tahribatı+sahil+yapılaşma+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "web": "https://news.google.com"},
    {"ad": "Google News",  "etiket": "Atık & Depolama",
     "url": "https://news.google.com/rss/search?q=atık+depolama+kirlilik+Türkiye+çevre&hl=tr&gl=TR&ceid=TR:tr",
     "web": "https://news.google.com"},
    {"ad": "Google News",  "etiket": "ÇED",
     "url": "https://news.google.com/rss/search?q=ÇED+olumlu+maden+baraj+Türkiye+2025&hl=tr&gl=TR&ceid=TR:tr",
     "web": "https://news.google.com"},
    {"ad": "Google News",  "etiket": "Sulak Alan",
     "url": "https://news.google.com/rss/search?q=sulak+alan+kurutma+dolgu+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "web": "https://news.google.com"},
    {"ad": "Google News",  "etiket": "Termik Reaktör",
     "url": "https://news.google.com/rss/search?q=termik+santral+kömür+Türkiye+çevre&hl=tr&gl=TR&ceid=TR:tr",
     "web": "https://news.google.com"},
    {"ad": "Bianet",       "etiket": "Ekolojik İhlal",
     "url": "https://bianet.org/bianet/feed/rss",
     "web": "https://bianet.org"},
    {"ad": "Gazete Duvar", "etiket": "Ekolojik İhlal",
     "url": "https://www.gazeteduvar.com.tr/feed",
     "web": "https://www.gazeteduvar.com.tr"},
]

IHLAL_ANAHTAR = [
    "acele kamulaştırma","maden ocağı","taş ocağı","hes","res","ges","termik","nükleer",
    "orman tahribi","ağaç katliamı","sulak alan","kıyı tahribatı","atık depolama",
    "çed","ÇED","kaçak yapı","kaçak inşaat","kirlilik","tahribat","yıkım","ruhsat",
    "baraj","dere","kamulaştırma","maden izni","ormansızlaşma","jeotermal",
]

def ihlal_mi(baslik, ozet=""):
    metin = (baslik + " " + ozet).lower()
    return any(k.lower() in metin for k in IHLAL_ANAHTAR)

def ihlal_rss_cek(kaynak):
    ihlaller = []
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "ekoloji-izleme-bot/2.0 (+https://ekoloji-izleme.com)",
    ]
    r = None
    for ua in user_agents:
        try:
            r = requests.get(kaynak["url"], timeout=12, headers={
                "User-Agent": ua,
                "Accept": "application/rss+xml,application/xml,*/*",
            })
            if r.status_code == 200: break
            r = None
        except Exception: continue

    if r is None or r.status_code != 200:
        status = r.status_code if r is not None else "bağlantı hatası"
        print(f"  ⚠️  {kaynak['ad']} [ihlaller]: HTTP {status} — atlanıyor")
        return ihlaller

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
            ozet   = html_temizle(txt("description") or txt("summary") or "")
            url    = txt("link") or txt("guid")
            tarih  = tarih_normalize(txt("pubDate") or txt("published") or "")
            if not baslik or not url: continue
            if not ihlal_mi(baslik, ozet):
                red += 1
                continue
            koord = il_koord_bul(baslik + " " + ozet)
            ihlaller.append({
                "baslik":     baslik,
                "konum":      _il_adi_bul(baslik + " " + ozet),
                "kategori":   kategori_tespit(baslik, ozet),
                "siddet":     siddet_tespit(baslik, ozet),
                "tarih":      tarih,
                "kaynak":     kaynak["ad"],
                "kaynak_url": url,
                "aciklama":   ozet,
                "lat":        koord[0] if koord else None,
                "lng":        koord[1] if koord else None,
                "foto_url":   "",
                "etiketler":  [kaynak["etiket"]],
            })
            kabul += 1
        print(f"  📡 {kaynak['ad']} [ihlaller]: {kabul} kabul / {red} red")
    except Exception as e:
        print(f"  ⚠️  {kaynak['ad']} [ihlaller]: parse hatası — {e}")
    return ihlaller

def _il_adi_bul(metin):
    metin_lower = metin.lower()
    for il in IL_KOORD:
        if il in metin_lower:
            return il.title()
    return "Türkiye"

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
    {"ad": "Google News",  "etiket": "Nesli Tehlike Türler",   "genel": False, "hedef": "ekosistem", "bolum": "turler",         "dil": "tr",
     "url": "https://news.google.com/rss/search?q=nesli+tehlike+tür+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "web": "https://news.google.com"},
    {"ad": "Google News",  "etiket": "Yaban Hayatı",           "genel": False, "hedef": "ekosistem", "bolum": "yaban",          "dil": "tr",
     "url": "https://news.google.com/rss/search?q=yaban+hayatı+izleme+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "web": "https://news.google.com"},
    {"ad": "Doğa Derneği", "etiket": "Yaban Hayatı",           "genel": False, "hedef": "ekosistem", "bolum": "yaban",          "dil": "tr",
     "url": "https://news.google.com/rss/search?q=site:dogadernegi.org&hl=tr&gl=TR&ceid=TR:tr", "web": "https://dogadernegi.org"},
    {"ad": "Google News",  "etiket": "Su Canlıları",            "genel": False, "hedef": "ekosistem", "bolum": "su-canlilari",   "dil": "tr",
     "url": "https://news.google.com/rss/search?q=balık+ölümü+su+kirliliği+deniz+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "web": "https://news.google.com"},
    {"ad": "Google News",  "etiket": "Hayvan Hakları",          "genel": False, "hedef": "ekosistem", "bolum": "hayvan-haklari", "dil": "tr",
     "url": "https://news.google.com/rss/search?q=hayvan+hakları+istismar+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "web": "https://news.google.com"},
    {"ad": "Google News",  "etiket": "Çiftçi & Köylü",         "genel": False, "hedef": "ekosistem", "bolum": "ciftci",         "dil": "tr",
     "url": "https://news.google.com/rss/search?q=çiftçi+köylü+tarım+maden+kamulaştırma+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "web": "https://news.google.com"},
    {"ad": "Google News",  "etiket": "Balıkçı Toplulukları",   "genel": False, "hedef": "ekosistem", "bolum": "balikci",        "dil": "tr",
     "url": "https://news.google.com/rss/search?q=balıkçı+deniz+kirliliği+av+yasağı+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "web": "https://news.google.com"},
    {"ad": "Google News",  "etiket": "Yerli & Yerel Haklar",   "genel": False, "hedef": "ekosistem", "bolum": "yerli",          "dil": "tr",
     "url": "https://news.google.com/rss/search?q=yerel+halk+maden+HES+RES+direniş+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "web": "https://news.google.com"},
    {"ad": "Google News",  "etiket": "Kadınlar & Ekoloji",     "genel": False, "hedef": "ekosistem", "bolum": "kadinlar",       "dil": "tr",
     "url": "https://news.google.com/rss/search?q=kadın+çevre+ekoloji+maden+HES+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "web": "https://news.google.com"},
    {"ad": "Google News",  "etiket": "Gençlik & Ekoloji",      "genel": False, "hedef": "ekosistem", "bolum": "genclik",        "dil": "tr",
     "url": "https://news.google.com/rss/search?q=iklim+gençlik+Türkiye+genç+aktivist&hl=tr&gl=TR&ceid=TR:tr", "web": "https://news.google.com"},
    {"ad": "Google News",  "etiket": "Kentsel Çevre",          "genel": False, "hedef": "ekosistem", "bolum": "kentsel",        "dil": "tr",
     "url": "https://news.google.com/rss/search?q=yeşil+alan+kentsel+dönüşüm+hava+kirliliği+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "web": "https://news.google.com"},
    {"ad": "Google News",  "etiket": "Ekolojik Eşitsizlik",    "genel": False, "hedef": "ekosistem", "bolum": "esitsizlik",     "dil": "tr",
     "url": "https://news.google.com/rss/search?q=çevre+adaleti+ekolojik+eşitsizlik+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "web": "https://news.google.com"},
    {"ad": "Google News",  "etiket": "İklim Göçü",             "genel": False, "hedef": "ekosistem", "bolum": "goc",            "dil": "tr",
     "url": "https://news.google.com/rss/search?q=iklim+göçü+yerinden+edilme+Türkiye&hl=tr&gl=TR&ceid=TR:tr", "web": "https://news.google.com"},
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
    url      = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
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
#  RSS ÇEKİCİ (haberler/raporlar/makaleler/uluslararasi/ekosistem)
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

    # Global görülmüş kümeler
    mevcut_urls      = set()
    mevcut_basliklar = set()
    for kol in ("ihlaller","haberler","raporlar","makaleler","uluslararasi","ekosistem"):
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

    # ── İhlal tarama ──
    print(f"\n🔴 İhlal taranıyor… ({len(IHLAL_RSS)} kaynak)")
    ihlal_id = sonraki_id(data.get("ihlaller",[]))
    yeni_ihlaller = []
    for kaynak in IHLAL_RSS:
        for ihlal in ihlal_rss_cek(kaynak):
            bn  = re.sub(r"\s+","",ihlal.get("baslik","")).strip().lower()
            url = ihlal.get("kaynak_url","")
            if url not in mevcut_urls and bn not in mevcut_basliklar:
                ihlal["id"] = ihlal_id
                ihlal_id += 1
                yeni_ihlaller.append(ihlal)
                mevcut_urls.add(url)
                if bn: mevcut_basliklar.add(bn)

    data["ihlaller"] = yeni_ihlaller + data.get("ihlaller",[])
    print(f"  ✅ ihlaller      : +{len(yeni_ihlaller)} yeni → toplam {len(data['ihlaller'])}")

    # ── Haber/rapor/makale/uluslararasi/ekosistem tarama ──
    tum_kaynaklar = KAYNAK_RSS + RAPOR_RSS + MAKALE_RSS + ULUSLARARASI_RSS + EKOSISTEM_RSS
    print(f"\n🔍 RSS taranıyor… ({len(tum_kaynaklar)} kaynak)")
    yeni_hedefler = {"haberler":[],"raporlar":[],"makaleler":[],"uluslararasi":[],"ekosistem":[]}
    id_sayaclar   = {kol: sonraki_id(data.get(kol,[])) for kol in yeni_hedefler}

    for kaynak in tum_kaynaklar:
        for h in rss_cek(kaynak):
            hedef = h.pop("_hedef", "haberler")
            bn    = re.sub(r"\s+","",h.get("baslik","")).strip().lower()
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
            bn    = re.sub(r"\s+","",h.get("baslik","")).strip().lower()
            if h["url"] not in mevcut_urls and bn not in mevcut_basliklar:
                h["id"] = id_sayaclar[hedef]
                id_sayaclar[hedef] += 1
                yeni_hedefler[hedef].append(h)
                mevcut_urls.add(h["url"])
                if bn: mevcut_basliklar.add(bn)

    for kol, yeni in yeni_hedefler.items():
        data[kol] = yeni + data.get(kol,[])
        print(f"  ✅ {kol:15s}: +{len(yeni)} yeni → toplam {len(data[kol])}")

    data["_meta"] = {
        "guncelleme":       datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "kaynak":           "otomatik_tarama_v7",
        "ihlal_sayisi":     len(data.get("ihlaller",[])),
        "haber_sayisi":     len(data.get("haberler",[])),
        "rapor_sayisi":     len(data.get("raporlar",[])),
        "makale_sayisi":    len(data.get("makaleler",[])),
        "ulus_sayisi":      len(data.get("uluslararasi",[])),
        "ekosistem_sayisi": len(data.get("ekosistem",[])),
    }

    print("\n📤 GitHub'a yazılıyor (API)…")
    update_remote_data(data, sha)

if __name__ == "__main__":
    main()
