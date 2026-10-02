/* ══════════════════════════════════════════════
   comic.js — Comic preview page logic
   ══════════════════════════════════════════════ */

// ── Panel Regeneration ────────────────────────────────────────────
async function regeneratePanel(comicId, panelNumber) {
  if (!confirm(`Regenerate panel ${panelNumber}? Only this panel will be changed.`)) return;
  const overlay = document.getElementById('regenOverlay');
  const msg = document.getElementById('regenMessage');
  overlay.style.display = 'flex';
  msg.textContent = `Regenerating panel ${panelNumber}...`;

  try {
    const res = await apiFetch(`/api/comics/${comicId}/panel/${panelNumber}/regenerate`, { method: 'POST' });
    if (res.ok) {
      const data = await res.json();
      msg.textContent = 'Panel is being regenerated. Polling for completion...';
      pollPanelRegeneration(data.job_id, comicId, panelNumber, overlay);
    } else {
      const err = await res.json();
      overlay.style.display = 'none';
      alert(err.detail || 'Panel regeneration failed.');
    }
  } catch(e) {
    overlay.style.display = 'none';
    alert('Network error. Please try again.');
  }
}

async function pollPanelRegeneration(jobId, comicId, panelNumber, overlay) {
  const maxAttempts = 60;
  let attempts = 0;
  const msg = document.getElementById('regenMessage');

  const poll = setInterval(async () => {
    attempts++;
    try {
      const res = await apiFetch('/api/jobs/' + jobId);
      if (!res.ok) return;
      const job = await res.json();
      if (job.current_step) msg.textContent = job.current_step;

      if (job.status === 'COMPLETED') {
        clearInterval(poll);
        overlay.style.display = 'none';
        // Reload the page to show updated panel
        window.location.reload();
      } else if (job.status === 'FAILED') {
        clearInterval(poll);
        overlay.style.display = 'none';
        alert('Panel regeneration failed: ' + (job.error_message || 'Unknown error'));
      }
    } catch(e) {
      console.error('Poll error:', e);
    }
    if (attempts >= maxAttempts) {
      clearInterval(poll);
      overlay.style.display = 'none';
      alert('Regeneration is taking too long. Please refresh the page.');
    }
  }, 2500);
}

// ── Full Comic Regeneration ───────────────────────────────────────
async function regenerateComic(comicId) {
  if (!confirm('Regenerate the entire comic? This will create a completely new story and images.')) return;
  const overlay = document.getElementById('regenOverlay');
  const msg = document.getElementById('regenMessage');
  overlay.style.display = 'flex';
  msg.textContent = 'Starting full regeneration...';

  try {
    const res = await apiFetch(`/api/comics/${comicId}/regenerate`, { method: 'POST' });
    if (res.ok) {
      const data = await res.json();
      overlay.style.display = 'none';
      window.location.href = '/generating/' + comicId + '?job_id=' + data.job_id;
    } else {
      const err = await res.json();
      overlay.style.display = 'none';
      alert(err.detail || 'Regeneration failed.');
    }
  } catch(e) {
    overlay.style.display = 'none';
    alert('Network error.');
  }
}

// ── Toggle Favorite ───────────────────────────────────────────────
async function toggleFavorite(comicId) {
  const btn = document.getElementById('favBtn');
  try {
    const res = await apiFetch(`/api/comics/${comicId}/favorite`, { method: 'POST' });
    if (res.ok) {
      const data = await res.json();
      btn.setAttribute('data-favorite', data.is_favorite.toString());
      btn.innerHTML = `<i class="${data.is_favorite ? 'fa-solid fa-star' : 'fa-regular fa-star'}"></i> ${data.is_favorite ? 'Unfavorite' : 'Favorite'}`;
    }
  } catch(e) {
    console.error('Favorite toggle failed:', e);
  }
}

// ── Continue Story ────────────────────────────────────────────────
async function continueStory(comicId) {
  if (!confirm('Continue this story into the next chapter? A new chapter will be generated using your character and story context.')) return;
  const btn = document.getElementById('continueBtn');
  if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Starting...'; }

  try {
    const res = await apiFetch(`/api/comics/${comicId}/continue`, { method: 'POST' });
    if (res.ok) {
      const data = await res.json();
      window.location.href = '/generating/' + data.comic_id + '?job_id=' + data.job_id;
    } else {
      const err = await res.json();
      alert(err.detail || 'Could not continue story.');
      if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-arrow-turn-down"></i> Continue Story'; }
    }
  } catch(e) {
    alert('Network error.');
    if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-arrow-turn-down"></i> Continue Story'; }
  }
}

// ── Download PDF ──────────────────────────────────────────────────
async function downloadPDF(comicId) {
  const btn = document.getElementById('pdfBtn');
  if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Generating PDF...'; }
  try {
    window.open('/api/comics/' + comicId + '/pdf', '_blank');
  } finally {
    setTimeout(() => {
      if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-file-pdf"></i> Download PDF'; }
    }, 2000);
  }
}

// ── Auto-refresh if panels are still generating ───────────────────
const hasIncomplete = document.querySelector('[id^="panel-img-"]');
if (hasIncomplete) {
  setTimeout(() => window.location.reload(), 8000);
}
