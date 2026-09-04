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
            
            # Extract and filter formats (preferring mp4 video with reasonable resolutions)
            formats = []
            seen_resolutions = set()
            
            for f in info.get('formats', []):
                res = f.get('format_note', '')
                ext = f.get('ext', '')
                
                # Filter for usable video formats
                if f.get('vcodec') != 'none' and ext == 'mp4' and res:
                    if res not in seen_resolutions:
                        seen_resolutions.add(res)
                        formats.append({
                            'resolution': res,
                            'ext': ext,
                            'url': f.get('url')
                        })
            
            # Sort formats by resolution (highest first)
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
    app.run(debug=True, port=5000)
