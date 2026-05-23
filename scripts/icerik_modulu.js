/**
 * ekoloji-izleme.com — İçerik Modülü v1
 * Raporlar, Makaleler, Uluslararası koleksiyonlarını haberler.json'dan okur
 * ve sayfada ilgili seksiyonlara render eder.
 *
 * KULLANIM:
 *   1. Bu dosyayı sitenin /scripts/ klasörüne koy
 *   2. Göstermek istediğin sayfaya ekle:
 *        <script src="/scripts/icerik_modulu.js"></script>
 *   3. HTML'de yer tutucu div'leri koy (aşağıya bak)
 *
 * HTML YER TUTUCULARI:
 *   <div id="raporlar-listesi" data-kategori="" data-limit="20"></div>
 *   <div id="makaleler-listesi" data-kategori="" data-limit="20"></div>
 *   <div id="uluslararasi-listesi" data-kategori="" data-limit="20"></div>
 *   <div id="haberler-listesi"    data-kategori="" data-limit="30"></div>
 *
 *   İsteğe bağlı filtreler:
 *     data-kategori="STK Raporu"         → sadece o kategori
 *     data-etiketi="Rapor & Analiz"      → sadece o etiket
 *     data-dil="en"                      → sadece o dil
 *     data-limit="20"                    → kaç kayıt gösterileceği
 */

(function () {
  "use strict";

  // ── Yapılandırma ────────────────────────────────────────────────
  const VERI_URL  = "/haberler.json";   // tarayici.py çıktısı
  // Alternatif: GitHub raw — CDN gecikmesi olabilir
  // const VERI_URL = "https://raw.githubusercontent.com/ipapila/ekoloji-izleme.com/main/haberler.json";

  const KOLEKSIYON_RENKLERI = {
    haberler:     { bg: "#1e3a5f", badge: "#3b82f6", etiket: "Haber"          },
    raporlar:     { bg: "#1e3d2f", badge: "#22c55e", etiket: "Rapor & Analiz" },
    makaleler:    { bg: "#3b2a1e", badge: "#f59e0b", etiket: "Köşe & Yorum"   },
    uluslararasi: { bg: "#2a1e3b", badge: "#a855f7", etiket: "Uluslararası"   },
  };

  const ICERIK_TIPI_RENGI = {
    haber:        "#3b82f6",
    rapor:        "#22c55e",
    kose:         "#f59e0b",
    uluslararasi: "#a855f7",
  };

  // ── Veri yükleme ────────────────────────────────────────────────
  let _veriCache = null;

  async function veriYukle() {
    if (_veriCache) return _veriCache;
    try {
      const r = await fetch(VERI_URL + "?_=" + Date.now());
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      _veriCache = await r.json();
      return _veriCache;
    } catch (e) {
      console.error("haberler.json yüklenemedi:", e);
      return null;
    }
  }

  // ── Filtreleme ──────────────────────────────────────────────────
  function filtrele(liste, { kategori, etiketi, dil, icerikTipi } = {}) {
    return liste.filter(h => {
      if (kategori   && h.kategori     !== kategori)   return false;
      if (etiketi    && !(h.etiketler || []).includes(etiketi)) return false;
      if (dil        && h.dil          !== dil)         return false;
      if (icerikTipi && h.icerik_tipi  !== icerikTipi) return false;
      return true;
    });
  }

  // ── Tek kart HTML'i ─────────────────────────────────────────────
  function kartHTML(h, koleksiyon) {
    const renk  = KOLEKSIYON_RENKLERI[koleksiyon] || KOLEKSIYON_RENKLERI.haberler;
    const tip   = h.icerik_tipi || "haber";
    const tipRenk = ICERIK_TIPI_RENGI[tip] || "#3b82f6";
    const tarih = h.tarih ? h.tarih.slice(0, 10) : "";
    const ozet  = h.ozet  ? `<p class="kart-ozet">${h.ozet.slice(0, 180)}…</p>` : "";
    const etiketler = (h.etiketler || [])
      .slice(0, 3)
      .map(e => `<span class="kart-etiket">${e}</span>`)
      .join("");
    const dilBadge = h.dil === "en"
      ? `<span class="kart-dil-en">EN</span>` : "";
    const kaynakBadge = h.kaynak
      ? `<span class="kart-kaynak">${h.kaynak}</span>` : "";

    return `
      <article class="icerik-kart" data-tip="${tip}" data-koleksiyon="${koleksiyon}">
        <div class="kart-ust">
          <span class="kart-tip-badge" style="background:${tipRenk}">${renk.etiket}</span>
          ${dilBadge}
          ${kaynakBadge}
          <time class="kart-tarih">${tarih}</time>
        </div>
        <h3 class="kart-baslik">
          <a href="${h.url}" target="_blank" rel="noopener">${h.baslik}</a>
        </h3>
        ${ozet}
        <div class="kart-etiketler">${etiketler}</div>
      </article>`;
  }

  // ── Liste render ────────────────────────────────────────────────
  function listeRender(konteyner, liste, koleksiyon) {
    if (!liste || liste.length === 0) {
      konteyner.innerHTML = `<p class="bos-mesaj">Henüz içerik yok.</p>`;
      return;
    }
    konteyner.innerHTML = liste.map(h => kartHTML(h, koleksiyon)).join("\n");
  }

  // ── İstatistik kartları (opsiyonel) ─────────────────────────────
  function istatistikRender(hedef, veri) {
    const el = document.getElementById(hedef);
    if (!el || !veri) return;
    const { haberler=[], raporlar=[], makaleler=[], uluslararasi=[] } = veri;
    el.innerHTML = `
      <div class="istatistik-grid">
        <div class="istatistik-kart" style="border-color:#3b82f6">
          <span class="istatistik-sayi">${haberler.length}</span>
          <span class="istatistik-etiket">Haber</span>
        </div>
        <div class="istatistik-kart" style="border-color:#22c55e">
          <span class="istatistik-sayi">${raporlar.length}</span>
          <span class="istatistik-etiket">Rapor & Analiz</span>
        </div>
        <div class="istatistik-kart" style="border-color:#f59e0b">
          <span class="istatistik-sayi">${makaleler.length}</span>
          <span class="istatistik-etiket">Köşe & Yorum</span>
        </div>
        <div class="istatistik-kart" style="border-color:#a855f7">
          <span class="istatistik-sayi">${uluslararasi.length}</span>
          <span class="istatistik-etiket">Uluslararası</span>
        </div>
      </div>`;
  }

  // ── Ana başlatıcı ────────────────────────────────────────────────
  async function baslat() {
    const veri = await veriYukle();
    if (!veri) return;

    const KONTEYNERLER = [
      { id: "haberler-listesi",    koleksiyon: "haberler"     },
      { id: "raporlar-listesi",    koleksiyon: "raporlar"     },
      { id: "makaleler-listesi",   koleksiyon: "makaleler"    },
      { id: "uluslararasi-listesi",koleksiyon: "uluslararasi" },
    ];

    for (const { id, koleksiyon } of KONTEYNERLER) {
      const el = document.getElementById(id);
      if (!el) continue;

      const kategori   = el.dataset.kategori   || "";
      const etiketi    = el.dataset.etiketi     || "";
      const dil        = el.dataset.dil         || "";
      const icerikTipi = el.dataset.iceriktipi  || "";
      const limit      = parseInt(el.dataset.limit || "20", 10);

      let liste = veri[koleksiyon] || [];
      liste = filtrele(liste, { kategori, etiketi, dil, icerikTipi });
      liste = liste.slice(0, limit);

      listeRender(el, liste, koleksiyon);
    }

    // İstatistik widget (varsa)
    istatistikRender("icerik-istatistik", veri);
  }

  // ── CSS enjeksiyonu ──────────────────────────────────────────────
  function cssEkle() {
    if (document.getElementById("icerik-modul-css")) return;
    const style = document.createElement("style");
    style.id = "icerik-modul-css";
    style.textContent = `
      .icerik-kart {
        background: #1a1a2e;
        border: 1px solid #2d2d4e;
        border-radius: 8px;
        padding: 14px 16px;
        margin-bottom: 12px;
        transition: border-color .2s;
      }
      .icerik-kart:hover { border-color: #4a4a8a; }
      .kart-ust {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
        margin-bottom: 8px;
        font-size: 0.75rem;
      }
      .kart-tip-badge {
        padding: 2px 8px;
        border-radius: 999px;
        color: #fff;
        font-weight: 600;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: .5px;
      }
      .kart-dil-en {
        background: #374151;
        color: #d1d5db;
        padding: 1px 6px;
        border-radius: 4px;
        font-size: 0.68rem;
        font-weight: 700;
      }
      .kart-kaynak {
        color: #9ca3af;
        font-size: 0.72rem;
      }
      .kart-tarih { color: #6b7280; margin-left: auto; }
      .kart-baslik { margin: 0 0 6px; font-size: 0.95rem; line-height: 1.4; }
      .kart-baslik a { color: #e2e8f0; text-decoration: none; }
      .kart-baslik a:hover { color: #93c5fd; text-decoration: underline; }
      .kart-ozet { color: #9ca3af; font-size: 0.82rem; margin: 0 0 8px; line-height: 1.5; }
      .kart-etiketler { display: flex; gap: 6px; flex-wrap: wrap; }
      .kart-etiket {
        background: #1e293b;
        color: #94a3b8;
        border: 1px solid #334155;
        border-radius: 4px;
        padding: 1px 7px;
        font-size: 0.68rem;
      }
      .bos-mesaj { color: #6b7280; font-style: italic; text-align: center; padding: 24px; }
      .istatistik-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 12px;
        margin: 16px 0;
      }
      .istatistik-kart {
        background: #0f172a;
        border: 2px solid;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
      }
      .istatistik-sayi { display: block; font-size: 2rem; font-weight: 700; color: #e2e8f0; }
      .istatistik-etiket { display: block; font-size: 0.75rem; color: #94a3b8; margin-top: 4px; }
    `;
    document.head.appendChild(style);
  }

  // ── Başlat ───────────────────────────────────────────────────────
  cssEkle();
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", baslat);
  } else {
    baslat();
  }

  // Public API (isteğe bağlı dışarıdan erişim)
  window.IcerikModul = { veriYukle, filtrele, listeRender, istatistikRender };
})();
