/**
 * nav.js — Ortak navigasyonu her sayfaya enjekte eder.
 * Her sayfanın <body> başında <div id="nav-root"></div> olmalı.
 * Kullanım: <script src="../nav.js"></script> veya <script src="nav.js"></script>
 */
(function () {
  const pages = {
    "index.html":         "",
    "ihlaller.html":      "İhlaller",
    "madenler.html":      "İzleme Konuları",
    "raporlar.html":      "Raporlar",
    "ekoloji-suclari.html": "Ekoloji Suçları",
    "etkinlikler.html":   "Etkinlikler",
    "karsı-durus.html":   "Karşı Duruş",
    "ekosistem.html":     "Ekosistem",
    "admin.html":         "",
  };

  const current = location.pathname.split("/").pop() || "index.html";
  const isAdmin = typeof SITE !== "undefined" && SITE.isAdmin();

  const html = `
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
      <a href="ekoloji-suclari.html" class="nav-link ${current === 'ekoloji-suclari.html' ? 'active' : ''}">Ekoloji Suçları
        <svg viewBox="0 0 10 6" fill="currentColor"><path d="M0 0l5 6 5-6z"/></svg>
      </a>
      <div class="dropdown">
        <a href="ihlaller.html"><span class="dot"></span>Ekolojik İhlaller (Günlük Tarama)</a>
        <hr>
        <div class="dropdown-label">Haberler &amp; Direniş</div>
        <a href="haberler.html"><span class="dot"></span>Basın Haberleri</a>
        <a href="haberler.html?tur=sosyal"><span class="dot"></span>Sosyal Medya Takibi</a>
        <a href="haberler.html?tur=hareket"><span class="dot"></span>Halk Hareketleri</a>
        <a href="haberler.html?tur=nobet"><span class="dot"></span>Nöbetler &amp; Protestolar</a>
        <a href="haberler.html?tur=direnis"><span class="dot"></span>Yerel Direnişler</a>
      </div>
    </li>

    <li class="nav-item">
      <a href="etkinlikler.html" class="nav-link ${current === 'etkinlikler.html' ? 'active' : ''}">Etkinlikler</a>
    </li>

    <li class="nav-item">
      <a href="karsı-durus.html" class="nav-link ${current === 'karsı-durus.html' ? 'active' : ''}">Karşı Duruş
        <svg viewBox="0 0 10 6" fill="currentColor"><path d="M0 0l5 6 5-6z"/></svg>
      </a>
      <div class="dropdown">
        <a href="karsı-durus.html?sec=hukuk"><span class="dot"></span>Hukuki Mücadele</a>
        <a href="karsı-durus.html?sec=stk"><span class="dot"></span>Sivil Toplum Ağı</a>
        <a href="karsı-durus.html?sec=kampanya"><span class="dot"></span>Farkındalık Kampanyaları</a>
        <a href="karsı-durus.html?sec=uluslararasi"><span class="dot"></span>Uluslararası Bağlantılar</a>
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
    <a href="admin.html" style="font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--muted);text-decoration:none;letter-spacing:.08em;padding:6px 12px;border:1px solid rgba(45,158,107,.2);border-radius:3px;transition:all .2s;" onmouseover="this.style.color='var(--bright)';this.style.borderColor='rgba(45,158,107,.4)'" onmouseout="this.style.color='var(--muted)';this.style.borderColor='rgba(45,158,107,.2)'">ADMIN</a>
  </div>

  <div class="hamburger" onclick="document.querySelector('.nav-menu').style.display=document.querySelector('.nav-menu').style.display==='flex'?'none':'flex'">
    <span></span><span></span><span></span>
  </div>
</nav>`;

  const root = document.getElementById("nav-root");
  if (root) root.innerHTML = html;
  else document.body.insertAdjacentHTML("afterbegin", html);
})();
