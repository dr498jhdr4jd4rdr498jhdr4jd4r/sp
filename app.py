import os
import re
import uuid
import requests
from flask import Flask, render_template, request, jsonify, send_file, after_this_request
import yt_dlp

app = Flask(__name__)
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def fetch_spotify_metadata(url):
    """Scrapes official track details and cover art from Spotify OpenGraph tags."""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    response = requests.get(url, headers=headers, timeout=10)
    
    title_match = re.search(r'<meta property="og:title" content="([^"]+)"', response.text)
    image_match = re.search(r'<meta property="og:image" content="([^"]+)"', response.text)
    
    if not title_match:
        raise ValueError("Could not extract track title from Spotify link.")
        
    track_title = title_match.group(1)
    thumbnail_url = image_match.group(1) if image_match else ""
    
    # Clean up Spotify title formatting (e.g., remove lyrics suffix or platform text)
    clean_query = (
        track_title
        .replace(" - song and lyrics by ", " - ")
        .replace(" | Spotify", "")
        .split(" | ")[0]
    )
    search_query = f"ytsearch1:{clean_query} official audio"
    
    return search_query, track_title, thumbnail_url

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/extract', methods=['POST'])
def extract_info():
    data = request.get_json() or {}
    raw_url = data.get('url')
    
    if not raw_url:
        return jsonify({'error': 'No URL provided'}), 400

    try:
        if "spotify.com" in raw_url:
            search_query, spotify_title, spotify_thumb = fetch_spotify_metadata(raw_url)
            target_url = search_query
        else:
            target_url = raw_url
            spotify_title = None
            spotify_thumb = None

        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'noplaylist': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=False)
            if 'entries' in info and info['entries']:
                info = info['entries'][0]

            return jsonify({
                'title': spotify_title or info.get('title', 'Unknown Title'),
                'thumbnail': spotify_thumb or info.get('thumbnail', ''),
                'duration': info.get('duration_string', '00:00'),
                'original_url': raw_url
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download', methods=['GET'])
def download_audio():
    raw_url = request.args.get('url')
    if not raw_url:
        return "No URL provided", 400

    try:
        if "spotify.com" in raw_url:
            search_query, spotify_title, _ = fetch_spotify_metadata(raw_url)
            target_url = search_query
            custom_title = spotify_title
        else:
            target_url = raw_url
            custom_title = None

        job_id = str(uuid.uuid4())
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(DOWNLOAD_DIR, f'{job_id}.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'noplaylist': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=True)
            if 'entries' in info and info['entries']:
                info = info['entries'][0]
            title = custom_title or info.get('title', 'Audio_Download')
            
        file_path = os.path.join(DOWNLOAD_DIR, f"{job_id}.mp3")
        safe_title = re.sub(r'[^\w\s-]', '', title).strip()
        download_name = f"{safe_title or 'track'}.mp3"

        @after_this_request
        def remove_file(response):
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                app.logger.error(f"Error removing file: {e}")
            return response

        return send_file(file_path, as_attachment=True, download_name=download_name, mimetype="audio/mpeg")

    except Exception as e:
        return f"Download failed: {str(e)}", 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
