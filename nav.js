/**
 * nav.js — Ortak Navigasyonu ve Canlı Haber Bandını Enjekte Eden Güvenli Script
 */
(function () {
  const SESSION_KEY = "ekoloji_admin_session";
  
  // Güvenli oturum kontrolü
  const adminAktif = (function() {
    const token = sessionStorage.getItem(SESSION_KEY);
    return token !== null && token.length > 15;
  })();
  
  const current = location.pathname.split("/").pop() || "index.html";

  // Çekilen haber verilerinin XSS riski olmadan hafızada tutulacağı yerel dizi
  let loadedTickerHaberler = [];

  // Stil Enjeksiyonu: CSS kodlarını HTML şablonundan ayırarak performansı ve güvenliği artırır
  const inlineStyles = `
    .nav-admin-wrapper { display: flex; align-items: center; gap: 8px; }
    .btn-admin-panel {
      font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--bright);
      text-decoration: none; letter-spacing: .08em; padding: 5px 12px;
      border: 1px solid rgba(45,158,107,.45); border-radius: 3px;
      background: rgba(45,158,107,.08); display: flex; align-items: center; gap: 6px;
      transition: all .2s;
    }
    .btn-admin-panel:hover { background: rgba(45,158,107,.18); }
    .btn-admin-logout {
      font-family: 'JetBrains Mono', monospace; font-size: 9px; color: var(--muted);
      letter-spacing: .06em; padding: 5px 10px; border: 1px solid rgba(232,92,42,.25);
      border-radius: 3px; background: transparent; cursor: pointer; transition: all .2s;
    }
    .btn-admin-logout:hover { color: var(--warn); border-color: rgba(232,92,42,.5); }
    .btn-admin-login {
      font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--muted);
      text-decoration: none; letter-spacing: .08em; padding: 6px 12px;
      border: 1px solid rgba(45,158,107,.2); border-radius: 3px; transition: all .2s;
    }
    .btn-admin-login:hover { color: var(--bright); border-color: rgba(45,158,107,.4); }
    .ticker-item-secure { cursor: pointer; display: inline-flex; align-items: center; gap: 6px; }
    .ticker-item-secure .label {
      background: rgba(45,158,107,.18); color: var(--bright); border: 1px solid rgba(45,158,107,.3);
      padding: 2px 6px; border-radius: 2px; font-size: 0.85em; font-weight: bold;
    }
    .ticker-item-secure .source-span { opacity: .5; font-size: .85em; }
    .modal-overlay-secure {
      position: fixed; inset: 0; z-index: 9999; background: rgba(0,0,0,.75);
      display: flex; align-items: center; justify-content: center; padding: 20px; backdrop-filter: blur(4px);
    }
    .modal-content-secure {
      background: var(--deep); border: 1px solid rgba(45,158,107,.25); border-radius: 8px;
      max-width: 640px; width: 100%; padding: 32px; position: relative;
    }
    .modal-close-secure {
      position: absolute; top: 16px; right: 16px; background: none; border: none;
      color: var(--muted); font-size: 20px; cursor: pointer;
    }
    .modal-tag-secure {
      font-family: 'JetBrains Mono', monospace; font-size: 9px; letter-spacing: .1em;
      text-transform: uppercase; color: var(--accent); margin-bottom: 12px;
    }
    .modal-title-secure {
      font-family: 'Crimson Pro', serif; font-size: 24px; font-weight: 400;
      color: var(--cream); line-height: 1.4; margin: 0 0 16px;
    }
    .modal-body-secure { font-size: 14px; color: var(--muted); line-height: 1.7; margin: 0 0 20px; }
    .modal-link-secure {
      display: inline-flex; align-items: center; gap: 8px; padding: 10px 18px;
      background: var(--accent); color: var(--dark); font-family: 'JetBrains Mono', monospace;
      font-size: 10px; letter-spacing: .08em; text-decoration: none; border-radius: 4px;
      text-transform: uppercase;
    }
  `;

  // CSS'i dökümana güvenli bir şekilde ekle
  const styleSheet = document.createElement("style");
  styleSheet.textContent = inlineStyles;
  document.head.appendChild(styleSheet);

  // Admin Kontrol Buton Şablonu
  const adminBtnHTML = adminAktif
    ? `<div class="nav-admin-wrapper">
         <a href="admin.html" class="btn-admin-panel">
           <span style="display:inline-block;width:6px;height:6px;border-radius:50%;
                        background:var(--bright);box-shadow:0 0 6px var(--bright);"></span>
           ADMIN
         </a>
         <button id="navLogoutBtn" class="btn-admin-logout">Çıkış</button>
       </div>`
    : `<a href="admin.html" class="btn-admin-login">ADMIN</a>`;

  // Tam Navigasyon HTML Şablonu
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
        <a href="ihlaller.html?kat=Maden"><span class="dot"></span>Maden Projeleri</a>
        <a href="ihlaller.html?kat=Taş-Mermer"><span class="dot"></span>Taş-Mermer Ocakları</a>
        <a href="ihlaller.html?kat=Termik"><span class="dot"></span>Termik Reaktörler</a>
        <a href="ihlaller.html?kat=HES"><span class="dot"></span>HES & Nehir Projeleri</a>
        <a href="ihlaller.html?kat=RES"><span class="dot"></span>RES & Rüzgar Santralleri</a>
        <a href="ihlaller.html?kat=GES"><span class="dot"></span>GES & Güneş Santralleri</a>
        <a href="ihlaller.html?kat=Nükleer"><span class="dot"></span>Nükleer Enerji</a>
        <a href="ihlaller.html?kat=Jeotermal"><span class="dot"></span>Jeotermal</a>
        <a href="ihlaller.html?kat=Enerji Lisans"><span class="dot"></span>Enerji Lisansları (EPDK)</a>
        <a href="ihlaller.html?kat=Ruhsat"><span class="dot"></span>Maden Ruhsatları (MAPEG)</a>
        <hr>
        <div class="dropdown-label">Koruma Alanları</div>
        <a href="ihlaller.html?kat=Milli Park"><span class="dot"></span>Milli Parklar</a>
        <a href="ihlaller.html?kat=Özel Çevre Koruma Alanı"><span class="dot"></span>Özel Çevre Koruma Alanları</a>
        <a href="ihlaller.html?kat=Orman Alanı"><span class="dot"></span>Orman Alanları</a>
        <a href="ihlaller.html?kat=Sulak Alan"><span class="dot"></span>Sulak Alanlar</a>
        <a href="ihlaller.html?kat=Kültür Varlığı"><span class="dot"></span>Kültür Varlıkları</a>
        <hr>
        <div class="dropdown-label">Diğer İhlaller</div>
        <a href="ihlaller.html?kat=Acele Kamulaştırma"><span class="dot"></span>Acele Kamulaştırma</a>
        <a href="ihlaller.html?kat=Kıyı İhlalleri"><span class="dot"></span>Kıyı İhlalleri</a>
        <a href="ihlaller.html?kat=Ekolojik İhlal"><span class="dot"></span>Genel Ekolojik İhlaller</a>
        <a href="ihlaller.html?kat=ÇED"><span class="dot"></span>ÇED Kararları</a>
        <hr>
        <div class="dropdown-label">Canlı Hakları</div>
        <a href="ihlaller.html?kat=Hayvan"><span class="dot"></span>Hayvan Hakları</a>
        <a href="ihlaller.html?kat=İnsan Hakları"><span class="dot"></span>İnsan Hakları</a>
        <a href="ihlaller.html?kat=Köylü"><span class="dot"></span>Çiftçi & Köylü Hakları</a>
      </div>
    </li>

    <li class="nav-item">
      <a href="haberler.html" class="nav-link ${current === 'haberler.html' ? 'active' : ''}">Haberler
        <svg viewBox="0 0 10 6" fill="currentColor"><path d="M0 0l5 6 5-6z"/></svg>
      </a>
      <div class="dropdown">
        <a href="haberler.html"><span class="dot"></span>Tüm Haberler</a>
        <hr>
        <div class="dropdown-label">Konu</div>
        <a href="haberler.html?hkat=%C4%B0klim+ve+Afet"><span class="dot"></span>İklim & Afet</a>
        <a href="haberler.html?hkat=Maden+ve+Enerji"><span class="dot"></span>Maden & Enerji</a>
        <a href="haberler.html?hkat=Orman+ve+Do%C4%9Fa"><span class="dot"></span>Orman & Doğa</a>
        <a href="haberler.html?hkat=Su+ve+K%C4%B1y%C4%B1"><span class="dot"></span>Su & Kıyı</a>
        <a href="haberler.html?hkat=Yaban+Hayat%C4%B1"><span class="dot"></span>Yaban Hayatı</a>
        <hr>
        <div class="dropdown-label">Eylem & Toplum</div>
        <a href="haberler.html?hkat=Direni%C5%9F+ve+Eylemler"><span class="dot"></span>Direniş & Eylemler</a>
        <a href="haberler.html?hkat=Hukuki+S%C3%BCre%C3%A7ler"><span class="dot"></span>Hukuki Süreçler</a>
        <a href="haberler.html?hkat=N%C3%B6betler+ve+G%C3%B6zalt%C4%B1lar"><span class="dot"></span>Nöbetler & Gözaltılar</a>
        <a href="haberler.html?hkat=STK+%26+Kampanyalar"><span class="dot"></span>STK & Kampanyalar</a>
        <hr>
        <a href="arsiv.html"><span class="dot"></span>Arşiv</a>
      </div>
    </li>

    <li class="nav-item">
      <a href="raporlar.html" class="nav-link ${current === 'raporlar.html' ? 'active' : ''}">Raporlar
        <svg viewBox="0 0 10 6" fill="currentColor"><path d="M0 0l5 6 5-6z"/></svg>
      </a>
      <div class="dropdown">
        <a href="raporlar.html"><span class="dot"></span>Tüm Raporlar</a>
        <hr>
        <div class="dropdown-label">Konu</div>
        <a href="raporlar.html?hkat=%C4%B0klim+ve+Afet"><span class="dot"></span>İklim & Afet</a>
        <a href="raporlar.html?hkat=Maden+ve+Enerji"><span class="dot"></span>Maden & Enerji</a>
        <a href="raporlar.html?hkat=Orman+ve+Do%C4%9Fa"><span class="dot"></span>Orman & Doğa</a>
        <a href="raporlar.html?hkat=Su+ve+K%C4%B1y%C4%B1"><span class="dot"></span>Su & Kıyı</a>
        <a href="raporlar.html?hkat=Yaban+Hayat%C4%B1"><span class="dot"></span>Yaban Hayatı</a>
        <hr>
        <div class="dropdown-label">Eylem & Toplum</div>
        <a href="raporlar.html?hkat=Direni%C5%9F+ve+Eylemler"><span class="dot"></span>Direniş & Eylemler</a>
        <a href="raporlar.html?hkat=Hukuki+S%C3%BCre%C3%A7ler"><span class="dot"></span>Hukuki Süreçler</a>
        <a href="raporlar.html?hkat=N%C3%B6betler+ve+G%C3%B6zalt%C4%B1lar"><span class="dot"></span>Nöbetler & Gözaltılar</a>
        <a href="raporlar.html?hkat=STK+%26+Kampanyalar"><span class="dot"></span>STK & Kampanyalar</a>
      </div>
    </li>

    <li class="nav-item">
      <a href="makaleler.html" class="nav-link ${current === 'makaleler.html' ? 'active' : ''}">Makaleler
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
      </div>
    </li>

    <li class="nav-item">
      <a href="kuresel.html" class="nav-link ${current === 'kuresel.html' ? 'active' : ''}">Küresel
        <svg viewBox="0 0 10 6" fill="currentColor"><path d="M0 0l5 6 5-6z"/></svg>
      </a>
      <div class="dropdown">
        <div class="dropdown-label">İçerik Türü</div>
        <a href="kuresel.html"><span class="dot"></span>Tüm İçerik</a>
        <a href="kuresel.html?tur=Haber"><span class="dot"></span>Haberler</a>
        <a href="kuresel.html?tur=Rapor"><span class="dot"></span>Raporlar</a>
        <a href="kuresel.html?tur=Araştırma"><span class="dot"></span>Araştırmalar</a>
        <a href="kuresel.html?tur=Analiz"><span class="dot"></span>Analizler</a>
        <a href="kuresel.html?tur=Aktivizm"><span class="dot"></span>Aktivizm</a>
        <a href="kuresel.html?tur=Politika"><span class="dot"></span>Politika</a>
        <a href="kuresel.html?tur=Uluslararas%C4%B1+Medya"><span class="dot"></span>Uluslararası Medya</a>
        <hr>
        <div class="dropdown-label">Dile Göre</div>
        <a href="kuresel.html?dil=EN"><span class="dot"></span>🇬🇧 İngilizce</a>
        <a href="kuresel.html?dil=DE"><span class="dot"></span>🇩🇪 Almanca</a>
        <a href="kuresel.html?dil=FR"><span class="dot"></span>🇫🇷 Fransızca</a>
        <a href="kuresel.html?dil=ES"><span class="dot"></span>🇪🇸 İspanyolca</a>
        <a href="kuresel.html?dil=AR"><span class="dot"></span>🇸🇦 Arapça</a>
        <a href="kuresel.html?dil=EL"><span class="dot"></span>🇬🇷 Yunanca</a>
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
    <li class="nav-item">
      <a href="arsiv.html" class="nav-link ${current === 'arsiv.html' ? 'active' : ''}">Arşiv</a>
    </li>
  </ul>

  <div style="display:flex;align-items:center;gap:16px;">
    <div class="rec-indicator">
      <div class="rec-dot"></div> CANLI İZLEME
    </div>
    ${adminBtnHTML}
  </div>

  <div class="hamburger">
    <span></span><span></span><span></span>
  </div>
</nav>

<div class="ticker-bar" id="navTicker" style="display:none;">
  <div class="ticker-inner" id="navTickerInner"></div>
</div>`;

  // DOM enjeksiyonu
  const root = document.getElementById("nav-root");
  if (root) root.innerHTML = navHTML;
  else document.body.insertAdjacentHTML("afterbegin", navHTML);

  // Hamburger mobil menü etkileşimi (Inline JS yerine temiz Olay Dinleyici)
  const hamburger = document.querySelector(".hamburger");
  const navMenu = document.querySelector(".nav-menu");
  if (hamburger && navMenu) {
    hamburger.addEventListener("click", function() {
      const isFlex = window.getComputedStyle(navMenu).display === "flex";
      navMenu.style.display = isFlex ? "none" : "flex";
    });
  }

  // Çıkış butonu olayı (Eğer buton DOM'da mevcutsa)
  const logoutBtn = document.getElementById("navLogoutBtn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", function() {
      if (typeof SITE !== "undefined" && typeof SITE.logout === "function") {
        SITE.logout();
      } else {
        sessionStorage.removeItem(SESSION_KEY);
      }
      location.reload();
    });
  }

  // Ticker Mantığı Başlangıcı
  const mevcutTicker = document.getElementById("tickerInner");
  if (mevcutTicker) {
    const navTickerBar = document.getElementById("navTicker");
    if (navTickerBar) navTickerBar.style.display = "none";
  } else {
    _tickerYukle();
  }

  function _tickerYukle() {
    const bar = document.getElementById("navTicker");
    const innerContainer = document.getElementById("navTickerInner");
    if (!bar || !innerContainer) return;

    function _tickerRender(haberler) {
      const silinen = (() => {
        try { return new Set(JSON.parse(localStorage.getItem("ekoloji_haber_silinen") || "[]").map(String)); }
        catch { return new Set(); }
      })();
      
      const liste = haberler.filter(h => h && !silinen.has(String(h.id))).slice(0, 12);
      if (!liste.length) return;
      
      // Haberleri XSS yapmadan referanslamak için yerel modül dizisine kaydet
      loadedTickerHaberler = liste;
      bar.style.display = "block";
      innerContainer.innerHTML = ""; // İçeriği temizle

      // DOM nesnelerini güvenli döngü ile oluşturma (String birleştirme yerine el ile veya kontrollü şablonla)
      const fragment = document.createDocumentFragment();
      
      // Çift kayma efekti için diziyi iki kez dönüyoruz
      for (let i = 0; i < 2; i++) {
        liste.forEach((h, index) => {
          const itemDiv = document.createElement("div");
          itemDiv.className = "ticker-item-secure";
          itemDiv.setAttribute("data-index", index); // Veriyi indis üzerinden eşleştiriyoruz (Güvenli!)

          const etiketStr = (Array.isArray(h.etiketler) && h.etiketler[0])
            ? h.etiketler[0]
            : (h.kategori || h.etiket || h.kaynak || "HABER");
          const etiketGoster = String(etiketStr || "HABER").slice(0, 14).toUpperCase();

          // İç etiket elementi (XSS korumalı textContent)
          const labelSpan = document.createElement("span");
          labelSpan.className = "label";
          labelSpan.textContent = etiketGoster;
          itemDiv.appendChild(labelSpan);

          // Başlık metni
          const titleText = document.createTextNode(" " + (h.baslik || ""));
          itemDiv.appendChild(titleText);

          // Kaynak metni
          if (h.kaynak) {
            const sourceSpan = document.createElement("span");
            sourceSpan.className = "source-span";
            sourceSpan.textContent = ` — ${h.kaynak}`;
            itemDiv.appendChild(sourceSpan);
          }

          fragment.appendChild(itemDiv);
        });
      }
      innerContainer.appendChild(fragment);
    }

    // Haberleri JSON servisinden çekme
    fetch("haberler.json?v=" + Date.now())
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => {
        const haberler = data && data.haberler ? data.haberler : (Array.isArray(data) ? data : []);
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

  // Ticker Tıklama Yakalayıcısı (Event Delegation - Güvenli Dinleyici)
  const tickerInnerEl = document.getElementById("navTickerInner");
  if (tickerInnerEl) {
    tickerInnerEl.addEventListener("click", function(e) {
      const targetItem = e.target.closest(".ticker-item-secure");
      if (!targetItem) return;
      
      const index = targetItem.getAttribute("data-index");
      const secilenHaber = loadedTickerHaberler[index];
      
      if (secilenHaber) {
        _navTickerModalAc(secilenHaber);
      }
    });
  }

  /**
   * Güvenli Ticker Detay Modal Penceresi (XSS Korumalı)
   * @param {Object} h - Haber nesnesi
   */
  function _navTickerModalAc(h) {
    const etiketler = Array.isArray(h.etiketler) ? h.etiketler.join(" · ") : (h.kategori || h.etiket || h.kaynak || "");
    
    // Modal kapsayıcı katmanı
    const overlay = document.createElement("div");
    overlay.className = "modal-overlay-secure";
    
    // Modal iç içerik kutusu
    const contentBox = document.createElement("div");
    contentBox.className = "modal-content-secure";
    
    // Kapatma butonu
    const closeBtn = document.createElement("button");
    closeBtn.className = "modal-close-secure";
    closeBtn.textContent = "✕";
    closeBtn.addEventListener("click", () => overlay.remove());
    contentBox.appendChild(closeBtn);
    
    // Kategori/Etiket alanı
    const tagDiv = document.createElement("div");
    tagDiv.className = "modal-tag-secure";
    tagDiv.textContent = etiketler;
    contentBox.appendChild(tagDiv);
    
    // Başlık
    const titleH3 = document.createElement("h3");
    titleH3.className = "modal-title-secure";
    titleH3.textContent = h.baslik || "";
    contentBox.appendChild(titleH3);
    
    // Özet içerik metni
    const bodyP = document.createElement("p");
    bodyP.className = "modal-body-secure";
    bodyP.textContent = h.ozet || "";
    contentBox.appendChild(bodyP);
    
    // Dış Bağlantı (Eğer URL mevcutsa)
    if (h.url) {
      const linkA = document.createElement("a");
      linkA.className = "modal-link-secure";
      linkA.href = h.url;
      linkA.target = "_blank";
      linkA.rel = "noopener noreferrer";
      linkA.textContent = "Kaynağa Git ↗";
      contentBox.appendChild(linkA);
    }
    
    overlay.appendChild(contentBox);
    
    // Arka plana tıklandığında kapanma özelliği
    overlay.addEventListener("click", function(e) {
      if (e.target === overlay) overlay.remove();
    });
    
    document.body.appendChild(overlay);
  }
})();
