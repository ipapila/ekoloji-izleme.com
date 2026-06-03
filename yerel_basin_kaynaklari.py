#!/usr/bin/env python3
"""
tarayici.py'ye eklenecek yerel basın kaynakları.
RSS_KAYNAKLARI listesinin sonuna ekleyin.

Strateji:
  1. Doğrudan RSS'i olan yerel gazeteler (güvenilir)
  2. Google News site: sorguları ile yerel gazeteler (geniş kapsam)
  3. Google News il adı + çevre anahtar kelime sorguları (yedek)

7 coğrafi bölge + özel sektör haberleri kapsanıyor.
"""

# ══════════════════════════════════════════════════════════════════
#  YEREL BASIN — KARADENİZ BÖLGESİ
#  (HES, maden, orman, kamulaştırma açısından kritik bölge)
#  İller: Zonguldak, Bartın, Karabük, Kastamonu, Sinop, Samsun,
#         Ordu, Giresun, Trabzon, Rize, Artvin
# ══════════════════════════════════════════════════════════════════

YEREL_KARADENIZ = [
    # Doğrudan RSS
    {"url": "https://www.rizeninsesi.net/rss",
     "kaynak": "Rize'nin Sesi", "kategori": "Yerel / Karadeniz",
     "genel": True, "hedef": "haberler", "dil": "tr"},

    # Google News site: sorguları — yerel gazeteler
    {"url": "https://news.google.com/rss/search?q=site:gunebakis.com.tr+(çevre+OR+maden+OR+orman+OR+HES+OR+kamulaştırma)&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Günebakış (Trabzon)", "kategori": "Yerel / Karadeniz",
     "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:karadenizdesonnokta.com.tr+(çevre+OR+maden+OR+orman+OR+HES)&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Karadeniz'de Son Nokta", "kategori": "Yerel / Karadeniz",
     "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:aciksoz.com.tr+(çevre+OR+maden+OR+orman+OR+HES+OR+kamulaştırma)&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Açıksöz (Kastamonu)", "kategori": "Yerel / Karadeniz",
     "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:gazeterize.com+(çevre+OR+maden+OR+HES+OR+RES+OR+orman)&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Gazete Rize", "kategori": "Yerel / Karadeniz",
     "genel": False, "hedef": "haberler", "dil": "tr"},

    # Google News il bazlı çevre sorguları
    {"url": "https://news.google.com/rss/search?q=Zonguldak+maden+çevre+OR+kömür+OR+işçi+OR+ocak&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Yerel / Zonguldak",
     "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Artvin+maden+OR+HES+OR+orman+OR+kamulaştırma+çevre&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Yerel / Artvin",
     "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Rize+OR+Trabzon+OR+Giresun+OR+Ordu+OR+Samsun+maden+OR+HES+OR+taş+ocağı+çevre+ihlal&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Yerel / Karadeniz",
     "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Kastamonu+OR+Sinop+OR+Bartın+OR+Karabük+maden+OR+çevre+OR+orman+OR+kamulaştırma&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Yerel / Batı Karadeniz",
     "genel": False, "hedef": "haberler", "dil": "tr"},
]

# ══════════════════════════════════════════════════════════════════
#  YEREL BASIN — EGE BÖLGESİ
#  (Kaz Dağları, Aliağa, zeytinlik, termik santral, GES)
#  İller: İzmir, Manisa, Aydın, Denizli, Muğla, Afyon, Kütahya, Uşak
# ══════════════════════════════════════════════════════════════════

YEREL_EGE = [
    # Doğrudan RSS — Yeni Asır İzmir kategorisi
    {"url": "https://www.yeniasir.com.tr/rss/Anasayfa.xml",
     "kaynak": "Yeni Asır (İzmir)", "kategori": "Yerel / Ege",
     "genel": True, "hedef": "haberler", "dil": "tr"},

    # Google News site: sorguları
    {"url": "https://news.google.com/rss/search?q=site:egedesonsoz.com+(çevre+OR+maden+OR+termik+OR+GES+OR+kamulaştırma)&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Ege'de Sonsöz (İzmir)", "kategori": "Yerel / Ege",
     "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:muglagazetesi.com.tr+(çevre+OR+maden+OR+Akbelen+OR+Yatağan+OR+kamulaştırma)&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Muğla Gazetesi", "kategori": "Yerel / Muğla",
     "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=site:muglayenigun.com+(çevre+OR+maden+OR+Akbelen+OR+orman)&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Muğla Yenigün", "kategori": "Yerel / Muğla",
     "genel": False, "hedef": "haberler", "dil": "tr"},

    # Google News il bazlı
    {"url": "https://news.google.com/rss/search?q=İzmir+Aliağa+OR+Bergama+OR+Foça+çevre+OR+termik+OR+kirlilik+OR+maden&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Yerel / İzmir",
     "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Muğla+Akbelen+OR+Yatağan+OR+Milas+OR+Ula+çevre+OR+maden+OR+orman&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Yerel / Muğla",
     "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Manisa+OR+Aydın+OR+Denizli+çevre+OR+maden+OR+termik+OR+GES+OR+kamulaştırma+ihlal&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Yerel / Ege",
     "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Kaz+Dağları+OR+İda+çevre+maden+OR+altın+OR+kamulaştırma&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Yerel / Kaz Dağları",
     "genel": False, "hedef": "haberler", "dil": "tr"},
]

# ══════════════════════════════════════════════════════════════════
#  YEREL BASIN — AKDENİZ BÖLGESİ
#  (Kıyı tahribatı, turizm baskısı, GES, maden)
#  İller: Antalya, Mersin, Adana, Hatay, Isparta, Burdur
# ══════════════════════════════════════════════════════════════════

YEREL_AKDENIZ = [
    {"url": "https://news.google.com/rss/search?q=Antalya+çevre+OR+kıyı+OR+maden+OR+GES+OR+kamulaştırma+OR+orman+ihlal&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Yerel / Antalya",
     "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Mersin+OR+Adana+çevre+OR+termik+OR+maden+OR+kirlilik+OR+kamulaştırma&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Yerel / Akdeniz",
     "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Hatay+çevre+OR+maden+OR+orman+OR+sel+OR+kirlilik+&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Yerel / Hatay",
     "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Isparta+OR+Burdur+OR+Kahramanmaraş+çevre+OR+maden+OR+orman+OR+kamulaştırma&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Yerel / Akdeniz",
     "genel": False, "hedef": "haberler", "dil": "tr"},
]

# ══════════════════════════════════════════════════════════════════
#  YEREL BASIN — MARMARA BÖLGESİ
#  (Sanayi kirliliği, kıyı, trafik kirliliği, Trakya maden)
#  İller: İstanbul, Bursa, Kocaeli, Sakarya, Tekirdağ,
#         Çanakkale, Balıkesir, Edirne, Kırklareli
# ══════════════════════════════════════════════════════════════════

YEREL_MARMARA = [
    {"url": "https://news.google.com/rss/search?q=Çanakkale+çevre+OR+maden+OR+altın+OR+Kaz+Dağları+OR+kamulaştırma&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Yerel / Çanakkale",
     "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Kocaeli+OR+Bursa+OR+İzmit+çevre+OR+sanayi+kirliliği+OR+hava+kirliliği+OR+kimyasal&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Yerel / Marmara",
     "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Tekirdağ+OR+Edirne+OR+Kırklareli+çevre+OR+maden+OR+GES+OR+kamulaştırma+OR+tarım&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Yerel / Trakya",
     "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Balıkesir+çevre+OR+maden+OR+GES+OR+RES+OR+termik+OR+kamulaştırma&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Yerel / Balıkesir",
     "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=İstanbul+çevre+OR+kanal+OR+dolgu+OR+orman+OR+yeşil+alan+OR+kirlilik+ihlal&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Yerel / İstanbul",
     "genel": False, "hedef": "haberler", "dil": "tr"},
]

# ══════════════════════════════════════════════════════════════════
#  YEREL BASIN — İÇ ANADOLU BÖLGESİ
#  (Tuz Gölü, maden, tarım arazisi)
#  İller: Ankara, Konya, Eskişehir, Kayseri, Sivas,
#         Çorum, Yozgat, Aksaray, Nevşehir, Niğde, Kırıkkale
# ══════════════════════════════════════════════════════════════════

YEREL_IC_ANADOLU = [
    {"url": "https://news.google.com/rss/search?q=Ankara+çevre+OR+maden+OR+bor+OR+kömür+OR+hava+kirliliği+OR+kamulaştırma&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Yerel / Ankara",
     "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Konya+OR+Eskişehir+çevre+OR+Tuz+Gölü+OR+maden+OR+kamulaştırma+OR+tarım&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Yerel / İç Anadolu",
     "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Kayseri+OR+Sivas+OR+Çorum+çevre+OR+maden+OR+manyezit+OR+kamulaştırma&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Yerel / İç Anadolu",
     "genel": False, "hedef": "haberler", "dil": "tr"},
]

# ══════════════════════════════════════════════════════════════════
#  YEREL BASIN — DOĞU VE GÜNEYDOĞU ANADOLU
#  (Maden, baraj, HES, tarım, sulak alan)
#  İller: Diyarbakır, Şanlıurfa, Mardin, Batman, Siirt, Şırnak,
#         Van, Bitlis, Hakkari, Muş, Bingöl, Elazığ, Malatya,
#         Erzurum, Erzincan, Kars, Ardahan, Iğdır, Ağrı, Tunceli
# ══════════════════════════════════════════════════════════════════

YEREL_DOGU_GUNEYDOGU = [
    {"url": "https://news.google.com/rss/search?q=Diyarbakır+OR+Şanlıurfa+OR+Mardin+çevre+OR+maden+OR+HES+OR+baraj+OR+Fırat+OR+Dicle&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Yerel / Güneydoğu",
     "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Van+OR+Bitlis+OR+Muş+OR+Hakkari+çevre+OR+maden+OR+HES+OR+baraj+OR+orman&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Yerel / Doğu",
     "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Erzurum+OR+Erzincan+OR+Kars+OR+Ardahan+çevre+OR+maden+OR+HES+OR+orman+OR+kamulaştırma&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Yerel / Kuzeydoğu",
     "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Elazığ+OR+Malatya+OR+Bingöl+OR+Tunceli+çevre+OR+maden+OR+HES+OR+kamulaştırma&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Yerel / Doğu Anadolu",
     "genel": False, "hedef": "haberler", "dil": "tr"},
    {"url": "https://news.google.com/rss/search?q=Batman+OR+Siirt+OR+Şırnak+çevre+OR+maden+OR+petrol+OR+boru+hattı+OR+kirlilik&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Yerel / Güneydoğu",
     "genel": False, "hedef": "haberler", "dil": "tr"},
]

# ══════════════════════════════════════════════════════════════════
#  YEREL BASIN — ORTA KARADENİZ / ORTA ANADOLU GEÇİŞ
#  İller: Amasya, Tokat, Çorum, Samsun (iç), Çankırı
# ══════════════════════════════════════════════════════════════════

YEREL_ORTA = [
    {"url": "https://news.google.com/rss/search?q=Amasya+OR+Tokat+OR+Çankırı+çevre+OR+maden+OR+orman+OR+HES+OR+kamulaştırma&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Yerel / Orta",
     "genel": False, "hedef": "haberler", "dil": "tr"},
]

# ══════════════════════════════════════════════════════════════════
#  YEREL BASIN — ÖZEL SEKTÖR / SEKTÖREL
#  Maden sektörü, enerji, çevre ihlali raporlama
# ══════════════════════════════════════════════════════════════════

YEREL_SEKTOREL = [
    # Gazete Duvar — bölgesel çevre haberciliği güçlü
    {"url": "https://www.gazeteduvar.com.tr/feeds/rss",
     "kaynak": "Gazete Duvar", "kategori": "Çevre / Gündem",
     "genel": True, "hedef": "haberler", "dil": "tr"},
    # Bianet bölgesel haberler
    {"url": "https://news.google.com/rss/search?q=site:bianet.org+(yerel+OR+bölge+OR+köy+OR+ilçe)+çevre+OR+maden+OR+HES&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Bianet Bölgesel", "kategori": "Yerel / Çevre",
     "genel": False, "hedef": "haberler", "dil": "tr"},
    # Sendika.org — işçi ve çevre haberleri
    {"url": "https://news.google.com/rss/search?q=site:sendika.org+(maden+OR+çevre+OR+işçi+OR+termik)&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Sendika.org", "kategori": "Yerel / Emek-Çevre",
     "genel": False, "hedef": "haberler", "dil": "tr"},
    # Maden kazaları ve işçi hakları
    {"url": "https://news.google.com/rss/search?q=maden+kazası+OR+maden+işçisi+OR+ocak+patlaması+Türkiye&hl=tr&gl=TR&ceid=TR:tr",
     "kaynak": "Google News", "kategori": "Yerel / Maden Kazası",
     "genel": False, "hedef": "haberler", "dil": "tr"},
]

# ══════════════════════════════════════════════════════════════════
#  TÜMÜNÜ BİRLEŞTİREN LİSTE
#  tarayici.py'de RSS_KAYNAKLARI'na eklenecek
# ══════════════════════════════════════════════════════════════════

YEREL_BASIN_TUM = (
    YEREL_KARADENIZ +
    YEREL_EGE +
    YEREL_AKDENIZ +
    YEREL_MARMARA +
    YEREL_IC_ANADOLU +
    YEREL_DOGU_GUNEYDOGU +
    YEREL_ORTA +
    YEREL_SEKTOREL
)

if __name__ == "__main__":
    print(f"Toplam yerel kaynak sayısı: {len(YEREL_BASIN_TUM)}")
    bolge_sayisi = {
        "Karadeniz": len(YEREL_KARADENIZ),
        "Ege": len(YEREL_EGE),
        "Akdeniz": len(YEREL_AKDENIZ),
        "Marmara": len(YEREL_MARMARA),
        "İç Anadolu": len(YEREL_IC_ANADOLU),
        "Doğu/Güneydoğu": len(YEREL_DOGU_GUNEYDOGU),
        "Orta": len(YEREL_ORTA),
        "Sektörel": len(YEREL_SEKTOREL),
    }
    for bolge, sayi in bolge_sayisi.items():
        print(f"  {bolge:20s}: {sayi} kaynak")
