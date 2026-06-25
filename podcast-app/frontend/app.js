'use strict';

// ── Config ────────────────────────────────────────────────────────────────
const API = '';   // same origin; change to 'http://localhost:8000' for dev

// ── State ─────────────────────────────────────────────────────────────────
let digest      = null;
let podcastText = '';
let utterance   = null;
let synth       = window.speechSynthesis;
let playing     = false;
let charIndex   = 0;
let totalChars  = 0;
let speed       = 1.0;
let progressTimer = null;

// ── DOM refs ──────────────────────────────────────────────────────────────
const $  = id => document.getElementById(id);
const $$ = sel => document.querySelectorAll(sel);

// ── Init ──────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  updateDateLabel();
  fetchDigest();
  bindEvents();
});

function updateDateLabel() {
  const now = new Date();
  const options = { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long', timeZone: 'Asia/Taipei' };
  $('dateLabel').textContent = now.toLocaleDateString('zh-TW', options);
}

// ── Data fetching ─────────────────────────────────────────────────────────
async function fetchDigest(showOverlay = false) {
  setStatus('loading', '擷取資料中…');
  if (showOverlay) $('loadingOverlay').classList.add('visible');

  try {
    const res  = await fetch(`${API}/api/digest/today`);
    const data = await res.json();

    if (!data.fetched) {
      setStatus('loading', '首次擷取新聞中，請稍候…');
      $('loadingOverlay').classList.add('visible');
      setTimeout(fetchDigest, 8000);
      return;
    }

    digest = data;
    podcastText = data.digest?.podcast_script || '';
    totalChars  = podcastText.length;

    renderAllTabs(data);
    setStatus('ok', '資料已更新');
    $('loadingOverlay').classList.remove('visible');

  } catch (err) {
    console.error(err);
    setStatus('error', '無法連線至伺服器');
    $('loadingOverlay').classList.remove('visible');
  }
}

function setStatus(type, text) {
  const pill = $('statusPill');
  pill.className = 'status-pill ' + (type === 'ok' ? '' : type);
  $('statusText').textContent = text;
}

// ── Render ────────────────────────────────────────────────────────────────
const CATEGORY_META = {
  international: { label: '國際要聞', emoji: '🌍' },
  health:        { label: '醫療健康', emoji: '🏥' },
  technology:    { label: '科技新聞', emoji: '💻' },
  ai:            { label: '人工智慧', emoji: '🤖' },
  taiwan:        { label: '台灣要聞', emoji: '🇹🇼' },
};

function renderAllTabs(data) {
  // News categories
  for (const [cat, meta] of Object.entries(CATEGORY_META)) {
    const grid = $(`grid-${cat}`);
    if (!grid) continue;
    const articles = (data.articles_by_category || {})[cat] || [];
    grid.innerHTML = articles.length
      ? articles.map(renderArticleCard).join('')
      : emptyState(meta.emoji, `暫無${meta.label}`, '今日尚未擷取或無相關新聞');
  }

  // Academic
  const papers = data.academic_papers || [];
  $('list-academic').innerHTML = papers.length
    ? papers.map(renderPaperCard).join('')
    : emptyState('📚', '暫無學術文章', '請確認 PubMed 關鍵字設定');

  // Script
  $('scriptContent').textContent = podcastText || '播報稿尚未產生';
}

function renderArticleCard(a) {
  const date = formatDate(a.published_at);
  const summary = a.summary ? `<p class="article-summary">${esc(a.summary)}</p>` : '';
  return `
    <article class="article-card" onclick="openLink('${esc(a.url || '')}')">
      <div class="article-source">${esc(a.source || '')}</div>
      <h3 class="article-title">${esc(a.title || '(無標題)')}</h3>
      ${summary}
      <div class="article-footer">
        <span class="article-date">${date}</span>
        ${a.url ? `<a class="article-link" href="${esc(a.url)}" target="_blank" rel="noopener" onclick="event.stopPropagation()">閱讀全文 →</a>` : ''}
      </div>
    </article>`;
}

function renderPaperCard(p) {
  const score = p.relevance_score ? Math.round(p.relevance_score * 100) : 0;
  return `
    <article class="paper-card">
      <div class="paper-badge">📖 ${esc(p.source || 'Academic')}</div>
      <h3 class="paper-title">${esc(p.title || '(無標題)')}</h3>
      ${p.authors ? `<p class="paper-authors">✍️ ${esc(p.authors)}</p>` : ''}
      ${p.abstract ? `<p class="paper-abstract">${esc(p.abstract)}</p>` : ''}
      <div class="paper-footer">
        <span class="paper-date">${esc(p.published_at || '')}</span>
        <div style="display:flex;gap:8px;align-items:center">
          <span class="score-badge">相關度 ${score}%</span>
          ${p.url ? `<a class="paper-link" href="${esc(p.url)}" target="_blank" rel="noopener">查看原文 →</a>` : ''}
        </div>
      </div>
    </article>`;
}

function emptyState(icon, title, sub) {
  return `
    <div class="empty-state">
      <span class="empty-icon">${icon}</span>
      <p class="empty-title">${title}</p>
      <p class="empty-sub">${sub}</p>
    </div>`;
}

// ── Podcast player ────────────────────────────────────────────────────────
function togglePlay() {
  if (!podcastText) return;
  playing ? pausePlayback() : startPlayback();
}

function startPlayback() {
  if (!synth) { alert('您的瀏覽器不支援語音合成'); return; }

  if (synth.paused && utterance) {
    synth.resume();
    playing = true;
    updatePlayBtn(true);
    startProgressTimer();
    return;
  }

  synth.cancel();
  utterance = new SpeechSynthesisUtterance(podcastText);
  utterance.lang = 'zh-TW';
  utterance.rate = speed;
  utterance.pitch = 1.0;

  // Pick a zh-TW voice if available
  const voices = synth.getVoices();
  const twVoice = voices.find(v => v.lang === 'zh-TW') || voices.find(v => v.lang.startsWith('zh'));
  if (twVoice) utterance.voice = twVoice;

  utterance.onboundary = e => {
    if (e.name === 'word') charIndex = e.charIndex;
    updateProgress();
  };
  utterance.onend = () => {
    playing = false;
    charIndex = 0;
    updatePlayBtn(false);
    updateProgress(100);
    clearInterval(progressTimer);
    $('playerProgressText').textContent = '00:00 / 00:00';
  };
  utterance.onerror = e => {
    if (e.error !== 'interrupted') console.warn('TTS error:', e.error);
    playing = false;
    updatePlayBtn(false);
  };

  synth.speak(utterance);
  playing = true;
  updatePlayBtn(true);
  startProgressTimer();
}

function pausePlayback() {
  synth.pause();
  playing = false;
  updatePlayBtn(false);
  clearInterval(progressTimer);
}

function stopPlayback() {
  synth.cancel();
  playing = false;
  charIndex = 0;
  updatePlayBtn(false);
  updateProgress(0);
  clearInterval(progressTimer);
  $('playerProgressText').textContent = '00:00 / 00:00';
}

function updatePlayBtn(isPlaying) {
  $('playIcon').style.display  = isPlaying ? 'none' : '';
  $('pauseIcon').style.display = isPlaying ? '' : 'none';
}

function updateProgress(pct = null) {
  const p = pct !== null ? pct : (totalChars ? (charIndex / totalChars) * 100 : 0);
  $('progressFill').style.width = Math.min(p, 100) + '%';
}

function startProgressTimer() {
  clearInterval(progressTimer);
  const charsPerSecond = 5 * speed;
  let elapsed = charIndex / charsPerSecond;
  const total  = totalChars / charsPerSecond;

  progressTimer = setInterval(() => {
    elapsed += 0.5;
    const pct = total > 0 ? (elapsed / total) * 100 : 0;
    updateProgress(Math.min(pct, 100));
    $('playerProgressText').textContent = `${fmtTime(elapsed)} / ${fmtTime(total)}`;
    if (elapsed >= total) clearInterval(progressTimer);
  }, 500);
}

function fmtTime(secs) {
  const m = Math.floor(secs / 60);
  const s = Math.floor(secs % 60);
  return `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
}

// ── Progress bar click ─────────────────────────────────────────────────────
function handleProgressClick(e) {
  const rect = $('progressTrack').getBoundingClientRect();
  const pct  = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
  charIndex = Math.floor(pct * totalChars);
  updateProgress(pct * 100);
  if (playing) {
    stopPlayback();
    setTimeout(startPlayback, 80);
  }
}

// ── Tabs ──────────────────────────────────────────────────────────────────
function activateTab(tabId) {
  $$('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === tabId));
  $$('.tab-panel').forEach(p => p.classList.toggle('active', p.id === `tab-${tabId}`));
}

// ── Settings ──────────────────────────────────────────────────────────────
async function openSettings() {
  try {
    const res  = await fetch(`${API}/api/settings`);
    const data = await res.json();
    $('topicsInput').value = (data.research_topics || []).join('\n');
  } catch (_) {}
  $('settingsBackdrop').classList.add('open');
}

function closeSettings() {
  $('settingsBackdrop').classList.remove('open');
}

async function saveSettings() {
  const topics = $('topicsInput').value
    .split('\n')
    .map(t => t.trim())
    .filter(Boolean);

  try {
    await fetch(`${API}/api/settings`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ research_topics: topics }),
    });
    closeSettings();
    fetchDigest(true);
  } catch (err) {
    alert('儲存失敗：' + err.message);
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────
function esc(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function openLink(url) {
  if (url) window.open(url, '_blank', 'noopener');
}

function formatDate(raw) {
  if (!raw) return '';
  try {
    const d = new Date(raw);
    if (isNaN(d)) return raw;
    return d.toLocaleDateString('zh-TW', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch (_) { return raw; }
}

// ── Event bindings ────────────────────────────────────────────────────────
function bindEvents() {
  $('playBtn').addEventListener('click', togglePlay);
  $('stopBtn').addEventListener('click', stopPlayback);
  $('progressTrack').addEventListener('click', handleProgressClick);

  $$('.speed-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      speed = parseFloat(btn.dataset.speed);
      $$('.speed-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      if (utterance) utterance.rate = speed;
      if (playing) { stopPlayback(); setTimeout(startPlayback, 80); }
    });
  });

  $$('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => activateTab(btn.dataset.tab));
  });

  $('refreshBtn').addEventListener('click', async () => {
    setStatus('loading', '重新擷取中…');
    $('loadingOverlay').classList.add('visible');
    try {
      await fetch(`${API}/api/digest/refresh`, { method: 'POST' });
      setTimeout(() => fetchDigest(), 3000);
    } catch (_) {
      setStatus('error', '更新失敗');
      $('loadingOverlay').classList.remove('visible');
    }
  });

  $('settingsBtn').addEventListener('click', openSettings);
  $('closeSettings').addEventListener('click', closeSettings);
  $('cancelSettings').addEventListener('click', closeSettings);
  $('saveSettings').addEventListener('click', saveSettings);

  $('settingsBackdrop').addEventListener('click', e => {
    if (e.target === $('settingsBackdrop')) closeSettings();
  });

  // Load voices when they become available
  if (synth) {
    synth.getVoices();
    synth.onvoiceschanged = () => synth.getVoices();
  }
}
