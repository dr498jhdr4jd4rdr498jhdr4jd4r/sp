import os
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

    ydl_opts = {
        'quiet': True,
        'skip_download': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            formats = []
            seen_resolutions = set()
            
            for f in info.get('formats', []):
                res = f.get('format_note', '')
                ext = f.get('ext', '')
                
                if f.get('vcodec') != 'none' and ext == 'mp4' and res:
                    if res not in seen_resolutions:
                        seen_resolutions.add(res)
                        formats.append({
                            'resolution': res,
                            'ext': ext,
                            'url': f.get('url')
                        })
            
            formats.sort(
                key=lambda x: int(x['resolution'].replace('p', '').replace('60', '')) if any(c.isdigit() for c in x['resolution']) else 0,
                reverse=True
            )

            return jsonify({
                'title': info.get('title', 'Unknown Title'),
                'thumbnail': info.get('thumbnail', ''),
                'duration': info.get('duration_string', '00:00'),
                'formats': formats
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Railway passes the port dynamically. Fallback to 5000 for local testing.
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
