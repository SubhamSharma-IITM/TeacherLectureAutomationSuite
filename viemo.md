# Drive → Vimeo Uploader

A simple script that takes a Google Drive folder and uploads every video in it to Vimeo. When it's done, you get a CSV with all the Vimeo links.

---

## What it does

1. Connects to your Google Drive (via OAuth — it opens a browser once to ask for permission)
2. Lists every video file in the folder you specify
3. Downloads each video temporarily
4. Uploads it to Vimeo using their resumable upload API
5. Saves a `vimeo_links.csv` with filenames and links

---

## Setup

### 1. Install dependencies

```bash
pip install google-api-python-client google-auth-oauthlib google-auth-httplib2 PyVimeo
```

### 2. Google Drive credentials

- Go to [console.cloud.google.com](https://console.cloud.google.com)
- Create a project → enable the **Google Drive API**
- Go to **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**
- Choose **Desktop App** → download the JSON
- Rename it to `credentials.json` and place it in this folder

> First time you run the script, a browser window will open asking you to sign in with Google. After that, it saves a `token.json` so you won't be asked again.

### 3. Vimeo access token

- Go to [developer.vimeo.com/apps](https://developer.vimeo.com/apps)
- Create an app → generate an **Access Token**
- Required scopes: `upload`, `edit`, `video_files`

---

## Usage

```bash
python3 upload.py --folder-id YOUR_FOLDER_ID --vimeo-token YOUR_TOKEN
```

**Where do I find the folder ID?**  
It's in the URL when you open the folder in Google Drive:
```
https://drive.google.com/drive/folders/1ABC123XYZ
                                        ^^^^^^^^^^^ this part
```

### Optional flags

| Flag | Default | Description |
|------|---------|-------------|
| `--output-csv` | `vimeo_links.csv` | Where to save the results |
| `--vimeo-token` | `VIMEO_ACCESS_TOKEN` env var | Your Vimeo access token |

You can also set your token as an environment variable to avoid typing it every time:
```bash
export VIMEO_ACCESS_TOKEN=your_token_here
python3 upload.py --folder-id YOUR_FOLDER_ID
```

---

## Output

The script prints progress as it runs:

```
Connecting to Google Drive...
Connecting to Vimeo...
Logged in as: Your Name

Looking for videos in folder: 1ABC123XYZ
Found 3 video(s):

  • intro.mp4  (45.2 MB)
  • demo.mp4   (120.8 MB)
  • outro.mp4  (30.1 MB)

[1/3] intro.mp4
  Downloading from Google Drive...
  Uploading to Vimeo...
  Done! → https://vimeo.com/123456789

...

──────────────────────────────────────────────────
Done! 3/3 uploaded successfully.
Links saved to: vimeo_links.csv
```

---

## Notes

- Videos are downloaded to a temporary folder and deleted after upload — nothing is stored permanently on your machine
- Free Vimeo accounts have a 500MB/week upload limit. You'll need a paid plan for more
- After uploading, Vimeo takes a few minutes to transcode the video before it's playable

---

## .gitignore

Make sure you don't accidentally commit your credentials:

```
credentials.json
token.json
vimeo_links.csv
__pycache__/
*.pyc
.env
```