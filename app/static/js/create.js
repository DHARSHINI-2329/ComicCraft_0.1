/* ══════════════════════════════════════════════
   create.js — Comic creation form logic
   ══════════════════════════════════════════════ */

// ── Setting dropdown: show custom input ───────────────────────────
const settingSelect = document.getElementById('setting');
const customGroup = document.getElementById('customSettingGroup');
if (settingSelect) {
  settingSelect.addEventListener('change', () => {
    customGroup.style.display = settingSelect.value === 'Custom' ? 'block' : 'none';
    if (settingSelect.value === 'Custom') {
      document.getElementById('custom_setting').required = true;
    } else {
      document.getElementById('custom_setting').required = false;
    }
    updatePreview();
  });
}

// ── Live preview update ───────────────────────────────────────────
const previewFields = ['story_prompt', 'character_name', 'character_description', 'setting', 'tone'];
previewFields.forEach(id => {
  const el = document.getElementById(id);
  if (el) el.addEventListener('input', updatePreview);
  if (el) el.addEventListener('change', updatePreview);
});
document.querySelectorAll('input[name="art_style"]').forEach(r => {
  r.addEventListener('change', updatePreview);
});

function updatePreview() {
  const prompt = (document.getElementById('story_prompt') || {}).value || '';
  const char = (document.getElementById('character_name') || {}).value || '';
  const charDesc = (document.getElementById('character_description') || {}).value || '';
  const settingVal = settingSelect ? settingSelect.value : '';
  const customSetting = (document.getElementById('custom_setting') || {}).value || '';
  const toneEl = document.getElementById('tone');
  const toneVal = toneEl ? toneEl.value : '';
  const styleEl = document.querySelector('input[name="art_style"]:checked');
  const styleVal = styleEl ? styleEl.value : '';
  const effectiveSetting = settingVal === 'Custom' ? customSetting : settingVal;

  const preview = document.getElementById('previewContent');
  if (!preview) return;

  if (!prompt && !char) {
    preview.innerHTML = `
      <div class="preview-placeholder">
        <div class="preview-icon"><i class="fa-solid fa-masks-theater text-muted"></i></div>
        <p>Fill in your story details and your comic preview will appear here.</p>
      </div>`;
    return;
  }

  preview.innerHTML = `
    <div class="preview-live">
      ${char ? `<div class="preview-item"><strong>CHARACTER</strong><span>${escHtml(char)}${charDesc ? ' — ' + escHtml(charDesc.slice(0, 80)) + (charDesc.length > 80 ? '...' : '') : ''}</span></div>` : ''}
      ${effectiveSetting ? `<div class="preview-item"><strong>SETTING</strong><span>${escHtml(effectiveSetting)}</span></div>` : ''}
      ${toneVal ? `<div class="preview-item"><strong>TONE</strong><span>${escHtml(toneVal)}</span></div>` : ''}
      ${styleVal ? `<div class="preview-item"><strong>ART STYLE</strong><span>${escHtml(styleVal)}</span></div>` : ''}
      ${prompt ? `<div class="preview-item"><strong>STORY IDEA</strong><span>${escHtml(prompt.slice(0, 150))}${prompt.length > 150 ? '...' : ''}</span></div>` : ''}
      <div class="preview-item" style="margin-top:16px;padding-top:12px;border-top:1px solid var(--border)">
        <span style="font-size:13px;color:var(--muted)"><i class="fa-solid fa-sparkles text-accent"></i> Ready to generate 5 illustrated panels!</span>
      </div>
    </div>`;
}

function escHtml(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}

// ── Fill example ──────────────────────────────────────────────────
function fillExample() {
  const sp = document.getElementById('story_prompt');
  const cn = document.getElementById('character_name');
  const cd = document.getElementById('character_description');
  const st = document.getElementById('setting');
  const tone = document.getElementById('tone');
  const style = document.querySelector('input[value="Comic Book"]');
  if (sp) sp.value = 'A brave fox discovers a mysterious glowing door inside an enchanted forest. She must solve an ancient riddle to unlock its secrets and uncover what lies beyond.';
  if (cn) cn.value = 'Luna';
  if (cd) cd.value = 'A young orange fox with a blue woolen scarf and emerald green eyes. Brave and curious, with a small scar above her left eyebrow.';
  if (st) st.value = 'Enchanted Forest';
  if (tone) tone.value = 'Adventure';
  if (style) style.checked = true;
  updatePreview();
}

// ── Form submit: generate comic ───────────────────────────────────
async function handleCreate(e) {
  e.preventDefault();
  const btn = document.getElementById('generateBtn');
  const errEl = document.getElementById('createError');
  errEl.style.display = 'none';

  // Build setting value
  let setting = settingSelect ? settingSelect.value : '';
  if (setting === 'Custom') {
    setting = (document.getElementById('custom_setting') || {}).value || 'Custom';
  }

  const artStyle = (document.querySelector('input[name="art_style"]:checked') || {}).value || 'Comic Book';

  const payload = {
    story_prompt: (document.getElementById('story_prompt') || {}).value || '',
    character_name: (document.getElementById('character_name') || {}).value || '',
    character_description: (document.getElementById('character_description') || {}).value || null,
    setting,
    tone: (document.getElementById('tone') || {}).value || '',
    art_style: artStyle,
  };

  // Basic validation
  if (!payload.story_prompt || payload.story_prompt.length < 10) {
    errEl.textContent = 'Please enter a story idea (at least 10 characters).';
    errEl.style.display = 'block';
    return;
  }
  if (!payload.character_name) {
    errEl.textContent = 'Please enter a character name.';
    errEl.style.display = 'block';
    return;
  }
  if (!payload.setting) {
    errEl.textContent = 'Please select a setting.';
    errEl.style.display = 'block';
    return;
  }
  if (!payload.tone) {
    errEl.textContent = 'Please select a story tone.';
    errEl.style.display = 'block';
    return;
  }

  btn.querySelector('.btn-text').style.display = 'none';
  btn.querySelector('.btn-spinner').style.display = 'inline';
  btn.disabled = true;

  try {
    const res = await apiFetch('/api/generate-comic/json', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    if (res.ok && data.success) {
      // Redirect to generating screen
      const jobParam = data.job_id ? '?job_id=' + data.job_id : '';
      window.location.href = '/generating/' + data.comic_id + jobParam;
    } else {
      let msg = data.detail || 'Generation failed. Please try again.';
      if (msg.includes('API key')) {
        msg = msg + ' You can enable DEMO_MODE=true in your .env file to test without an API key.';
      }
      errEl.textContent = msg;
      errEl.style.display = 'block';
    }
  } catch(ex) {
    errEl.textContent = 'Network error. Is the server running?';
    errEl.style.display = 'block';
  } finally {
    btn.querySelector('.btn-text').style.display = 'inline';
    btn.querySelector('.btn-spinner').style.display = 'none';
    btn.disabled = false;
  }
}
