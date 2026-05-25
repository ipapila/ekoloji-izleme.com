#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
direnis_guncelle.py
-------------------
• data.json içindeki mevcut haberlere haber_kategorisi atar
• direniş-ağı için haberler + direnis koleksiyonlarını günceller
• Çalıştırma: python3 direnis_guncelle.py
  (data.json ile aynı klasörde olmalı)
"""

import json, os, random, string, time, re
from pathlib import Path

# ── Yol ─────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
DATA_PATH  = SCRIPT_DIR / "data.json"

# ── ID üretici ──────────────────────────────────────────────────
def uid(prefix="dr"):
    chars = string.ascii_lowercase + string.digits
    return prefix + "-" + "".join(random.choices(chars, k=6)) + str(int(time.time()*1000))[-5:]

# ════════════════════════════════════════════════════════════════
#  9 KATEGORİ TESPİT FONKSİYONU
#  haberler.html ve tarayici.py ile senkronize
# ════════════════════════════════════════════════════════════════

def haber_kategorisi_tespit(kayit: dict) -> str:
    eylem = (kayit.get("eylem") or "").lower()
    kat   = (kayit.get("kategori") or "").lower()
    hkat  = (kayit.get("haber_kategorisi") or "").strip()

    # Zaten atanmışsa değiştirme
    if hkat:
        return hkat

    metin = " ".join([
        kayit.get("baslik", ""),
        kayit.get("ozet", "") or kayit.get("aciklama", ""),
        kayit.get("kategori", ""),
        " ".join(kayit.get("etiketler") or []),
        kayit.get("eylem", ""),
    ]).lower()

    # ── Eylem / mücadele önce ────────────────────────────────────
    if "nöbet & gözaltı" in eylem or any(k in metin for k in
            ["nöbet", "gözaltı", "tutuklama", "biber gazı", "linç", "polis müdahale"]):
        return "Nöbetler ve Gözaltılar"

    if "direniş & eylem" in eylem or any(k in metin for k in
            ["direniş", "direnis", "protesto", "miting", "yürüyüş", "boykot",
             "oturma eylemi", "blokaj", "barış nöbeti", "çadır", "işgal"]):
        return "Direniş ve Eylemler"

    if "stk & kampanya" in eylem or "stk" in kat or any(k in metin for k in
            ["greenpeace", "wwf", "tema vakfı", "doğa derneği", "350.org",
             "kampanya başlat", "imza kampanyası", "sivil toplum", "dernek açıkladı",
             "vakıf raporu", "iklim ağı", "çevre platformu"]):
        return "STK & Kampanyalar"

    if "hukuk & dava" in eylem or any(k in metin for k in
            ["dava açıl", "mahkeme", "yürütmeyi durdur", "iptal kararı",
             "çed kararı", "çed iptali", "ruhsat iptali", "idare mahkemesi",
             "danıştay", "anayasa mahkemesi", "avukat", "hukuki"]):
        return "Hukuki Süreçler"

    # ── Konu bazlı ──────────────────────────────────────────────
    if any(k in metin for k in
            ["iklim", "sel", "yangın", "kuraklık", "hava durumu", "afet",
             "deprem", "fırtına", "sıcak hava", "don", "kar fırtınası"]):
        return "İklim ve Afet"

    if any(k in metin for k in
            ["maden", "madencilik", "enerji santrali", "termik", "nükleer",
             "akkuyu", "res", "ges", "hes", "jeotermal", "mapeg", "epdk",
             "ruhsat", "eti bakır", "siyanür", "kömür", "altın maden"]):
        return "Maden ve Enerji"

    if any(k in metin for k in
            ["orman", "ağaç kesim", "ormansızlaş", "orman yangını",
             "habitat", "flora", "fauna", "ekosistem"]):
        return "Orman ve Doğa"

    if any(k in metin for k in
            ["su kirliliği", "nehir", "göl", "kıyı", "deniz", "marina",
             "sulak alan", "ramsar", "baraj", "taşkın", "dere"]):
        return "Su ve Kıyı"

    if any(k in metin for k in
            ["yaban hayatı", "türün tükenmesi", "nesli tehlike", "kaçak avcılık",
             "kuş", "kurt", "ayı", "vaşak", "kaplumbağa", "yunus"]):
        return "Yaban Hayatı"

    return ""   # tespit edilemedi → "Tüm İçerik"'te görünür


# ════════════════════════════════════════════════════════════════
#  YENİ DİRENİŞ HABERLERİ  (taramadan derlendi – Mayıs 2026)
# ════════════════════════════════════════════════════════════════

YENI_HABERLER = [
    {
        "id": uid("hdr"),
        "baslik": "Zeytinlik yasasına karşı 'Toprağımızı Vermiyoruz' platformu miting düzenledi",
        "ozet": "7554 sayılı zeytinlikleri madenciliğe açan kanuna karşı köylüler ve muhalefet partilerinin desteğiyle kurulan platform Ankara ve İstanbul'da geniş katılımlı mitingler düzenledi.",
        "kaynak": "Cumhuriyet",
        "kaynak_link": "https://www.cumhuriyet.com.tr/cevre/2025-turkiye-sinde-yurttasin-direnisi-surdu-akp-iktidari-ise-dogayi-hice-saydi-yesil-in-mucadelesi-2466390",
        "tarih": "2025-06-01",
        "il": "Ankara",
        "ilce": "Çankaya",
        "koordinatlar": {"lat": 39.91987, "lng": 32.85427},
        "kategori": "Ekolojik İhlal",
        "eylem": "Direniş & Eylem",
        "etiket": "Maden Karşıtı",
        "haber_kategorisi": "Direniş ve Eylemler",
        "kaynak_turu": "haber"
    },
    {
        "id": uid("hdr"),
        "baslik": "Doruk Madencilik işçileri Ankara Kurtuluş Parkı'nda direniş çadırı kurdu",
        "ozet": "Haklarını arayan Doruk Madencilik işçileri Ankara'ya gelerek Kurtuluş Parkı'nda eylem yaptı. Oyuncu, müzisyen ve akademisyenler dayanışma videoları yayınladı.",
        "kaynak": "WSWS",
        "kaynak_link": "https://www.wsws.org/tr/articles/2026/04/24/mine-a24.html",
        "tarih": "2026-04-23",
        "il": "Ankara",
        "ilce": "Çankaya",
        "koordinatlar": {"lat": 39.92847, "lng": 32.86013},
        "kategori": "Ekolojik İhlal",
        "eylem": "Direniş & Eylem",
        "etiket": "İşçi Direnişi",
        "haber_kategorisi": "Direniş ve Eylemler",
        "kaynak_turu": "haber"
    },
    {
        "id": uid("hdr"),
        "baslik": "Şişli'de Taşyapı projesine karşı yurttaşlar aylarca eylem yaptı",
        "ozet": "Şişli'nin 'Kanal İstanbul'u' olarak adlandırılan Taşyapı projesi aylarca süren yurttaş eylemine konu oldu. 24 bin metrekarelik bölge rezerv alan ilan edilerek yapı yükseldi.",
        "kaynak": "Cumhuriyet",
        "kaynak_link": "https://www.cumhuriyet.com.tr/cevre/2025-turkiye-sinde-yurttasin-direnisi-surdu-akp-iktidari-ise-dogayi-hice-saydi-yesil-in-mucadelesi-2466390",
        "tarih": "2025-10-01",
        "il": "İstanbul",
        "ilce": "Şişli",
        "koordinatlar": {"lat": 41.06084, "lng": 28.98659},
        "kategori": "Kıyı İhlalleri",
        "eylem": "Direniş & Eylem",
        "etiket": "Kent Direnişi",
        "haber_kategorisi": "Direniş ve Eylemler",
        "kaynak_turu": "haber"
    },
    {
        "id": uid("hdr"),
        "baslik": "Ünye Çevre Platformu: MAPEG 317. Grup maden ihalesi bölgeyi tehdit ediyor",
        "ozet": "MAPEG'in Nisan 2026'da gerçekleştirdiği ihalede Ünye, İkizce, Kumru ve Çaybaşı ilçelerini kapsayan geniş alanda maden arama faaliyeti ihaleye çıkarıldı. Platform acil açıklama yaptı.",
        "kaynak": "Dokuz8Haber",
        "kaynak_link": "https://www.dokuz8haber.net/unye-cevre-platformundan-maden-ihalelerine-tepki-yasam-alanlarimizi-savunuyoruz",
        "tarih": "2026-04-10",
        "il": "Ordu",
        "ilce": "Ünye",
        "koordinatlar": {"lat": 41.13312, "lng": 37.28134},
        "kategori": "Maden Ocağı",
        "eylem": "Direniş & Eylem",
        "etiket": "Maden Karşıtı",
        "haber_kategorisi": "Direniş ve Eylemler",
        "kaynak_turu": "haber"
    },
    {
        "id": uid("hdr"),
        "baslik": "Günçalı köylüleri Zeni Madencilik'e karşı yürütmeyi durdurma kararı aldırdı",
        "ozet": "Tokat Günçalı köylüleri Çalbaba Ormanı'nda Zeni Madencilik'e verilen maden arama ruhsatına karşı Tokat İdare Mahkemesi'ne açtıkları davada yürütmeyi durdurma kararı elde etti.",
        "kaynak": "Veryansın TV",
        "kaynak_link": "https://www.veryansintv.com/guncalida-maden-projesine-yurutmeyi-durdurma-karari-avukat-atal-emperyalizmin-somurge-madenciligiyle-turksuzlestirme-projesine-karsi-zafer",
        "tarih": "2025-12-13",
        "il": "Tokat",
        "ilce": "Merkez",
        "koordinatlar": {"lat": 40.31381, "lng": 36.55447},
        "kategori": "Maden Ocağı",
        "eylem": "Hukuk & Dava",
        "etiket": "Yürütmeyi Durdurma",
        "haber_kategorisi": "Hukuki Süreçler",
        "kaynak_turu": "haber"
    },
    {
        "id": uid("hdr"),
        "baslik": "Tokat'ta halk direndi, mahkeme durdurdu: Mera komisyonu maden kararı iptal",
        "ozet": "Tokat'ta köylüler mera vasıflı taşınmazlarda maden araması izni veren Valilik onayına karşı idare mahkemesinde kazandı. Mahkeme, maden arama ruhsatı iptal edildiğinden komisyon kararının dayanaksız kaldığını hükmetti.",
        "kaynak": "Cumhuriyet",
        "kaynak_link": "https://www.cumhuriyet.com.tr/turkiye/tokat-ta-halk-direndi-mahkeme-durdurdu-maden-sirketine-sok-karar-2423884",
        "tarih": "2025-08-04",
        "il": "Tokat",
        "ilce": "Merkez",
        "koordinatlar": {"lat": 40.31897, "lng": 36.55921},
        "kategori": "Maden Ocağı",
        "eylem": "Hukuk & Dava",
        "etiket": "Ruhsat İptali",
        "haber_kategorisi": "Hukuki Süreçler",
        "kaynak_turu": "haber"
    },
    {
        "id": uid("hdr"),
        "baslik": "Danıştay kararı: Maden idari yargısında içtihat değişikliği",
        "ozet": "Danıştay İDDK'nın 2025 kararıyla temyiz sınırı altındaki maden idari para cezaları artık Danıştay'da değil bölge idare mahkemelerinde sonuçlanacak. Bu değişiklik 12 ildeki istinaf mahkemelerinde içtihat birliği sorununa yol açabilir.",
        "kaynak": "Madencilik Türkiye",
        "kaynak_link": "https://madencilikturkiye.com/hukuki-gelismelerle-2025-yilinda-madencilik-sektoru/",
        "tarih": "2026-01-02",
        "il": "Ankara",
        "ilce": "Çankaya",
        "koordinatlar": {"lat": 39.90429, "lng": 32.86321},
        "kategori": "Maden Ocağı",
        "eylem": "Hukuk & Dava",
        "etiket": "Yargı Kararı",
        "haber_kategorisi": "Hukuki Süreçler",
        "kaynak_turu": "haber"
    },
    {
        "id": uid("hdr"),
        "baslik": "Zeytinlik yasası Meclis'te görüşülürken köylüler Cemal Süreya Parkı'nda nöbete başladı",
        "ozet": "7554 sayılı yasanın TBMM'de görüşüldüğü günlerde köylüler ve çevre savunucuları Ankara'da Cemal Süreya Parkı'nda nöbet başlattı. Yasa geçmesine karşın nöbet çevre savunuculuğunun önemli bir belgesi oldu.",
        "kaynak": "Cumhuriyet",
        "kaynak_link": "https://www.cumhuriyet.com.tr/cevre/2025-turkiye-sinde-yurttasin-direnisi-surdu-akp-iktidari-ise-dogayi-hice-saydi-yesil-in-mucadelesi-2466390",
        "tarih": "2025-04-01",
        "il": "Ankara",
        "ilce": "Çankaya",
        "koordinatlar": {"lat": 39.92133, "lng": 32.84809},
        "kategori": "Ekolojik İhlal",
        "eylem": "Nöbet & Gözaltı",
        "etiket": "Nöbet",
        "haber_kategorisi": "Nöbetler ve Gözaltılar",
        "kaynak_turu": "haber"
    },
    {
        "id": uid("hdr"),
        "baslik": "Eskişehir'de Doğa ve Yaşam Platformu zeytinlik yasasına karşı 1 saatlik nöbet düzenledi",
        "ozet": "Eskişehir Doğa ve Yaşam Platformu'nun çağrısıyla Yediler Parkı'nda bir araya gelen yurttaşlar zeytinlikleri madenciliğe açan yasa teklifine tepki olarak 1 saat boyunca nöbet tuttu.",
        "kaynak": "Ekoloji Birliği",
        "kaynak_link": "https://ekolojibirligi.org/etiket/heslere-hayir/",
        "tarih": "2025-05-01",
        "il": "Eskişehir",
        "ilce": "Merkez",
        "koordinatlar": {"lat": 39.77441, "lng": 30.52029},
        "kategori": "Ekolojik İhlal",
        "eylem": "Nöbet & Gözaltı",
        "etiket": "Nöbet",
        "haber_kategorisi": "Nöbetler ve Gözaltılar",
        "kaynak_turu": "stk"
    },
    {
        "id": uid("hdr"),
        "baslik": "İklim Ağı 16 STK ile Türkiye'nin 2025 İklim Karnesi'ni açıkladı",
        "ozet": "Greenpeace TR, TEMA, WWF-Türkiye, Doğa Derneği ve 12 diğer STK'den oluşan İklim Ağı 12 maddede 2025 iklim politikalarını değerlendirdi. 2053 stratejisinin fosil yakıtlardan çıkışı içermediği eleştirildi.",
        "kaynak": "Greenpeace Türkiye",
        "kaynak_link": "https://www.greenpeace.org/turkey/raporlar/rapor-turkiyede-vergi-ve-iklim-adaleti/",
        "tarih": "2026-01-01",
        "il": "İstanbul",
        "ilce": "Beyoğlu",
        "koordinatlar": {"lat": 41.03498, "lng": 28.97782},
        "kategori": "İklim Olayları",
        "eylem": "STK & Kampanya",
        "etiket": "İklim Raporu",
        "haber_kategorisi": "STK & Kampanyalar",
        "kaynak_turu": "stk"
    },
    {
        "id": uid("hdr"),
        "baslik": "Greenpeace Türkiye: AB'de yasaklanan tek kullanımlık plastikler Türkiye'de de yasaklansın",
        "ozet": "Greenpeace Türkiye, AB'de yasaklanan tek kullanımlık plastiklerin Türkiye'de de yasaklanması ve Avrupa'dan Türkiye'ye plastik atık gönderiminin son bulması için imza kampanyası başlattı.",
        "kaynak": "Greenpeace Türkiye",
        "kaynak_link": "https://imza.greenpeace.org/",
        "tarih": "2025-09-01",
        "il": "İstanbul",
        "ilce": "Beyoğlu",
        "koordinatlar": {"lat": 41.03212, "lng": 28.97341},
        "kategori": "Ekolojik İhlal",
        "eylem": "STK & Kampanya",
        "etiket": "İmza Kampanyası",
        "haber_kategorisi": "STK & Kampanyalar",
        "kaynak_turu": "stk"
    },
    {
        "id": uid("hdr"),
        "baslik": "TEMA: İklim Kanunu taslağı azaltım ve uyum hedeflerini içermiyor",
        "ozet": "TEMA Vakfı Çevre Politikaları Bölümü, 2025'te yürürlüğe girmesi planlanan İklim Kanunu taslağının gerekli azaltım ve uyum hedeflerini barındırmadığını, sivil toplumun sürece dahil edilmesi gerektiğini duyurdu.",
        "kaynak": "Anadolu Ajansı",
        "kaynak_link": "https://www.aa.com.tr/tr/yesilhat/cevre-hikayeleri/turkiyede-iklim-kriziyle-mucadele-eden-stklerin-kurdugu-iklim-agi-tanitildi/1825060",
        "tarih": "2025-03-01",
        "il": "İstanbul",
        "ilce": "Fatih",
        "koordinatlar": {"lat": 41.00831, "lng": 28.94513},
        "kategori": "İklim Olayları",
        "eylem": "STK & Kampanya",
        "etiket": "Politika Eleştirisi",
        "haber_kategorisi": "STK & Kampanyalar",
        "kaynak_turu": "stk"
    },
]

# ════════════════════════════════════════════════════════════════
#  YENİ GRUPLAR & PLATFORMLAR (direnis koleksiyonu)
# ════════════════════════════════════════════════════════════════

YENI_DIRENIS = [
    {
        "id": uid("grp"),
        "ad": "Toprağımızı Vermiyoruz Platformu",
        "tip": "platform",
        "aciklama": "Zeytinlikleri madenciliğe açan 7554 sayılı kanuna karşı muhalefet partileri ve yurttaşların ortak kurduğu mücadele platformu. Ankara ve İstanbul'da büyük mitingler düzenledi.",
        "il": "Ankara",
        "web": "",
        "instagram": "",
        "twitter": "",
        "eklenme": "2025-06-01"
    },
    {
        "id": uid("grp"),
        "ad": "İklim Ağı",
        "tip": "platform",
        "aciklama": "Greenpeace TR, TEMA, WWF-Türkiye, Doğa Derneği, ClientEarth, 350 Türkiye ve 10 diğer STK'den oluşan 16 üyeli iklim mücadelesi koordinasyon çatısı.",
        "il": "İstanbul",
        "web": "https://www.greenpeace.org/turkey",
        "instagram": "",
        "twitter": "",
        "eklenme": "2025-01-01"
    },
    {
        "id": uid("grp"),
        "ad": "Ünye Çevre Platformu",
        "tip": "platform",
        "aciklama": "Ordu'nun Ünye, İkizce, Kumru ve Çaybaşı ilçelerinde maden ihalelerine karşı mücadele eden yerel çevre platformu.",
        "il": "Ordu",
        "web": "",
        "instagram": "",
        "twitter": "",
        "eklenme": "2026-04-10"
    },
    {
        "id": uid("grp"),
        "ad": "Eskişehir Doğa ve Yaşam Platformu",
        "tip": "platform",
        "aciklama": "Eskişehir'de doğa hakları ve yaşam alanlarını savunan yerel platform. Zeytinlik yasasına karşı nöbet eylemleri örgütledi.",
        "il": "Eskişehir",
        "web": "",
        "instagram": "",
        "twitter": "",
        "eklenme": "2025-05-01"
    },
    {
        "id": uid("grp"),
        "ad": "Ekoloji Birliği",
        "tip": "platform",
        "aciklama": "HES'lere hayır kampanyası ve iklim adaleti konularında çalışan, COP süreçlerini takip eden çevre örgütleri çatı platformu.",
        "il": "İstanbul",
        "web": "https://ekolojibirligi.org",
        "instagram": "",
        "twitter": "",
        "eklenme": "2025-01-01"
    },
    {
        "id": uid("grp"),
        "ad": "Günçalı Köy Girişimi",
        "tip": "grup",
        "aciklama": "Tokat Günçalı köylülerinin Çalbaba Ormanı'nda siyanürlü altın madenciliğine karşı oluşturduğu mücadele girişimi. Tokat İdare Mahkemesi'nden yürütmeyi durdurma kararı aldı.",
        "il": "Tokat",
        "web": "",
        "instagram": "",
        "twitter": "",
        "eklenme": "2025-12-13"
    },
]


# ════════════════════════════════════════════════════════════════
#  ANA FONKSİYON
# ════════════════════════════════════════════════════════════════

def main():
    if not DATA_PATH.exists():
        print(f"✗ {DATA_PATH} bulunamadı — scripti data.json ile aynı klasöre koy.")
        return

    # Yedek al
    yedek = DATA_PATH.with_suffix(".json.bak")
    yedek.write_text(DATA_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"✓ Yedek alındı: {yedek.name}")

    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    # ── Koleksiyon varlık kontrolü ──────────────────────────────
    if isinstance(data, list):
        # Sadece haberler dizisi formatı
        print("⚠ data.json düz dizi formatında — haberler anahtarıyla sarmala")
        data = {"haberler": data}

    if "haberler" not in data:
        data["haberler"] = []
    if "direnis" not in data:
        data["direnis"] = []

    # ── 1. Mevcut haberlere haber_kategorisi ata ────────────────
    atanan = 0
    for h in data["haberler"]:
        if not h.get("haber_kategorisi"):
            sonuc = haber_kategorisi_tespit(h)
            if sonuc:
                h["haber_kategorisi"] = sonuc
                atanan += 1
    print(f"✓ Mevcut haberlere kategori atandı: {atanan} kayıt güncellendi")

    # ── 2. Yeni haberleri ekle (yineleme önleme) ─────────────────
    mevcut_linkler = {h.get("kaynak_link", "") for h in data["haberler"]}
    mevcut_basliklar = {h.get("baslik", "").strip().lower() for h in data["haberler"]}
    eklenen_h = 0
    for yeni in YENI_HABERLER:
        link = yeni.get("kaynak_link", "")
        baslik = yeni.get("baslik", "").strip().lower()
        if link and link in mevcut_linkler:
            continue
        if baslik and baslik in mevcut_basliklar:
            continue
        yeni["id"] = uid("hdr")   # taze ID
        data["haberler"].append(yeni)
        mevcut_linkler.add(link)
        mevcut_basliklar.add(baslik)
        eklenen_h += 1
    print(f"✓ Yeni haber eklendi: {eklenen_h} kayıt")

    # ── 3. Yeni grup/platform kayıtları ─────────────────────────
    mevcut_adlar = {d.get("ad", "").strip().lower() for d in data["direnis"]}
    eklenen_d = 0
    for yeni in YENI_DIRENIS:
        ad = yeni.get("ad", "").strip().lower()
        if ad in mevcut_adlar:
            continue
        yeni["id"] = uid("grp")
        data["direnis"].append(yeni)
        mevcut_adlar.add(ad)
        eklenen_d += 1
    print(f"✓ Yeni grup/platform eklendi: {eklenen_d} kayıt")

    # ── 4. Kaydet ────────────────────────────────────────────────
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*50}")
    print(f"✓ data.json güncellendi")
    print(f"  Toplam haberler : {len(data['haberler'])}")
    print(f"  Toplam direnis  : {len(data['direnis'])}")
    print(f"{'='*50}")
    print("\nArtık direnis-agi.html'de tüm kategoriler dolu görünecek.")
    print("Uygulamayı yeniden başlatmana gerek yok — sayfa data.json'ı anında okur.")


if __name__ == "__main__":
    main()
