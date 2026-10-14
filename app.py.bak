#!/usr/bin/env python3
"""Instagram Reels Downloader — Flask Backend"""

from flask import Flask, request, jsonify, render_template, send_from_directory
import os, glob, time, re, subprocess, uuid

app = Flask(__name__)

BASE = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE, 'downloads')
COOKIE_FILE = os.path.join(BASE, 'ig_cookies.txt')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Cleanup old files (older than 1 hour)
def cleanup():
    now = time.time()
    for f in glob.glob(os.path.join(DOWNLOAD_DIR, '*')):
        if os.path.getmtime(f) < now - 3600:
            try: os.remove(f)
            except: pass

def is_valid_instagram(url):
    """Instagram URL validate karo"""
    patterns = [
        r'instagram\.com/(p|reel|reels|tv|share)/',
        r'instagram\.com/stories/',
        r'instagr\.am/',
    ]
    return any(re.search(p, url) for p in patterns)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/download', methods=['POST'])
def download_reel():
    cleanup()  # Purani files saaf karo
    
    data = request.get_json() or {}
    url = (data.get('url') or '').strip()
    
    if not url:
        return jsonify({'ok': False, 'error': 'URL daalo'}), 400
    
    if not is_valid_instagram(url):
        return jsonify({'ok': False, 'error': 'Valid Instagram URL daalo (reel/post/tv)'}), 400
    
    # Unique ID se file save karo
    uid = str(uuid.uuid4())[:8]
    output_template = os.path.join(DOWNLOAD_DIR, f'ig_{uid}.%(ext)s')
    
    # yt-dlp command
    cmd = ['yt-dlp']
    if os.path.exists(COOKIE_FILE):
        cmd += ['--cookies', COOKIE_FILE]
    cmd += [
        '--no-playlist',
        '--no-warnings',
        '--no-check-certificate',
        '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        '-f', 'best',
        '-o', output_template,
        url
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip()[-300:] if result.stderr else 'Download failed'
            return jsonify({
                'ok': False,
                'error': 'Video download nahi hui. Private/deleted ho sakti hai. ' + error_msg
            }), 500
        
        # Downloaded file dhundo
        files = glob.glob(os.path.join(DOWNLOAD_DIR, f'ig_{uid}.*'))
        if not files:
            return jsonify({'ok': False, 'error': 'File save nahi hui'}), 500
        
        filepath = files[0]
        filename = os.path.basename(filepath)
        size = os.path.getsize(filepath)
        
        return jsonify({
            'ok': True,
            'file': f'/file/{filename}',
            'filename': filename,
            'size': f'{size / 1024 / 1024:.1f} MB',
            'size_bytes': size
        })
    
    except subprocess.TimeoutExpired:
        return jsonify({'ok': False, 'error': 'Timeout — thodi der baad try karo'}), 504
    except Exception as e:
        return jsonify({'ok': False, 'error': f'Error: {str(e)}'}), 500

@app.route('/file/<filename>')
def serve_file(filename):
    """Downloaded file serve karo"""
    # Security check
    if not re.match(r'^ig_[a-zA-Z0-9_\-]+\.(mp4|jpg|webp|png)$', filename):
        return 'Invalid file', 400
    return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)

@app.route('/health')
def health():
    return jsonify({'ok': True, 'status': 'running'})

if __name__ == '__main__':
    print("\n" + "="*55)
    print("📥 Instagram Reels Downloader")
    print("="*55)
    print("📱 Chrome me kholo: http://localhost:5000")
    print("⚠️  Server band: Ctrl+C")
    print("="*55 + "\n")
    app.run(host='0.0.0.0', port=5000, debug=False)
