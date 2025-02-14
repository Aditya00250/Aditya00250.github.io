# !/usr/bin/env python3
import argparse
import requests
import os
import re
import sys
from flask import Flask, request, send_from_directory

# --- Core Functionality ---

def extract_video_id(input_str):
    # Extract video ID from a common YouTube URL format (e.g., ...?v=VIDEO_ID) or return the input if already an ID.
    match = re.search(r"v=([^&]+)", input_str)
    if match:
        return match.group(1)
    return input_str

def sanitize_filename(filename):
    # Replace invalid filename characters with underscore
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

def download_mp3(video_id, api_key, download_dir="downloads", poll=False):
    api_url = "https://youtube-mp36.p.rapidapi.com/dl"
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "youtube-mp36.p.rapidapi.com"
    }
    params = {"id": video_id}
    
    # Call the conversion API
    response = requests.get(api_url, headers=headers, params=params)
    if response.status_code != 200:
        print("Error: Failed to contact API. Status code:", response.status_code)
        return

    data = response.json()
    if data.get("status") != "ok":
        msg = data.get("msg", "Unknown error occurred")
        if "queue" in msg.lower():
            if poll:
                import time
                attempts = 0
                max_attempts = 12
                delay = 5
                print("Conversion in queue. Polling for completion...")
                while attempts < max_attempts:
                    time.sleep(delay)
                    attempts += 1
                    response = requests.get(api_url, headers=headers, params=params)
                    data = response.json()
                    if data.get("status") == "ok":
                        break
                    print(f"Polling attempt {attempts}: still in queue...")
                if data.get("status") != "ok":
                    print("Error: Conversion is still in queue after polling.")
                    return
            else:
                print("Error: in queue")
                return
        else:
            print("Error:", msg)
            return

    download_link = data.get("link")
    title = data.get("title", video_id)
    if not download_link:
        print("Error: Download link not found in API response.")
        return

    print("Downloading:", title)
    # Download the MP3 file using streaming
    r = requests.get(download_link, stream=True)
    if r.status_code == 200:
        os.makedirs(download_dir, exist_ok=True)
        # Sanitize title for filename use if needed
        sanitized_title = sanitize_filename(title)
        filepath = os.path.join(download_dir, f"{sanitized_title}.mp3")
        with open(filepath, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
        print("Download completed:", filepath)
    else:
        print("Error: Failed to download MP3. Status code:", r.status_code)

# --- Command Line Interface ---

def cli_main():
    parser = argparse.ArgumentParser(description="YouTube to MP3 Downloader (CLI mode)")
    parser.add_argument("video", nargs="?", help="YouTube video ID or URL")
    parser.add_argument("--api-key", default="3a7e9844ffmsh5d0520e908fa6e7p1da7d9jsn9d8f1e787e46", help="RapidAPI key for youtube-mp36 API")
    parser.add_argument("--download-dir", default="downloads", help="Directory to save downloads")
    args = parser.parse_args()

    if args.video:
        video_id = extract_video_id(args.video)
    else:
        video_input = input("Enter YouTube video URL or ID: ")
        video_id = extract_video_id(video_input)
    download_mp3(video_id, args.api_key, args.download_dir)

# --- Web Application ---

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    message = ''
    if request.method == 'POST':
        video = request.form.get('video')
        api_key = request.form.get('api_key') or "3a7e9844ffmsh5d0520e908fa6e7p1da7d9jsn9d8f1e787e46"
        if video:
            poll = True if request.form.get('poll') == "yes" else False
            video_id = extract_video_id(video)
            download_mp3(video_id, api_key, download_dir, poll)
            message = f"Download initiated for video '{video_id}' in directory '{download_dir}'."
        else:
            message = "Please provide a video URL or ID."
    return f'''
    <html>
      <head>
        <title>Youtube -> mp3</title>
        <style>
          body {{
            margin: 0;
            padding: 0;
            background-color: #121212;
            color: #ffffff;
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
          }}
          .container {{
            display: flex;
            height: 100vh;
          }}
          .sidebar {{
            background-color: #000000;
            width: 240px;
            padding: 20px;
            box-sizing: border-box;
          }}
          .sidebar h2 {{
            color: #1db954;
            font-size: 24px;
          }}
          .sidebar ul {{
            list-style-type: none;
            padding-left: 0;
          }}
          .sidebar ul li {{
            margin: 15px 0;
          }}
          .sidebar ul li a {{
            color: #ffffff;
            text-decoration: none;
            font-size: 16px;
          }}
          .main-content {{
            flex: 1;
            padding: 30px;
          }}
          .form-container {{
            background-color: #1e1e1e;
            padding: 20px;
            border-radius: 8px;
            max-width: 500px;
          }}
          .form-container h1 {{
            margin-top: 0;
          }}
          .form-container label {{
            display: block;
            margin-bottom: 5px;
            font-size: 14px;
          }}
          .form-container input[type="text"] {{
            width: 100%;
            padding: 10px;
            margin-bottom: 15px;
            border: none;
            border-radius: 4px;
          }}
          .form-container input[type="checkbox"] {{
            margin-right: 5px;
          }}
          .form-container input[type="submit"] {{
            background-color: #1db954;
            color: #ffffff;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
          }}
          .message {{
            margin-top: 15px;
            font-size: 14px;
          }}
        </style>
      </head>
      <body>
        <div class="container">
          <div class="sidebar">
            <h2>Youtube to mp3 download</h2>
            <ul>
              <li><a href="/">Home</a></li>
              <li><a href="/downloads">Downloads</a></li>
            </ul>
          </div>
          <div class="main-content">
            <div class="form-container">
              <h1>YouTube to MP3 Downloader</h1>
              <form method="post">
                <label for="video">YouTube Video URL or ID:</label>
                <input type="text" name="video" id="video" required>
                <label for="api_key">API Key (optional):</label>
                <input type="text" name="api_key" id="api_key">
                <label for="poll">Poll until conversion is complete:</label>
                <input type="checkbox" name="poll" id="poll" value="yes">
                <br><br>
                <input type="submit" value="Download MP3">
              </form>
              <p class="message">{message}</p>
            </div>
          </div>
        </div>
      </body>
    </html>
    '''

@app.route('/downloads/<path:filename>')
def download_file(filename):
    return send_from_directory('downloads', filename, as_attachment=True)

# --- Execution Entry Point ---

if __name__ == '__main__':
    # Check for CLI mode flag
    if "--cli" in sys.argv:
        sys.argv.remove("--cli")
        cli_main()
    else:
        os.makedirs("downloads", exist_ok=True)
        app.run(debug=True)
