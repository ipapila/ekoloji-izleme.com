#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
direnis_agi_patch.py
--------------------
direnis-agi.html içindeki veri yükleme bloğunu günceller.

SORUN: direnis-agi.html sadece `eylem` alanına bakıyor
       ama haberler.html `haber_kategorisi` alanını kullanıyor.
       İkisi birbirini görmüyor → bölümler boş kalıyor.

ÇÖZÜM: norm() + bolumBelirle() fonksiyonları eklenir.
       Hem eylem hem haber_kategorisi hem etiketler kontrol edilir.
       kaynak_link → url, il/ilce → konum otomatik eşlenir.
       direnis koleksiyonundaki "platform" tipi artık _grup'a gider.

KULLANIM:
  python3 direnis_agi_patch.py
  (direnis-agi.html ile aynı klasörde çalıştır)
"""

import sys
from pathlib import Path

HTML = Path(__file__).parent / "direnis-agi.html"

if not HTML.exists():
    print(f"✗ {HTML} bulunamadı — bu scripti direnis-agi.html ile aynı klasöre koy.")
    sys.exit(1)

content = HTML.read_text(encoding="utf-8")

# ── Değiştirilecek blok ──────────────────────────────────────────
OLD = """fetch("data.json?v=" + Date.now())
  .then(r => r.ok ? r.json() : Promise.reject())
  .then(data => {
    /* Haberlerden eylem türüne göre ayır */
    const haberler = (data.haberler || []).filter(h => !silinen.has(String(h.id)));
    haberler.forEach(h => {
      const tip = EYLEM_ETIKETI[h.eylem];
      if (tip === "eylem") _eylem.push(h);
      else if (tip === "hukuk") _hukuk.push(h);
      else if (tip === "nobet") _nobet.push(h);
      else if (tip === "stk")   _stk.push(h);
      /* Etiketlerden de topla */
      const etiketler = Array.isArray(h.etiketler) ? h.etiketler : [];
      etiketler.forEach(et => {
        if ((et === "Direniş & Eylem") && !_eylem.includes(h)) _eylem.push(h);
        if ((et === "Hukuk & Dava")    && !_hukuk.includes(h)) _hukuk.push(h);
        if ((et === "Nöbet & Gözaltı") && !_nobet.includes(h)) _nobet.push(h);
        if ((et === "STK & Kampanya")  && !_stk.includes(h))   _stk.push(h);
      });
    });
    /* Ayrıca direnis koleksiyonu (admin ile eklenen gruplar & özel kayıtlar) */
    const direnis = (data.direnis || []).filter(d => !silinen.has(String(d.id)));
    direnis.forEach(d => {
      if (d.tip === "grup" || d.tur === "grup" || !d.tip) _grup.push(d);
      else if (d.tip === "eylem") _eylem.push(d);
      else if (d.tip === "hukuk") _hukuk.push(d);
      else if (d.tip === "nobet") _nobet.push(d);
      else if (d.tip === "stk")   _stk.push(d);
    });
    /* localStorage'dan ekle */
    const lsDirenis = (typeof SITE !== "undefined" ? (SITE.get("direnis") || []) : [])
      .filter(d => !silinen.has(String(d.id)));
    const serverIds = new Set(direnis.map(d => String(d.id)));
    lsDirenis.filter(d => !serverIds.has(String(d.id))).forEach(d => {
      if (d.tip === "grup" || !d.tip) _grup.push(d);
      else if (d.tip === "eylem") _eylem.push(d);
      else if (d.tip === "hukuk") _hukuk.push(d);
      else if (d.tip === "nobet") _nobet.push(d);
      else if (d.tip === "stk")   _stk.push(d);
    });
    /* Tarihe göre sırala */
    const sırala = arr => arr.sort((a,b) => new Date(b.tarih||0) - new Date(a.tarih||0));
    [_eylem, _hukuk, _nobet, _stk, _grup].forEach(sırala);
    renderAll();
  })
  .catch(() => {
    /* Fallback: localStorage */
    const lsDirenis = (typeof SITE !== "undefined" ? (SITE.get("direnis") || []) : [])
      .filter(d => !silinen.has(String(d.id)));
    _grup = lsDirenis.filter(d => d.tip === "grup" || !d.tip);
    renderAll();
  });"""

# ── Yeni blok ────────────────────────────────────────────────────
NEW = """fetch("data.json?v=" + Date.now())
  .then(r => r.ok ? r.json() : Promise.reject())
  .then(data => {

    /* ── Normalize: haberler.html ile direnis-agi.html alan adlarını eşle ──
       haberler.html kayıtları: kaynak_link / il+ilce / haber_kategorisi
       direnis-agi.html bekler:  url          / konum   / eylem
       norm() her ikisini de destekler. */
    function norm(h) {
      if (!h.url && h.kaynak_link) h.url = h.kaynak_link;
      if (!h.konum) {
        if (h.ilce && h.il) h.konum = h.ilce + " / " + h.il;
        else if (h.il)      h.konum = h.il;
      }
      return h;
    }

    /* ── Bölüm belirle ─────────────────────────────────────────
       Öncelik: eylem alanı → haber_kategorisi alanı → etiketler */
    function bolumBelirle(h) {
      // 1) eylem alanı  (örn. "Direniş & Eylem")
      const tipEylem = EYLEM_ETIKETI[h.eylem];
      if (tipEylem) return tipEylem;
      // 2) haber_kategorisi alanı  (haberler.html ile tam senkron)
      const hkat = (h.haber_kategorisi || "").trim();
      if (hkat === "Direniş ve Eylemler")    return "eylem";
      if (hkat === "Hukuki Süreçler")        return "hukuk";
      if (hkat === "Nöbetler ve Gözaltılar") return "nobet";
      if (hkat === "STK & Kampanyalar")      return "stk";
      // 3) etiketler dizisi
      const et = Array.isArray(h.etiketler) ? h.etiketler : [];
      if (et.includes("Direniş & Eylem"))  return "eylem";
      if (et.includes("Hukuk & Dava"))     return "hukuk";
      if (et.includes("Nöbet & Gözaltı"))  return "nobet";
      if (et.includes("STK & Kampanya"))   return "stk";
      return null;  // bu bölüme ait değil
    }

    /* Haberlerden bölüme göre ayır */
    const haberler = (data.haberler || []).filter(h => !silinen.has(String(h.id)));
    haberler.forEach(h => {
      norm(h);
      const tip = bolumBelirle(h);
      if      (tip === "eylem") _eylem.push(h);
      else if (tip === "hukuk") _hukuk.push(h);
      else if (tip === "nobet") _nobet.push(h);
      else if (tip === "stk")   _stk.push(h);
    });

    /* direnis koleksiyonu — "platform" tipi de gruplar'a gider */
    const direnis = (data.direnis || []).filter(d => !silinen.has(String(d.id)));
    direnis.forEach(d => {
      norm(d);
      if      (d.tip === "platform" || d.tip === "grup" || d.tur === "grup" || !d.tip) _grup.push(d);
      else if (d.tip === "eylem")  _eylem.push(d);
      else if (d.tip === "hukuk")  _hukuk.push(d);
      else if (d.tip === "nobet")  _nobet.push(d);
      else if (d.tip === "stk")    _stk.push(d);
    });

    /* localStorage'dan ekle */
    const lsDirenis = (typeof SITE !== "undefined" ? (SITE.get("direnis") || []) : [])
      .filter(d => !silinen.has(String(d.id)));
    const serverIds = new Set(direnis.map(d => String(d.id)));
    lsDirenis.filter(d => !serverIds.has(String(d.id))).forEach(d => {
      norm(d);
      if      (d.tip === "platform" || d.tip === "grup" || !d.tip) _grup.push(d);
      else if (d.tip === "eylem")  _eylem.push(d);
      else if (d.tip === "hukuk")  _hukuk.push(d);
      else if (d.tip === "nobet")  _nobet.push(d);
      else if (d.tip === "stk")    _stk.push(d);
    });

    const sırala = arr => arr.sort((a,b) => new Date(b.tarih||0) - new Date(a.tarih||0));
    [_eylem, _hukuk, _nobet, _stk, _grup].forEach(sırala);
    renderAll();
  })
  .catch(() => {
    const lsDirenis = (typeof SITE !== "undefined" ? (SITE.get("direnis") || []) : [])
      .filter(d => !silinen.has(String(d.id)));
    _grup = lsDirenis.filter(d => d.tip === "platform" || d.tip === "grup" || !d.tip);
    renderAll();
  });"""

# ── Uygula ──────────────────────────────────────────────────────
if OLD not in content:
    print("✗ Hedef metin bulunamadı.")
    print("  Büyük ihtimalle direnis-agi.html daha önce güncellenmiş.")
    print("  Kontrol: 'EYLEM_ETIKETI[h.eylem]' satırı hâlâ dosyada var mı?")
    sys.exit(1)

# Yedek al
bak = HTML.with_suffix(".html.bak")
bak.write_text(content, encoding="utf-8")
print(f"✓ Yedek: {bak.name}")

content = content.replace(OLD, NEW, 1)
HTML.write_text(content, encoding="utf-8")

print("✓ direnis-agi.html güncellendi")
print()
print("Ne değişti:")
print("  • norm()        — kaynak_link→url, il/ilce→konum otomatik eşleme")
print("  • bolumBelirle() — eylem + haber_kategorisi + etiketler üçlü kontrol")
print("  • 'platform' tipi direnis kayıtları artık Gruplar & Platformlar'da")
print()
print("Artık haberler.html'deki tüm direniş haberleri")
print("direnis-agi.html'de doğru bölümlerde görünecek.")
