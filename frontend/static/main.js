// frontend/static/main.js
// Replace 'https://REPLACE_WITH_YOUR_RAILWAY_URL/api/extract-reel' with your actual Railway backend URL
// Example: 'https://awesome-service.up.railway.app/api/extract-reel'
const BACKEND_URL = window.BACKEND_URL || 'https://surprising-eagerness.up.railway.app/api/extract-reel';

console.log('[main.js] script loaded');
console.log('[main.js] using BACKEND_URL =', BACKEND_URL);

// DOM elements (must match IDs from index.html)
const reelUrlInput = document.getElementById('reelUrlInput');
const extractBtn = document.getElementById('extractBtn');
const quickBtn = document.getElementById('quickBtn');
const loading = document.getElementById('loading');
const resultSection = document.getElementById('result');
const directUrl = document.getElementById('directUrl');
const previewVideo = document.getElementById('previewVideo');

if (!reelUrlInput || !extractBtn || !loading) {
  console.error('[main.js] One or more required DOM elements were not found. Check your index.html IDs.');
}

// Attach event listeners
extractBtn && extractBtn.addEventListener('click', testWithBackend);
quickBtn && quickBtn.addEventListener('click', quickTest);

function showLoading(show = true) {
  loading.style.display = show ? 'block' : 'none';
}

function showResult(show = true) {
  resultSection.style.display = show ? 'block' : 'none';
}

function showError(message) {
  console.error('[main.js] ERROR:', message);
  alert('Error: ' + message);
}

async function testWithBackend() {
  const url = (reelUrlInput && reelUrlInput.value || '').trim();
  if (!url) {
    showError('Please paste an Instagram URL in the input field.');
    return;
  }

  console.log('[testWithBackend] extracting for:', url);
  showLoading(true);
  showResult(false);
  directUrl.textContent = '';
  previewVideo.src = '';
  previewVideo.style.display = 'none';

  try {
    const body = { url };
    console.log('[testWithBackend] POST', BACKEND_URL, 'body=', body);

    const resp = await fetch(BACKEND_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });

    console.log('[testWithBackend] fetch complete. status =', resp.status);

    // Try to parse JSON safely
    let data;
    try {
      data = await resp.json();
      console.log('[testWithBackend] response JSON:', data);
    } catch (parseErr) {
      const text = await resp.text();
      console.warn('[testWithBackend] response not JSON. text:', text);
      throw new Error('Backend response not JSON. See console.');
    }

    if (resp.ok && data && data.success) {
      console.log('[testWithBackend] success. video_url =', data.video_url);
      directUrl.textContent = data.video_url || '(no url returned)';
      previewVideo.src = data.video_url || '';
      if (data.video_url) previewVideo.style.display = 'block';
      showResult(true);
      alert('✅ Success! Backend extracted the URL. Check the console/network for details.');
    } else {
      const errMsg = (data && (data.error || JSON.stringify(data))) || 'Unknown backend error';
      showError('Backend error: ' + errMsg);
    }
  } catch (err) {
    showError('Backend connection failed: ' + (err && err.message ? err.message : String(err)));
  } finally {
    showLoading(false);
  }
}

// Quick test uses public endpoints (unreliable). Logs everything.
async function quickTest() {
  const url = (reelUrlInput && reelUrlInput.value || '').trim();
  if (!url) {
    showError('Please paste an Instagram URL in the input field.');
    return;
  }

  showLoading(true);
  showResult(false);
  directUrl.textContent = '';
  previewVideo.src = '';
  previewVideo.style.display = 'none';

  console.log('[quickTest] starting quick test for:', url);

  // Example public proxies — these change often and may be blocked
  const services = [
    'https://api.allorigins.win/raw?url=' + encodeURIComponent(`https://api.instagram.com/oembed?url=${url}`),
    // you can add more proxies or public APIs here for testing
  ];

  for (const service of services) {
    console.log('[quickTest] trying service:', service);
    try {
      const r = await fetch(service);
      console.log('[quickTest] service response status:', r.status);
      if (!r.ok) {
        console.warn('[quickTest] service returned non-OK status, trying next.');
        continue;
      }
      const text = await r.text();
      console.log('[quickTest] service returned text (first 200 chars):', text.slice(0, 200));
      // Display partial raw output so we can inspect it
      directUrl.textContent = text.slice(0, 200) + (text.length > 200 ? '\n\n(...truncated...)' : '');
      showResult(true);
      alert('Quick test returned data. Inspect console/network for full output.');
      break;
    } catch (e) {
      console.warn('[quickTest] service failed:', e);
      continue;
    } finally {
      showLoading(false);
    }
  }

  showLoading(false);
}

// Service worker registration with logs
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/static/sw.js')
      .then(reg => {
        console.log('[main.js] Service worker registered:', reg);
      })
      .catch(err => {
        console.warn('[main.js] Service worker registration failed:', err);
      });
  });
}

// helpful dev-only function to quickly test the backend from console
window.__testBackendDirectly = async function(testUrl) {
  const u = testUrl || (reelUrlInput && reelUrlInput.value) || '';
  if (!u) { console.error('[__testBackendDirectly] no url supplied'); return; }
  console.log('[__testBackendDirectly] sending test url to backend:', u);
  try {
    const resp = await fetch(BACKEND_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: u })
    });
    console.log('[__testBackendDirectly] status =', resp.status);
    const data = await resp.json().catch(() => null);
    console.log('[__testBackendDirectly] json =', data);
  } catch (err) {
    console.error('[__testBackendDirectly] failed:', err);
  }
};

console.log('[main.js] ready — click Extract. If nothing happens, open DevTools -> Network and Console to inspect the POST request.');
