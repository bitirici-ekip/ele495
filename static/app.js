/* PNP Kontrol Merkezi — app.js */
let moveStep = 1.0, socket = null;
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
    socket.on('connect', () => { addC('✓ Bağlantı kuruldu.', 'info'); setBadge('motorBadge', 'motorBadgeTxt', 'Motor', 'ok'); });
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
    ['grblBadge', 'grblSm'].forEach(id => { const e = $(id); if (e) { e.textContent = s; e.className = (id === 'grblBadge' ? 'grbl-badge ' : 'grbl-sm ') + cls; } });
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
async function homeMotor() {
    addC('Home gönderiliyor...', 'info');
    showOverlay('Home Konumuna Gidiliyor...');
    const r = await api('/api/home');
    if (!r.success) { showToast(r.message || 'Home hatası'); showOverlay('Home Hatası!'); setTimeout(hideOverlay, 3000); }
    else { setTimeout(hideOverlay, 5000); }
}
function startAutoCenter() {
    const inp = $('targetInput');
    const word = inp ? inp.value.trim().toUpperCase() : "";

    $('acStatusBox').innerHTML = '<div style="color:#aaa">Başlatılıyor...</div>';
    api('/api/auto_center', { target_word: word }, 'POST');
}
async function pumpCtl(on) {
    addC(`Pompa ${on ? 'açılıyor' : 'kapatılıyor'}...`, 'info');
    showOverlay(on ? 'Pompa AÇIK' : 'Pompa KAPALI');
    const r = await api('/api/pump', { state: on });
    addC(r.message, 'info');
    setTimeout(hideOverlay, 1500);
}
async function emergencyStop() {
    addC('🚨 ACİL DURDURMA!', 'error');
    showOverlay('⚠️ ACİL DURDURMA ⚠️');
    showToast('ACİL DURDURMA aktif!', 'error');
    await api('/api/emergency_stop');
    setTimeout(hideOverlay, 3000);
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
}
async function loadConfig() { try { const r = await fetch('/api/config').then(r => r.json()); applyConfig(r); } catch (e) { } }
async function saveConfig() {
    const r = await api('/api/config', { pixel_to_mm_x: +$('cfgPxX').value, pixel_to_mm_y: +$('cfgPxY').value, target_x: +$('cfgTX').value, target_y: +$('cfgTY').value, auto_center_tolerance: +$('cfgTol').value, auto_center_max_iter: +$('cfgMaxIter').value, feed_rate: +$('cfgFeed').value, invert_x: $('cfgIX').checked, invert_y: $('cfgIY').checked });
    addC('Kalibrasyon kaydedildi.', 'info'); showToast('Ayarlar kaydedildi', 'info');
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
function setStep(s) { moveStep = s; document.querySelectorAll('.sb').forEach(b => b.classList.toggle('active', parseFloat(b.textContent) === s)); }

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
        case 'h': case 'H': homeMotor(); break;
        case 'c': case 'C': autoCenter(); break;
        case 'e': case 'E': emergencyStop(); break;
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


/* ═══ HELPERS ═══ */
function $(id) { return document.getElementById(id); }
function esc(t) { const d = document.createElement('div'); d.textContent = t; return d.innerHTML; }
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
