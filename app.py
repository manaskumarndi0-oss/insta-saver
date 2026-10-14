#!/usr/bin/env python3
"""Instagram Reels Downloader v2 — Faster + More Options"""

from flask import Flask, request, jsonify, render_template, send_from_directory
import os, glob, time, re, subprocess, uuid, json

app = Flask(__name__)

BASE = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE, 'downloads')
COOKIE_FILE = os.path.join(BASE, 'ig_cookies.txt')
CACHE_FILE = os.path.join(BASE, 'cache.json')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# ============ CACHE ============
def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE) as f:
                return json.load(f)
        except: return {}
    return {}

def save_cache(c):
    with open(CACHE_FILE, 'w') as f:
        json.dump(c, f)

def cleanup():
    now = time.time()
    for f in glob.glob(os.path.join(DOWNLOAD_DIR, '*')):
        if os.path.getmtime(f) < now - 3600:
            try: os.remove(f)
            except: pass

def is_valid_instagram(url):
    patterns = [
        r'instagram\.com/(p|reel|reels|tv|share)/',
        r'instagram\.com/stories/',
        r'instagr\.am/',
    ]
    return any(re.search(p, url) for p in patterns)

# ============ MAIN DOWNLOAD ============
def download_media(url, mode='video'):
    """mode: video | audio | thumb"""
    uid = str(uuid.uuid4())[:8]
    
    # Cache check (same URL + mode)
    cache = load_cache()
    cache_key = f"{url}::{mode}"
    if cache_key in cache:
        cached = cache[cache_key]
        path = os.path.join(DOWNLOAD_DIR, cached)
        if os.path.exists(path):
            return {'ok': True, 'file': cached, 'size': os.path.getsize(path), 'cached': True}
    
    # Output template
    if mode == 'audio':
        ext = 'mp3'
    elif mode == 'thumb':
        ext = 'jpg'
    else:
        ext = 'mp4'
    
    output_template = os.path.join(DOWNLOAD_DIR, f'ig_{uid}.%(ext)s')
    
    # Build command — faster options
    cmd = ['yt-dlp', '--no-playlist', '--no-warnings', '--no-check-certificate']
    
    if os.path.exists(COOKIE_FILE):
        cmd += ['--cookies', COOKIE_FILE]
    
    cmd += [
        '--user-agent', UA,
        '--concurrent-fragments', '5',   # ⚡ 5 parallel downloads
        '--retries', '3',
        '--fragment-retries', '3',
        '--no-part',
        '--no-mtime',
    ]
    
    if mode == 'audio':
        cmd += [
            '-x', '--audio-format', 'mp3', '--audio-quality', '0',
            '-o', output_template,
        ]
    elif mode == 'thumb':
        cmd += [
            '--skip-download',
            '--write-thumbnail',
            '--convert-thumbnails', 'jpg',
            '-o', output_template,
        ]
    else:
        cmd += [
            '-f', 'bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b',
            '--merge-output-format', 'mp4',
            '-o', output_template,
        ]
    
    cmd.append(url)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        
        # File dhundo
        files = glob.glob(os.path.join(DOWNLOAD_DIR, f'ig_{uid}.*'))
        if not files:
            err = result.stderr.strip()[-250:] if result.stderr else 'Failed'
            return {'ok': False, 'error': err}
        
        filepath = files[0]
        filename = os.path.basename(filepath)
        size = os.path.getsize(filepath)
        
        # Cache save
        cache[cache_key] = filename
        save_cache(cache)
        
        return {'ok': True, 'file': filename, 'size': size, 'cached': False}
    
    except subprocess.TimeoutExpired:
        return {'ok': False, 'error': 'Timeout — chhota video try karo'}
    except Exception as e:
        return {'ok': False, 'error': str(e)}

# ============ ROUTES ============
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/download', methods=['POST'])
def api_download():
    cleanup()
    data = request.get_json() or {}
    url = (data.get('url') or '').strip()
    mode = (data.get('mode') or 'video').strip()
    
    if not url:
        return jsonify({'ok': False, 'error': 'URL daalo'}), 400
    if not is_valid_instagram(url):
        return jsonify({'ok': False, 'error': 'Valid Instagram URL daalo'}), 400
    if mode not in ['video', 'audio', 'thumb']:
        mode = 'video'
    
    result = download_media(url, mode)
    
    if not result['ok']:
        return jsonify({'ok': False, 'error': result.get('error', 'Download fail')}), 500
    
    size_mb = result['size'] / 1024 / 1024
    return jsonify({
        'ok': True,
        'file': f'/file/{result["file"]}',
        'filename': result['file'],
        'size': f'{size_mb:.1f} MB',
        'cached': result.get('cached', False),
        'mode': mode,
    })

@app.route('/api/bulk', methods=['POST'])
def api_bulk():
    """Bulk download — multiple URLs"""
    cleanup()
    data = request.get_json() or {}
    urls = data.get('urls', [])
    
    if not urls:
        return jsonify({'ok': False, 'error': 'Koi URL nahi diya'}), 400
    
    results = []
    for url in urls[:5]:  # Max 5 at a time
        url = url.strip()
        if not url or not is_valid_instagram(url):
            results.append({'url': url, 'ok': False, 'error': 'Invalid'})
            continue
        r = download_media(url, 'video')
        if r['ok']:
            results.append({
                'url': url,
                'ok': True,
                'file': f'/file/{r["file"]}',
                'filename': r['file'],
                'size': f'{r["size"]/1024/1024:.1f} MB'
            })
        else:
            results.append({'url': url, 'ok': False, 'error': r.get('error', 'Failed')})
    
    return jsonify({'ok': True, 'results': results})

@app.route('/file/<filename>')
def serve_file(filename):
    if not re.match(r'^ig_[a-zA-Z0-9_\-]+\.(mp4|mp3|jpg|webp|png)$', filename):
        return 'Invalid file', 400
    return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)

@app.route('/health')
def health():
    return jsonify({'ok': True, 'status': 'running', 'version': '2.0'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"\n🚀 Insta-Saver v2 running on port {port}\n")
    app.run(host='0.0.0.0', port=port, debug=False)

# ============ PWA ROUTES ============
@app.route('/manifest.json')
def manifest():
    return send_from_directory(os.path.join(BASE, 'static'), 'manifest.json')

@app.route('/sw.js')
def service_worker():
    response = send_from_directory(os.path.join(BASE, 'static'), 'sw.js')
    response.headers['Service-Worker-Allowed'] = '/'
    return response

@app.route('/icon-192.png')
def icon192():
    return send_from_directory(os.path.join(BASE, 'static'), 'icon-192.png')

@app.route('/icon-512.png')
def icon512():
    return send_from_directory(os.path.join(BASE, 'static'), 'icon-512.png')
