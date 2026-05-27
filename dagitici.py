#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dagitici.py — Tarama sonuçlarını 6 hedef JSON dosyasına dağıtır.
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

# ─── AYARLAR ──────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GITHUB_TOKEN      = os.environ.get("GITHUB_TOKEN", "")
REPO_OWNER        = os.environ.get("GITHUB_REPO_OWNER", "ipapila")
REPO_NAME         = os.environ.get("GITHUB_REPO_NAME", "ekoloji-izleme.com")
MODEL             = "claude-haiku-4-5-20251001"

HABERLER_DOSYA = Path("haberler.json")
DATA_JSON_DOSYA = Path("data.json")

def data_json_guncelle(ihlaller: list):
    mevcut = {}
    if DATA_JSON_DOSYA.exists():
        try:
            mevcut = json.loads(DATA_JSON_DOSYA.read_text(encoding="utf-8"))
        except Exception:
            pass
    mevcut["ihlaller"] = ihlaller
    if "_meta" not in mevcut:
        mevcut["_meta"] = {}
    mevcut["_meta"]["guncelleme"] = datetime.now(timezone.utc).isoformat()
    mevcut["_meta"]["ihlal_sayisi"] = len(ihlaller)
    DATA_JSON_DOSYA.write_text(json.dumps(mevcut, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✓ data.json: ihlaller güncellendi ({len(ihlaller)} kayıt)")

HEDEFLER = {
    "ihlaller":  Path("ihlaller.json"),
    "raporlar":  Path("raporlar.json"),
    "makaleler": Path("makaleler.json"),
    "kuresel":   Path("kuresel.json"),
    "ekosistem": Path("ekosistem.json"),
    "haberler":  Path("haberler.json"),
}

MAX_KAYIT = {
    "ihlaller":  500,
    "raporlar":  300,
    "makaleler": 300,
    "kuresel":   300,
    "ekosistem": 300,
    "haberler":  500,
}

KURALLAR = [
    ("ihlaller", [
        "hayvan istismarı", "hayvan hakları ihlal", "itlaf", "hayvan dövüşü",
        "hayvanat bahçesi", "endüstriyel hayvancılık", "kümes hayvanı",
        "hayvan ölümü", "toplu katliam hayvan",
        "insan hakları ihlal", "gözaltı", "tutuklama", "işkence",
        "zorla kaybetme", "toplu tutuklama", "ifade özgürlüğü ihlal",
        "basın özgürlüğü ihlal",
        "maden ruhsatı", "maden işletme", "maden arama ruhsat",
        "üretim lisansı", "enerji lisansı", "RES lisans", "GES lisans", "HES lisans",
        "jeotermal lisans", "termik santral lisans", "petrol arama ruhsat",
        "ÇED olumlu", "ÇED gerekli değil", "ÇED muafiyet",
        "orman izni verildi", "orman arazisi tahsis", "2634 sayılı",
        "acele kamulaştırma kararı", "kamulaştırma kararnamesi",
        "kamu yararı kararı", "resmî gazete karar",
        "MAPEG", "EPDK karar", "KİK ihale enerji", "KİK ihale maden",
        "Akkuyu", "nükleer santral lisans",
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
        "rapor yayımlandı", "araştırma raporu", "izleme raporu",
        "dava açıldı", "mahkeme kararı", "yürütmeyi durdurma",
        "iptal davası", "itiraz edildi", "temyiz",
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

def kural_siniflandir(item: dict) -> str:
    metin = (
        (item.get("baslik") or "") + " " +
        (item.get("ozet") or "") + " " +
        (item.get("kategori") or "")
    ).lower()

    kaynak_turu = item.get("kaynak_turu", "")
    kategori    = (item.get("kategori") or "").lower()

    if kaynak_turu == "harita":
        return "ihlaller"

    if kategori in ["çevre ihlali", "hed / res / baraj", "kamulaştırma", "çed kararları", "orman / maden"]:
        return "ihlaller"
    if kategori in ["stk"]:
        return "raporlar"
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


def dosya_oku(yol: Path, anahtar: str) -> list:
    if not yol.exists():
        return []
    try:
        veri = json.loads(yol.read_text(encoding="utf-8"))
        if isinstance(veri, list):
            return veri
        return veri.get(anahtar, veri.get("haberler", veri.get("items", [])))
    except Exception:
        return []

def dosya_yaz(yol: Path, yeni_items: list, hedef_adi: str, mevcut: list):
    mevcut_idler = {i.get("id","") for i in mevcut}
    eklenecek = [i for i in yeni_items if i.get("id","") not in mevcut_idler]

    birlesik = eklenecek + mevcut
    birlesik.sort(key=lambda x: x.get("tarih") or "1970", reverse=True)
    birlesik = birlesik[:MAX_KAYIT[hedef_adi]]

    if hedef_adi == "ihlaller":
        for item in birlesik:
            if not item.get("kaynak_url") and item.get("url"):
                item["kaynak_url"] = item["url"]

    cikti = {
        "meta": {
            "guncelleme": datetime.now(timezone.utc).isoformat(),
            "toplam": len(birlesik),
            "yeni_eklenen": len(eklenecek),
        },
        hedef_adi: birlesik,
    }
    if hedef_adi == "haberler":
        cikti["haberler"] = cikti.pop(hedef_adi)

    yol.write_text(json.dumps(cikti, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✓ {yol.name}: {len(birlesik)} kayıt ({len(eklenecek)} yeni)")
    return len(eklenecek)


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


def dagit(gonder_github=False):
    print("═" * 55)
    print("  ekoloji-izleme.com — Dağıtıcı v1")
    print("═" * 55)

    if not HABERLER_DOSYA.exists():
        print("HATA: haberler.json bulunamadı. Önce tarayici.py çalıştır.")
        sys.exit(1)

    kaynak = json.loads(HABERLER_DOSYA.read_text(encoding="utf-8"))
    haberler     = kaynak.get("haberler", [])
    harita_kayit = kaynak.get("harita_kayitlari", [])
    tum_items    = haberler + harita_kayit

    sinir = datetime.now(timezone.utc) - timedelta(hours=48)
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

    siniflar = {k: [] for k in HEDEFLER}
    belirsizler = []

    for item in yeni_items:
        hedef = kural_siniflandir(item)
        if hedef == "belirsiz":
            belirsizler.append(item)
        else:
            siniflar[hedef].append(item)

    print(f"\nKural sınıflandırma:")
    for k, v in siniflar.items():
        print(f"  {k:12s}: {len(v)}")
    print(f"  {'belirsiz':12s}: {len(belirsizler)}")

    if belirsizler:
        print(f"\nClaude ile {len(belirsizler)} belirsiz öğe sınıflandırılıyor…")
        claude_sonuc = claude_siniflandir(belirsizler)
        for item in belirsizler:
            hedef = claude_sonuc.get(item["id"], "haberler")
            if hedef in siniflar:
                siniflar[hedef].append(item)
            else:
                siniflar["haberler"].append(item)

    print("\nDosyalar güncelleniyor…")
    toplam_yeni = 0
    for hedef_adi, dosya in HEDEFLER.items():
        if hedef_adi == "haberler":
            continue
        mevcut = dosya_oku(dosya, hedef_adi)
        n = dosya_yaz(dosya, siniflar[hedef_adi], hedef_adi, mevcut)
        toplam_yeni += n

    # data.json güncelle (ihlaller.html buradan okuyor)
    ihlaller_mevcut = dosya_oku(HEDEFLER["ihlaller"], "ihlaller")
    data_json_guncelle(ihlaller_mevcut)

    # haberler.json meta güncelle
    kaynak["meta"]["dagitici_calistirma"] = datetime.now(timezone.utc).isoformat()
    HABERLER_DOSYA.write_text(json.dumps(kaynak, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✓ haberler.json: meta güncellendi")

    # 5. GitHub'a yükle
    if gonder_github:
        print("\nGitHub'a yükleniyor…")
        for hedef_adi, dosya in HEDEFLER.items():
            if dosya.exists():
                github_yaz(dosya)
                time.sleep(0.3)
        # data.json ayrıca gönder
        if DATA_JSON_DOSYA.exists():
            github_yaz(DATA_JSON_DOSYA)
            time.sleep(0.3)

    print(f"\n✓ Dağıtım tamamlandı — {toplam_yeni} yeni öğe dağıtıldı")


def main():
    parser = argparse.ArgumentParser(description="Tarama sonuçlarını 6 JSON dosyasına dağıt")
    parser.add_argument("--tara",   action="store_true", help="Önce tarayici.py çalıştır")
    parser.add_argument("--gonder", action="store_true", help="GitHub'a yükle")
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
