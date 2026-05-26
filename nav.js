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
        <a href="makaleler.html?tur=Akademik
