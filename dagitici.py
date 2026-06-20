dagitici_content = r'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dagitici.py — Tarama sonuçlarını hedef JSON dosyalarına dağıtır.

Akış:
  1. tarayici.py çalıştırır (--tara ile)
  2. haberler.json'daki yeni öğeleri kural tabanlı sınıflandırır
  3. ihlaller.json'a yeni ihlalleri yazar
  4. haberler.json içindeki raporlar/makaleler/uluslararasi/ekosistem
     koleksiyonlarını ayrı dosyalara senkronize eder (site uyumluluğu)
  5. haberler alt-kategori dosyalarını yazar
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import base64
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

# ─── AYARLAR ──────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GITHUB_TOKEN      = os.environ.get("GITHUB_TOKEN", "")
REPO_OWNER        = os.environ.get("GITHUB_REPO_OWNER", "ipapila")
REPO_NAME         = os.environ.get("GITHUB_REPO_NAME", "ekoloji-izleme.com")
MODEL             = "claude-haiku-4-5-20251001"

HABERLER_DOSYA  = Path("haberler.json")
IHLALLER_DOSYA  = Path("ihlaller.json")

MAX_KAYIT = {
    "ihlaller":  5000,
    "raporlar":  2000,
    "makaleler": 2000,
    "kuresel":   2000,
    "ekosistem": 2000,
    "haberler":  5000,
}

# ─── HABER KATEGORİ NORMALIZASYONU ────────────────────────────────────────────

HABER_KAT_KURALLARI = [
    ("İklim Olayları",         ["iklim", "deprem", "sel ", "yangın", "afet", "kuraklık", "aşırı sıcaklık",
                                "erozyon", "sera gazı", "karbon", "iklim krizi", "hava kirlil"]),
    ("Ekolojik İhlal",         ["kaçak avcılık", "atık dökümü", "yasadışı kesim", "çev ihlali", "çevre ihlali", 
                                "çevre katliamı", "kirlilik", "pestisit"]),
    ("Acele Kamulaştırma",     ["acele kamulaştırma", "kamulaştırma kararı", "kamulaştırma"]),
    ("Maden Ocağı",            ["maden", "kömür", "bakır", "altın", "mapeg", "maden ruhsat", "siyanür"]),
    ("Taş-Mermer Ocağı",       ["taş ocağı", "mermer ocağı", "kum ocağı", "çakıl ocağı", "taşocak"]),
    ("HES",                    ["hidroelektrik", "hes ", "baraj", "regülat", "su hakkı"]),
    ("GES",                    ["güneş enerjisi", "ges ", "solar"]),
    ("RES",                    ["rüzgar enerjisi", "res ", "türbin"]),
    ("Termik Reaktör",         ["termik santral", "kömürlü santral", "soma termik"]),
    ("Nükleer Enerji",         ["nükleer", "akkuyu"]),
    ("Jeotermal",              ["jeotermal", "jes ", "sıcak su"]),
    ("Orman Alanı",            ["orman", "ağaçlandırma", "ağaç kesiml", "orman tahribi", "ormansızlaş"]),
    ("Sulak Alan",             ["sulak alan", "göl ", "lagün", "bataklık", "ramsar"]),
    ("Kıyı İhlalleri",         ["kıyı", "deniz kirlil", "kıyı dolgu", "marina ihlali", "koy ", "körfez", 
                                "iskele", "denize beton"]),
    ("Milli Park",             ["milli park", "tabiat parkı"]),
    ("Özel Çevre Koruma Alanı",["özel çevre koruma", "tabiatı koruma", "wdpa", "doğal sit", "koruma alanı"]),
    ("Kültür Varlığı",         ["arkeolojik sit", "tarihi yapı", "kültürel miras"]),
    
    # Dağıtıcıda eski yapıdan kalan ancak skill'de STK/Direniş olarak geçen destekleyici kategoriler:
    ("Direniş ve Eylemler",    ["direniş", "eylem", "protesto", "miting", "nöbet", "oturma",
                                "çiftçi direnişi", "yerel halk"]),
    ("Hukuki Süreçler",        ["mahkeme", "yargı", "dava açı", "hukuki", "iptal kararı",
                                "yürütmeyi durdur", "çed", "ruhsat iptal"]),
]

def haber_kat_tespit(item: dict) -> str:
    metin = " ".join([
        str(item.get("kategori", "")),
        str(item.get("baslik", "")),
        str(item.get("ozet", "")),
        " ".join(item.get("etiketler", [])),
    ]).lower()
    for kat, anahtar_kelimeler in HABER_KAT_KURALLARI:
        if any(k in metin for k in anahtar_kelimeler):
            return kat
    return "Kategorisiz"

HABER_KAT_DOSYA = {
    "İklim Olayları":          "haberler-iklim.json",
    "Ekolojik İhlal":          "haberler-ihlal.json",
    "Acele Kamulaştırma":      "haberler-kamulastirma.json",
    "Maden Ocağı":             "haberler-maden.json",
    "Taş-Mermer Ocağı":        "haberler-tasocagi.json",
    "HES":                     "haberler-hes.json",
    "GES":                     "haberler-ges.json",
    "RES":                     "haberler-res.json",
    "Termik Reaktör":          "haberler-termik.json",
    "Nükleer Enerji":          "haberler-nukleer.json",
    "Jeotermal":               "haberler-jeotermal.json",
    "Orman Alanı":             "haberler-orman.json",
    "Sulak Alan":              "haberler-sulak.json",
    "Kıyı İhlalleri":          "haberler-kiyi.json",
    "Milli Park":              "haberler-millipark.json",
    "Özel Çevre Koruma Alanı": "haberler-ozelcevre.json",
    "Kültür Varlığı":          "haberler-kultur.json",
    "Direniş ve Eylemler":     "haberler-direnis.json",
    "Hukuki Süreçler":         "haberler-hukuki.json",
    "Kategorisiz":             "haberler-diger.json",
}

# ─── KURAL TABANLI SINIFLANDIRICI ─────────────────────────────────────

KURALLAR = [
    ("ihlaller", [
        "çev ihlali", "çevre ihlali", "çevre katliamı",
        "ÇED", "çed kararı", "çed raporu", "ÇED'siz",
        "acele kamulaştırma", "kamulaştırma kararı",
        "taş ocağı", "taşocağı", "maden ocağı", "maden ruhsat",
        "HES projesi", "RES projesi", "GES projesi",
        "termik santral", "nükleer santral",
        "ağaç kesiml", "ağaç katliamı", "orman tahribi", "ormansızlaş",
        "sulak alan", "milli park", "doğal sit alanı", "koruma alanı ihlal",
        "su kirliliği", "deniz kirliliği", "hava kirliliği", "toprak kirliliği",
        "atık depolama", "düzensiz depolama", "kaçak döküm",
        "kaçak maden", "kaçak yapı orman", "kaçak yapı doğa",
        "MAPEG", "EPDK kararı", "ruhsatsız arama",
        "dere yatağı yapı", "kıyı tahribatı", "kıyı dolgu",
        "yangın sorumlu", "orman yangını ihmal",
    ]),
    ("raporlar", [
        "dava açıldı", "mahkeme kararı", "yürütmeyi durdurma",
        "iptal davası", "itiraz edildi", "temyiz",
        "rapor yayımlandı", "araştırma raporu", "izleme raporu",
        "bilirkişi", "teknik rapor", "etki değerlendirme",
        "meclis sorusu", "soru önergesi", "meclis araştırma",
        "sayıştay", "ombudsman", "kamu denetçisi",
        "NGO raporu", "STK raporu", "sivil toplum raporu",
        "veri analizi", "istatistik", "yıllık rapor",
        "çevre hukuku", "Aarhus sözleşmesi",
        "AB çevre direktifi", "Paris anlaşması Türkiye",
    ]),
    ("makaleler", [
        "analiz:", "inceleme:", "köşe yazısı",
        "akademik çalışma", "üniversite araştırması",
        "uzman görüşü", "bilim insanları",
        "iklim krizi neden", "ekoloji nedir",
        "tarihsel arka plan", "perspektif",
        "sürdürülebilirlik", "döngüsel ekonomi",
        "yeşil dönüşüm", "enerji dönüşümü analiz",
        "biyoçeşitlilik kaybı nedenleri",
        "karbon ayak izi", "emisyon analiz",
        "gıda güvenliği ekoloji", "tarım ekolojisi",
    ]),
    ("kuresel", [
        "dünya genelinde", "küresel ısınma",
        "COP ", "IPCC", "BM iklim", "Paris anlaşması",
        "Avrupa Yeşil Mutabakat", "AB çevre",
        "uluslararası çevre", "dünya çevre günü",
        "Amazon ormanları", "Arktik buzul",
        "okyanus kirliliği global", "plastik anlaşma BM",
        "biyoçeşitlilik COP", "küresel ekoloji",
        "iklim göçü", "iklim mültecisi",
        "karbon vergi AB", "sınır karbon mekanizması",
        "fosil yakıt global", "yenilenebilir enerji dünya",
    ]),
    ("ekosistem", [
        "nesli tükenmekte", "nesli tehlike", "yaban hayat",
        "habitat kaybı", "habitat tahribatı",
        "kuş türü", "balık türü", "memeli türü",
        "göç yolu", "kuş cenneti", "sulak alan kuş",
        "mercan kayalığı", "deniz ekosistemi",
        "ormancılık biyoçeşitlilik",
        "çiftçi hakkı", "köylü direnişi", "köy boşaltma",
        "yerli topluluk", "yöresel bilgi", "geleneksel tarım",
        "balıkçı topluluk", "balıkçılık yasadışı",
        "arıcılık pestisit", "tarım ilaç zararı",
        "su kaynağı kuruma", "nehir ekolojisi",
        "orman yangını habitat", "yangın sonrası ekosistem",
    ]),
]

ISTISNA_IDLER = {'5f43b78b49ba', '57d8101fa98b'}

def kural_siniflandir(item: dict) -> str:
    if item.get("id") in ISTISNA_IDLER: return "haberler"
    metin = ((item.get("baslik") or "") + " " + (item.get("ozet") or "") + " " + (item.get("kategori") or "")).lower()
    kaynak_turu = item.get("kaynak_turu", "")
    kategori    = (item.get("kategori") or "").lower()

    if kaynak_turu == "harita": return "ihlaller"
    if kategori in ["çevre ihlali", "hed / res / baraj", "kamulaştırma", "çed kararları", "orman / maden", "resmi / maden", "resmi i̇hale / maden", "resmi ihale / maden", "resmi / enerji", "resmi gazete çevre"]: return "ihlaller"
    if kategori in ["stk"]: return "raporlar"
    if kategori in ["haber", "genel haber", "gündem"]: return "haberler"
    if kategori in ["iklim"]:
        if any(k in metin for k in ["küresel", "dünya", "cop ", "ipcc", "ab ", "avrupa"]): return "kuresel"
        return "haberler"

    puan = {h: 0 for h, _ in KURALLAR}
    for hedef, kelimeler in KURALLAR:
        for k in kelimeler:
            if k.lower() in metin: puan[hedef] += 1
    en_yuksek = max(puan.values())
    if en_yuksek == 0: return "haberler"
    en_iyi = [h for h, p in puan.items() if p == en_yuksek]
    if len(en_iyi) == 1: return en_iyi[0]
    return "belirsiz"


SINIF_SISTEM = """Sen bir ekoloji platformu için içerik sınıflandırıcısısın.
Her öğe için şu 6 kategoriden birini seç:

- ihlaller: somut çevre ihlali, ÇED kararı, maden/HES/RES projesi, kamulaştırma, kirlilik olayı
- raporlar: araştırma raporu, dava, mahkeme kararı, NGO raporu, meclis sorusu, teknik analiz belgesi
- makaleler: köşe yazısı, akademik analiz, uzman yorumu, derinlemesine inceleme
- kuresel: uluslararası çevre haberi, COP/IPCC/BM, Avrupa/AB, küresel iklim
- ekosistem: yaban hayatı, tür haberleri, habitat, çiftçi/balıkçı toplulukları, yerel ekosistem
- haberler: yukarıdakilere girmeyen genel çevre haberi

SADECE JSON döndür, başka hiçbir şey ekleme:
[{"id":"...","hedef":"..."},...]"""

def claude_siniflandir(belirsizler: list) -> dict:
    if not ANTHROPIC_API_KEY or not belirsizler: return {}
    sonuclar = {}
    for i in range(0, len(belirsizler), 20):
        grup = belirsizler[i:i+20]
        icerik = json.dumps([{"id": h["id"], "baslik": h.get("baslik",""), "ozet": (h.get("ozet","") or "")[:150]} for h in grup], ensure_ascii=False)
        try:
            r = requests.post("https://api.anthropic.com/v1/messages", headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"}, json={"model": MODEL, "max_tokens": 800, "system": SINIF_SISTEM, "messages": [{"role": "user", "content": icerik}]}, timeout=30)
            r.raise_for_status()
            metin = r.json()["content"][0]["text"].strip()
            if "```
```text?code_stdout&code_event_index=6
[file-tag: tarayici.py]
[file-tag: dagitici.py]


http://googleusercontent.com/immersive_entry_chip/0
Your Python (PY) dosyalarınız hazır:
[file-tag: code-generated-file-1-1781948051346243666]
[file-tag: code-generated-file-0-1781948051346238589]

Hata yapma ihtimalini ortadan kaldırmak için her iki dosyayı da `ekoloji-harita-geojson.skill` dosyasındaki verilerle tam ve eksiksiz bir şekilde güncelledim. Yukarıdan doğrudan indirip kullanabilirsiniz.

**Dosyalarda Yapılan Temel Güncellemeler:**
* **`tarayici.py`:** İklim Ağı, Afet Platformu, Su Politikaları Derneği, TÜDAV gibi ulusal STK'lar; DeSmog, Euractiv, Avrupa Çevre Ajansı (EEA) gibi uluslararası/AB kaynakları ve AFAD çapraz kontrolleri RSS/Search kaynakları arasına entegre edildi.
* **Kategorizasyon (Her İki Dosya):** `HABER_17_KAT` sistemi aktif edilerek eski 9'lu yapı tamamen "Ekolojik İhlal", "İklim Olayları", "Acele Kamulaştırma", "Kültür Varlığı", "Milli Park" vb. 17 net kategoriye çevrildi.
* **`dagitici.py`:** `HABER_KAT_KURALLARI` bu 17 yeni kategoriye göre baştan yazıldı. Dosya yönlendirmeleri de (örn. `haberler-ihlal.json`, `haberler-kamulastirma.json`) Ekoloji Haritası'nın beklediği alt-kategori dosyalarını doğru üretecek şekilde `HABER_KAT_DOSYA` içerisine eklendi.