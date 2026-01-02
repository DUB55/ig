// main.js - frontend logic to call our Flask backend
const reelUrlInput = document.getElementById('reelUrlInput');
const extractBtn = document.getElementById('extractBtn');
const quickBtn = document.getElementById('quickBtn');
const loading = document.getElementById('loading');
const resultSection = document.getElementById('result');
const directUrl = document.getElementById('directUrl');
const previewVideo = document.getElementById('previewVideo');
const BACKEND_URL =
  import.meta?.env?.VITE_BACKEND_URL ||
  window.BACKEND_URL ||
  'https://ig-ecru.vercel.app/api/extract-reel';

extractBtn.addEventListener('click', testWithBackend);
quickBtn.addEventListener('click', quickTest);

async function testWithBackend() {
  const url = reelUrlInput.value.trim();
  if (!url) {
    alert('Please paste an Instagram URL.');
    return;
  }
  loading.style.display = 'block';
  resultSection.style.display = 'none';
  directUrl.textContent = '';
  previewVideo.style.display = 'none';
  previewVideo.src = '';

  try {
    // When server and frontend are served from same origin, this will be a relative call.
    const resp = await fetch(BACKEND_URL,
 {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });


    const data = await resp.json();
    if (resp.ok && data.success) {
      directUrl.textContent = data.video_url;
      previewVideo.src = data.video_url;
      previewVideo.style.display = 'block';
      resultSection.style.display = 'block';
      alert('✅ Extracted successfully.');
    } else {
      const err = data.error || 'Unknown error';
      alert('Backend error: ' + err);
    }
  } catch (err) {
    alert('Connection error: ' + err.message);
  } finally {
    loading.style.display = 'none';
  }
}

// Quick test using public downloader endpoints (temporary, unreliable)
async function quickTest() {
  const url = reelUrlInput.value.trim();
  if (!url) { alert('Please paste an Instagram URL.'); return; }

  loading.style.display = 'block';
  directUrl.textContent = '';
  resultSection.style.display = 'none';

  // These endpoints are examples — they are often offline / rate-limited
  const services = [
    'https://api.allorigins.win/raw?url=' + encodeURIComponent(`https://api.instagram.com/oembed?url=${url}`),
    // Other publicly-available proxies sometimes exist, but usage is unreliable.
  ];

  for (const service of services) {
    try {
      const r = await fetch(service);
      if (!r.ok) continue;
      const txt = await r.text();
      // show raw output
      directUrl.textContent = txt.slice(0, 1000) + (txt.length > 1000 ? '\n\n(...truncated...)' : '');
      resultSection.style.display = 'block';
      alert('Quick test returned data (inspect the output).');
      break;
    } catch (e) {
      // try next
      continue;
    } finally {
      loading.style.display = 'none';
    }
  }

  loading.style.display = 'none';
}

// Register service worker for basic offline caching (optional)
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/static/sw.js').catch(()=>{});
  });
}
