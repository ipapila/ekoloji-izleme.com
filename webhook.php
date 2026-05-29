<?php
/**
 * webhook.php — Plesk dosya alıcısı + Bot tetikleyici v2
 */

define('SECRET',      getenv('WEBHOOK_SECRET') ?: 'Smtppl5862');
@ini_set('post_max_size', '32M');
@ini_set('upload_max_filesize', '32M');
@ini_set('memory_limit', '256M');
define('PYTHON',      '/usr/bin/python3');
define('BOT_SCRIPT',  __DIR__ . '/bot.py');
define('LOG_DOSYA',   __DIR__ . '/bot.log');
define('KILITDOSYA',  sys_get_temp_dir() . '/ekoloji_bot.lock');
define('IZIN_DOSYA',  [
    'data.json', 'ihlaller.json', 'haberler.json',
    'rapor.json', 'icerik.json', 'raporlar.json',
    'makaleler.json', 'ekosistem.json', 'kuresel.json',
    'gunluk-raporlar.json',
    // Haberler alt-kategori dosyaları
    'haberler-iklim.json', 'haberler-maden.json', 'haberler-orman.json',
    'haberler-su.json',    'haberler-yaban.json',  'haberler-direnis.json',
    'haberler-hukuki.json','haberler-nobet.json',  'haberler-ihaklar.json',
    'haberler-stk.json',   'haberler-diger.json',
]);
define('HEDEF_DIZIN', __DIR__ . '/');

header('Content-Type: application/json; charset=utf-8');

$token_header = $_SERVER['HTTP_X_WEBHOOK_SECRET'] ?? '';
$token_query  = $_GET['token'] ?? '';
if ($token_header !== SECRET && $token_query !== SECRET) {
    http_response_code(403);
    echo json_encode(['ok' => false, 'hata' => 'Geçersiz token']);
    exit;
}

$action = $_GET['action'] ?? '';

// ── ACTION: dosya indir (GET) ─────────────────────────────────────────
if ($_SERVER['REQUEST_METHOD'] === 'GET' && !$action) {
    $dosya = basename($_GET['dosya'] ?? $_GET['file'] ?? '');
    if (!$dosya || !in_array($dosya, IZIN_DOSYA, true)) {
        http_response_code(400);
        echo json_encode(['ok' => false, 'hata' => 'İzin verilmeyen dosya: ' . $dosya]);
        exit;
    }
    $yol = HEDEF_DIZIN . $dosya;
    if (!file_exists($yol)) {
        http_response_code(404);
        echo json_encode(['ok' => false, 'hata' => 'Dosya bulunamadı: ' . $dosya]);
        exit;
    }
    // JSON olarak servis et
    readfile($yol);
    exit;
}

// ── ACTION: tara ──────────────────────────────────────────────────────
if ($action === 'tara') {
    if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
        http_response_code(405);
        echo json_encode(['ok' => false, 'hata' => 'POST gerekli']);
        exit;
    }
    if (!file_exists(BOT_SCRIPT)) {
        http_response_code(500);
        echo json_encode(['ok' => false, 'hata' => 'bot.py bulunamadı: ' . BOT_SCRIPT]);
        exit;
    }
    if (file_exists(KILITDOSYA)) {
        $pid = trim(file_get_contents(KILITDOSYA));
        if ($pid && file_exists("/proc/$pid")) {
            echo json_encode(['ok' => true, 'durum' => 'zaten_calisiyor', 'pid' => (int)$pid]);
            exit;
        }
        @unlink(KILITDOSYA);
    }
    $python = escapeshellcmd(PYTHON);
    $script = escapeshellarg(BOT_SCRIPT);
    $log    = escapeshellarg(LOG_DOSYA);
    $kilit  = escapeshellarg(KILITDOSYA);
    $dizin  = escapeshellarg(__DIR__);
    $cmd = "cd $dizin && nohup $python $script >> $log 2>&1 & echo \$! > $kilit";
    shell_exec($cmd);
    usleep(200000);
    $pid = file_exists(KILITDOSYA) ? trim(file_get_contents(KILITDOSYA)) : '?';
    echo json_encode(['ok' => true, 'durum' => 'baslatildi', 'pid' => (int)$pid]);
    exit;
}

// ── ACTION: durum ─────────────────────────────────────────────────────
if ($action === 'durum') {
    $calisiyor = false;
    $pid       = null;
    if (file_exists(KILITDOSYA)) {
        $pid = (int)trim(file_get_contents(KILITDOSYA));
        $calisiyor = $pid && file_exists("/proc/$pid");
    }
    $log_satirlar = [];
    if (file_exists(LOG_DOSYA)) {
        $satirlar = file(LOG_DOSYA, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
        $log_satirlar = array_slice($satirlar, -30);
    }
    $dosya_durumu = [];
    foreach (['haberler.json', 'ihlaller.json', 'raporlar.json', 'makaleler.json',
              'ekosistem.json', 'kuresel.json', 'gunluk-raporlar.json'] as $d) {
        $yol = HEDEF_DIZIN . $d;
        $dosya_durumu[$d] = file_exists($yol)
            ? ['boyut_kb' => round(filesize($yol) / 1024, 1),
               'degistirme' => date('Y-m-d H:i:s', filemtime($yol))]
            : null;
    }
    echo json_encode(['ok' => true, 'calisiyor' => $calisiyor, 'pid' => $pid,
                      'log' => $log_satirlar, 'dosyalar' => $dosya_durumu,
                      'zaman' => date('Y-m-d H:i:s T')]);
    exit;
}

// ── Varsayılan: JSON dosyası yaz (POST) ──────────────────────────────
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['ok' => false, 'hata' => 'Yalnızca POST kabul edilir']);
    exit;
}

$dosya = basename($_GET['dosya'] ?? $_GET['file'] ?? 'data.json');

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
