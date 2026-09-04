import os
import re
import uuid
import requests
from flask import Flask, render_template, request, jsonify, send_file, after_this_request
import yt_dlp

app = Flask(__name__)
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/extract', methods=['POST'])
def extract_info():
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    # Handle Spotify bypass for metadata
    if "spotify.com" in url:
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers)
            title_match = re.search(r'<title>(.+?)</title>', response.text)
            if title_match:
                search_query = title_match.group(1).replace(" | Spotify", "").replace(" - song and lyrics by ", " ")
                url = f"ytsearch1:{search_query} audio"
            else:
                return jsonify({'error': 'Could not read Spotify metadata'}), 400
        except Exception as e:
            return jsonify({'error': f'Spotify parse error: {str(e)}'}), 500

    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'noplaylist': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if 'entries' in info and len(info['entries']) > 0:
                info = info['entries'][0]

            return jsonify({
                'title': info.get('title', 'Unknown Title'),
                'thumbnail': info.get('thumbnail', ''),
                'duration': info.get('duration_string', '00:00'),
                'original_url': request.get_json().get('url')
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download', methods=['GET'])
def download_audio():
    url = request.args.get('url')
    if not url:
        return "No URL provided", 400

    if "spotify.com" in url:
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers)
            title_match = re.search(r'<title>(.+?)</title>', response.text)
            if title_match:
                search_query = title_match.group(1).replace(" | Spotify", "").replace(" - song and lyrics by ", " ")
                url = f"ytsearch1:{search_query} audio"
            else:
                return "Could not read Spotify metadata", 400
        except Exception as e:
            return f"Spotify parse error: {str(e)}", 500

    job_id = str(uuid.uuid4())
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{DOWNLOAD_DIR}/{job_id}.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'noplaylist': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if 'entries' in info and len(info['entries']) > 0:
                info = info['entries'][0]
            title = info.get('title', 'Audio_Download')
            
        file_path = f"{DOWNLOAD_DIR}/{job_id}.mp3"
        safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c==' ']).rstrip()
        download_name = f"{safe_title}.mp3"

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
