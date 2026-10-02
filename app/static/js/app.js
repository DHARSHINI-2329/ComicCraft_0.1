/* ══════════════════════════════════════════════
   app.js — Global JavaScript for ComicCraft
   ══════════════════════════════════════════════ */

// ── Navbar hamburger ──────────────────────────────────────────────
const hamburger = document.getElementById('navHamburger');
const mobileMenu = document.getElementById('navMobile');
if (hamburger && mobileMenu) {
  hamburger.addEventListener('click', () => {
    mobileMenu.classList.toggle('open');
  });
}

// ── Logout handler ────────────────────────────────────────────────
async function handleLogout() {
  try {
    await fetch('/auth/logout', { method: 'POST' });
  } catch(e) { /* ignore */ }
  document.cookie = 'access_token=; path=/; max-age=0';
  window.location.href = '/';
}

// ── Read cookie ──────────────────────────────────────────────────
function getCookie(name) {
  const m = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'));
  return m ? decodeURIComponent(m[1]) : null;
}

// ── Authenticated fetch wrapper ───────────────────────────────────
async function apiFetch(url, options = {}) {
  const token = getCookie('access_token');
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (token) headers['Authorization'] = 'Bearer ' + token;
  const res = await fetch(url, { ...options, headers });
  return res;
}

// ── Scroll navbar shadow ─────────────────────────────────────────
const navbar = document.getElementById('navbar');
if (navbar) {
  window.addEventListener('scroll', () => {
    navbar.style.boxShadow = window.scrollY > 10
      ? '0 2px 16px rgba(23,23,23,0.12)'
      : '0 1px 8px rgba(0,0,0,0.04)';
  });
}
