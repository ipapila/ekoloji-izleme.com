#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rapor_uret.py — Günlük Bütünleşik Değerlendirme Raporu
Yerel rapor.json ve gunluk-raporlar.json yazar.
GitHub commit + Plesk gönderimi workflow tarafından yapılır.
"""

import json
import os
import time
import requests
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path

REPO_OWNER     = os.environ.get("GITHUB_REPO_OWNER", "ipapila")
REPO_NAME      = os.environ.get("GITHUB_REPO_NAME",  "ekoloji-izleme.com")
HABERLER_YEREL = Path("haberler.json")
IHLALLER_YEREL = Path("ihlaller.json")
ARSIV_YEREL    = Path("gunluk-raporlar.json")
HABERLER_URL   = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/haberler.json"
DATA_URL       = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/ihlaller.json"
ARSIV_URL      = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/gunluk-raporlar.json"
SON_SAAT       = 24   # Günde tek rapor (17:00 TSİ), son 24 saatin verileri
ARSIV_MAKS     = 1000
TR_SAAT      = ZoneInfo("Europe/Istanbul")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL      = "claude-haiku-4-5-20251001"
MAX_TOKENS = 1800


# ─── 1. VERİ ÇEKME ────────────────────────────────────────────────────

def _json_cek(url):
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"⚠  {url} cekilemedi: {e}")
        return None


def son_n_saat_haberleri():
    if HABERLER_YEREL.exists():
        try:
            veri = json.loads(HABERLER_YEREL.read_text(encoding="utf-8"))
            print("  yerel haberler.json okundu")
        except Exception:
            veri = _json_cek(HABERLER_URL)
    else:
        veri = _json_cek(HABERLER_URL)
    if not veri:
        return []
    haberler = veri.get("haberler", []) if isinstance(veri, dict) else veri
    sinir = datetime.now(timezone.utc) - timedelta(hours=SON_SAAT)
    yeni = []
    for h in haberler:
        tarih_str = h.get("tarih") or h.get("date") or ""
        try:
            if "T" in tarih_str:
                t = datetime.fromisoformat(tarih_str.replace("Z", "+00:00"))
            else:
                t = datetime.strptime(tarih_str[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if t >= sinir:
                yeni.append(h)
        except Exception:
            yeni.append(h)  # tarih parse edilemezse dahil et
    print(f"Son {SON_SAAT} saatte {len(yeni)} haber, toplam {len(haberler)} kayit")
    return yeni


def son_n_saat_ihlalleri():
    if IHLALLER_YEREL.exists():
        try:
            veri = json.loads(IHLALLER_YEREL.read_text(encoding="utf-8"))
            print("  yerel ihlaller.json okundu")
        except Exception:
            veri = _json_cek(DATA_URL)
    else:
        veri = _json_cek(DATA_URL)
    if not veri:
        return []
    ihlaller = veri if isinstance(veri, list) else veri.get("ihlaller", [])
    sinir = datetime.now(timezone.utc) - timedelta(hours=SON_SAAT)
    yeni = []
    for ih in ihlaller:
        tarih_str = ih.get("tarih") or ih.get("eklenme") or ""
        try:
            t = datetime.strptime(tarih_str[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if t >= sinir:
                yeni.append(ih)
        except Exception:
            yeni.append(ih)  # tarih parse edilemezse dahil et
    print(f"Son {SON_SAAT} saatte {len(yeni)} ihlal kaydi")
    return yeni


# ─── 2. RAPOR ÜRETME ──────────────────────────────────────────────────

SISTEM_PROMPT = """Sen ekoloji-izleme.com adlı Türkiye'nin çevre tahribatını belgeleyen bağımsız bir izleme platformunun günlük rapor yazarısın.

Senin perspektifin bütünleşik bir mücadele anlayışına dayanır: sosyalist, feminist, ekolojik, iklim aktivisti, hayvan hakları savunucusu ve insan hakları perspektiflerini birbirinden kopuk değil, tek ve tutarlı bir siyasi-etik tutum olarak kullanırsın. Bu bakış açılarını ayrı başlıklar altında sıralamaz, her cümleye sindirmiş olarak yazarsın.

Üslup:
- Doğrudan, sade, keskin — akademik jargonsuz
- Verilerden somut çıkarımlar yap, soyut kalmaktan kaçın
- Öfkeli değil, berrak ol — gerçekler yeterince konuşur
- Kısa paragraflar, nefes alan bir ritim
- Türkçe

Yapı:
1. Bugün ne oldu — somut sayılar ve olgular
2. Bu veriler ne anlama geliyor — bütünleşik yorum
3. Yarına bakış — hangi gelişmeler yakından izlenmeli

Uzunluk: 350-450 kelime arası. JSON formatında döndür."""

KULLANICI_SABLONU = """Bugünkü tarih: {bugun}

Son {son_saat} saatte sistemimizin topladığı veriler:

=== HABERLER ({haber_sayisi} kayıt) ===
{haberler_ozet}

=== İHLAL KAYITLARI ({ihlal_sayisi} kayıt) ===
{ihlaller_ozet}

Yanıtı YALNIZCA şu JSON formatında ver, başka hiçbir şey ekleme:
{{
  "baslik": "kısa çarpıcı başlık",
  "giris": "birinci paragraf — bugün ne oldu",
  "yorum": "ikinci paragraf — bütünleşik analiz",
  "bakia": "üçüncü paragraf — yarına bakış",
  "veri_ozet": {{
    "haber_sayisi": {haber_sayisi},
    "ihlal_sayisi": {ihlal_sayisi},
    "one_cikan_kategoriler": []
  }}
}}"""


def _haber_ozet(haberler, maks=15):
    if not haberler:
        return "(bu periyotta yeni haber tespit edilmedi)"
    satirlar = []
    for h in haberler[:maks]:
        baslik   = h.get("baslik") or h.get("title") or "—"
        kaynak   = h.get("kaynak") or h.get("source") or ""
        kategori = h.get("kategori") or ""
        satirlar.append(f"- [{kategori}] {baslik} ({kaynak})")
    return "\n".join(satirlar)


def _ihlal_ozet(ihlaller, maks=10):
    if not ihlaller:
        return "(bu periyotta yeni ihlal kaydı girilmedi)"
    satirlar = []
    for ih in ihlaller[:maks]:
        ad  = ih.get("ad") or ih.get("isim") or "—"
        il  = ih.get("il") or ""
        tip = ih.get("tip") or ih.get("kategori") or ""
        satirlar.append(f"- [{tip}] {ad} — {il}")
    return "\n".join(satirlar)


def rapor_uret(haberler, ihlaller):
    if not ANTHROPIC_API_KEY:
        print("ANTHROPIC_API_KEY yok, rapor uretilemedi.")
        return _bos_rapor()

    kategoriler = {}
    for h in haberler:
        k = h.get("kategori") or h.get("etiket") or "Diger"
        kategoriler[k] = kategoriler.get(k, 0) + 1
    for ih in ihlaller:
        k = ih.get("tip") or "Diger"
        kategoriler[k] = kategoriler.get(k, 0) + 1
    one_cikanlar = sorted(kategoriler, key=lambda x: -kategoriler[x])[:4]

    kullanici = KULLANICI_SABLONU.format(
        bugun         = datetime.now(timezone.utc).strftime("%d %B %Y"),
        son_saat      = SON_SAAT,
        haber_sayisi  = len(haberler),
        ihlal_sayisi  = len(ihlaller),
        haberler_ozet = _haber_ozet(haberler),
        ihlaller_ozet = _ihlal_ozet(ihlaller),
    )

    MAKS_DENEME = 3
    BEKLEME_SANIYE = [5, 15]  # denemeler arasi bekleme (son deneme sonrasi beklenmez)
    son_hata = None

    for deneme in range(1, MAKS_DENEME + 1):
        try:
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key":         ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type":      "application/json",
                },
                json={
                    "model":      MODEL,
                    "max_tokens": MAX_TOKENS,
                    "system":     SISTEM_PROMPT,
                    "messages":   [{"role": "user", "content": kullanici}],
                },
                timeout=60,
            )
            if r.status_code in (429, 500, 502, 503, 529) and deneme < MAKS_DENEME:
                bekleme = BEKLEME_SANIYE[deneme - 1]
                print(f"Claude API {r.status_code} (gecici) — {deneme}. deneme basarisiz, {bekleme}sn sonra tekrar denenecek")
                time.sleep(bekleme)
                continue
            if r.status_code >= 400:
                # raise_for_status() sadece durum kodunu iceren kisa bir mesaj uretir;
                # asil hata nedeni (invalid_request_error mesaji vb.) govdede yer alir.
                print(f"Claude API {r.status_code} yanit govdesi: {r.text[:2000]}")
            r.raise_for_status()
            metin = r.json()["content"][0]["text"].strip()
            if metin.startswith("```"):
                metin = metin.split("```")[1]
                if metin.startswith("json"):
                    metin = metin[4:]
            rapor = json.loads(metin.strip())
            rapor["uretildi"] = datetime.now(timezone.utc).isoformat()
            rapor.setdefault("veri_ozet", {})["one_cikan_kategoriler"] = one_cikanlar
            print(f"Rapor uretildi ({deneme}. denemede)")
            return rapor
        except Exception as e:
            son_hata = e
            if deneme < MAKS_DENEME:
                bekleme = BEKLEME_SANIYE[deneme - 1]
                print(f"Claude API hatasi ({deneme}. deneme): {e} — {bekleme}sn sonra tekrar denenecek")
                time.sleep(bekleme)
            else:
                print(f"Claude API hatasi ({deneme}. deneme, son): {e}")

    print(f"UYARI: {MAKS_DENEME} denemenin tumu basarisiz oldu, hata raporu yazilacak. Son hata: {son_hata}")
    return _bos_rapor()


def _bos_rapor():
    return {
        "baslik": "Günlük Rapor Üretilemedi",
        "giris":  "Sistem bugün rapor oluşturamadı.",
        "yorum":  "",
        "bakia":  "",
        "veri_ozet": {"haber_sayisi": 0, "ihlal_sayisi": 0, "one_cikan_kategoriler": []},
        "uretildi": datetime.now(timezone.utc).isoformat(),
        "hata": True,
    }


# ─── 3. ARŞİV GÜNCELLE ────────────────────────────────────────────────

def arsiv_girisi_olustur(rapor):
    simdi     = datetime.now(TR_SAAT)
    tarih_str = simdi.strftime("%Y-%m-%d")
    saat_str  = simdi.strftime("%H:%M")
    uretildi  = rapor.get("uretildi", datetime.now(timezone.utc).isoformat())
    vo = rapor.get("veri_ozet", {})
    one_cikan = ", ".join(vo.get("one_cikan_kategoriler", [])[:3])
    return {
        "id":          f"gunluk-{tarih_str}",  # gün başına tek rapor; aynı gün tekrar çalışırsa üzerine yazar
        "baslik":      rapor.get("baslik", "Günlük Rapor"),
        "kaynak":      "ekoloji-izleme.com",
        "kategori":    "Günlük Rapor",
        "etiket":      "Günlük Rapor",
        "tarih":       tarih_str,
        "saat":        saat_str,
        "uretildi":    uretildi,
        "ozet":        rapor.get("giris", ""),
        "giris":       rapor.get("giris", ""),
        "yorum":       rapor.get("yorum", ""),
        "bakia":       rapor.get("bakia", ""),
        "icerik_tipi": "rapor",
        "etiketler":   [one_cikan] if one_cikan else [],
        "veri_ozet":   vo,
        "hata":        rapor.get("hata", False),
    }


def arsiv_guncelle(rapor):
    mevcut = []
    if ARSIV_YEREL.exists():
        try:
            mevcut = json.loads(ARSIV_YEREL.read_text(encoding="utf-8"))
            if not isinstance(mevcut, list):
                mevcut = mevcut.get("raporlar", [])
        except Exception as e:
            print(f"  arşiv okunamadı: {e}")
    else:
        uzak = _json_cek(ARSIV_URL)
        if uzak:
            mevcut = uzak if isinstance(uzak, list) else uzak.get("raporlar", [])

    yeni_giris = arsiv_girisi_olustur(rapor)
    mevcut = [x for x in mevcut if x.get("id") != yeni_giris["id"]]
    mevcut = [yeni_giris] + mevcut
    mevcut = mevcut[:ARSIV_MAKS]

    ARSIV_YEREL.write_text(
        json.dumps(mevcut, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Arşive eklendi: {yeni_giris['id']} — toplam {len(mevcut)} rapor")
    return mevcut


# ─── 4. YEREL YAZ ─────────────────────────────────────────────────────

def yerel_yaz(rapor):
    Path("rapor.json").write_text(
        json.dumps(rapor, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("rapor.json yerel yazıldı")


# ─── 5. ANA AKIŞ ──────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"=== Gunluk Rapor Uretimi — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} ===")
    haberler = son_n_saat_haberleri()
    ihlaller = son_n_saat_ihlalleri()
    rapor    = rapor_uret(haberler, ihlaller)
    arsiv    = arsiv_guncelle(rapor)
    yerel_yaz(rapor)
    if rapor.get("hata"):
        print("=== Tamamlandi (HATA: rapor icerigi uretilemedi, bos rapor arsivlendi) ===")
    else:
        print("=== Tamamlandi ===")
