/* PNP Kontrol Merkezi — app.js */
let moveStep = 5.0, socket = null, pumpState = false;
const STEPS = [0.1, 0.5, 1.0, 5.0, 10, 50];
const MAX_LOG = 300;

/* ═══ INIT ═══ */
document.addEventListener('DOMContentLoaded', () => {
    initSocket(); loadConfig(); loadWords(); loadErrors();
    addC('Arayüz yüklendi. Ok tuşları=Hareket, H=Home, C=Center, E=Acil Durdur', 'info');
    setInterval(pollGrbl, 2000);
    setInterval(pollUptime, 5000);
    // Apply saved theme
    const t = localStorage.getItem('pnp-theme') || 'dark';
    document.documentElement.setAttribute('data-theme', t);
    // Ripple
    document.addEventListener('click', function (e) {
        const b = e.target.closest('.ripple');
        if (!b) return;
        const r = document.createElement('span'); r.className = 'ripple-wave';
        const d = Math.max(b.clientWidth, b.clientHeight);
        r.style.width = r.style.height = d + 'px';
        r.style.left = e.clientX - b.getBoundingClientRect().left - d / 2 + 'px';
        r.style.top = e.clientY - b.getBoundingClientRect().top - d / 2 + 'px';
        b.appendChild(r); setTimeout(() => r.remove(), 600);
    });
});

/* ═══ SOCKET.IO ═══ */
function initSocket() {
    socket = io();
    socket.on('connect', () => { addC('✓ Bağlantı kuruldu.', 'info'); setBadge('motorBadge', 'motorBadgeTxt', 'Motor', 'ok'); refreshNozzleStatus(); });
    socket.on('disconnect', () => { addC('✗ Bağlantı kesildi!', 'error'); setBadge('motorBadge', 'motorBadgeTxt', 'Bağlantı Yok', 'err'); });
    socket.on('status_update', (d) => {
        if (d.motor) updateMotor(d.motor);
        if (d.camera_fps !== undefined) $('fpsCam').textContent = d.camera_fps.toFixed(0);
        if (d.ocr_fps !== undefined) $('fpsOcr').textContent = d.ocr_fps.toFixed(1);
        if (d.ocr) updateOCR(d.ocr);
        if (d.config) applyConfig(d.config);
    });
    socket.on('motor_update', (d) => { if (d) updateMotor(d); });
    socket.on('auto_center_update', (d) => {
        // Show overlay status
        if (d.status === 'started' || d.status === 'moving') {
            showOverlay(d.message);
        } else if (d.status === 'done') {
            showOverlay(d.message);
            setTimeout(hideOverlay, 2000);
        } else if (d.status === 'error') {
            showOverlay("HATA: " + d.message);
            setTimeout(hideOverlay, 3000);
        }

        const box = $('acStatusBox');
        if (box) {
            const div = document.createElement('div');
            div.textContent = `[${d.status}] ${d.message}`;
            div.style.color = d.status === 'error' ? '#ff6b6b' : d.status === 'done' ? '#51cf66' : '#fff';
            div.style.borderBottom = '1px solid rgba(255,255,255,0.05)';
            div.style.padding = '2px 0';
            box.appendChild(div);
            box.scrollTop = box.scrollHeight;
        }

        if (d.status === 'done' || d.status === 'error' || d.status === 'timeout') {
            $('acBtn').disabled = false;
        } else {
            $('acBtn').disabled = true;
        }
    });
    socket.on('log_message', (d) => {
        const l = (d.level || 'INFO').toLowerCase();
        addC(d.message, l === 'error' ? 'error' : l === 'warning' ? 'warning' : 'info');
    });
    socket.on('error_toast', (d) => {
        showToast(d.message, d.level?.toLowerCase() || 'error');
        refreshErrors();
    });
    socket.on('scenario_update', (d) => {
        const box = $('scenarioStatusBox');
        const runBtn = $('quickScenarioRunBtn');
        const stopBtn = $('quickScenarioStopBtn');
        if (box) {
            box.style.display = 'block';
            const div = document.createElement('div');
            div.textContent = d.message;
            div.style.color = d.status === 'error' ? '#ff6b6b' : d.status === 'done' ? '#51cf66' : d.status === 'stopped' ? '#ffa726' : '#fff';
            div.style.padding = '2px 0';
            div.style.borderBottom = '1px solid rgba(255,255,255,0.05)';
            box.appendChild(div);
            box.scrollTop = box.scrollHeight;
        }
        if (d.status === 'started' || d.status === 'running') {
            if (runBtn) runBtn.style.display = 'none';
            if (stopBtn) stopBtn.style.display = '';

            // Delay adımlarında popup gösterme (önceki adımın mesajı kalsın)
            if (d.step_type !== 'delay') {
                showOverlay(`🎬 ${d.message}`);
            }
        } else if (d.status === 'done' || d.status === 'error' || d.status === 'stopped') {
            if (runBtn) runBtn.style.display = '';
            if (stopBtn) stopBtn.style.display = 'none';
            showOverlay(d.message);
            setTimeout(hideOverlay, 3000);
        }
    });
    socket.on('verification_update', d => {
        if (d.status === 'running' || d.status === 'info' || d.status === 'warning') {
            showToast('Doğrulama: ' + d.message, d.status === 'warning' ? 'warning' : 'info');
            // Ana ekrandaki HUD'da durum göster
            const hud = $('verificationResultsHUD');
            if (hud) hud.innerHTML = `<div style="background:#222; border:1px solid var(--blue); border-left:4px solid var(--blue); padding:8px 14px; border-radius:4px; white-space:nowrap; display:flex; align-items:center; gap:8px; animation:pulse 1s infinite">
                <span style="font-size:1.2rem">⏳</span>
                <span style="font-size:0.85rem; color:#fff">${esc(d.message)}</span>
            </div>`;
        } else if (d.status === 'threshold_frame') {
            // Threshold önizleme görüntüsünü göster (doğrulama sekmesinde)
            const prev = $('vThresholdPreview');
            if (prev && d.data && d.data.image) {
                prev.src = 'data:image/jpeg;base64,' + d.data.image;
            }
        } else if (d.status === 'box_progress') {
            // Her kutu analiz edilirken gerçek zamanlı güncelleme
            appendBoxProgressToHUD(d.data);
        } else if (d.status === 'error') {
            showToast('Doğrulama: ' + d.message, 'error');
            const hud = $('verificationResultsHUD');
            if (hud) hud.innerHTML = `<div style="background:#222; border:1px solid var(--red); border-left:4px solid var(--red); padding:8px 14px; border-radius:4px; white-space:nowrap">
                <span style="font-size:0.85rem; color:var(--red)">❌ ${esc(d.message)}</span>
            </div>`;
        } else if (d.status === 'done') {
            showToast('Doğrulama tamamlandı!', 'success');
            renderVerificationHUD(d.data);
            renderVerificationResults(d.data);
        }
    });
}

function appendBoxProgressToHUD(boxData) {
    const hud = $('verificationResultsHUD');
    if (!hud) return;
    // İlk kutu geldiğinde HUD'ı temizle (eski bekleme mesajını kaldır)
    if (boxData.box_index === 0) hud.innerHTML = '';

    const color = boxData.success ? 'var(--green)' : 'var(--red)';
    const icon = boxData.success ? '✅' : '❌';
    const card = document.createElement('div');
    card.style.cssText = `background:#222; border:1px solid ${color}; border-left:4px solid ${color}; padding:6px 10px; border-radius:6px; white-space:nowrap; display:flex; align-items:center; gap:8px; min-width:140px; animation:fadeIn 0.4s ease`;
    card.innerHTML = `
        <img src="data:image/jpeg;base64,${boxData.roi_image}" style="width:50px; height:38px; border-radius:3px; border:1px solid #555; object-fit:cover">
        <div style="display:flex; flex-direction:column">
            <span style="font-size:0.7rem; color:#aaa; font-weight:bold">${esc(boxData.name)}</span>
            <span style="font-size:0.95rem; font-weight:bold; color:${color}">${boxData.ratio}% ${icon}</span>
            <span style="font-size:0.6rem; color:#666">hedef: ${boxData.target}%</span>
        </div>`;
    hud.appendChild(card);
}

function renderVerificationHUD(results) {
    const hud = $('verificationResultsHUD');
    if (!hud) return;
    if (!results || !results.length) { hud.innerHTML = ''; return; }

    let h = '';
    results.forEach(r => {
        const color = r.success ? 'var(--green)' : 'var(--red)';
        const icon = r.success ? '✅' : '❌';
        const roiImg = r.roi_image ? `<img src="data:image/jpeg;base64,${r.roi_image}" style="width:50px; height:38px; border-radius:3px; border:1px solid #555; object-fit:cover">` : '';
        h += `<div style="background:#222; border:1px solid ${color}; border-left:4px solid ${color}; padding:6px 10px; border-radius:6px; white-space:nowrap; display:flex; align-items:center; gap:8px; min-width:140px">
            ${roiImg}
            <div style="display:flex; flex-direction:column">
                <span style="font-size:0.7rem; color:#aaa; font-weight:bold">${esc(r.name)}</span>
                <span style="font-size:0.95rem; font-weight:bold; color:${color}">${r.ratio}% ${icon}</span>
                <span style="font-size:0.6rem; color:#666">hedef: ${r.target}%</span>
            </div>
        </div>`;
    });
    hud.innerHTML = h;
}

function renderVerificationResults(results) {
    const panel = $('vResultsPanel');
    const content = $('vResultsContent');
    if (!panel || !content) return;
    if (!results || !results.length) { panel.style.display = 'none'; return; }

    panel.style.display = 'block';
    const allPass = results.every(r => r.success);

    // Banner'ı kameranın üstüne overlay olarak göster
    showVerificationBanner(allPass);

    // Sadece kutu detaylarını panelde göster (banner yok)
    let h = '<div style="display:flex; flex-direction:column; gap:6px">';
    results.forEach(r => {
        const color = r.success ? 'var(--green)' : 'var(--red)';
        h += `<div style="display:flex; justify-content:space-between; align-items:center; background:#111; border-left:4px solid ${color}; border-radius:4px; padding:6px 8px">
            <div style="font-size:0.8rem; color:#aaa; display:flex; flex-direction:column">
                <span>${esc(r.name)}</span>
                <span style="font-size:0.6rem; color:#666">Hedef: ${r.target}%</span>
            </div>
            <div style="font-weight:bold; color:${color}; font-size:1rem">${r.ratio}%</div>
        </div>`;
    });
    h += '</div>';
    content.innerHTML = h;
}

function showVerificationBanner(allPass) {
    // Kameranın üstüne overlay banner
    const container = $('vCanvasContainer');
    if (!container) return;
    // Eski banner'ı kaldır
    const old = document.getElementById('vBannerOverlay');
    if (old) old.remove();

    const banner = document.createElement('div');
    banner.id = 'vBannerOverlay';
    banner.style.cssText = `position:absolute; top:10px; left:50%; transform:translateX(-50%); z-index:20;
        padding:10px 24px; border-radius:10px; font-weight:bold; font-size:1.2rem;
        pointer-events:none; animation:fadeIn 0.5s ease;
        background:${allPass ? 'rgba(16,185,129,0.85)' : 'rgba(239,68,68,0.85)'};
        color:#fff; backdrop-filter:blur(4px); box-shadow:0 4px 20px rgba(0,0,0,0.5);`;
    banner.textContent = allPass ? '\u2705 T\u00dcM KUTULAR BA\u015eARILI' : '\u274c BA\u015eARISIZ KUTULAR VAR';
    container.appendChild(banner);
    // 6 saniye sonra solarak kaybol
    setTimeout(() => { if (banner.parentNode) { banner.style.transition = 'opacity 1s'; banner.style.opacity = '0'; setTimeout(() => banner.remove(), 1000); } }, 6000);
}

/* ═══ MOTOR ═══ */
function updateMotor(d) {
    $('posX').textContent = (d.x ?? 0).toFixed(2);
    $('posY').textContent = (d.y ?? 0).toFixed(2);
    $('posZ').textContent = (d.z ?? 0).toFixed(2);
    setBadge('motorBadge', 'motorBadgeTxt', d.connected ? 'Bağlı' : 'Simülasyon', d.connected ? 'ok' : 'warn');
    if (d.state) updateGrblState(d.state, d.alarm);
    // Settings tab
    $('sysPort').textContent = d.port || '--';
    $('sysMotor').textContent = d.connected ? 'Bağlı' : 'Simülasyon';
    $('sysGrbl').textContent = d.state || '--';
}
function updateGrblState(state, alarm) {
    const s = state.toUpperCase();
    let cls = s.includes('ALARM') ? 'alarm' : s.includes('RUN') ? 'run' : (s.includes('HOLD') || s.includes('HOME') || s.includes('SLEEP')) ? 'hold' : 'idle';
    ['grblBadge'].forEach(id => { const e = $(id); if (e) { e.textContent = s; e.className = (id === 'grblBadge' ? 'grbl-badge ' : 'grbl-sm ') + cls; } });
    const bar = $('alarmBar'); bar.classList.toggle('show', alarm === true);
}

/* ═══ OCR ═══ */
function updateOCR(results) {
    $('detCnt').textContent = results.length;
    $('ocrCnt2').textContent = results.length;
    if (!results.length) { $('ocrList').innerHTML = '<div class="ocr-empty">Yazı algılanmadı</div>'; $('tgtSt').textContent = 'Aranıyor'; $('tgtSt').className = 'mono tgt-search'; return; }
    // Get target words
    const chips = document.querySelectorAll('.word-chip');
    const words = []; chips.forEach(c => { const t = c.getAttribute('data-word'); if (t) words.push(t.toUpperCase()); });
    let found = false, h = '';
    results.forEach(r => {
        const hit = words.some(w => r.text.toUpperCase().includes(w));
        if (hit) found = true;
        h += `<div class="ocr-item" style="${hit ? 'border-color:rgba(16,185,129,.25);background:rgba(16,185,129,.05)' : ''}">
            <span class="ocr-text" ${hit ? 'style="color:var(--green)"' : ''}>${hit ? '🎯 ' : ''}${esc(r.text)}</span>
            <span class="ocr-coords">⊕${r.center[0]},${r.center[1]}</span></div>`;
    });
    $('ocrList').innerHTML = h;
    $('tgtSt').textContent = found ? 'Bulundu ✓' : 'Aranıyor';
    $('tgtSt').className = 'mono ' + (found ? 'tgt-found' : 'tgt-search');
}

/* ═══ TABS ═══ */
function switchTab(id) {
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    const tab = document.getElementById('tab-' + id); if (tab) tab.classList.add('active');
    const btn = document.querySelector(`[data-tab="${id}"]`); if (btn) btn.classList.add('active');
    if (id === 'nozzle') refreshNozzleStatus();
}

/* ═══ THEME ═══ */
function toggleTheme() {
    const cur = document.documentElement.getAttribute('data-theme');
    const nxt = cur === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', nxt);
    localStorage.setItem('pnp-theme', nxt);
}

/* ═══ TOAST ═══ */
function showToast(msg, level = 'error') {
    const box = $('toastBox'), t = document.createElement('div');
    t.className = 'toast ' + level;
    t.innerHTML = (level === 'error' ? '❌' : level === 'warning' ? '⚠️' : 'ℹ️') + ' ' + esc(msg);
    t.onclick = () => { t.classList.add('hide'); setTimeout(() => t.remove(), 300); };
    box.appendChild(t);
    setTimeout(() => { if (t.parentNode) { t.classList.add('hide'); setTimeout(() => t.remove(), 300); } }, 5000);
}

/* ═══ API ═══ */
async function moveMotor(dx, dy) { try { const r = await api('/api/move', { x: dx * moveStep, y: dy * moveStep }); if (r.motor) updateMotor(r.motor); } catch (e) { addC('Hareket hatası: ' + e, 'error'); showToast('Hareket hatası: ' + e); } }
async function moveZ(dz) { try { const r = await api('/api/move', { x: 0, y: 0, z: dz * moveStep }); if (r.motor) updateMotor(r.motor); } catch (e) { addC('Z hatası: ' + e, 'error'); } }

async function moveToZ() {
    const inp = $('zTargetInput');
    const zVal = parseFloat(inp.value);

    if (isNaN(zVal)) { showToast('Geçersiz Z değeri!', 'error'); return; }

    showOverlay('İndiriliyor...');
    try {
        const res = await api('/api/move_z_absolute', { z: zVal });
        if (res.success) {
            showToast('Z hareketi tamamlandı.', 'info');
            if (res.motor) updateMotor(res.motor);
        } else {
            showToast('Z hareketi başarısız!', 'error');
        }
    } catch (e) {
        showToast('Hata: ' + e, 'error');
    } finally {
        hideOverlay();
    }
}
async function homeMotor() {
    addC('Home gönderiliyor...', 'info');
    showOverlay('Home Konumuna Gidiliyor...');
    const r = await api('/api/home');
    if (!r.success) { showToast(r.message || 'Home hatası'); showOverlay('Home Hatası!'); setTimeout(hideOverlay, 3000); }
    else { setTimeout(hideOverlay, 5000); }
}
function setInputAndCenter(text) {
    const inp = $('targetInput');
    if (inp) {
        inp.value = text;
        startAutoCenter();
    }
}

function startAutoCenter() {
    const inp = $('targetInput');
    const word = inp ? inp.value.trim().toUpperCase() : "";

    $('acStatusBox').innerHTML = '<div style="color:#aaa">Başlatılıyor...</div>';
    api('/api/auto_center', { target_word: word }, 'POST');
}
async function pumpCtl(on) {
    pumpState = on;
    addC(`Pompa ${on ? 'açılıyor' : 'kapatılıyor'}...`, 'info');
    showOverlay(on ? 'Pompa AÇIK' : 'Pompa KAPALI');
    const r = await api('/api/pump', { state: on });
    addC(r.message, 'info');
    setTimeout(hideOverlay, 1500);
}
function togglePump() { pumpCtl(!pumpState); }
async function shutdownServer() {
    if (!confirm('Sunucuyu kapatmak istediğinizden emin misiniz? Python kodu tamamen duracak.')) return;
    addC('🔌 Sunucu kapatılıyor...', 'error');
    showOverlay('⚠️ SUNUCU KAPATILIYOR ⚠️');
    showToast('Sunucu kapatılıyor...', 'error');
    try {
        await fetch('/api/shutdown', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
    } catch (e) { /* bağlantı kapandığında hata normal */ }
}
async function unlockGrbl() { addC('Kilit açılıyor...', 'info'); const r = await api('/api/unlock'); addC(r.message, r.success ? 'info' : 'error'); if (!r.success) showToast(r.message); }
async function softReset() { addC('Soft Reset...', 'info'); const r = await api('/api/soft_reset'); addC(r.message, r.success ? 'info' : 'error'); if (!r.success) showToast(r.message); }
async function sendGcode() { const inp = $('gcodeIn'), cmd = inp.value.trim(); if (!cmd) return; addC('> ' + cmd, 'info'); inp.value = ''; const r = await api('/api/send_gcode', { command: cmd }); addC(r.message, r.success ? 'info' : 'error'); if (!r.success) showToast(r.message); }

/* ═══ CONFIG ═══ */
function applyConfig(c) {
    if (c.pixel_to_mm_x !== undefined) $('cfgPxX').value = c.pixel_to_mm_x;
    if (c.pixel_to_mm_y !== undefined) $('cfgPxY').value = c.pixel_to_mm_y;
    if (c.target_x !== undefined) $('cfgTX').value = c.target_x;
    if (c.target_y !== undefined) $('cfgTY').value = c.target_y;
    if (c.auto_center_tolerance !== undefined) $('cfgTol').value = c.auto_center_tolerance;
    if (c.auto_center_max_iter !== undefined) $('cfgMaxIter').value = c.auto_center_max_iter;
    if (c.feed_rate !== undefined) $('cfgFeed').value = c.feed_rate;
    if (c.invert_x !== undefined) $('cfgIX').checked = c.invert_x;
    if (c.invert_y !== undefined) $('cfgIY').checked = c.invert_y;
    if (c.target_words) {
        // target_words artık legacy, ocrGroups kullanıyoruz ama yine de birleştirebiliriz
        // Şimdilik sadece renderWords çağrısını kaldırıyoruz çünkü renderOCRGroups var
    }
    // Calibration
    if (c.swap_axes !== undefined) { $('calSwapCb').checked = c.swap_axes; $('calSwap').textContent = c.swap_axes ? 'Evet' : 'Hayır'; }
    if (c.negate_screen_x !== undefined) { $('calNegXCb').checked = c.negate_screen_x; $('calNegX').textContent = c.negate_screen_x ? 'Evet' : 'Hayır'; }
    if (c.negate_screen_y !== undefined) { $('calNegYCb').checked = c.negate_screen_y; $('calNegY').textContent = c.negate_screen_y ? 'Evet' : 'Hayır'; }
    // Camera
    if (c.camera_width !== undefined) { $('camW').value = c.camera_width; }
    if (c.camera_height !== undefined) { $('camH').value = c.camera_height; }
    if (c.camera_width && c.camera_height) { $('camResBadge').textContent = c.camera_width + '×' + c.camera_height; }
    updateCalSummary();
    // OCR Settings
    if (c.ocr_confidence !== undefined) { $('cfgOcrConf').value = c.ocr_confidence; $('cfgOcrConfVal').textContent = c.ocr_confidence; }
    if (c.ocr_psm_mode !== undefined) { $('cfgOcrPsm').value = c.ocr_psm_mode; }
    if (c.ocr_whitelist !== undefined) { $('cfgOcrWhitelist').value = c.ocr_whitelist; }
    if (c.zoom_factor !== undefined) {
        const zs = $('zoomSlider');
        if (zs) {
            zs.value = c.zoom_factor;
            $('zoomVal').textContent = 'x' + parseFloat(c.zoom_factor).toFixed(1);
        }
    }
    if (c.ocr_min_word_length !== undefined) {
        const el = $('cfgMinWordLen');
        if (el) el.value = c.ocr_min_word_length;
    }
    if (c.box_growth_limit !== undefined) {
        const el = $('cfgBoxGrowth');
        if (el) el.value = c.box_growth_limit;
    }
    if (c.auto_home !== undefined) {
        const el = $('cfgAutoHome');
        if (el) el.checked = c.auto_home;
    }
}
async function loadConfig() { try { const r = await fetch('/api/config').then(r => r.json()); applyConfig(r); } catch (e) { } }
async function saveConfig() {
    const r = await api('/api/config', { pixel_to_mm_x: +$('cfgPxX').value, pixel_to_mm_y: +$('cfgPxY').value, target_x: +$('cfgTX').value, target_y: +$('cfgTY').value, auto_center_tolerance: +$('cfgTol').value, auto_center_max_iter: +$('cfgMaxIter').value, feed_rate: +$('cfgFeed').value, invert_x: $('cfgIX').checked, invert_y: $('cfgIY').checked });
    addC('Kalibrasyon kaydedildi.', 'info'); showToast('Ayarlar kaydedildi', 'info');
}
async function saveOcrConfig() {
    const r = await api('/api/config', {
        ocr_confidence: +$('cfgOcrConf').value,
        ocr_psm_mode: +$('cfgOcrPsm').value,
        ocr_whitelist: $('cfgOcrWhitelist').value.toUpperCase(),
        ocr_min_word_length: +$('cfgMinWordLen').value,
        box_growth_limit: +$('cfgBoxGrowth').value,
        auto_home: $('cfgAutoHome').checked
    });
    addC('OCR ayarları kaydedildi.', 'info'); showToast('OCR ayarları kaydedildi', 'info');
}

/* ═══ OCR WORDS & GROUPS ═══ */
let ocrGroups = {};
let targetGroup = "Varsayilan";

function loadWords() {
    api('/api/config').then(d => {
        if (d) {
            ocrGroups = d.ocr_groups || {};
            // Eğer ocrGroups boşsa ve target_words varsa (eski config), onu varsayılan gruba at
            if (Object.keys(ocrGroups).length === 0 && d.target_words && d.target_words.length > 0) {
                ocrGroups["Varsayilan"] = d.target_words;
            }

            targetGroup = d.target_group || "Varsayilan";

            renderOCRGroups();

            // İlk yüklemede hedef kelimeyi de set et
            if (d.selected_target_word) {
                setTimeout(() => {
                    const inp = $('targetInput');
                    if (inp) inp.value = d.selected_target_word;
                }, 500);
            }
        }
    });
}

function renderOCRGroups() {
    // 1. Word Listesi Yönetimi (OCR Sekmesi)
    const cont = $('wordList');
    if (cont) {
        let html = `
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px">
            <select id="groupSel" class="cam-inp" style="width:auto; flex:1" onchange="changeTargetGroup(this.value)">
                ${Object.keys(ocrGroups).map(k => `<option value="${k}" ${k === targetGroup ? 'selected' : ''}>${k}</option>`).join('')}
            </select>
            <button class="btn-sm" onclick="addNewGroup()">+ Grup</button>
        </div>
        <div style="max-height:150px; overflow-y:auto; border:1px solid rgba(255,255,255,0.1); padding:4px; border-radius:4px">
        `;

        const words = ocrGroups[targetGroup] || [];
        if (words.length === 0) html += '<div style="color:#aaa; font-style:italic; padding:4px">Grup boş.</div>';

        words.forEach(w => {
            html += `
            <div class="word-tag">
                <span>${w}</span>
                <span class="del-w" onclick="removeWord('${w}')">×</span>
            </div>`;
        });
        html += '</div>';

        html += `
        <div style="display:flex; gap:4px; margin-top:8px">
            <input id="newWordInp" class="cam-inp" placeholder="Yeni kelime..." onkeydown="if(event.key==='Enter')addWord()">
            <button class="btn-sm" onclick="addWord()">Ekle</button>
        </div>
        `;
        cont.innerHTML = html;
    }

    // 2. Control Tab Datalist Sync
    const dl = $('ocrWordsList');
    if (dl) {
        const words = ocrGroups[targetGroup] || [];
        let opts = '';
        words.forEach(w => {
            opts += `<option value="${w}">`;
        });
        dl.innerHTML = opts;
    }
}

function selectTargetWord(w) {
    // Legacy - removed
}

function changeTargetGroup(g) {
    targetGroup = g;
    api('/api/config', { target_group: g }).then(() => {
        renderOCRGroups();
        addC(`Hedef grup değiştirildi: ${g}`, 'info');
    });
}

function addNewGroup() {
    const name = prompt("Yeni grup adı:");
    if (name && !ocrGroups[name]) {
        ocrGroups[name] = [];
        targetGroup = name;
        saveGroups();
    }
}

function addWord() {
    const inp = $('newWordInp');
    const w = inp.value.trim().toUpperCase();
    if (w) {
        if (!ocrGroups[targetGroup]) ocrGroups[targetGroup] = [];
        if (!ocrGroups[targetGroup].includes(w)) {
            ocrGroups[targetGroup].push(w);
            saveGroups();
            inp.value = '';
        }
    }
}

function removeWord(w) {
    if (ocrGroups[targetGroup]) {
        ocrGroups[targetGroup] = ocrGroups[targetGroup].filter(item => item !== w);
        saveGroups();
    }
}

function saveGroups() {
    api('/api/config', { ocr_groups: ocrGroups, target_group: targetGroup }).then(() => {
        renderOCRGroups();
    });
}

/* ═══ ERRORS ═══ */
async function loadErrors() { refreshErrors(); }
async function refreshErrors() { try { const r = await fetch('/api/errors').then(r => r.json()); renderErrors(r.errors || []); } catch (e) { } }
function renderErrors(errs) {
    const el = $('errorList');
    if (!errs.length) { el.innerHTML = '<div class="ocr-empty">Hata yok ✓</div>'; return; }
    el.innerHTML = errs.slice().reverse().map(e => `<div class="error-item"><span class="et">${e.timestamp}</span><span>${esc(e.message)}</span></div>`).join('');
}
async function clearErrors() { await api('/api/errors/clear'); $('errorList').innerHTML = '<div class="ocr-empty">Hata yok ✓</div>'; addC('Hata geçmişi temizlendi.', 'info'); }

/* ═══ STEP ═══ */
/* ═══ STEP ═══ */
function setStep(s) { moveStep = s; document.querySelectorAll('.sb').forEach(b => b.classList.toggle('active', parseFloat(b.textContent) === s)); }
function changeStep(dir) {
    let idx = STEPS.indexOf(moveStep);
    if (idx < 0) idx = 3; // Default to 5.0 if not found
    let n = idx + dir;
    if (n < 0) n = 0;
    if (n >= STEPS.length) n = STEPS.length - 1;
    setStep(STEPS[n]);
    showToast('Adım: ' + STEPS[n] + 'mm', 'info');
}

/* ═══ POLLING ═══ */
function pollGrbl() { fetch('/api/grbl_status').then(r => r.json()).then(d => updateMotor(d)).catch(() => { }); }
function pollUptime() { fetch('/api/uptime').then(r => r.json()).then(d => { $('uptimeEl').textContent = '⏱ ' + d.uptime_formatted; $('sysUptime').textContent = d.uptime_formatted; }).catch(() => { }); }

/* ═══ CONSOLE ═══ */
function addC(msg, lvl = 'info') { const c = $('console'), t = new Date().toLocaleTimeString('tr-TR'); const ln = document.createElement('div'); ln.className = 'cline ' + lvl; ln.innerHTML = `<span class="ct">[${t}]</span> ${esc(msg)}`; c.appendChild(ln); while (c.children.length > MAX_LOG) c.removeChild(c.firstChild); c.scrollTop = c.scrollHeight; }
function clearConsole() { $('console').innerHTML = ''; addC('Konsol temizlendi.', 'info'); }

/* ═══ KEYBOARD ═══ */
document.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT') return;
    switch (e.key) {
        case 'ArrowUp': e.preventDefault(); moveMotor(0, -1); break;
        case 'ArrowDown': e.preventDefault(); moveMotor(0, 1); break;
        case 'ArrowLeft': e.preventDefault(); moveMotor(-1, 0); break;
        case 'ArrowRight': e.preventDefault(); moveMotor(1, 0); break;
        case 'PageUp': e.preventDefault(); moveZ(1); break;
        case 'PageDown': e.preventDefault(); moveZ(-1); break;
        case 'w': case 'W': moveZ(1); break;
        case 's': case 'S': moveZ(-1); break;
        case 'q': case 'Q': changeStep(-1); break;
        case 'e': case 'E': changeStep(1); break;
        case ' ': e.preventDefault(); togglePump(); break;
        case 'h': case 'H': homeMotor(); break;
        case 'c': case 'C': autoCenter(); break;
        // case 'e': case 'E': shutdownServer(); break;
    }
});

/* ═══ CAMERA RESOLUTION & ZOOM ═══ */
function setStreamRes(w, btn) {
    const inp = $('streamW');
    if (inp) inp.value = w;

    // Highlight active button
    if (btn) {
        // Remove active from siblings
        const parent = btn.parentNode;
        parent.querySelectorAll('.btn-sm').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
    }
}

function setRes(w, h) {
    $('camW').value = w;
    $('camH').value = h;
}

function toggleCamSettings() {
    const p = $('camSettings');
    if (p.style.display === 'block') { p.style.display = 'none'; }
    else {
        p.style.display = 'block';
        // Pop-up'ı ekranın ortasına hizala (CSS transform: translate(-50%, -50%) kullanıldığı için top/left %50 olmalı)
        p.style.top = '50%';
        p.style.left = '50%';
    }
}
async function applyCamRes() {
    const w = parseInt($('camW').value) || 800;
    const h = parseInt($('camH').value) || 1080;
    const sw = parseInt($('streamW').value) || 500;

    // Stream genişliğini ayrıca kaydet
    await api('/api/config', { stream_max_width: sw });

    addC(`Çözünürlük ayarlanıyor: ${w}x${h} (Stream: ${sw}px)...`, 'warning');

    const r = await api('/api/camera/resolution', { width: w, height: h });
    if (r.success) {
        addC('Kamera yeniden başlatıldı.', 'success');
        setTimeout(() => location.reload(), 1000);
    } else {
        showToast('Hata oluştu');
    }
}

/* ═══ CALIBRATION ═══ */
let calMapping = { x: null, y: null }; // Motor X+ ve Y+ kamerada hangi yöne gidiyor

async function calTestMotor(axis, dir) {
    const step = parseFloat($('calStep').value) || 2;
    addC(`Kalibrasyon testi: Motor ${axis.toUpperCase()}${dir > 0 ? '+' : '-'}, ${step}mm`, 'info');
    showToast(`Motor ${axis.toUpperCase()}${dir > 0 ? '+' : '-'} ${step}mm hareket ediliyor...`, 'info');
    const r = await api('/api/calibration/test', { axis, direction: dir, step });
    if (r.success) {
        addC(`Test tamamlandı. Kamerada nesnenin hangi yöne gittiğini işaretleyin.`, 'info');
    } else {
        showToast('Motor test hatası!', 'error');
    }
}

function calSetMapping(axis, screenDir) {
    calMapping[axis] = screenDir;
    // Highlight selected button
    const pick = $('calPick' + axis.toUpperCase());
    pick.querySelectorAll('.cw-dir').forEach(b => b.classList.remove('selected'));
    event.target.closest('.cw-dir').classList.add('selected');
    addC(`Motor ${axis.toUpperCase()}+ → Kamera ${screenDir}`, 'info');

    // If both mapped, auto-calculate calibration
    if (calMapping.x && calMapping.y) {
        autoCalculateCalibration();
    }
}

function autoCalculateCalibration() {
    const mx = calMapping.x; // Motor X+ kamerada nereye gidiyor
    const my = calMapping.y; // Motor Y+ kamerada nereye gidiyor

    let swap = false, negX = false, negY = false;

    // Motor X+ ekranda sağ/sol ise → swap yok (X→X)
    // Motor X+ ekranda yukarı/aşağı ise → swap var (X→Y)
    if (mx === 'up' || mx === 'down') {
        swap = true;
    }

    if (swap) {
        // swap=true: ekran X → motor Y, ekran Y → motor X
        // Motor X+ goes to screen up/down → this affects screen Y after swap
        // For screen "right" button (screen_dx=+1): after swap → motor_dy=+1
        //   We want motor Y+ to go right on screen
        //   my tells us where motor Y+ actually goes
        negX = (my === 'left');   // negate_screen_x: motor Y+ ekranda sola gidiyorsa
        negY = (mx === 'down');   // negate_screen_y: motor X+ ekranda aşağı gidiyorsa
    } else {
        // No swap: screen X → motor X directly
        negX = (mx === 'left');
        negY = (my === 'down');
    }

    // Update checkboxes
    $('calSwapCb').checked = swap;
    $('calNegXCb').checked = negX;
    $('calNegYCb').checked = negY;

    // Update display
    $('calSwap').textContent = swap ? 'Evet' : 'Hayır';
    $('calNegX').textContent = negX ? 'Evet' : 'Hayır';
    $('calNegY').textContent = negY ? 'Evet' : 'Hayır';

    updateCalSummary();
    showToast('Kalibrasyon hesaplandı! Kaydetmeyi unutmayın.', 'info');
    addC(`Hesaplandı: swap=${swap}, negX=${negX}, negY=${negY}`, 'info');
}

function updateCalSummary() {
    const swap = $('calSwapCb').checked;
    const negX = $('calNegXCb').checked;
    const negY = $('calNegYCb').checked;

    let lines = [];
    if (swap) {
        lines.push('Eksenler yer değiştiriyor (Swap aktif)');
        lines.push(`Ekran Sağ/Sol → Motor ${negX ? 'Y-/Y+' : 'Y+/Y-'}`);
        lines.push(`Ekran Yukarı/Aşağı → Motor ${negY ? 'X+/X-' : 'X-/X+'}`);
    } else {
        lines.push('Eksenler normal (Swap kapalı)');
        lines.push(`Ekran Sağ/Sol → Motor ${negX ? 'X-/X+' : 'X+/X-'}`);
        lines.push(`Ekran Yukarı/Aşağı → Motor ${negY ? 'Y+/Y-' : 'Y-/Y+'}`);
    }
    $('calMapText').innerHTML = lines.join('<br>');
}

async function saveCalibration() {
    const swap = $('calSwapCb').checked;
    const negX = $('calNegXCb').checked;
    const negY = $('calNegYCb').checked;

    const r = await api('/api/calibration', {
        swap_axes: swap,
        negate_screen_x: negX,
        negate_screen_y: negY
    });

    if (r.success) {
        showToast('Kalibrasyon kaydedildi! ✓', 'info');
        addC('Kalibrasyon kaydedildi.', 'info');
        $('calSwap').textContent = swap ? 'Evet' : 'Hayır';
        $('calNegX').textContent = negX ? 'Evet' : 'Hayır';
        $('calNegY').textContent = negY ? 'Evet' : 'Hayır';
        updateCalSummary();
    } else {
        showToast('Kalibrasyon kayıt hatası!', 'error');
    }
}


/* ═══ BASES ═══ */
async function loadBases() {
    try {
        const r = await fetch('/api/bases').then(res => res.json());
        renderBases(r.bases || []);
        if (typeof onStepTypeChange === 'function') onStepTypeChange();
    } catch (e) { console.error('Bases load error', e); }
}

let _basesList = []; // son yüklenen konumlar

function renderBases(list) {
    _basesList = list; // cache for edit
    // Render Table List
    const cont = $('baseList');
    if (!list.length) {
        cont.innerHTML = '<div class="ocr-empty">Kayıtlı konum yok.</div>';
    } else {
        let h = '<table style="width:100%; border-collapse:collapse; font-size:0.9rem">';
        h += '<tr style="border-bottom:1px solid #444; text-align:left; color:#aaa"><th style="padding:4px">İsim</th><th>X</th><th>Y</th><th>Z</th><th></th></tr>';
        list.forEach(b => {
            h += `<tr id="baseRow_${esc(b.name)}" style="border-bottom:1px solid #333">
                <td style="padding:8px">${esc(b.name)}</td>
                <td>${b.x}</td><td>${b.y}</td><td>${b.z}</td>
                <td style="text-align:right; white-space:nowrap">
                    <button class="btn-sm" style="background:#4caf50;color:#fff" onclick="editBase('${esc(b.name)}')">✏️</button>
                    <button class="btn-sm" style="background:#d32f2f;color:#fff" onclick="deleteBase('${esc(b.name)}')">Sil</button>
                    <button class="btn-sm" style="background:#1976d2;color:#fff" onclick="gotoBaseDirect('${esc(b.name)}')">Git</button>
                </td>
             </tr>`;
        });
        h += '</table>';
        cont.innerHTML = h;
    }

    // Render Dropdown (if exists)
    const sel = $('quickBaseSel');
    if (sel) {
        const cur = sel.value;
        sel.innerHTML = '<option value="">Seç...</option>' + list.map(b => `<option value="${esc(b.name)}">${esc(b.name)}</option>`).join('');
        if (cur && list.find(b => b.name === cur)) sel.value = cur;
    }

    // Update Main Control Dropdown
    const selMain = $('quickBaseSelMain');
    if (selMain) {
        const curMain = selMain.value;
        selMain.innerHTML = '<option value="">Konum seç...</option>' + list.map(b => `<option value="${esc(b.name)}">${esc(b.name)}</option>`).join('');
        if (curMain && list.find(b => b.name === curMain)) selMain.value = curMain;
    }

    // Update Verification Dropdown
    const vSel = $('vBaseSelect');
    if (vSel) {
        const vCur = vSel.value;
        vSel.innerHTML = '<option value="">(Mevcut Konum)</option>' + list.map(b => `<option value="${esc(b.name)}">${esc(b.name)}</option>`).join('');
        if (vCur && list.find(b => b.name === vCur)) vSel.value = vCur;
        else if (typeof _vConfig !== 'undefined' && _vConfig.base_name) vSel.value = _vConfig.base_name;
    }
}

function editBase(name) {
    const b = _basesList.find(item => item.name === name);
    if (!b) return;
    const row = document.getElementById('baseRow_' + name);
    if (!row) return;
    row.innerHTML = `
        <td style="padding:4px"><input type="text" class="cfg-in" id="editName_${esc(name)}" value="${esc(b.name)}" style="width:80px"></td>
        <td><input type="number" class="cfg-in" id="editX_${esc(name)}" value="${b.x}" step="0.01" style="width:70px"></td>
        <td><input type="number" class="cfg-in" id="editY_${esc(name)}" value="${b.y}" step="0.01" style="width:70px"></td>
        <td><input type="number" class="cfg-in" id="editZ_${esc(name)}" value="${b.z}" step="0.01" style="width:70px"></td>
        <td style="text-align:right; white-space:nowrap">
            <button class="btn-sm" style="background:#4caf50;color:#fff" onclick="saveEditBase('${esc(name)}')">✓</button>
            <button class="btn-sm" style="background:#757575;color:#fff" onclick="cancelEditBase()">✗</button>
        </td>
    `;
}

async function saveEditBase(originalName) {
    const newName = document.getElementById('editName_' + originalName)?.value.trim();
    const x = parseFloat(document.getElementById('editX_' + originalName)?.value) || 0;
    const y = parseFloat(document.getElementById('editY_' + originalName)?.value) || 0;
    const z = parseFloat(document.getElementById('editZ_' + originalName)?.value) || 0;
    if (!newName) { showToast('İsim boş olamaz!', 'error'); return; }

    // Eğer isim değiştiyse eski kaydı sil
    if (newName !== originalName) {
        await fetch('/api/bases/' + encodeURIComponent(originalName), { method: 'DELETE' }).then(r => r.json());
    }
    const r = await api('/api/bases', { name: newName, x, y, z });
    if (r.success) {
        showToast('Konum güncellendi.', 'info');
        renderBases(r.bases);
    } else {
        showToast('Hata: ' + r.message, 'error');
    }
}

function cancelEditBase() {
    renderBases(_basesList);
}

async function saveBase() {
    const name = $('baseName').value.trim();
    if (!name) { showToast('İsim gerekli!', 'error'); return; }
    const x = parseFloat($('baseX').value) || 0;
    const y = parseFloat($('baseY').value) || 0;
    const z = parseFloat($('baseZ').value) || 0;

    const r = await api('/api/bases', { name, x, y, z });
    if (r.success) {
        showToast('Konum kaydedildi.', 'info');
        renderBases(r.bases);
        $('baseName').value = ''; // clear name
    } else {
        showToast('Hata: ' + r.message, 'error');
    }
}

async function deleteBase(name) {
    if (!confirm(name + ' silinsin mi?')) return;
    const r = await fetch('/api/bases/' + name, { method: 'DELETE' }).then(res => res.json());
    if (r.success) {
        showToast('Konum silindi.', 'info');
        renderBases(r.bases);
    } else {
        showToast('Hata: ' + r.message, 'error');
    }
}

function fetchCurrentPos() {
    $('baseX').value = $('posX').textContent;
    $('baseY').value = $('posY').textContent;
    $('baseZ').value = $('posZ').textContent;
}

async function gotoBase() {
    const name = $('quickBaseSel').value;
    if (!name) return;
    gotoBaseDirect(name);
}

async function gotoBaseDirect(name) {
    showOverlay(name + ' konumuna gidiliyor...');
    const r = await api('/api/goto_base', { name });
    hideOverlay();
    if (r.success) {
        showToast(r.message, 'info');
        addC(r.message, 'success');
    } else {
        showToast('Hata: ' + r.message, 'error');
        addC('Hata: ' + r.message, 'error');
    }
}

async function quickGotoBaseMain() {
    const name = $('quickBaseSelMain').value;
    if (!name) { showToast('Lütfen bir konum seçin!', 'warning'); return; }
    gotoBaseDirect(name);
}

async function quickReadResistance() {
    const hud = $('quickMeasurementHUD');
    const box = $('qmResBox');
    if (hud) hud.style.display = 'block';
    if (box) box.style.display = 'block';
    $('qmResValue').textContent = '...';
    $('qmResValue').style.color = '#66bb6a';
    $('qmResDetail').textContent = 'Ölçülüyor...';
    try {
        const r = await fetch('/api/nozzle/read_resistance').then(res => res.json());
        if (r.success) {
            $('qmResValue').textContent = r.resistance_formatted;
            $('qmResDetail').textContent = `ADC: ${r.adc} | V: ${r.voltage}V | ${r.status}`;
            if (r.status !== 'NORMAL') $('qmResValue').style.color = '#f44336';
        } else {
            $('qmResValue').textContent = 'HATA';
            $('qmResValue').style.color = '#f44336';
            $('qmResDetail').textContent = r.error || 'Bağlantı yok';
        }
    } catch (e) {
        $('qmResValue').textContent = 'HATA';
        $('qmResValue').style.color = '#f44336';
        $('qmResDetail').textContent = 'Bağlantı hatası';
    }
}

async function quickReadDiode() {
    const hud = $('quickMeasurementHUD');
    const box = $('qmDiodeBox');
    if (hud) hud.style.display = 'block';
    if (box) box.style.display = 'block';
    $('qmDiodeValue').textContent = '...';
    $('qmDiodeValue').style.color = '#ce93d8';
    $('qmDiodeDetail').textContent = 'Ölçülüyor...';
    try {
        const r = await fetch('/api/nozzle/read_diode').then(res => res.json());
        if (r.success) {
            const passing = r.current_passing;
            $('qmDiodeValue').textContent = passing ? 'AKIM GEÇİYOR ✅' : 'AKIM GEÇMİYOR ❌';
            $('qmDiodeValue').style.color = passing ? '#4caf50' : '#f44336';
            $('qmDiodeDetail').textContent = `ADC: ${r.adc} | Eşik: ${r.threshold} | ${r.result}`;
        } else {
            $('qmDiodeValue').textContent = 'HATA';
            $('qmDiodeValue').style.color = '#f44336';
            $('qmDiodeDetail').textContent = r.error || 'Bağlantı yok';
        }
    } catch (e) {
        $('qmDiodeValue').textContent = 'HATA';
        $('qmDiodeValue').style.color = '#f44336';
        $('qmDiodeDetail').textContent = 'Bağlantı hatası';
    }
}

async function setZoom(val) {
    const v = parseFloat(val);
    $('zoomVal').textContent = 'x' + v.toFixed(1);
    await api('/api/config', { zoom_factor: v });
}

/* ═══ HELPERS ═══ */
function $(id) { return document.getElementById(id); }
function esc(t) { return t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;"); }
async function api(url, body) { const o = body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : { method: 'POST' }; return fetch(url, o).then(r => r.json()); }
function setBadge(bid, tid, txt, st) { $(bid).className = 'badge ' + (st === 'ok' ? 'ok' : st === 'warn' ? 'warn' : 'err'); $(tid).textContent = txt; }

function showOverlay(txt) {
    const el = document.getElementById('camOverlayText');
    if (el) { el.textContent = txt; el.style.display = 'block'; }
}
function hideOverlay() {
    const el = document.getElementById('camOverlayText');
    if (el) el.style.display = 'none';
}

// Init
loadBases();

/* ═══ SCENARIOS ═══ */
let _scenariosList = [];
let _scenarioSteps = []; // current editor steps

async function loadScenarios() {
    try {
        const r = await fetch('/api/scenarios').then(res => res.json());
        _scenariosList = r.scenarios || [];
        renderScenarioList();
        updateScenarioDropdown();
    } catch (e) { console.error('Scenarios load error', e); }
}

function renderScenarioList() {
    const cont = $('scenarioList');
    if (!cont) return;
    if (!_scenariosList.length) {
        cont.innerHTML = '<div class="ocr-empty">Kayıtlı senaryo yok.</div>';
        return;
    }
    let h = '<table style="width:100%; border-collapse:collapse; font-size:0.9rem">';
    h += '<tr style="border-bottom:1px solid #444; text-align:left; color:#aaa"><th style="padding:4px">İsim</th><th>Adım</th><th></th></tr>';
    _scenariosList.forEach(s => {
        h += `<tr style="border-bottom:1px solid #333">
            <td style="padding:8px">${esc(s.name)}</td>
            <td>${s.steps ? s.steps.length : 0}</td>
            <td style="text-align:right; white-space:nowrap">
                <button class="btn-sm" style="background:#4caf50;color:#fff" onclick="editScenario('${esc(s.name)}')">✏️</button>
                <button class="btn-sm" style="background:var(--blue);color:#fff" onclick="duplicateScenario('${esc(s.name)}')">📋 Çoğalt</button>
                <button class="btn-sm" style="background:#d32f2f;color:#fff" onclick="deleteScenario('${esc(s.name)}')">Sil</button>
                <button class="btn-sm" style="background:#1976d2;color:#fff" onclick="runScenarioByName('${esc(s.name)}')">▶ Çalıştır</button>
            </td>
         </tr>`;
    });
    h += '</table>';
    cont.innerHTML = h;
}

function updateScenarioDropdown() {
    const sel = $('quickScenarioSel');
    if (!sel) return;
    const cur = sel.value;
    sel.innerHTML = '<option value="">Senaryo seç...</option>' + _scenariosList.map(s => `<option value="${esc(s.name)}">${esc(s.name)}</option>`).join('');
    if (cur && _scenariosList.find(s => s.name === cur)) sel.value = cur;

    // Also update master scenarios sub-scenario selector
    const msel = $('masterStepSelect');
    if (msel) {
        const mcur = msel.value;
        msel.innerHTML = _scenariosList.map(s => `<option value="${esc(s.name)}">${esc(s.name)}</option>`).join('');
        if (mcur && _scenariosList.find(s => s.name === mcur)) msel.value = mcur;
    }
}

// — Duplicate Scenarios —
async function duplicateScenario(name) {
    const s = _scenariosList.find(item => item.name === name);
    if (!s) return;

    let newName = s.name + ' (Kopya)';
    let counter = 1;
    let finalName = newName;
    while (_scenariosList.find(item => item.name === finalName)) {
        counter++;
        finalName = s.name + ` (Kopya ${counter})`;
    }

    const r = await api('/api/scenarios', { name: finalName, steps: s.steps });
    if (r.success) {
        showToast(`'${finalName}' başarıyla oluşturuldu.`, 'info');
        _scenariosList = r.scenarios;
        renderScenarioList();
        updateScenarioDropdown();
    } else {
        showToast('Hata: ' + r.message, 'error');
    }
}

// — Create New Scenario —
function createNewScenario() {
    clearScenarioSteps();
    $('scenarioName').focus();
    showToast('Yeni senaryo oluşturmak için temizlendi.', 'info');
}

// — Step Builder —
let _editingStepIndex = -1;

function onStepTypeChange() {
    const type = $('stepType').value;
    const box = $('stepParamBox');
    if (type === 'goto_base') {
        let opts = _basesList.map(b => `<option value="${esc(b.name)}">${esc(b.name)}</option>`).join('');
        box.innerHTML = `<select class="cfg-in" id="stepBaseSelect">${opts}</select>`;
        box.style.display = '';
    } else if (type === 'auto_center') {
        box.innerHTML = `<input type="text" class="cfg-in" id="stepWordInput" placeholder="Kelime..." style="text-transform:uppercase">`;
        box.style.display = '';
    } else if (type === 'delay') {
        box.innerHTML = `<input type="number" class="cfg-in" id="stepDelayInput" placeholder="Saniye" value="5" min="0.5" step="0.5">`;
        box.style.display = '';
    } else if (type === 'move_z') {
        box.innerHTML = `<input type="number" class="cfg-in" id="stepZInput" placeholder="Z (mm)" value="-163">`;
        box.style.display = '';
    } else if (type === 'nozzle_goto') {
        box.innerHTML = `<input type="number" class="cfg-in" id="stepNozzleAngle" placeholder="Açı (0-180°)" value="0" min="0" max="180">`;
        box.style.display = '';
    } else if (type === 'resistance_test' || type === 'diode_test') {
        box.innerHTML = `<input type="number" class="cfg-in" id="stepTestCount" placeholder="Test Sayısı" value="10" min="1" max="100">`;
        box.style.display = '';
    } else {
        box.innerHTML = '';
        box.style.display = 'none';
    }
}

function addScenarioStep() {
    const type = $('stepType').value;
    let step = { type };

    if (type === 'goto_base') {
        const sel = $('stepBaseSelect');
        if (!sel || !sel.value) { showToast('Konum seçin!', 'error'); return; }
        step.base_name = sel.value;
    } else if (type === 'auto_center') {
        const inp = $('stepWordInput');
        const w = inp ? inp.value.trim().toUpperCase() : '';
        if (!w) { showToast('Kelime girin!', 'error'); return; }
        step.word = w;
    } else if (type === 'delay') {
        const inp = $('stepDelayInput');
        const s = parseFloat(inp ? inp.value : 1) || 1;
        step.seconds = s;
    } else if (type === 'move_z') {
        const inp = $('stepZInput');
        const z = parseFloat(inp ? inp.value : 0);
        if (isNaN(z)) { showToast('Geçerli Z değeri girin!', 'error'); return; }
        step.z = z;
    } else if (type === 'nozzle_goto') {
        const inp = $('stepNozzleAngle');
        let a = parseFloat(inp ? inp.value : 0);
        if (isNaN(a)) { showToast('Geçerli açı değeri girin!', 'error'); return; }
        a = Math.max(0, Math.min(180, a));
        step.angle = a;
    } else if (type === 'resistance_test' || type === 'diode_test') {
        const inp = $('stepTestCount');
        step.test_count = parseInt(inp ? inp.value : 10) || 10;
    }

    if (_editingStepIndex >= 0) {
        _scenarioSteps[_editingStepIndex] = step;
        _editingStepIndex = -1;
        const btn = $('addStepBtn');
        if (btn) {
            btn.innerHTML = '+ Ekle';
            btn.style.background = '';
        }
    } else {
        _scenarioSteps.push(step);
    }
    renderScenarioSteps();
}

function editScenarioStep(idx) {
    if (idx < 0 || idx >= _scenarioSteps.length) return;
    const step = _scenarioSteps[idx];
    _editingStepIndex = idx;

    // Set type and render inputs
    const typeSel = $('stepType');
    if (typeSel) {
        typeSel.value = step.type;
        onStepTypeChange();
    }

    // Populate inputs
    setTimeout(() => { // ensure DOM update
        if (step.type === 'goto_base') {
            const sel = $('stepBaseSelect');
            if (sel) sel.value = step.base_name;
        } else if (step.type === 'auto_center') {
            const inp = $('stepWordInput');
            if (inp) inp.value = step.word;
        } else if (step.type === 'delay') {
            const inp = $('stepDelayInput');
            if (inp) inp.value = step.seconds;
        } else if (step.type === 'move_z') {
            const inp = $('stepZInput');
            if (inp) inp.value = step.z;
        } else if (step.type === 'nozzle_goto') {
            const inp = $('stepNozzleAngle');
            if (inp) inp.value = step.angle;
        } else if (step.type === 'resistance_test' || step.type === 'diode_test') {
            const inp = $('stepTestCount');
            if (inp) inp.value = step.test_count || 10;
        }
    }, 0);

    // Update button text
    const btn = $('addStepBtn');
    if (btn) {
        btn.innerHTML = '📝 Güncelle';
        btn.style.background = 'var(--orange)';
    }
}

function removeScenarioStep(idx) {
    if (_editingStepIndex === idx) {
        _editingStepIndex = -1;
        const btn = $('addStepBtn');
        if (btn) {
            btn.innerHTML = '+ Ekle';
            btn.style.background = '';
        }
    } else if (_editingStepIndex > idx) {
        _editingStepIndex--;
    }
    _scenarioSteps.splice(idx, 1);
    renderScenarioSteps();
}

function moveScenarioStep(idx, dir) {
    const newIdx = idx + dir;
    if (newIdx < 0 || newIdx >= _scenarioSteps.length) return;

    // Update editing index if moved
    if (_editingStepIndex === idx) _editingStepIndex = newIdx;
    else if (_editingStepIndex === newIdx) _editingStepIndex = idx;

    const tmp = _scenarioSteps[idx];
    _scenarioSteps[idx] = _scenarioSteps[newIdx];
    _scenarioSteps[newIdx] = tmp;
    renderScenarioSteps();
}

function clearScenarioSteps() {
    _scenarioSteps = [];
    _editingStepIndex = -1;
    const btn = $('addStepBtn');
    if (btn) {
        btn.innerHTML = '+ Ekle';
        btn.style.background = '';
    }
    $('scenarioName').value = '';
    renderScenarioSteps();
}

function stepLabel(step) {
    const t = step.type;
    if (t === 'goto_base') return `📍 ${step.base_name} konumuna git`;
    if (t === 'auto_center') return `🎯 '${step.word}' kelimesine merkezle`;
    if (t === 'pump_on') return '💨 Pompa AÇ';
    if (t === 'pump_off') return '🛑 Pompa KAPAT';
    if (t === 'delay') return `⏳ ${step.seconds}s bekle`;
    if (t === 'move_z') return `↕️ Z: ${step.z}mm konumuna git`;
    if (t === 'home') return '🏠 Home';
    if (t === 'verify') return '👁️ Doğruluk Kontrolü';
    if (t === 'resistance_test') return `🔬 Direnç Testi (${step.test_count || 10} ölçüm)`;
    if (t === 'diode_test') return `💡 Diyot Testi (${step.test_count || 10} ölçüm)`;
    if (t === 'nozzle_goto') return `🔄 Nozzle ${step.angle || 0}° açıya git`;
    if (t === 'nozzle_home') return '🏠 Nozzle Home';
    return `❓ ${t}`;
}

function renderScenarioSteps() {
    const cont = $('scenarioStepList');
    if (!cont) return;
    if (!_scenarioSteps.length) {
        cont.innerHTML = '<div class="ocr-empty">Henüz adım eklenmedi.</div>';
        return;
    }
    let h = '';
    _scenarioSteps.forEach((s, i) => {
        const bg = (i === _editingStepIndex) ? 'rgba(245, 158, 11, 0.1)' : 'transparent';
        const border = (i === _editingStepIndex) ? '1px solid var(--orange)' : '1px solid rgba(255,255,255,0.06)';

        h += `<div style="display:flex; align-items:center; gap:6px; padding:6px 8px; border-bottom:${border}; background:${bg}; font-size:0.85rem">
            <span style="color:#666; font-weight:600; min-width:24px">${i + 1}.</span>
            <span style="flex:1">${stepLabel(s)}</span>
            <button class="btn-sm" onclick="editScenarioStep(${i})" style="padding:2px 6px; font-size:0.7rem; background:var(--blue); color:#fff" title="Düzenle">✎</button>
            <button class="btn-sm" onclick="moveScenarioStep(${i},-1)" style="padding:2px 6px; font-size:0.7rem" title="Yukarı">▲</button>
            <button class="btn-sm" onclick="moveScenarioStep(${i},1)" style="padding:2px 6px; font-size:0.7rem" title="Aşağı">▼</button>
            <button class="btn-sm" style="background:#d32f2f;color:#fff; padding:2px 6px; font-size:0.7rem" onclick="removeScenarioStep(${i})">✗</button>
        </div>`;
    });
    cont.innerHTML = h;
}

// — CRUD —
async function saveScenario() {
    const name = $('scenarioName').value.trim();
    if (!name) { showToast('Senaryo adı gerekli!', 'error'); return; }
    if (!_scenarioSteps.length) { showToast('En az bir adım ekleyin!', 'error'); return; }

    const r = await api('/api/scenarios', { name, steps: _scenarioSteps });
    if (r.success) {
        showToast('Senaryo kaydedildi.', 'info');
        _scenariosList = r.scenarios;
        renderScenarioList();
        updateScenarioDropdown();
        clearScenarioSteps();
    } else {
        showToast('Hata: ' + r.message, 'error');
    }
}

async function deleteScenario(name) {
    if (!confirm(name + ' silinsin mi?')) return;
    const r = await fetch('/api/scenarios/' + encodeURIComponent(name), { method: 'DELETE' }).then(res => res.json());
    if (r.success) {
        showToast('Senaryo silindi.', 'info');
        _scenariosList = r.scenarios;
        renderScenarioList();
        updateScenarioDropdown();
    } else {
        showToast('Hata: ' + r.message, 'error');
    }
}

function editScenario(name) {
    const s = _scenariosList.find(item => item.name === name);
    if (!s) return;
    $('scenarioName').value = s.name;
    _scenarioSteps = JSON.parse(JSON.stringify(s.steps || []));
    renderScenarioSteps();
    switchTab('scenarios');
    showToast(`'${name}' düzenleme modunda.`, 'info');
}

// — Execution —
async function runScenarioByName(name) {
    const r = await api('/api/scenario/run', { name });
    if (r.success) {
        showToast(r.message, 'info');
    } else {
        showToast(r.message, 'error');
    }
}

async function quickRunScenario() {
    const name = $('quickScenarioSel').value;
    if (!name) { showToast('Senaryo seçin!', 'error'); return; }
    runScenarioByName(name);
}

async function stopScenario() {
    const r = await api('/api/scenario/stop');
    showToast(r.message, r.success ? 'info' : 'error');
}

// — Master Scenarios —
let _masterScenariosList = [];
let _masterScenarioSteps = []; // currently building list of scenario names

async function loadMasterScenarios() {
    try {
        const r = await fetch('/api/master_scenarios').then(res => res.json());
        if (r.success) {
            _masterScenariosList = r.master_scenarios || [];
            renderMasterScenarioList();
            updateMasterScenarioDropdown();
        }
    } catch (e) { console.error('Master Scenarios load error', e); }
}

function renderMasterScenarioList() {
    const cont = $('masterScenarioList');
    if (!cont) return;
    if (!_masterScenariosList.length) {
        cont.innerHTML = '<div class="ocr-empty">Kayıtlı master senaryo yok.</div>';
        return;
    }
    let h = '<table style="width:100%; border-collapse:collapse; font-size:0.9rem">';
    h += '<tr style="border-bottom:1px solid #444; text-align:left; color:#aaa"><th style="padding:4px">İsim</th><th>Sıralama</th><th></th></tr>';
    _masterScenariosList.forEach(ms => {
        const seqStr = ms.sequence ? ms.sequence.join(', ') : '';
        h += `<tr style="border-bottom:1px solid #333">
            <td style="padding:8px">${esc(ms.name)}</td>
            <td style="max-width:150px; text-overflow:ellipsis; overflow:hidden; white-space:nowrap" title="${esc(seqStr)}">${esc(seqStr)}</td>
            <td style="text-align:right; white-space:nowrap">
                <button class="btn-sm" style="background:#4caf50;color:#fff" onclick="editMasterScenario('${esc(ms.name)}')">✏️</button>
                <button class="btn-sm" style="background:#d32f2f;color:#fff" onclick="deleteMasterScenario('${esc(ms.name)}')">Sil</button>
                <button class="btn-sm" style="background:var(--yellow);color:#000" onclick="runMasterScenarioByName('${esc(ms.name)}')">▶ P. Başlat</button>
            </td>
         </tr>`;
    });
    h += '</table>';
    cont.innerHTML = h;
}

function updateMasterScenarioDropdown() {
    const sel = $('quickMasterScenarioSel');
    if (!sel) return;
    const cur = sel.value;
    sel.innerHTML = '<option value="">👑 Master Senaryo seç...</option>' + _masterScenariosList.map(s => `<option value="${esc(s.name)}">${esc(s.name)}</option>`).join('');
    if (cur && _masterScenariosList.find(s => s.name === cur)) sel.value = cur;
}

function addMasterScenarioStep() {
    const sel = $('masterStepSelect');
    if (!sel || !sel.value) { showToast('Eklenecek senaryoyu seçin!', 'warning'); return; }
    _masterScenarioSteps.push(sel.value);
    renderMasterScenarioSteps();
}

function removeMasterScenarioStep(idx) {
    _masterScenarioSteps.splice(idx, 1);
    renderMasterScenarioSteps();
}

function moveMasterScenarioStep(idx, dir) {
    const newIdx = idx + dir;
    if (newIdx < 0 || newIdx >= _masterScenarioSteps.length) return;
    const tmp = _masterScenarioSteps[idx];
    _masterScenarioSteps[idx] = _masterScenarioSteps[newIdx];
    _masterScenarioSteps[newIdx] = tmp;
    renderMasterScenarioSteps();
}

function clearMasterScenarioSteps() {
    _masterScenarioSteps = [];
    $('masterScenarioName').value = '';
    renderMasterScenarioSteps();
}

function renderMasterScenarioSteps() {
    const cont = $('masterScenarioStepList');
    if (!cont) return;
    if (!_masterScenarioSteps.length) {
        cont.innerHTML = '<div class="ocr-empty">Henüz senaryo eklenmedi.</div>';
        return;
    }
    let h = '';
    _masterScenarioSteps.forEach((sName, i) => {
        h += `<div style="display:flex; align-items:center; gap:6px; padding:6px 8px; border-bottom:1px solid rgba(255,255,255,0.06); font-size:0.85rem">
            <span style="color:#666; font-weight:600; min-width:24px">${i + 1}.</span>
            <span style="flex:1">🎬 ${esc(sName)}</span>
            <button class="btn-sm" onclick="moveMasterScenarioStep(${i},-1)" style="padding:2px 6px; font-size:0.7rem" title="Yukarı">▲</button>
            <button class="btn-sm" onclick="moveMasterScenarioStep(${i},1)" style="padding:2px 6px; font-size:0.7rem" title="Aşağı">▼</button>
            <button class="btn-sm" style="background:#d32f2f;color:#fff; padding:2px 6px; font-size:0.7rem" onclick="removeMasterScenarioStep(${i})">✗</button>
        </div>`;
    });
    cont.innerHTML = h;
}

async function saveMasterScenario() {
    const name = $('masterScenarioName').value.trim();
    if (!name) { showToast('Master Senaryo adı gerekli!', 'error'); return; }
    if (!_masterScenarioSteps.length) { showToast('En az bir senaryo ekleyin!', 'error'); return; }

    const r = await api('/api/master_scenarios', { name, sequence: _masterScenarioSteps });
    if (r.success) {
        showToast('Master Senaryo kaydedildi.', 'info');
        _masterScenariosList = r.master_scenarios;
        renderMasterScenarioList();
        updateMasterScenarioDropdown();
        clearMasterScenarioSteps();
    } else {
        showToast('Hata: ' + r.message, 'error');
    }
}

function editMasterScenario(name) {
    const ms = _masterScenariosList.find(item => item.name === name);
    if (!ms) return;
    $('masterScenarioName').value = ms.name;
    _masterScenarioSteps = [...(ms.sequence || [])];
    renderMasterScenarioSteps();
    switchTab('scenarios');
    showToast(`'${name}' (Master) düzenleme modunda.`, 'info');
}

async function deleteMasterScenario(name) {
    if (!confirm(name + ' silinsin mi?')) return;
    const r = await fetch('/api/master_scenarios/' + encodeURIComponent(name), { method: 'DELETE' }).then(res => res.json());
    if (r.success) {
        showToast('Master Senaryo silindi.', 'info');
        _masterScenariosList = r.master_scenarios;
        renderMasterScenarioList();
        updateMasterScenarioDropdown();
    } else {
        showToast('Hata: ' + r.message, 'error');
    }
}

async function runMasterScenarioByName(name) {
    const r = await api('/api/master_scenario/run', { name });
    if (r.success) {
        showToast(r.message, 'info');
    } else {
        showToast(r.message, 'error');
    }
}

// — Verification (Doğrulama) —
let _vConfig = { base_name: '', threshold: 127, boxes: [] };

async function loadVerification() {
    try {
        const r = await fetch('/api/verification/settings').then(res => res.json());
        if (r.success) {
            _vConfig = r.verification;
            if (!_vConfig.boxes) _vConfig.boxes = [];

            const eTh = $('vThreshold');
            if (eTh) {
                eTh.value = _vConfig.threshold || 127;
                const lbl = $('vThVal');
                if (lbl) lbl.textContent = eTh.value;
            }

            renderVerificationBoxes();
            renderBoxOverlay();

            if (_basesList && _basesList.length > 0) {
                renderBases(_basesList);
            }
        }
    } catch (e) { console.error('Verification load error', e); }
}

function renderVerificationBoxes() {
    const cont = $('vBoxEditorList');
    if (!cont) return;
    if (!_vConfig.boxes.length) {
        cont.innerHTML = '<div class="ocr-empty" style="font-size:0.8rem">Henüz kutu eklenmedi.</div>';
        return;
    }

    let h = '';
    _vConfig.boxes.forEach((b, i) => {
        h += `<div style="background:#222; padding:8px; border-radius:4px; border:1px solid #333; display:flex; flex-direction:column; gap:6px">
            <div style="display:flex; justify-content:space-between; align-items:center">
                <input type="text" class="cfg-in" style="width:120px; padding:2px 4px" value="${esc(b.name)}" oninput="updateVBox(${i}, 'name', this.value)">
                <button class="btn-sm" style="background:#d32f2f; color:#fff" onclick="removeVBox(${i})">Sil</button>
            </div>
            <div style="display:flex; gap:8px; align-items:center; font-size:0.8rem; color:#aaa">
                Hedef Doluluk (%): 
                <input type="number" class="cfg-in" style="width:60px; padding:2px 4px" value="${b.target_ratio}" step="0.5" oninput="updateVBox(${i}, 'target_ratio', parseFloat(this.value)||0)">
            </div>
        </div>`;
    });
    cont.innerHTML = h;
}

function updateVBox(idx, key, val) {
    if (_vConfig.boxes[idx]) {
        _vConfig.boxes[idx][key] = val;
    }
}

function removeVBox(idx) {
    _vConfig.boxes.splice(idx, 1);
    renderVerificationBoxes();
    renderBoxOverlay();
}

function addNewVerificationBox() {
    const newId = 'box_' + Date.now();
    _vConfig.boxes.push({
        id: newId,
        name: 'Yeni Kutu ' + (_vConfig.boxes.length + 1),
        x: 0.4, y: 0.4, w: 0.2, h: 0.2, // percentages (0 -> 1)
        target_ratio: 10.0
    });
    renderVerificationBoxes();
    renderBoxOverlay();
}

async function saveVerificationSettings() {
    _vConfig.base_name = $('vBaseSelect').value;
    _vConfig.threshold = parseInt($('vThreshold').value) || 127;

    const r = await api('/api/verification/settings', _vConfig, 'POST');
    if (r.success) {
        showToast('Doğrulama ayarları kaydedildi.', 'info');
    } else {
        showToast('Hata: ' + r.message, 'error');
    }
}

async function testVerification() {
    saveVerificationSettings().then(async () => {
        const r = await fetch('/api/verification/run', { method: 'POST' }).then(res => res.json());
        if (r.success) {
            showToast('Doğrulama testi başlatıldı...', 'info');
            switchTab('control'); // Odaklanmak ve HUD'ı görmek için
        } else {
            showToast('Hata: ' + r.message, 'error');
        }
    });
}

// GUI Drawing and dragging over #vBoxOverlay
let _vDrag = null; // { type, idx, startX, startY, origX, origY, origW, origH }

/** Kameranın container içinde gerçekte kapladığı alanı hesapla (object-fit:contain) */
function getRenderedImageRect() {
    const img = $('vMainCam');
    const container = $('vCanvasContainer');
    if (!img || !container) return null;
    const cRect = container.getBoundingClientRect();
    const natW = img.naturalWidth || 640;
    const natH = img.naturalHeight || 480;
    const scale = Math.min(cRect.width / natW, cRect.height / natH);
    const rw = natW * scale;
    const rh = natH * scale;
    const rx = (cRect.width - rw) / 2;
    const ry = (cRect.height - rh) / 2;
    return { x: rx, y: ry, w: rw, h: rh };
}

function syncOverlayToImage() {
    const ov = $('vBoxOverlay');
    const r = getRenderedImageRect();
    if (!ov || !r) return;
    ov.style.left = r.x + 'px';
    ov.style.top = r.y + 'px';
    ov.style.width = r.w + 'px';
    ov.style.height = r.h + 'px';
}

// Sürekli RAF döngüsü ile overlay'ı her zaman kamera ile senkron tut
(function _vSyncLoop() {
    syncOverlayToImage();
    requestAnimationFrame(_vSyncLoop);
})();

function renderBoxOverlay() {
    const ov = $('vBoxOverlay');
    if (!ov) return;
    syncOverlayToImage();
    ov.innerHTML = '';

    _vConfig.boxes.forEach((b, i) => {
        const div = document.createElement('div');
        div.style.position = 'absolute';
        div.style.left = (b.x * 100) + '%';
        div.style.top = (b.y * 100) + '%';
        div.style.width = (b.w * 100) + '%';
        div.style.height = (b.h * 100) + '%';
        div.style.border = '2px solid var(--orange)';
        div.style.backgroundColor = 'rgba(245, 158, 11, 0.1)';
        div.style.pointerEvents = 'auto';
        div.style.cursor = 'move';
        div.style.boxSizing = 'border-box';

        // Label
        const lbl = document.createElement('div');
        lbl.textContent = b.name;
        lbl.style.cssText = 'position:absolute;top:-18px;left:-2px;background:var(--orange);color:#000;font-size:0.65rem;padding:1px 4px;font-weight:bold;white-space:nowrap';
        div.appendChild(lbl);

        // Resize handle
        const handle = document.createElement('div');
        handle.style.cssText = 'position:absolute;right:-4px;bottom:-4px;width:10px;height:10px;background:#fff;border:1px solid #000;cursor:se-resize';
        handle.onmousedown = (e) => { e.preventDefault(); e.stopPropagation(); startVDrop(e, i, 'resize'); };
        div.appendChild(handle);

        div.onmousedown = (e) => { e.preventDefault(); e.stopPropagation(); startVDrop(e, i, 'move'); };
        ov.appendChild(div);
    });
}

function startVDrop(e, idx, type) {
    const b = _vConfig.boxes[idx];
    _vDrag = {
        type, idx,
        startX: e.clientX, startY: e.clientY,
        origX: b.x, origY: b.y, origW: b.w, origH: b.h
    };
    document.addEventListener('mousemove', onVMouseMove);
    document.addEventListener('mouseup', onVMouseUp);
}

function onVMouseMove(e) {
    if (!_vDrag) return;
    const ov = $('vBoxOverlay');
    const rect = ov.getBoundingClientRect();
    const dx = (e.clientX - _vDrag.startX) / rect.width;
    const dy = (e.clientY - _vDrag.startY) / rect.height;
    const b = _vConfig.boxes[_vDrag.idx];
    if (_vDrag.type === 'move') {
        b.x = Math.max(0, Math.min(1 - b.w, _vDrag.origX + dx));
        b.y = Math.max(0, Math.min(1 - b.h, _vDrag.origY + dy));
    } else if (_vDrag.type === 'resize') {
        b.w = Math.max(0.02, Math.min(1 - b.x, _vDrag.origW + dx));
        b.h = Math.max(0.02, Math.min(1 - b.y, _vDrag.origH + dy));
    }
    renderBoxOverlay();
}

function onVMouseUp() {
    if (_vDrag) {
        document.removeEventListener('mousemove', onVMouseMove);
        document.removeEventListener('mouseup', onVMouseUp);
        _vDrag = null;
    }
}

function quickRunMasterScenario() {
    const name = $('quickMasterScenarioSel').value;
    if (!name) { showToast('Master Senaryo seçin!', 'error'); return; }
    runMasterScenarioByName(name);
}

// — Init —
loadScenarios();
loadMasterScenarios();
loadVerification();
onStepTypeChange(); // init param box


/* ═══════════════════════════════════════════════════════════════════════════
   NOZZLE CONTROLLER (Slave Arduino — Step Motor + Direnç + Diyot)
   ═══════════════════════════════════════════════════════════════════════════ */

// ─── Measurement Storage ────────────────────────────────────────────────────
let _nzResMeasurements = [];
let _nzDiodeMeasurements = [];

// ─── SocketIO Listeners ─────────────────────────────────────────────────────

socket.on('nozzle_status', (d) => {
    updateNozzleUI(d);
});

socket.on('nozzle_home_result', (d) => {
    showToast(d.message, d.success ? 'info' : 'error');
});

socket.on('nozzle_test_progress', (d) => {
    if (d.test_type === 'resistance') {
        const prog = $('nzResProgress');
        if (!prog) return;
        const total = d.total || 10;
        const current = d.current || 0;

        // Initialize dots if first call
        if (current === 1 || prog.children.length !== total) {
            prog.innerHTML = '';
            for (let i = 0; i < total; i++) {
                const dot = document.createElement('div');
                dot.className = 'nz-test-dot';
                dot.textContent = i + 1;
                prog.appendChild(dot);
            }
        }

        // Store measurement
        if (d.result && current > 0) {
            _nzResMeasurements[current - 1] = d.result;

            const dot = prog.children[current - 1];
            if (dot) {
                dot.classList.add(d.result.status === 'NORMAL' ? 'pass' : 'fail');
                dot.classList.add('active');
                dot.title = d.result.resistance_formatted || '';
            }
            if (current > 1 && prog.children[current - 2]) {
                prog.children[current - 2].classList.remove('active');
            }
        }

        // Update instant display
        if (d.result && d.result.success) {
            $('nzResValue').textContent = d.result.resistance_formatted;
            $('nzResDetails').textContent = `ADC: ${d.result.adc} | V: ${d.result.voltage}V | ${d.result.status}`;
        }
    }

    if (d.test_type === 'diode') {
        if (d.message) {
            showToast(d.message, 'info');
            return;
        }
        const prog = $('nzDiodeProgress');
        if (!prog) return;
        const total = d.total || 10;
        const current = d.current || 0;

        if (current === 1 || prog.children.length !== total) {
            prog.innerHTML = '';
            for (let i = 0; i < total; i++) {
                const dot = document.createElement('div');
                dot.className = 'nz-test-dot';
                dot.textContent = i + 1;
                prog.appendChild(dot);
            }
        }

        // Store measurement
        if (d.result && current > 0) {
            _nzDiodeMeasurements[current - 1] = d.result;

            const dot = prog.children[current - 1];
            if (dot) {
                dot.classList.add(d.result.current_passing ? 'pass' : 'fail');
                dot.classList.add('active');
                dot.textContent = d.result.current_passing ? '✓' : '✗';
            }
            if (current > 1 && prog.children[current - 2]) {
                prog.children[current - 2].classList.remove('active');
            }
        }

        // Update instant display
        if (d.result && d.result.success) {
            $('nzDiodeValue').textContent = d.result.result;
            $('nzDiodeValue').style.color = d.result.current_passing ? 'var(--green)' : '#f44336';
            $('nzDiodeDetails').textContent = `ADC: ${d.result.adc} | Eşik: ${d.result.threshold}`;
        }
    }
});

socket.on('nozzle_test_result', (d) => {
    if (d.test_type === 'resistance') {
        const el = $('nzResTestResult');
        if (el) {
            el.style.display = 'block';
            el.innerHTML = _buildResistanceDetailReport(d);
        }
        showToast(`Direnç Testi Tamamlandı: ${d.average_formatted}`, 'info');
    }

    if (d.test_type === 'diode') {
        const el = $('nzDiodeTestResult');
        if (el) {
            el.style.display = 'block';
            el.innerHTML = _buildDiodeDetailReport(d);
        }
        showToast(`Diyot Testi: ${d.decision}`, d.is_passing ? 'info' : 'warning');
    }
});

// ─── Detail Report Builders ─────────────────────────────────────────────────

function _buildResistanceDetailReport(d) {
    const cls = d.valid_count > 0 ? 'pass' : 'fail';
    let h = `<div class="nz-decision ${cls}" style="margin-bottom:8px">
        ORTALAMA: ${d.average_formatted}<br>
        <span style="font-size:0.7rem;font-weight:400">${d.valid_count}/${d.total} geçerli ölçüm</span>
    </div>`;

    // Statistics
    if (d.stats) {
        h += `<div class="nz-stat-grid">
            <div class="nz-stat-box"><div class="nz-stat-label">Min</div><div class="nz-stat-value">${d.stats.min_formatted}</div></div>
            <div class="nz-stat-box"><div class="nz-stat-label">Max</div><div class="nz-stat-value">${d.stats.max_formatted}</div></div>
            <div class="nz-stat-box"><div class="nz-stat-label">Std Sapma</div><div class="nz-stat-value">${d.stats.std_formatted}</div></div>
            <div class="nz-stat-box"><div class="nz-stat-label">Geçerli</div><div class="nz-stat-value">${d.valid_count}/${d.total}</div></div>
        </div>`;
    }

    // Detail table from stored measurements
    const measurements = d.measurements || _nzResMeasurements;
    if (measurements && measurements.length > 0) {
        h += `<div style="max-height:150px;overflow-y:auto;margin-top:6px">
        <table class="nz-detail-table">
            <thead><tr><th>#</th><th>ADC</th><th>Voltaj</th><th>Direnç</th><th>Durum</th></tr></thead>
            <tbody>`;
        measurements.forEach((m, i) => {
            if (!m) return;
            const statusColor = m.status === 'NORMAL' ? '#4caf50' : '#f44336';
            const statusIcon = m.status === 'NORMAL' ? '✓' : m.status === 'ACIK_DEVRE' ? '∞' : '⚡';
            h += `<tr>
                <td style="color:#666">${i + 1}</td>
                <td>${m.adc || '--'}</td>
                <td>${m.voltage !== undefined ? m.voltage + 'V' : '--'}</td>
                <td style="font-weight:600;color:var(--green)">${m.resistance_formatted || '--'}</td>
                <td style="color:${statusColor}">${statusIcon} ${m.status || '--'}</td>
            </tr>`;
        });
        h += `</tbody></table></div>`;
    }

    return h;
}

function _buildDiodeDetailReport(d) {
    const cls = d.is_passing ? 'pass' : 'fail';
    let h = `<div class="nz-decision ${cls}" style="margin-bottom:8px">
        ${d.decision}<br>
        <span style="font-size:0.7rem;font-weight:400">${d.passing_count}/${d.total} akım geçti (≥${d.majority_needed} gerekli)</span>
    </div>`;

    if (d.auto_corrected) {
        h += `<div style="background:rgba(59,130,246,0.1);border:1px solid rgba(59,130,246,0.3);border-radius:6px;padding:6px;margin-bottom:6px;font-size:0.72rem;color:var(--blue);text-align:center">
            🔄 Otomatik düzeltme uygulandı — Nozzle 180° döndürüldü
        </div>`;
    }

    // Statistics 
    if (d.stats) {
        h += `<div class="nz-stat-grid">
            <div class="nz-stat-box"><div class="nz-stat-label">Ort. ADC</div><div class="nz-stat-value">${d.stats.avg_adc}</div></div>
            <div class="nz-stat-box"><div class="nz-stat-label">Eşik</div><div class="nz-stat-value">${d.stats.threshold}</div></div>
            <div class="nz-stat-box"><div class="nz-stat-label">Min ADC</div><div class="nz-stat-value">${d.stats.min_adc}</div></div>
            <div class="nz-stat-box"><div class="nz-stat-label">Max ADC</div><div class="nz-stat-value">${d.stats.max_adc}</div></div>
        </div>`;
    }

    // Detail table from stored measurements
    const measurements = d.measurements || _nzDiodeMeasurements;
    if (measurements && measurements.length > 0) {
        h += `<div style="max-height:150px;overflow-y:auto;margin-top:6px">
        <table class="nz-detail-table">
            <thead><tr><th>#</th><th>ADC</th><th>Eşik</th><th>Fark</th><th>Sonuç</th></tr></thead>
            <tbody>`;
        measurements.forEach((m, i) => {
            if (!m) return;
            const passing = m.current_passing;
            const diff = m.adc - (m.threshold || 0);
            const diffColor = diff >= 0 ? '#4caf50' : '#f44336';
            h += `<tr>
                <td style="color:#666">${i + 1}</td>
                <td>${m.adc || '--'}</td>
                <td style="color:#888">${m.threshold || '--'}</td>
                <td style="color:${diffColor};font-weight:600">${diff >= 0 ? '+' : ''}${diff}</td>
                <td style="color:${passing ? '#4caf50' : '#f44336'};font-weight:bold">${passing ? '✅ GEÇİYOR' : '❌ GEÇMİYOR'}</td>
            </tr>`;
        });
        h += `</tbody></table></div>`;
    }

    return h;
}

// ─── Nozzle UI Update ───────────────────────────────────────────────────────

function updateNozzleUI(d) {
    if (!d) return;
    const dot = $('nzStatusDot');
    const status = $('nzConnStatus');
    const angle = $('nzAngle');
    const badge = $('nzHomedBadge');

    if (dot) { dot.className = 'nz-status-dot ' + (d.connected ? 'on' : 'off'); }
    if (status) {
        status.textContent = d.connected ? 'Bağlı ✓' : 'Bağlı Değil';
        status.style.color = d.connected ? '#4caf50' : '#f44336';
    }
    if (angle) { angle.innerHTML = `${d.angle.toFixed(1)}<span class="nz-unit">°</span>`; }
    if (badge) {
        if (d.is_homed) {
            badge.textContent = 'HOMED ✓';
            badge.style.background = '#4caf50';
        } else {
            badge.textContent = 'HOME YOK';
            badge.style.background = '#f44336';
        }
    }
}

// ─── Nozzle Functions ───────────────────────────────────────────────────────

async function nozzleConnect() {
    const port = $('nzPort') ? $('nzPort').value : '';
    const body = port ? { port } : {};
    const r = await api('/api/nozzle/connect', body);
    showToast(r.message, r.success ? 'info' : 'error');
    if (r.nozzle_status) updateNozzleUI(r.nozzle_status);
    else await refreshNozzleStatus();
}

async function nozzleDisconnect() {
    const r = await api('/api/nozzle/disconnect');
    showToast(r.message, 'info');
    if (r.nozzle_status) updateNozzleUI(r.nozzle_status);
    else await refreshNozzleStatus();
}

async function nozzleHome() {
    showToast('Nozzle Homing başlatıldı...', 'info');
    const r = await api('/api/nozzle/home');
    if (!r.success) showToast(r.message, 'error');
    setTimeout(refreshNozzleStatus, 2000);
    setTimeout(refreshNozzleStatus, 5000);
    setTimeout(refreshNozzleStatus, 10000);
    setTimeout(refreshNozzleStatus, 20000);
}

async function nozzleGoto() {
    const angle = parseFloat($('nzTargetAngle') ? $('nzTargetAngle').value : 0);
    const r = await api('/api/nozzle/goto', { angle });
    showToast(r.message, 'info');
    if (r.nozzle_status) updateNozzleUI(r.nozzle_status);
    else await refreshNozzleStatus();
}

async function nozzleMoveRel(degrees) {
    const r = await api('/api/nozzle/move_relative', { degrees });
    showToast(r.message, 'info');
    if (r.nozzle_status) updateNozzleUI(r.nozzle_status);
    else await refreshNozzleStatus();
}

async function refreshNozzleStatus() {
    try {
        const st = await fetch('/api/nozzle/status').then(res => res.json());
        updateNozzleUI(st);
    } catch (e) { /* ignore */ }
}

async function nozzleReadResistance() {
    try {
        const r = await fetch('/api/nozzle/read_resistance').then(res => res.json());
        if (r.success) {
            $('nzResValue').textContent = r.resistance_formatted;
            $('nzResDetails').textContent = `ADC: ${r.adc} | V: ${r.voltage}V | ${r.status}`;
        } else {
            showToast('Direnç okuma hatası: ' + (r.error || ''), 'error');
        }
    } catch (e) {
        showToast('Direnç okuma hatası!', 'error');
    }
}

async function nozzleReadDiode() {
    try {
        const r = await fetch('/api/nozzle/read_diode').then(res => res.json());
        if (r.success) {
            $('nzDiodeValue').textContent = r.result;
            $('nzDiodeValue').style.color = r.current_passing ? 'var(--green)' : '#f44336';
            $('nzDiodeDetails').textContent = `ADC: ${r.adc} | Eşik: ${r.threshold}`;
        } else {
            showToast('Diyot okuma hatası: ' + (r.error || ''), 'error');
        }
    } catch (e) {
        showToast('Diyot okuma hatası!', 'error');
    }
}

async function nozzleResistanceTest() {
    // Reset progress and stored measurements
    _nzResMeasurements = [];
    const prog = $('nzResProgress');
    if (prog) prog.innerHTML = '';
    const res = $('nzResTestResult');
    if (res) res.style.display = 'none';

    showToast('Tekrarlı direnç testi başlatılıyor...', 'info');
    const r = await api('/api/nozzle/resistance_test', {});
    if (!r.success) showToast(r.message, 'error');
}

async function nozzleDiodeTest() {
    // Reset progress and stored measurements
    _nzDiodeMeasurements = [];
    const prog = $('nzDiodeProgress');
    if (prog) prog.innerHTML = '';
    const res = $('nzDiodeTestResult');
    if (res) res.style.display = 'none';

    const autoCorrect = $('nzAutoCorrect') ? $('nzAutoCorrect').checked : true;
    showToast('Tekrarlı diyot testi başlatılıyor...', 'info');
    const r = await api('/api/nozzle/diode_test', { auto_correct: autoCorrect });
    if (!r.success) showToast(r.message, 'error');
}

async function loadNozzleConfig() {
    try {
        const r = await fetch('/api/nozzle/config').then(res => res.json());
        if ($('nzPort')) $('nzPort').value = r.serial_port || '';
        if ($('nzCfgStepsRev')) $('nzCfgStepsRev').value = r.steps_per_rev_base || 200;
        if ($('nzCfgMicrostep')) $('nzCfgMicrostep').value = r.microstepping || 16;
        if ($('nzCfgMinAngle')) $('nzCfgMinAngle').value = r.min_angle || -180;
        if ($('nzCfgMaxAngle')) $('nzCfgMaxAngle').value = r.max_angle || 180;
        if ($('nzCfgNormalSpeed')) $('nzCfgNormalSpeed').value = r.normal_speed_us || 400;
        if ($('nzCfgHomingSpeed')) $('nzCfgHomingSpeed').value = r.homing_speed_us || 2000;
        if ($('nzCfgAccelSteps')) $('nzCfgAccelSteps').value = r.accel_steps || 200;
        if ($('nzCfgAccelStart')) $('nzCfgAccelStart').value = r.accel_start_us || 2000;
        if ($('nzCfgLimitPin')) $('nzCfgLimitPin').value = r.limit_pin || 9;
        if ($('nzCfgAnalogPin')) $('nzCfgAnalogPin').value = r.analog_pin || 1;
        if ($('nzCfgHomingDir')) $('nzCfgHomingDir').value = r.homing_dir || 1;
        if ($('nzCfgBackDir')) $('nzCfgBackDir').value = r.homing_back_dir || 0;
        if ($('nzCfgKnownR')) $('nzCfgKnownR').value = r.known_resistance || 10000;
        if ($('nzCfgAdcSamples')) $('nzCfgAdcSamples').value = r.adc_sample_count || 20;
        if ($('nzCfgDiodeThreshold')) $('nzCfgDiodeThreshold').value = r.diode_threshold || 500;
        if ($('nzCfgTestCount')) $('nzCfgTestCount').value = r.test_count || 10;
        if ($('nzCfgTestInterval')) $('nzCfgTestInterval').value = r.test_interval || 1.0;

        // Fetch current status
        const st = await fetch('/api/nozzle/status').then(res => res.json());
        updateNozzleUI(st);
    } catch (e) {
        console.error('Nozzle config load error', e);
    }
}

async function saveNozzleConfig() {
    const data = {
        serial_port: $('nzPort') ? $('nzPort').value : '',
        steps_per_rev_base: parseInt($('nzCfgStepsRev')?.value) || 200,
        microstepping: parseInt($('nzCfgMicrostep')?.value) || 16,
        min_angle: parseFloat($('nzCfgMinAngle')?.value) || -180,
        max_angle: parseFloat($('nzCfgMaxAngle')?.value) || 180,
        normal_speed_us: parseInt($('nzCfgNormalSpeed')?.value) || 400,
        homing_speed_us: parseInt($('nzCfgHomingSpeed')?.value) || 2000,
        accel_steps: parseInt($('nzCfgAccelSteps')?.value) || 200,
        accel_start_us: parseInt($('nzCfgAccelStart')?.value) || 2000,
        limit_pin: parseInt($('nzCfgLimitPin')?.value) || 9,
        analog_pin: parseInt($('nzCfgAnalogPin')?.value) || 1,
        homing_dir: parseInt($('nzCfgHomingDir')?.value) || 1,
        homing_back_dir: parseInt($('nzCfgBackDir')?.value) || 0,
        known_resistance: parseInt($('nzCfgKnownR')?.value) || 10000,
        adc_sample_count: parseInt($('nzCfgAdcSamples')?.value) || 20,
        diode_threshold: parseInt($('nzCfgDiodeThreshold')?.value) || 500,
        test_count: parseInt($('nzCfgTestCount')?.value) || 10,
        test_interval: parseFloat($('nzCfgTestInterval')?.value) || 1.0,
    };

    const r = await api('/api/nozzle/config', data);
    showToast(r.message, r.success ? 'info' : 'error');
}

// Init Nozzle
loadNozzleConfig();
