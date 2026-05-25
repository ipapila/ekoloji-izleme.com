#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
admin_import_patch.py
---------------------
admin.html'deki JSON/GeoJSON import fonksiyonunu düzeltir.

SORUNLAR:
  1. Her şey kör biçimde 'ihlaller' koleksiyonuna gidiyor
  2. kaynak_link alanı okunmuyor (sadece url okunuyor)
  3. GeoJSON properties'ten baslik/ozet alınmıyor
  4. koleksiyon alanı dikkate alınmıyor

ÇÖZÜM: importVeriIsle() fonksiyonunu aşağıdaki yeni versiyonla değiştir.

KULLANIM:
  python3 admin_import_patch.py
  (admin.html ile aynı klasörde çalıştır)
"""

import sys, re
from pathlib import Path

HTML = Path(__file__).parent / "admin.html"
if not HTML.exists():
    print(f"✗ {HTML} bulunamadı.")
    sys.exit(1)

content = HTML.read_text(encoding="utf-8")

# ── Eski import işleme fonksiyonunu bul ─────────────────────────
# Admin.html'de importVeriIsle veya benzeri bir fonksiyon var.
# Önce ne var kontrol et:
has_import_isle = "importVeriIsle" in content or "importUygula" in content
print(f"Import fonksiyonu mevcut: {has_import_isle}")

# ── Yeni yönlendirici fonksiyonu ────────────────────────────────
YENI_IMPORT_JS = """
/* ═══════════════════════════════════════════════════════════════
   GeoJSON / JSON IMPORT — KOLEKSİYONA GÖRE YÖNLENDİRME
   Düzeltme: koleksiyon alanı, kaynak_turu, eylem alanı dikkate alınır
             kaynak_link → url eşlemesi yapılır
             baslik/ozet/ad alanları normalize edilir
═══════════════════════════════════════════════════════════════ */

function importKoleksiyonBelirle(kayit) {
  // 1) Açık koleksiyon alanı varsa kullan
  const kol = (kayit.koleksiyon || kayit.tur || "").toLowerCase().trim();
  if (kol && ["ihlaller","haberler","raporlar","makaleler","ekosistem","kuresel","direnis"].includes(kol))
    return kol;

  // 2) eylem veya haber_kategorisi varsa → haberler
  if (kayit.eylem || kayit.haber_kategorisi) return "haberler";

  // 3) kaynak_turu'na göre
  const kt = (kayit.kaynak_turu || "").toLowerCase();
  if (kt === "haber" || kt === "sosyal_medya") return "haberler";
  if (kt === "uydu")  return "ekosistem";

  // 4) tip direniş/platform/grup ise
  const tip = (kayit.tip || "").toLowerCase();
  if (tip === "platform" || tip === "grup") return "direnis";

  // 5) baslik var, ad yok → muhtemelen haber
  if (kayit.baslik && !kayit.ad) return "haberler";

  // 6) varsayılan → ihlaller (harita verisi)
  return "ihlaller";
}

function importKayitNormalize(kayit) {
  // kaynak_link ↔ url tutarlılığı
  if (!kayit.url && kayit.kaynak_link) kayit.url = kayit.kaynak_link;
  if (!kayit.kaynak_link && kayit.url) kayit.kaynak_link = kayit.url;

  // ad ↔ baslik tutarlılığı
  if (!kayit.baslik && kayit.ad) kayit.baslik = kayit.ad;
  if (!kayit.ad && kayit.baslik) kayit.ad = kayit.baslik;

  // aciklama ↔ ozet tutarlılığı
  if (!kayit.ozet && kayit.aciklama) kayit.ozet = kayit.aciklama;
  if (!kayit.aciklama && kayit.ozet) kayit.aciklama = kayit.ozet;

  // koordinat normalize (GeoJSON geometry → koordinatlar)
  if (!kayit.koordinatlar && kayit.geometry && kayit.geometry.coordinates) {
    const [lng, lat] = kayit.geometry.coordinates;
    kayit.koordinatlar = { lat, lng };
  }

  // GeoJSON properties'i düzleştir
  if (kayit.properties && typeof kayit.properties === "object") {
    Object.assign(kayit, kayit.properties);
    delete kayit.properties;
    delete kayit.geometry;
    delete kayit.type;
    // Yeniden normalize et (properties'ten gelen kaynak_link için)
    if (!kayit.url && kayit.kaynak_link) kayit.url = kayit.kaynak_link;
    if (!kayit.kaynak_link && kayit.url) kayit.kaynak_link = kayit.url;
    if (!kayit.baslik && kayit.ad) kayit.baslik = kayit.ad;
    if (!kayit.ad && kayit.baslik) kayit.ad = kayit.baslik;
  }

  // tarih normalize
  if (!kayit.tarih && kayit.eklenme) kayit.tarih = kayit.eklenme;
  if (!kayit.eklenme && kayit.tarih) kayit.eklenme = kayit.tarih;

  return kayit;
}

function importVeriIsle(raw) {
  /* raw: File içeriği (string) */
  let parsed;
  try { parsed = JSON.parse(raw); }
  catch(e) { return { hata: "JSON parse hatası: " + e.message }; }

  // Kayıt listesini çıkar
  let liste = [];
  if (Array.isArray(parsed)) {
    liste = parsed;
  } else if (parsed.type === "FeatureCollection" && Array.isArray(parsed.features)) {
    // GeoJSON FeatureCollection — properties + geometry düzleştir
    liste = parsed.features.map(f => {
      const k = Object.assign({}, f.properties || {});
      if (f.geometry && f.geometry.coordinates) {
        const [lng, lat] = f.geometry.coordinates;
        k.koordinatlar = { lat: parseFloat(lat.toFixed(5)), lng: parseFloat(lng.toFixed(5)) };
      }
      if (f.id && !k.id) k.id = f.id;
      return k;
    });
  } else if (parsed.ihlaller || parsed.haberler || parsed.raporlar || parsed.direnis) {
    // data.json formatı — zaten koleksiyonlara ayrılmış
    const sonuc = { ihlaller:0, haberler:0, raporlar:0, makaleler:0, ekosistem:0, kuresel:0, direnis:0, atlan:0 };
    const kollar = ["ihlaller","haberler","raporlar","makaleler","ekosistem","kuresel","direnis"];
    kollar.forEach(kol => {
      if (!parsed[kol]) return;
      const mevcutIdler = new Set((SITE.get(kol)||[]).map(x=>String(x.id)));
      const yeniler = parsed[kol]
        .map(k => importKayitNormalize(k))
        .filter(k => k.id && !mevcutIdler.has(String(k.id)));
      if (yeniler.length) {
        SITE.set(kol, [...(SITE.get(kol)||[]), ...yeniler]);
        sonuc[kol] += yeniler.length;
      }
      sonuc.atlan += parsed[kol].length - yeniler.length;
    });
    return sonuc;
  } else {
    return { hata: "Tanınan format değil. Düz JSON dizi, GeoJSON FeatureCollection veya data.json bekleniyor." };
  }

  // Tek liste → koleksiyona yönlendir
  const sonuc = { ihlaller:0, haberler:0, raporlar:0, makaleler:0, ekosistem:0, kuresel:0, direnis:0, atlan:0 };
  const mevcutIhlalIdler  = new Set((SITE.get("ihlaller")||[]).map(x=>String(x.id)));
  const mevcutHaberIdler  = new Set((SITE.get("haberler")||[]).map(x=>String(x.id)));
  const mevcutRaporIdler  = new Set((SITE.get("raporlar")||[]).map(x=>String(x.id)));
  const mevcutDirenisIdler= new Set((SITE.get("direnis")||[]).map(x=>String(x.id)));
  const mevcutEkosistemIdler = new Set((SITE.get("ekosistem")||[]).map(x=>String(x.id)));

  const eklenecekler = { ihlaller:[], haberler:[], raporlar:[], makaleler:[], ekosistem:[], kuresel:[], direnis:[] };

  liste.forEach(kayitHam => {
    const k = importKayitNormalize(Object.assign({}, kayitHam));
    if (!k.id) k.id = "imp-" + Math.random().toString(36).slice(2,9) + Date.now().toString(36).slice(-4);
    const kol = importKoleksiyonBelirle(k);
    k.koleksiyon = kol;

    // Duplicate kontrolü
    const mevcutSet = kol === "ihlaller"  ? mevcutIhlalIdler
                    : kol === "haberler"  ? mevcutHaberIdler
                    : kol === "raporlar"  ? mevcutRaporIdler
                    : kol === "direnis"   ? mevcutDirenisIdler
                    : kol === "ekosistem" ? mevcutEkosistemIdler
                    : new Set();

    if (mevcutSet.has(String(k.id))) { sonuc.atlan++; return; }
    mevcutSet.add(String(k.id));
    eklenecekler[kol].push(k);
  });

  // localStorage'a yaz
  Object.keys(eklenecekler).forEach(kol => {
    if (!eklenecekler[kol].length) return;
    SITE.set(kol, [...(SITE.get(kol)||[]), ...eklenecekler[kol]]);
    sonuc[kol] += eklenecekler[kol].length;
  });

  return sonuc;
}
"""

# ── Eski importVeriIsle veya import handler'ı bul ve değiştir ───
# Birden fazla olası pattern var — hangisi match ediyor kontrol et

patterns_to_try = [
    # Pattern 1: function importVeriIsle
    (r'function importVeriIsle\(.*?\)\s*\{.*?\n\}', "function importVeriIsle"),
    # Pattern 2: importUygulaBtn click handler içinde parse
    (r'/\* ─+ GeoJSON.*?importUygulaBtn.*?}\);', "GeoJSON block"),
]

replaced = False

# En güvenli yol: mevcut import JS kodunu bul
# admin.html'de importFile, importUygula, importDrop gibi elementler var
# Bu elementlerin bulunduğu script bloğunu tespit et

# importUygula butonunun click handler'ını bul
import_handler_match = re.search(
    r"(document\.getElementById\(['\"]importUygula[Bb]tn?['\"]|"
    r"getElementById\(['\"]importUygula['\"])"
    r".*?\.addEventListener\(['\"]click['\"].*?\}\s*\);",
    content, re.DOTALL
)

if import_handler_match:
    print(f"Import handler bulundu ({import_handler_match.start()}-{import_handler_match.end()})")
else:
    print("Import handler direkt bulunamadı — script bloğunu arıyorum...")

# Yedek al
bak = HTML.with_suffix(".html.bak2")
bak.write_text(content, encoding="utf-8")
print(f"✓ Yedek: {bak.name}")

# importVeriIsle fonksiyonu zaten var mı?
if "function importVeriIsle" in content:
    # Fonksiyonu değiştir
    new_content = re.sub(
        r'function importVeriIsle\([^)]*\)\s*\{[^}]*(?:\{[^}]*\}[^}]*)*\}',
        "",  # sil, yerine yenisini ekleyeceğiz
        content, count=1, flags=re.DOTALL
    )
    # script kapanışından önce ekle
    new_content = new_content.replace("</script>", YENI_IMPORT_JS + "\n</script>", 1)
    HTML.write_text(new_content, encoding="utf-8")
    print("✓ importVeriIsle() değiştirildi")
    replaced = True
else:
    # Fonksiyon yok — import script bloğunun sonuna ekle
    # importUygula butonunun bulunduğu script bloğuna ekle
    if "importUygula" in content or "importFile" in content:
        # İlk </script>'ten önce değil, importFile'ın bulunduğu bloğa ekle
        idx = content.rfind("importUygula")
        # Bu satırın bulunduğu script bloğunun kapanışını bul
        script_end = content.find("</script>", idx)
        if script_end > 0:
            content = content[:script_end] + YENI_IMPORT_JS + "\n" + content[script_end:]
            HTML.write_text(content, encoding="utf-8")
            print("✓ importVeriIsle() importUygula script bloğuna eklendi")
            replaced = True

if not replaced:
    # Son çare: ilk </script>'ten önce ekle
    content = content.replace("</script>", YENI_IMPORT_JS + "\n</script>", 1)
    HTML.write_text(content, encoding="utf-8")
    print("✓ importVeriIsle() ilk script bloğuna eklendi")

print()
print("Sonraki adım: admin.html'deki importUygula butonunun")
print("click handler'ında importVeriIsle(raw) çağrısını kontrol et.")
print("Şöyle görünmeli:")
print()
print("  document.getElementById('importUygula').onclick = () => {")
print("    const sonuc = importVeriIsle(importData);")
print("    // sonuc.ihlaller, sonuc.haberler, sonuc.raporlar vb.")
print("    alert(`Eklendi: ${JSON.stringify(sonuc)}`);")
print("  };")
print()
print("Eğer import buton handler'ı başka bir mantık kullanıyorsa")
print("admin.html dosyasını paylaş, handler'ı da güncelleyelim.")
