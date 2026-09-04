import os
import re
import requests
from flask import Flask, render_template, request, jsonify
import yt_dlp

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/extract', methods=['POST'])
def extract_info():
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    # --- SPOTIFY DRM BYPASS LOGIC ---
    if "spotify.com" in url:
        try:
            # Fetch the Spotify page to grab the title and artist
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers)
            
            # Extract the page title (e.g., "SongName - song and lyrics by Artist | Spotify")
            title_match = re.search(r'<title>(.+?)</title>', response.text)
            if title_match:
                raw_title = title_match.group(1)
                # Clean up the title to create a clean search query
                search_query = raw_title.replace(" | Spotify", "").replace(" - song and lyrics by ", " ")
                
                # Tell yt-dlp to search YouTube for the top result instead of using the Spotify URL
                url = f"ytsearch1:{search_query} audio"
            else:
                return jsonify({'error': 'Could not read Spotify metadata'}), 400
        except Exception as e:
            return jsonify({'error': f'Spotify parse error: {str(e)}'}), 500
    # --------------------------------

    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'noplaylist': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # If it's a search query, extract_info returns a dictionary with an 'entries' list
            info = ydl.extract_info(url, download=False)
            
            if 'entries' in info and len(info['entries']) > 0:
                info = info['entries'][0]

            formats = []
            seen_resolutions = set()
            
            for f in info.get('formats', []):
                # Handle standard video/audio formats
                res = f.get('format_note', '') or f.get('resolution', '')
                ext = f.get('ext', '')
                vcodec = f.get('vcodec', 'none')
                acodec = f.get('acodec', 'none')
                
                # We want either mp4 videos OR m4a/webm audio-only streams (great for music)
                if ext in ['mp4', 'm4a', 'webm'] and (vcodec != 'none' or acodec != 'none'):
                    display_res = res if res and res != 'audio only' else f"{f.get('abr', 128)}kbps Audio"
                    
                    if display_res not in seen_resolutions:
                        seen_resolutions.add(display_res)
                        formats.append({
                            'resolution': display_res,
                            'ext': ext,
                            'url': f.get('url'),
                            'is_audio': vcodec == 'none'
                        })
            
            # Sort formats (video highest to lowest, then audio)
            def sort_key(x):
                if x['is_audio']: return -1
                return int(''.join(filter(str.isdigit, x['resolution'])) or 0)
                
            formats.sort(key=sort_key, reverse=True)

            return jsonify({
                'title': info.get('title', 'Unknown Title'),
                'thumbnail': info.get('thumbnail', ''),
                'duration': info.get('duration_string', '00:00'),
                'formats': formats
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
