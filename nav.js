/**
 * nav.js — Ortak navigasyonu her sayfaya enjekte eder.
 */
(function () {
  const SESSION_KEY = "ekoloji_admin_session";
  const adminAktif  = sessionStorage.getItem(SESSION_KEY) === "1";
  const current = location.pathname.split("/").pop() || "index.html";

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
        <div class="dropdown-label">Enerji & Maden</div>
        <a href="ihlaller.html?kat=Maden Ocağı"><span class="dot"></span>Maden Ocakları</a>
        <a href="ihlaller.html?kat=Taş-Mermer Ocağı"><span class="dot"></span>Taş-Mermer Ocakları</a>
        <a href="ihlaller.html?kat=Termik Reaktör"><span class="dot"></span>Termik Reaktörler</a>
        <a href="ihlaller.html?kat=HES"><span class="dot"></span>HES & Nehir Projeleri</a>
        <a href="ihlaller.html?kat=RES"><span class="dot"></span>RES & Rüzgar Santralleri</a>
        <a href="ihlaller.html?kat=GES"><span class="dot"></span>GES & Güneş Santralleri</a>
        <a href="ihlaller.html?kat=Nükleer Enerji"><span class="dot"></span>Nükleer Enerji</a>
        <a href="ihlaller.html?kat=Jeotermal"><span class="dot"></span>Jeotermal</a>
        <hr>
        <div class="dropdown-label">Koruma Alanları</div>
        <a href="ihlaller.html?kat=Milli Park"><span class="dot"></span>Milli Parklar</a>
        <a href="ihlaller.html?kat=Özel Çevre Koruma Alanı"><span class="dot"></span>Özel Çevre Koruma Alanları</a>
        <a href="ihlaller.html?kat=Orman Alanı"><span class="dot"></span>Orman Alanları</a>
        <a href="ihlaller.html?kat=Sulak Alan"><span class="dot"></span>Sulak Alanlar</a>
        <a href="ihlaller.html?kat=Kültür Varlığı"><span class="dot"></span>Kültür Varlıkları</a>
        <hr>
        <div class="dropdown-label">Diğer</div>
        <a href="ihlaller.html?kat=Acele Kamulaştırma"><span class="dot"></span>Acele Kamulaştırma</a>
        <a href="ihlaller.html?kat=Kıyı İhlalleri"><span class="dot"></span>Kıyı İhlalleri</a>
        <a href="ihlaller.html?kat=Ekolojik İhlal"><span class="dot"></span>Genel Ekolojik İhlaller</a>
      </div>
    </li>

    <li class="nav-item">
      <a href="haberler.html" class="nav-link ${current === 'haberler.html' ? 'active' : ''}">Haberler
        <svg viewBox="0 0 10 6" fill="currentColor"><path d="M0 0l5 6 5-6z"/></svg>
      </a>
      <div class="dropdown">
        <div class="dropdown-label">Konu</div>
        <a href="haberler.html"><span class="dot"></span>Tüm Haberler</a>
        <a href="haberler.html?kat=İklim Olayları"><span class="dot"></span>İklim & Afet</a>
        <a href="haberler.html?kat=Maden Ocağı"><span class="dot"></span>Maden & Enerji</a>
        <a href="haberler.html?kat=Orman Alanı"><span class="dot"></span>Orman & Doğa</a>
        <a href="haberler.html?kat=Sulak Alan"><span class="dot"></span>Su & Kıyı</a>
        <a href="haberler.html?kat=Yaban Hayatı"><span class="dot"></span>Yaban Hayatı</a>
        <hr>
        <div class="dropdown-label">Eylem & Toplum</div>
        <a href="haberler.html?eylem=Direniş & Eylem"><span class="dot"></span>Direniş & Eylemler</a>
        <a href="haberler.html?eylem=Hukuk & Dava"><span class="dot"></span>Hukuki Süreçler</a>
        <a href="haberler.html?eylem=Nöbet & Gözaltı"><span class="dot"></span>Nöbetler & Gözaltılar</a>
        <a href="haberler.html?eylem=STK & Kampanya"><span class="dot"></span>STK & Kampanyalar</a>
      </div>
    </li>

    <li class="nav-item">
      <a href="raporlar.html" class="nav-link ${current === 'raporlar.html' ? 'active' : ''}">Raporlar
        <svg viewBox="0 0 10 6" fill="currentColor"><path d="M0 0l5 6 5-6z"/></svg>
      </a>
      <div class="dropdown">
        <a href="raporlar.html"><span class="dot"></span>Tüm Raporlar</a>
        <a href="raporlar.html?tur=Yıllık Rapor"><span class="dot"></span>Yıllık Raporlar</a>
        <a href="raporlar.html?tur=Alan Araştırması"><span class="dot"></span>Alan Araştırmaları</a>
        <a href="raporlar.html?tur=Veri & İstatistik"><span class="dot"></span>Veri & İstatistik</a>
        <a href="raporlar.html?tur=Hukuki Analiz"><span class="dot"></span>Hukuki Analizler</a>
        <a href="raporlar.html?tur=İzleme Raporu"><span class="dot"></span>İzleme Raporları</a>
      </div>
    </li>

    <li class="nav-item">
      <a href="makaleler.html" class="nav-link ${current === 'makaleler.html' || current === 'uluslararasi.html' ? 'active' : ''}">Makaleler
        <svg viewBox="0 0 10 6" fill="currentColor"><path d="M0 0l5 6 5-6z"/></svg>
      </a>
      <div class="dropdown">
        <div class="dropdown-label">Türkçe Yazılar</div>
        <a href="makaleler.html"><span class="dot"></span>Tüm Makaleler</a>
        <a href="makaleler.html?tur=Resmi Açıklama"><span class="dot"></span>Resmi Açıklamalar</a>
        <a href="makaleler.html?tur=Basın Bülteni"><span class="dot"></span>Basın Bültenleri</a>
        <a href="makaleler.html?tur=Bireysel Yazı"><span class="dot"></span>Bireysel Yazılar</a>
        <a href="makaleler.html?tur=Köşe Yazısı"><span class="dot"></span>Köşe Yazıları</a>
        <a href="makaleler.html?tur=Analiz"><span class="dot"></span>Analiz & Araştırma</a>
        <a href="makaleler.html?tur=Akademik Makale"><span class="dot"></span>Akademik Makaleler</a>
        <a href="makaleler.html?tur=Röportaj"><span class="dot"></span>Röportajlar</a>
        <hr>
        <div class="dropdown-label">Küresel</div>
        <a href="uluslararasi.html"><span class="dot"></span>Uluslararası Medya</a>
        <a href="uluslararasi.html?dil=EN"><span class="dot"></span>İngilizce Yayınlar</a>
        <a href="uluslararasi.html?kat=İklim"><span class="dot"></span>İklim & Çevre</a>
        <a href="uluslararasi.html?kat=Araştırma"><span class="dot"></span>Bilimsel Araştırmalar</a>
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
        <a href="ekosistem.html?sec=bitki"><span class="dot"></span>Bitki Örtüsü & Habitatlar</a>
        <a href="ekosistem.html?sec=su-canlilari"><span class="dot"></span>Su Canlıları</a>
        <a href="ekosistem.html?sec=hayvan-haklari"><span class="dot"></span>Hayvan Hakları & Refahı</a>
        <hr>
        <div class="dropdown-label">İnsan Toplulukları</div>
        <a href="ekosistem.html?sec=kadinlar"><span class="dot"></span>Kadınlar & Ekoloji</a>
        <a href="ekosistem.html?sec=lgbti"><span class="dot"></span>LGBTİ+ & Çevre</a>
        <a href="ekosistem.html?sec=engelliler"><span class="dot"></span>Engelliler & Erişim</a>
        <a href="ekosistem.html?sec=ciftci"><span class="dot"></span>Çiftçi & Köylü Sorunları</a>
        <a href="ekosistem.html?sec=balikci"><span class="dot"></span>Balıkçı Toplulukları</a>
        <a href="ekosistem.html?sec=yerli"><span class="dot"></span>Yerli & Yerel Haklar</a>
        <a href="ekosistem.html?sec=genclik"><span class="dot"></span>Çocuklar & Gençlik</a>
        <hr>
        <div class="dropdown-label">Çevre Adaleti</div>
        <a href="ekosistem.html?sec=esitsizlik"><span class="dot"></span>Ekolojik Eşitsizlik</a>
        <a href="ekosistem.html?sec=kentsel"><span class="dot"></span>Kentsel Çevre</a>
        <a href="ekosistem.html?sec=goc"><span class="dot"></span>İklim Göçü & Yerinden Edilme</a>
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

<div class="ticker-bar" id="navTicker" style="display:none;">
  <div class="ticker-inner" id="navTickerInner"></div>
</div>`;

  const root = document.getElementById("nav-root");
  if (root) root.innerHTML = navHTML;
  else document.body.insertAdjacentHTML("afterbegin", navHTML);

  const mevcutTicker = document.getElementById("tickerInner");
  if (mevcutTicker) {
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
      const items = liste.map(h => `
        <div class="ticker-item" style="cursor:pointer;" onclick='_navTickerAc(${JSON.stringify(h).replace(/'/g, "&#39;")})'>
          <span class="label" style="background:rgba(45,158,107,.18);color:var(--bright);border:1px solid rgba(45,158,107,.3);">
            ${(Array.isArray(h.etiketler) ? h.etiketler[0] : h.kategori || h.etiket || h.kaynak || "HABER").toString().slice(0, 14).toUpperCase()}
          </span>
          ${h.baslik}${h.kaynak ? ` <span style="opacity:.5;font-size:.85em;">— ${h.kaynak}</span>` : ""}
        </div>`).join("");
      document.getElementById("navTickerInner").innerHTML = items + items;
    }

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
        const h = SITE.getList("haberler") || [];
        if (h.length) _tickerRender(h);
      }
    }
  }
})();

function _navTickerAc(h) {
  const etiketler = Array.isArray(h.etiketler) ? h.etiketler.join(" · ") : (h.kategori || h.etiket || h.kaynak || "");
  const m = document.createElement("div");
  m.style.cssText = "position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,.75);display:flex;align-items:center;justify-content:center;padding:20px;backdrop-filter:blur(4px);";
  m.innerHTML = `
    <div style="background:var(--deep);border:1px solid rgba(45,158,107,.25);border-radius:8px;
                max-width:640px;width:100%;padding:32px;position:relative;">
      <button onclick="this.closest('div[style]').remove()"
        style="position:absolute;top:16px;right:16px;background:none;border:none;
               color:var(--muted);font-size:20px;cursor:pointer;">✕</button>
      <div style="font-family:'JetBrains Mono',monospace;font-size:9px;letter-spacing:.1em;
                  text-transform:uppercase;color:var(--accent);margin-bottom:12px;">${etiketler}</div>
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

function adminCikis() {
  if (typeof SITE !== "undefined" && typeof SITE.logout === "function") SITE.logout();
  else sessionStorage.removeItem("ekoloji_admin_session");
  location.reload();
}
