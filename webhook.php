<?php
/**
 * webhook.php — Plesk dosya alıcısı + Bot tetikleyici v2
 * ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 * Sunucuda httpdocs/ kök dizinine koyun.
 *
 * Action'lar:
 *   POST ?action=tara  &token=SECRET  → bot.py çalıştırır (arka planda)
 *   GET  ?action=durum &token=SECRET  → son tarama durumunu döner
 *   POST ?dosya=x.json &token=SECRET  → JSON dosyası yazar (eski davranış)
 */

// ── Ayarlar ─────────────────────────────────────────────────────────────
define('SECRET',      getenv('WEBHOOK_SECRET') ?: 'Smtppl5862');
define('PYTHON',      '/usr/bin/python3');          // Plesk'te doğru yolu kontrol edin
define('BOT_SCRIPT',  __DIR__ . '/bot.py');
define('LOG_DOSYA',   __DIR__ . '/bot.log');
define('KILITDOSYA',  sys_get_temp_dir() . '/ekoloji_bot.lock');
define('IZIN_DOSYA',  ['data.json', 'ihlaller.json', 'haberler.json', 'rapor.json', 'icerik.json',
                        'raporlar.json', 'makaleler.json', 'ekosistem.json', 'kuresel.json']);
define('HEDEF_DIZIN', __DIR__ . '/');
// ────────────────────────────────────────────────────────────────────────

header('Content-Type: application/json; charset=utf-8');

// ── Token doğrula ────────────────────────────────────────────────────────
$token_header = $_SERVER['HTTP_X_WEBHOOK_SECRET'] ?? '';
$token_query  = $_GET['token'] ?? '';
if ($token_header !== SECRET && $token_query !== SECRET) {
    http_response_code(403);
    echo json_encode(['ok' => false, 'hata' => 'Geçersiz token']);
    exit;
}

$action = $_GET['action'] ?? '';

// ════════════════════════════════════════════════════════════════════════
// ACTION: tara — bot.py'yi arka planda başlatır
// ════════════════════════════════════════════════════════════════════════
if ($action === 'tara') {
    if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
        http_response_code(405);
        echo json_encode(['ok' => false, 'hata' => 'POST gerekli']);
        exit;
    }

    // bot.py dosyası var mı?
    if (!file_exists(BOT_SCRIPT)) {
        http_response_code(500);
        echo json_encode(['ok' => false, 'hata' => 'bot.py bulunamadı: ' . BOT_SCRIPT]);
        exit;
    }

    // Zaten çalışıyor mu? (kilit dosyasına bak)
    if (file_exists(KILITDOSYA)) {
        $pid = trim(file_get_contents(KILITDOSYA));
        // PID hâlâ aktif mi?
        if ($pid && file_exists("/proc/$pid")) {
            echo json_encode([
                'ok'    => true,
                'durum' => 'zaten_calisiyor',
                'pid'   => (int)$pid,
                'mesaj' => 'Bot zaten çalışıyor, lütfen bekleyin.'
            ]);
            exit;
        }
        // Eski kilit dosyasını temizle
        @unlink(KILITDOSYA);
    }

    // Arka planda başlat
    $python = escapeshellcmd(PYTHON);
    $script = escapeshellarg(BOT_SCRIPT);
    $log    = escapeshellarg(LOG_DOSYA);
    $kilit  = escapeshellarg(KILITDOSYA);
    $dizin  = escapeshellarg(__DIR__);

    // nohup ile arka planda çalıştır, PID'i kilit dosyasına yaz
    $cmd = "cd $dizin && nohup $python $script >> $log 2>&1 & echo \$! > $kilit";
    shell_exec($cmd);

    // Küçük bir bekleme ile PID'i oku
    usleep(200000); // 0.2sn
    $pid = file_exists(KILITDOSYA) ? trim(file_get_contents(KILITDOSYA)) : '?';

    echo json_encode([
        'ok'    => true,
        'durum' => 'baslatildi',
        'pid'   => (int)$pid,
        'log'   => LOG_DOSYA,
        'mesaj' => 'Bot arka planda başlatıldı.'
    ]);
    exit;
}

// ════════════════════════════════════════════════════════════════════════
// ACTION: durum — son log satırlarını döner
// ════════════════════════════════════════════════════════════════════════
if ($action === 'durum') {
    $calisiyor = false;
    $pid       = null;

    if (file_exists(KILITDOSYA)) {
        $pid = (int)trim(file_get_contents(KILITDOSYA));
        $calisiyor = $pid && file_exists("/proc/$pid");
    }

    // Son log satırları
    $log_satirlar = [];
    if (file_exists(LOG_DOSYA)) {
        $satirlar = file(LOG_DOSYA, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
        $log_satirlar = array_slice($satirlar, -30); // son 30 satır
    }

    // JSON dosyalarının boyutları
    $dosya_durumu = [];
    foreach (['haberler.json', 'ihlaller.json', 'raporlar.json', 'makaleler.json',
              'ekosistem.json', 'kuresel.json'] as $d) {
        $yol = HEDEF_DIZIN . $d;
        $dosya_durumu[$d] = file_exists($yol)
            ? ['boyut_kb' => round(filesize($yol) / 1024, 1),
               'degistirme' => date('Y-m-d H:i:s', filemtime($yol))]
            : null;
    }

    echo json_encode([
        'ok'          => true,
        'calisiyor'   => $calisiyor,
        'pid'         => $pid,
        'log'         => $log_satirlar,
        'dosyalar'    => $dosya_durumu,
        'zaman'       => date('Y-m-d H:i:s T'),
    ]);
    exit;
}

// ════════════════════════════════════════════════════════════════════════
// Varsayılan: JSON dosyası yaz (eski davranış — GitHub Actions uyumlu)
// ════════════════════════════════════════════════════════════════════════
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['ok' => false, 'hata' => 'Yalnızca POST kabul edilir']);
    exit;
}

$dosya = $_GET['dosya'] ?? $_GET['file'] ?? 'data.json';
$dosya = basename($dosya);

if (!in_array($dosya, IZIN_DOSYA, true)) {
    http_response_code(400);
    echo json_encode(['ok' => false, 'hata' => 'İzin verilmeyen dosya: ' . $dosya]);
    exit;
}

$icerik = file_get_contents('php://input');
if ($icerik === false || strlen($icerik) < 2) {
    http_response_code(400);
    echo json_encode(['ok' => false, 'hata' => 'Boş içerik']);
    exit;
}

json_decode($icerik);
if (json_last_error() !== JSON_ERROR_NONE) {
    http_response_code(400);
    echo json_encode(['ok' => false, 'hata' => 'Geçersiz JSON: ' . json_last_error_msg()]);
    exit;
}

$hedef  = HEDEF_DIZIN . $dosya;
$gecici = $hedef . '.tmp.' . uniqid();

if (file_put_contents($gecici, $icerik) === false) {
    http_response_code(500);
    echo json_encode(['ok' => false, 'hata' => 'Dosya yazılamadı']);
    exit;
}

if (!rename($gecici, $hedef)) {
    @unlink($gecici);
    http_response_code(500);
    echo json_encode(['ok' => false, 'hata' => 'Dosya taşınamadı']);
    exit;
}

echo json_encode([
    'ok'    => true,
    'dosya' => $dosya,
    'boyut' => strlen($icerik),
    'zaman' => date('Y-m-d H:i:s T'),
]);
