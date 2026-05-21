#!/usr/bin/env python3
"""
admin.html'deki eski veriYaz bloğunu yeni versiyonla değiştirir.
Sunucuda çalıştır: python3 patch_admin.py
"""
import re, shutil, datetime

SRC = "admin.html"
DST = f"admin_yedek_{datetime.date.today()}.html"

with open(SRC, 'r', encoding='utf-8') as f:
    html = f.read()

# Eski veriYaz bloğunu bul
PATTERN = r'/\* ═══ VERİ\.JSON OTO-SYNC.*?(?=\n</script>)'
match = re.search(PATTERN, html, re.DOTALL)
if not match:
    print("❌ Eski veriYaz bloğu bulunamadı!")
    exit(1)

print(f"✓ Eski blok bulundu ({len(match.group())} karakter)")

# Yedeği al
shutil.copy(SRC, DST)
print(f"✓ Yedek: {DST}")

NEW_FUNC = r'''/* ═══ VERİ.JSON OTO-SYNC — DÜZELTİLMİŞ v5 ═══════════════════════
   1) GitHub API ile data.json'u güncelle (raporlar/makaleler/uluslararasi)
   2) webhook.php'ye POST at → Flex sunucusunu güncelle
   Her iki adım bağımsız çalışır; biri başarısız olursa diğeri devam eder.
══════════════════════════════════════════════════════════════════ */
async function veriYaz() {
  const { repo, token } = ghAyarAl();
  const flexUrl    = localStorage.getItem("ekoloji_flex_url")    || "";
  const flexSecret = localStorage.getItem("ekoloji_flex_secret") || "";

  if (!flexUrl && (!repo || !token)) { setSyncDurum("local"); return; }
  setSyncDurum("syncing");
  let githubOk = false, flexOk = false;

  // ── 1) GitHub API ──────────────────────────────────────────────
  if (repo && token) {
    const [ow, rn] = repo.split("/");
    try {
      const mr = await fetch(
        `https://api.github.com/repos/${ow}/${rn}/contents/data.json`,
        { headers: { "Authorization": `Bearer ${token}`, "Accept": "application/vnd.github+json" } }
      );
      if (!mr.ok) throw new Error(`data.json okunamadı (HTTP ${mr.status})`);
      const md  = await mr.json();
      const sha = md.sha;

      // UTF-8 güvenli decode (Türkçe karakter fix)
      const raw    = md.content.replace(/\n/g, "");
      const bytes  = Uint8Array.from(atob(raw), c => c.charCodeAt(0));
      const mevcut = JSON.parse(new TextDecoder("utf-8").decode(bytes));

      mevcut.raporlar     = SITE.getList("raporlar");
      mevcut.makaleler    = SITE.getList("makaleler");
      mevcut.uluslararasi = SITE.getList("uluslararasi");
      mevcut._meta = { ...(mevcut._meta || {}),
        guncelleme: new Date().toISOString(),
        rapor_sayisi:  mevcut.raporlar.length,
        makale_sayisi: mevcut.makaleler.length,
        ulus_sayisi:   mevcut.uluslararasi.length };

      // UTF-8 güvenli encode
      const encoded = new TextEncoder().encode(JSON.stringify(mevcut, null, 2));
      const b64     = btoa(String.fromCharCode(...encoded));

      const pr = await fetch(
        `https://api.github.com/repos/${ow}/${rn}/contents/data.json`,
        { method: "PUT",
          headers: { "Authorization": `Bearer ${token}`,
                     "Accept": "application/vnd.github+json",
                     "Content-Type": "application/json" },
          body: JSON.stringify({
            message: `admin: içerik güncellendi ${new Date().toISOString().slice(0,10)}`,
            content: b64, sha }) }
      );
      if (pr.ok) {
        githubOk = true;
        _actionsDispatch(ow, rn, token).catch(() => {});
      } else {
        const e = await pr.json().catch(() => ({}));
        setSyncDurum("error", `HTTP ${pr.status}`);
        toast(`⚠ GitHub: HTTP ${pr.status} — ${e.message || ""}`, 5000);
      }
    } catch (e) {
      setSyncDurum("error", e.message.slice(0,40));
      toast("⚠ " + e.message, 5000);
    }
  }

  // ── 2) Webhook (Flex/Plesk) ────────────────────────────────────
  if (flexUrl) {
    try {
      const payload = JSON.stringify({
        raporlar:     SITE.getList("raporlar"),
        makaleler:    SITE.getList("makaleler"),
        uluslararasi: SITE.getList("uluslararasi"),
        _meta: { guncelleme: new Date().toISOString() }
      });
      const wr = await fetch(flexUrl + "?dosya=data.json", {
        method: "POST",
        headers: { "Content-Type": "application/json",
                   "X-Webhook-Secret": flexSecret },
        body: payload
      });
      if (wr.ok) { flexOk = true; console.log("✓ Flex OK:", await wr.text()); }
      else { toast(`⚠ Webhook: HTTP ${wr.status}`, 4000); }
    } catch (e) { toast("⚠ Webhook: " + e.message.slice(0,60), 4000); }
  }

  if (githubOk || flexOk) setSyncDurum("synced");
  else setSyncDurum("error", "her iki hedef başarısız");
}

async function _actionsDispatch(owner, repoName, token) {
  const rd = await fetch(`https://api.github.com/repos/${owner}/${repoName}`,
    { headers: { "Authorization": `Bearer ${token}`, "Accept": "application/vnd.github+json" } });
  const d  = await rd.json();
  const br = d.default_branch || "main";
  const wf = localStorage.getItem("ekoloji_gh_workflow") || "update_data.yml";
  await fetch(`https://api.github.com/repos/${owner}/${repoName}/actions/workflows/${wf}/dispatches`,
    { method: "POST",
      headers: { "Authorization": `Bearer ${token}`, "Accept": "application/vnd.github+json",
                 "Content-Type": "application/json" },
      body: JSON.stringify({ ref: br }) });
}'''

html_new = html[:match.start()] + NEW_FUNC + html[match.end():]

with open(SRC, 'w', encoding='utf-8') as f:
    f.write(html_new)

print(f"✅ admin.html güncellendi! (eski: {len(html)}, yeni: {len(html_new)} karakter)")
