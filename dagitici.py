# ─── HABER KATEGORİ NORMALIZASYONU ────────────────────────────────────────────

HABER_KAT_KURALLARI = [
    ("İklim ve Afet",        ["iklim", "deprem", "sel ", "yangın", "afet", "kuraklık",
                               "erozyon", "sera gazı", "karbon", "iklim krizi", "hava kirlil"]),
    ("Maden ve Enerji",      ["maden", "taş ocak", "mermer ocak", "termik", "nükleer",
                               "jeotermal", "enerji lisans", "res lisans", "ges lisans",
                               "hes lisans", "res ", " ges ", " hes ", "epdk", "mapeg",
                               "kamulaştırma", "çed", "ihale", "ruhsat", "akkuyu",
                               "petrol", "doğal gaz", "kömür", "baraj ", "regülat"]),
    ("Orman ve Doğa",        ["orman", "ağaç", "milli park", "koruma alan", "doğa park",
                               "sulak alan", "habitat", "biyoçeşitli", "flora", "fauna",
                               "özel çevre"]),
    ("Su ve Kıyı",           ["su kirlil", "nehir", " göl ", "kıyı", "deniz kirlil",
                               "içme suyu", "su hakkı", "dere", "taşkın", "baraj gölü"]),
    ("Yaban Hayatı",         ["yaban hayat", "hayvan hak", "hayvan hakk", "itlaf",
                               "nesli tehlike", "tür ", "balık ölü", "kuş ölü", "vegan",
                               "hayvan istismar", "hayvancılık çevre"]),
    ("Nöbetler ve Gözaltılar",["gözaltı", "tutuklama", "nöbet tut", "baskın", "operasyon"]),
    ("Direniş ve Eylemler",  ["direniş", "eylem", "protesto", "miting", "nöbet", "oturma",
                               "köylü", "çiftçi direnişi", "yerel halk", "muhalefet"]),
    ("Hukuki Süreçler",      ["mahkeme", "yargı", "dava açı", "hukuki", "iptal kararı",
                               "yürütmeyi durdur", "anayasa", "idare mahkeme", "temyiz",
                               "imar iptal", "lisans iptal", "ruhsat iptal"]),
    ("İnsan Hakları",        ["insan hakları", "işkence", "zorla kaybetme", "gözaltı",
                               "ifade özgürlüğü", "basın özgürlüğü", "tutuklama"]),
    ("STK & Kampanyalar",    ["wwf", "greenpeace", "tema ", "bianet", "gazete duvar",
                               "medyascope", "stk rapor", "kampanya", "imza kampanya",
                               "amnesty", "ihd ", "tvd ", "haytap"]),
    ("Maden ve Enerji",      ["orman / maden", "tarım alanları / maden", "maden riski",
                               "jes ", "çed kararları", "hes / res", "ihale / enerji"]),
    ("Hukuki Süreçler",      ["çevre ceza", "idari ceza", "ceza kesil", "ceza veril",
                               "aktivist tutukla", "cop31", "aktivist gözaltı",
                               "çevre aktivist", "kirleten ceza"]),
    ("Su ve Kıyı",           ["koy", "körfez", "beton deniz", "denize beton", "kıyı talan",
                               "deniz kirlil", "iskele", "marina", "atık su ceza"]),
    ("Maden ve Enerji",      ["çevre ihlali", "ekoloji", "gündem / çevre", "çevre / gündem",
                               "kirlilik", "soma termik", "termik ceza"]),
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
    "İklim ve Afet":           "haberler-iklim.json",
    "Maden ve Enerji":         "haberler-maden.json",
    "Orman ve Doğa":           "haberler-orman.json",
    "Su ve Kıyı":              "haberler-su.json",
    "Yaban Hayatı":            "haberler-yaban.json",
    "Direniş ve Eylemler":     "haberler-direnis.json",
    "Hukuki Süreçler":         "haberler-hukuki.json",
    "Nöbetler ve Gözaltılar":  "haberler-nobet.json",
    "İnsan Hakları":           "haberler-ihaklar.json",
    "STK & Kampanyalar":       "haberler-stk.json",
    "Kategorisiz":             "haberler-diger.json",
}

#!/usr/bin/env python3
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
        "TEMA raporu", "WWF raporu", "Greenpeace raporu",
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


# Kalici istisna listesi - bu ID ler hic bir zaman ihlallere gitmez
ISTISNA_IDLER = {
    '5f43b78b49ba',  # Esra Isik davasi
    '57d8101fa98b',  # CHP Meclis haberi
}

def kural_siniflandir(item: dict) -> str:
    if item.get("id") in ISTISNA_IDLER:
        return "haberler"
    metin = (
        (item.get("baslik") or "") + " " +
        (item.get("ozet") or "") + " " +
        (item.get("kategori") or "")
    ).lower()

    kaynak_turu = item.get("kaynak_turu", "")
    kategori    = (item.get("kategori") or "").lower()

    if kaynak_turu == "harita":
        return "ihlaller"

    if kategori in ["çevre ihlali", "hed / res / baraj", "kamulaştırma", "çed kararları", "orman / maden", "resmi / maden", "resmi i̇hale / maden", "resmi ihale / maden", "resmi / enerji", "resmi gazete çevre"]:
        return "ihlaller"
    if kategori in ["stk"]:
        return "raporlar"
    if kategori in ["haber", "genel haber", "gündem"]:
        return "haberler"
    if kategori in ["iklim"]:
        if any(k in metin for k in ["küresel", "dünya", "cop ", "ipcc", "ab ", "avrupa"]):
            return "kuresel"
        return "haberler"

    puan = {h: 0 for h, _ in KURALLAR}
    for hedef, kelimeler in KURALLAR:
        for k in kelimeler:
            if k.lower() in metin:
                puan[hedef] += 1

    en_yuksek = max(puan.values())
    if en_yuksek == 0:
        return "haberler"

    en_iyi = [h for h, p in puan.items() if p == en_yuksek]
    if len(en_iyi) == 1:
        return en_iyi[0]

    return "belirsiz"


# ─── CLAUDE SINIFLANDIRICI ────────────────────────────────────────────

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
    if not ANTHROPIC_API_KEY or not belirsizler:
        return {}
    sonuclar = {}
    for i in range(0, len(belirsizler), 20):
        grup = belirsizler[i:i+20]
        icerik = json.dumps([
            {"id": h["id"], "baslik": h.get("baslik",""), "ozet": (h.get("ozet","") or "")[:150]}
            for h in grup
        ], ensure_ascii=False)
        try:
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": MODEL,
                    "max_tokens": 800,
                    "system": SINIF_SISTEM,
                    "messages": [{"role": "user", "content": icerik}],
                },
                timeout=30,
            )
            r.raise_for_status()
            metin = r.json()["content"][0]["text"].strip()
            if "```" in metin:
                metin = metin.split("```")[1]
                if metin.startswith("json"):
                    metin = metin[4:]
            liste = json.loads(metin.strip())
            for item in liste:
                sonuclar[item["id"]] = item.get("hedef", "haberler")
            print(f"  Claude: {len(grup)} öğe sınıflandırıldı")
            time.sleep(0.5)
        except Exception as e:
            print(f"  Claude API hatası: {e}")
            for h in grup:
                sonuclar[h["id"]] = "haberler"
    return sonuclar


# ─── İHLALLER DOSYA YÖNETİMİ ─────────────────────────────────────────

def ihlaller_guncelle(yeni_ihlaller: list) -> int:
    """Yeni ihlalleri ihlaller.json'a ekler, duplicate'leri atlar."""
    mevcut = []
    if IHLALLER_DOSYA.exists():
        try:
            veri = json.loads(IHLALLER_DOSYA.read_text(encoding="utf-8"))
            mevcut = veri.get("ihlaller", [])
        except Exception:
            mevcut = []

    mevcut_idler = {i.get("id", "") for i in mevcut}
    eklenecek = [i for i in yeni_ihlaller if i.get("id", "") not in mevcut_idler]

    birlesik = eklenecek + mevcut
    birlesik.sort(key=lambda x: x.get("tarih") or "1970", reverse=True)
    from datetime import datetime, timedelta as _td
_sinir_i = (datetime.now() - _td(days=180)).strftime("%Y-%m-%d")
birlesik = [x for x in birlesik if (x.get("tarih") or "9999") >= _sinir_i or not x.get("tarih")]
birlesik = birlesik[:MAX_KAYIT["ihlaller"]]

    cikti = {
        "meta": {
            "guncelleme": datetime.now(timezone.utc).isoformat(),
            "toplam": len(birlesik),
            "yeni_eklenen": len(eklenecek),
        },
        "ihlaller": birlesik,
    }
    IHLALLER_DOSYA.write_text(json.dumps(cikti, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✓ ihlaller.json: {len(birlesik)} kayıt ({len(eklenecek)} yeni)")
    return len(eklenecek)


# ─── HABERLER.JSON SENKRONIZASYONU ────────────────────────────────────



# ─── AYLIK ARŞİV ──────────────────────────────────────────────────────

def arsiv_yaz(kaynak: dict):
    """
    Her koleksiyonun geçen aya ait kayıtlarını arsiv/ klasörüne yazar.
    Mevcut aydaki kayıtlara dokunmaz. Dosya zaten varsa üzerine yazmaz.
    """
    from datetime import date
    bugun = date.today()
    gecen_ay = (bugun.replace(day=1) - timedelta(days=1))
    ay_str = gecen_ay.strftime("%Y-%m")

    arsiv_dir = Path("arsiv")
    arsiv_dir.mkdir(exist_ok=True)

    KOLEKSIYONLAR = {
        "haberler":     "haberler",
        "raporlar":     "raporlar",
        "makaleler":    "makaleler",
        "uluslararasi": "kuresel",
        "ekosistem":    "ekosistem",
    }

    for kaynak_adi, dosya_adi in KOLEKSIYONLAR.items():
        arsiv_dosya = arsiv_dir / f"{dosya_adi}-{ay_str}.json"
        if arsiv_dosya.exists():
            continue

        liste = kaynak.get(kaynak_adi, [])
        ay_kayitlar = [
            item for item in liste
            if item.get("tarih", "")[:7] == ay_str
        ]

        if not ay_kayitlar:
            continue

        cikti = {
            "meta": {
                "arsiv_ay": ay_str,
                "koleksiyon": dosya_adi,
                "toplam": len(ay_kayitlar),
                "olusturulma": datetime.now(timezone.utc).isoformat(),
            },
            dosya_adi: ay_kayitlar,
        }
        arsiv_dosya.write_text(
            json.dumps(cikti, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"  ✓ Arşiv: {arsiv_dosya.name} ({len(ay_kayitlar)} kayıt)")

def haberler_senkronize(kaynak: dict) -> int:
    """
    haberler.json içindeki raporlar/makaleler/uluslararasi/ekosistem
    koleksiyonlarını ayrı dosyalara yazar (site uyumluluğu için).
    """
    ESLESME = {
        "raporlar":     ("raporlar.json",  "raporlar"),
        "makaleler":    ("makaleler.json", "makaleler"),
        "uluslararasi": ("kuresel.json",   "kuresel"),
        "ekosistem":    ("ekosistem.json", "ekosistem"),
    }
    toplam = 0
    for kaynak_adi, (hedef_dosya, hedef_anahtar) in ESLESME.items():
        liste = kaynak.get(kaynak_adi, [])

        # makaleler: Google News kaynaklı yorum/haber kategorilerini çıkar
        if kaynak_adi == "makaleler":
            liste = [
                m for m in liste
                if not (
                    m.get("kaynak", "") == "Google News" and
                    m.get("kategori", "") in ["Hukuki Yorum", "Yorum / Değerlendirme", "Köşe / Görüş"]
                )
            ]
        from datetime import datetime as _dt, timedelta as _td
        _sinir_h = (_dt.now() - _td(days=180)).strftime("%Y-%m-%d")
        if kaynak_adi not in ("raporlar", "makaleler"):
            liste = [x for x in liste if (x.get("tarih") or "9999") >= _sinir_h or not x.get("tarih")]
        from datetime import datetime as _dt, timedelta as _td
        _sinir_h = (_dt.now() - _td(days=180)).strftime("%Y-%m-%d")
        if kaynak_adi not in ("raporlar", "makaleler"):
            liste = [x for x in liste if (x.get("tarih") or "9999") >= _sinir_h or not x.get("tarih")]
        from datetime import datetime as _dt, timedelta as _td
        _sinir_h = (_dt.now() - _td(days=180)).strftime("%Y-%m-%d")
        if kaynak_adi not in ("raporlar", "makaleler"):
            liste = [x for x in liste if (x.get("tarih") or "9999") >= _sinir_h or not x.get("tarih")]
        liste = liste[:MAX_KAYIT.get(hedef_anahtar, 300)]
        cikti = {
            "meta": {
                "guncelleme": datetime.now(timezone.utc).isoformat(),
                "toplam": len(liste),
            },
            hedef_anahtar: liste,
        }
        Path(hedef_dosya).write_text(
            json.dumps(cikti, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"  ✓ {hedef_dosya}: {len(liste)} kayıt senkronize edildi")
        toplam += len(liste)
    return toplam


# ─── GITHUB'A YÜKLE ───────────────────────────────────────────────────

def github_yaz(dosya_yolu: Path):
    if not GITHUB_TOKEN:
        return
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{dosya_yolu.name}"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Content-Type": "application/json"}
    r = requests.get(url, headers=headers, timeout=15)
    sha = r.json().get("sha") if r.status_code == 200 else None
    icerik = base64.b64encode(dosya_yolu.read_bytes()).decode()
    payload = {
        "message": f"dagitici: {dosya_yolu.name} guncellendi {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        "content": icerik,
    }
    if sha:
        payload["sha"] = sha
    r = requests.put(url, headers=headers, json=payload, timeout=30)
    if r.status_code in (200, 201):
        print(f"    → GitHub: {dosya_yolu.name} yüklendi")
    else:
        print(f"    → GitHub hatası ({r.status_code}): {dosya_yolu.name}")


# ─── ANA AKIŞ ─────────────────────────────────────────────────────────

def dagit(gonder_github=False):
    print("═" * 55)
    print("  ekoloji-izleme.com — Dağıtıcı v2")
    print("═" * 55)

    if not HABERLER_DOSYA.exists():
        print("HATA: haberler.json bulunamadı.")
        sys.exit(1)

    kaynak = json.loads(HABERLER_DOSYA.read_text(encoding="utf-8"))
    haberler     = kaynak.get("haberler", [])
    harita_kayit = kaynak.get("harita_kayitlari", [])
    tum_items    = haberler + harita_kayit

    # Son 48 saatin yeni öğeleri
    sinir = datetime.now(timezone.utc) - timedelta(days=365)
    yeni_items = []
    for h in tum_items:
        tarih_str = h.get("tarih") or ""
        try:
            if "T" in tarih_str:
                t = datetime.fromisoformat(tarih_str.replace("Z", "+00:00"))
            else:
                t = datetime.strptime(tarih_str[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if t >= sinir:
                yeni_items.append(h)
        except Exception:
            yeni_items.append(h)

    print(f"\nİşlenecek: {len(yeni_items)} yeni öğe (son 48 saat)")

    # Kural tabanlı sınıflandır
    siniflar = defaultdict(list)
    belirsizler = []
    for item in yeni_items:
        hedef = kural_siniflandir(item)
        if hedef == "belirsiz":
            belirsizler.append(item)
        else:
            siniflar[hedef].append(item)

    print(f"\nKural sınıflandırma:")
    for k in ["ihlaller", "raporlar", "makaleler", "kuresel", "ekosistem", "haberler"]:
        print(f"  {k:12s}: {len(siniflar[k])}")
    print(f"  {'belirsiz':12s}: {len(belirsizler)}")

    # Belirsizleri Claude'a gönder
    if belirsizler:
        print(f"\nClaude ile {len(belirsizler)} belirsiz öğe sınıflandırılıyor…")
        claude_sonuc = claude_siniflandir(belirsizler)
        for item in belirsizler:
            hedef = claude_sonuc.get(item.get("id",""), "haberler")
            siniflar[hedef].append(item)

    # 1. İhlalleri ayrı dosyaya yaz
    print("\nDosyalar güncelleniyor…")
    toplam_yeni = ihlaller_guncelle(siniflar["ihlaller"])

    # 2. haberler.json: _haber_kat ata + meta güncelle
    haberler_liste = kaynak.get("haberler", [])
    for item in haberler_liste:
        if not item.get("_haber_kat") or item["_haber_kat"] == "?":
            item["_haber_kat"] = haber_kat_tespit(item)
    kaynak["haberler"] = haberler_liste
    kaynak.setdefault("meta", {})["dagitici_calistirma"] = datetime.now(timezone.utc).isoformat()
    HABERLER_DOSYA.write_text(json.dumps(kaynak, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✓ haberler.json: meta güncellendi + _haber_kat atandı")

    # 3. haberler.json koleksiyonlarını ayrı dosyalara senkronize et
    # Aylık arşiv yaz (her ayın 1inde önceki ayı arşivler)
    from datetime import date
    if date.today().day == 1:
        print("\nAylık arşiv yazılıyor…")
        arsiv_yaz(kaynak)

    print("\nKoleksiyonlar senkronize ediliyor…")
    haberler_senkronize(kaynak)

    # 4. Alt-kategori dosyaları yaz
    print("  Alt-kategori dosyaları yazılıyor…")
    kat_gruplari = defaultdict(list)
    for item in haberler_liste:
        kat_gruplari[item["_haber_kat"]].append(item)

    for kat, items in kat_gruplari.items():
        dosya_adi = HABER_KAT_DOSYA.get(kat, "haberler-diger.json")
        yol = Path(dosya_adi)
        cikti = {
            "meta": {"guncelleme": datetime.now(timezone.utc).isoformat(),
                     "kategori": kat, "toplam": len(items)},
            "haberler": items
        }
        yol.write_text(json.dumps(cikti, ensure_ascii=False, indent=2), encoding="utf-8")
        boyut_kb = round(yol.stat().st_size / 1024, 1)
        print(f"    {dosya_adi}: {len(items)} kayıt ({boyut_kb} KB)")

    print(f"  ✓ {len(kat_gruplari)} alt-kategori dosyası yazıldı")

    # 5. GitHub'a yükle
    if gonder_github:
        print("\nGitHub'a yükleniyor…")
        dosyalar = [
            HABERLER_DOSYA, IHLALLER_DOSYA,
            Path("raporlar.json"), Path("makaleler.json"),
            Path("kuresel.json"), Path("ekosistem.json"),
        ]
        for dosya in dosyalar:
            if dosya.exists():
                github_yaz(dosya)
                time.sleep(0.3)

    print(f"\n✓ Dağıtım tamamlandı — {toplam_yeni} yeni ihlal dağıtıldı")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tara",   action="store_true")
    parser.add_argument("--gonder", action="store_true")
    args = parser.parse_args()

    if args.tara:
        print("Tarayıcı başlatılıyor…")
        r = subprocess.run(
            [sys.executable, "tarayici.py"],
            capture_output=True, text=True
        )
        print(r.stdout)
        if r.returncode != 0:
            print("HATA:", r.stderr)
            sys.exit(1)

    dagit(gonder_github=args.gonder)


if __name__ == "__main__":
    main()
