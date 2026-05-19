/**
 * nav.js — Ortak navigasyonu her sayfaya enjekte eder.
 * Admin oturumu sessionStorage'dan okunur; aktifse nav'da rozet gösterilir.
 * Ticker (kayar haber şeridi) de burada oluşturulur — tüm sayfalarda çalışır.
 *
 * SESSION_KEY: site-data.js → SITE.SESSION_KEY = "ekoloji_admin_session"
 * ile birebir aynı anahtar kullanılır. İKİ AYRIDAN ASLA OLMASIN.
 */
(function () {
  // ⚠️  Bu değer SITE.SESSION_KEY ile senkron kalmalı.
  //     Değiştirirsen site-data.js'de de değiştir.
  const SESSION_KEY = "ekoloji_admin_session";
  const adminAktif  = sessionStorage.getItem(SESSION_KEY) === "1";

  const current = location.pathname.split("/").pop() || "index.html";

  /* Admin butonu */
  const adminBtn = adminAktif
    ? `<div style="display:flex;align-items:center;gap:8px;">
         <a href="admin.html"
            style="font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--bright);
                   text-decoration:none;letter-spacing:.08em;padding:5px 12px;
                   border:1px solid rgba(45,158,107,.45);border-radius:3px;
                   background:rgba(45,158,107,.08);display:flex;align-items:center;gap:6px;
                   transition:all .2s;"
            onmouseover="this.style.background='rgba(45,158,107,.18)'"
            onmouseout="this.style.background='rgba(45,158,107,.08)'">
           <span style="display:inline-block;width:6px;height:6px;border-radius:50%;
                        background:var(--bright);box-shadow:0 0 6px var(--bright);"></span>
           ADMIN
         </a>
         <button onclick="adminCikis()"
            style="font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--muted);
                   letter-spacing:.06em;padding:5px 10px;border:1px solid rgba(232,92,42,.25);
                   border-radius:3px;background:transparent;cursor:pointer;transition:all .2s;"
            onmouseover="this.style.color='var(--warn)';this.style.borderColor='rgba(232,92,42,.5)'"
            onmouseout="this.style.color='var(--muted)';this.style.borderColor='rgba(232,92,42,.25)'">
           Çıkış
         </button>
       </div>`
    : `<a href="admin.html"
          style="font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--muted);
                 text-decoration:none;letter-spacing:.08em;padding:6px 12px;
                 border:1px solid rgba(45,158,107,.2);border-radius:3px;transition:all .2s;"
          onmouseover="this.style.color='var(--bright)';this.style.borderColor='rgba(45,158,107,.4)'"
          onmouseout="this.style.color='var(--muted)';this.style.borderColor='rgba(45,158,107,.2)'">
        ADMIN
       </a>`;

  const navHTML = `
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Crimson+Pro:ital,wght@0,300;0,400;0,600;1,300;1,400&family=JetBrains+Mono:wght@300;400&display=swap" rel="stylesheet">
<nav>
  <a href="index.html" class="nav-logo">
    <span>ekoloji-izleme<b>.com</b></span>
  </a>

  <ul class="nav-menu">
    <li class="nav-item">
      <a href="ihlaller.html" class="nav-link ${current === 'ihlaller.html' ? 'active' : ''}">İzleme Konuları
        <svg viewBox="0 0 10 6" fill="currentColor"><path d="M0 0l5 6 5-6z"/></svg>
      </a>
      <div class="dropdown">
        <div class="dropdown-label">Çevre Tehditleri</div>
        <a href="ihlaller.html?kat=Maden"><span class="dot"></span>Maden &amp; Taş Ocakları</a>
        <a href="ihlaller.html?kat=Termik"><span class="dot"></span>Termik Santraller</a>
        <a href="ihlaller.html?kat=HES"><span class="dot"></span>HES &amp; Nehir Projeleri</a>
        <a href="ihlaller.html?kat=RES"><span class="dot"></span>RES &amp; Enerji Santralleri</a>
        <hr>
        <div class="dropdown-label">Arazi &amp; Su</div>
        <a href="ihlaller.html?kat=Tarım Arazisi"><span class="dot"></span>Tarım Arazisi İhlalleri</a>
        <a href="ihlaller.html?kat=Su Kirliliği"><span class="dot"></span>Su Kaynakları Kirliliği</a>
        <a href="ihlaller.html?kat=Orman"><span class="dot"></span>Orman Katliamları</a>
        <a href="ihlaller.html?kat=Kıyı"><span class="dot"></span>Kıyı &amp; Deniz Tahribatı</a>
        <hr>
        <div class="dropdown-label">Kentsel</div>
        <a href="ihlaller.html?kat=Atık"><span class="dot"></span>Atık &amp; Depolama Alanları</a>
        <a href="ihlaller.html?kat=Sanayi"><span class="dot"></span>Sanayi Bölgeleri</a>
        <a href="ihlaller.html?kat=Kaçak Yapı"><span class="dot"></span>Kaçak Yapılaşma</a>
      </div>
    </li>

    <li class="nav-item">
      <a href="haberler.html" class="nav-link ${current === 'haberler.html' ? 'active' : ''}">Haberler
        <svg viewBox="0 0 10 6" fill="currentColor"><path d="M0 0l5 6 5-6z"/></svg>
      </a>
      <div class="dropdown">
        <div class="dropdown-label">Konu</div>
        <a href="haberler.html"><span class="dot"></span>Tüm Haberler</a>
        <a href="haberler.html?kat=Çevre İhlali"><span class="dot"></span>Çevre İhlali</a>
        <a href="haberler.html?kat=Orman / Maden"><span class="dot"></span>Orman / Maden</a>
        <a href="haberler.html?kat=HES / RES / Baraj"><span class="dot"></span>HES / RES / Baraj</a>
        <a href="haberler.html?kat=İklim"><span class="dot"></span>İklim</a>
        <hr>
        <div class="dropdown-label">Direniş &amp; Toplum</div>
        <a href="haberler.html?tur=nobet"><span class="dot"></span>Nöbetler &amp; Protestolar</a>
        <a href="haberler.html?tur=direnis"><span class="dot"></span>Yerel Direnişler</a>
        <a href="haberler.html?tur=hareket"><span class="dot"></span>Halk Hareketleri</a>
      </div>
    </li>

    <li class="nav-item">
      <a href="raporlar.html" class="nav-link ${current === 'raporlar.html' ? 'active' : ''}">Raporlar
        <svg viewBox="0 0 10 6" fill="currentColor"><path d="M0 0l5 6 5-6z"/></svg>
      </a>
      <div class="dropdown">
        <a href="raporlar.html"><span class="dot"></span>Tüm Raporlar</a>
        <a href="raporlar.html?tur=Makale"><span class="dot"></span>Makaleler</a>
        <a href="raporlar.html?tur=Özel"><span class="dot"></span>Özel Raporlar</a>
        <a href="raporlar.html?tur=Veri"><span class="dot"></span>Veri Analizleri</a>
      </div>
    </li>

    <li class="nav-item">
      <a href="ekosistem.html" class="nav-link ${current === 'ekosistem.html' ? 'active' : ''}">Ekosistem
        <svg viewBox="0 0 10 6" fill="currentColor"><path d="M0 0l5 6 5-6z"/></svg>
      </a>
      <div class="dropdown">
        <div class="dropdown-label">İnsan Dışı Canlılar</div>
        <a href="ekosistem.html?sec=turler"><span class="dot"></span>Nesli Tehlike Altında Türler</a>
        <a href="ekosistem.html?sec=yaban"><span class="dot"></span>Yaban Hayatı İzleme</a>
        <a href="ekosistem.html?sec=bitki"><span class="dot"></span>Bitki Örtüsü</a>
        <hr>
        <div class="dropdown-label">Dezavantajlı Gruplar</div>
        <a href="ekosistem.html?sec=ciftci"><span class="dot"></span>Çiftçi &amp; Köylü Sorunları</a>
        <a href="ekosistem.html?sec=yerli"><span class="dot"></span>Yerli Haklar</a>
        <a href="ekosistem.html?sec=balikci"><span class="dot"></span>Balıkçı Toplulukları</a>
      </div>
    </li>
  </ul>

  <div style="display:flex;align-items:center;gap:16px;">
    <div class="rec-indicator">
      <div class="rec-dot"></div> CANLI İZLEME
    </div>
    ${adminBtn}
  </div>

  <div class="hamburger" onclick="document.querySelector('.nav-menu').style.display=document.querySelector('.nav-menu').style.display==='flex'?'none':'flex'">
    <span></span><span></span><span></span>
  </div>
</nav>

<!-- TICKER: nav'ın hemen altında kayar haber şeridi -->
<div class="ticker-bar" id="navTicker" style="display:none;">
  <div class="ticker-inner" id="navTickerInner"></div>
</div>`;

  const root = document.getElementById("nav-root");
  if (root) root.innerHTML = navHTML;
  else document.body.insertAdjacentHTML("afterbegin", navHTML);

  // ── Ticker yükle ──────────────────────────────────────────────────────────
  // Sadece index.html'de zaten ticker varsa çakışmayı önle
  const mevcutTicker = document.getElementById("tickerInner");
  if (mevcutTicker) {
    // index.html kendi ticker'ını zaten yönetiyor; nav ticker'ını gizle
    document.getElementById("navTicker").style.display = "none";
  } else {
    _tickerYukle();
  }

  function _tickerYukle() {
    const bar = document.getElementById("navTicker");
    if (!bar) return;

    function _tickerRender(haberler) {
      const silinen = (() => {
        try { return new Set(JSON.parse(localStorage.getItem("ekoloji_haber_silinen") || "[]").map(String)); }
        catch { return new Set(); }
      })();

      const liste = haberler.filter(h => !silinen.has(String(h.id))).slice(0, 12);
      if (!liste.length) return;

      bar.style.display = "block";

      // Ticker öğelerini iki kez ekle (sonsuz döngü efekti için)
      const items = liste.map(h => `
        <div class="ticker-item" style="cursor:pointer;" onclick='_navTickerAc(${JSON.stringify(h).replace(/'/g, "&#39;")})'>
          <span class="label" style="background:rgba(45,158,107,.18);color:var(--bright);border:1px solid rgba(45,158,107,.3);">
            ${(h.kategori || h.etiket || h.kaynak || "HABER").toString().slice(0, 14).toUpperCase()}
          </span>
          ${h.baslik}${h.kaynak ? ` <span style="opacity:.5;font-size:.85em;">— ${h.kaynak}</span>` : ""}
        </div>`).join("");

      document.getElementById("navTickerInner").innerHTML = items + items;
    }

    // Veri kaynağı: önce haberler.json, yoksa localStorage/defaults
    fetch("haberler.json?v=" + Date.now())
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => {
        const haberler = data.haberler || (Array.isArray(data) ? data : []);
        if (haberler.length) _tickerRender(haberler);
        else _tickerFallback();
      })
      .catch(_tickerFallback);

    function _tickerFallback() {
      if (typeof SITE !== "undefined") {
        const h = SITE.getList("haberler") || SITE.defaults.haberler || [];
        if (h.length) _tickerRender(h);
      }
    }
  }
})();

// ── Ticker haber modalı (global — onclick içinden erişilebilir) ───────────
function _navTickerAc(h) {
  const m = document.createElement("div");
  m.style.cssText = "position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,.75);display:flex;align-items:center;justify-content:center;padding:20px;backdrop-filter:blur(4px);";
  m.innerHTML = `
    <div style="background:var(--deep);border:1px solid rgba(45,158,107,.25);border-radius:8px;
                max-width:640px;width:100%;padding:32px;position:relative;">
      <button onclick="this.closest('div[style]').remove()"
        style="position:absolute;top:16px;right:16px;background:none;border:none;
               color:var(--muted);font-size:20px;cursor:pointer;">✕</button>
      <div style="font-family:'JetBrains Mono',monospace;font-size:9px;letter-spacing:.1em;
                  text-transform:uppercase;color:var(--accent);margin-bottom:12px;">
        ${h.kategori || h.etiket || h.kaynak || ""}
      </div>
      <h3 style="font-family:'Crimson Pro',serif;font-size:24px;font-weight:400;
                 color:var(--cream);line-height:1.4;margin:0 0 16px;">${h.baslik}</h3>
      <p style="font-size:14px;color:var(--muted);line-height:1.7;margin:0 0 20px;">${h.ozet || ""}</p>
      ${h.url ? `<a href="${h.url}" target="_blank" rel="noopener"
        style="display:inline-flex;align-items:center;gap:8px;padding:10px 18px;
               background:var(--accent);color:var(--dark);font-family:'JetBrains Mono',monospace;
               font-size:10px;letter-spacing:.08em;text-decoration:none;border-radius:4px;
               text-transform:uppercase;">Kaynağa Git ↗</a>` : ""}
    </div>`;
  m.addEventListener("click", e => { if (e.target === m) m.remove(); });
  document.body.appendChild(m);
}

/**
 * Global: nav'daki Çıkış butonu tarafından çağrılır.
 */
function adminCikis() {
  if (typeof SITE !== "undefined" && typeof SITE.logout === "function") {
    SITE.logout();
  } else {
    sessionStorage.removeItem("ekoloji_admin_session");
  }
  location.reload();
}
