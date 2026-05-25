"""
Drive → Vimeo Uploader
Takes a Google Drive folder and uploads all videos in it to Vimeo.
Spits out a CSV with the Vimeo links incrementally when done.
"""

import os
import sys
import csv
import argparse
import tempfile
import mimetypes

# ── Third-party Dependencies Validation ────────────────────────────────────────

try:
    import vimeo
except ImportError:
    sys.exit("Error: PyVimeo missing. Run: pip install PyVimeo")

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
except ImportError:
    sys.exit(
        "Error: Google client libraries missing. "
        "Run: pip install google-api-python-client google-auth-oauthlib google-auth-httplib2"
    )

# ── Configuration Constants ───────────────────────────────────────────────────

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
TOKEN_FILE = "token.json"
CREDENTIALS_FILE = "credentials.json"

# File types we consider "video"
VIDEO_MIMETYPES = {
    "video/mp4", "video/quicktime", "video/x-msvideo",
    "video/x-matroska", "video/webm", "video/mpeg",
    "video/3gpp", "video/x-flv", "video/x-ms-wmv",
}


# ── Google Drive Helpers ─────────────────────────────────────────────────────

def get_drive_service():
    """
    Handles Google OAuth. Opens a browser on first run to ask for permission.
    Saves the token locally so you don't have to log in every time.
    """
    creds = None

    # Reuse saved token if we have one
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, DRIVE_SCOPES)
        except Exception:
            creds = None

    # If token is missing or expired, refresh or re-authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                # If refresh payload is rejected, force programmatic re-auth flow
                creds = None

        if not creds:
            if not os.path.exists(CREDENTIALS_FILE):
                sys.exit(
                    f"\nError: Missing '{CREDENTIALS_FILE}'.\n"
                    "Download it from: Google Cloud Console → APIs & Services → Credentials\n"
                    "Choose 'OAuth 2.0 Client ID' (Desktop App) → Download JSON → rename to credentials.json"
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, DRIVE_SCOPES)
            creds = flow.run_local_server(port=0)

        # Save context for next loop
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    return build("drive", "v3", credentials=creds)


def list_videos_in_folder(drive, folder_id):
    """
    Returns all video files inside a Drive folder.
    Each item is a dict with: id, name, mimeType, size.
    """
    videos = []
    page_token = None

    try:
        while True:
            result = drive.files().list(
                q=f"'{folder_id}' in parents and trashed = false",
                spaces="drive",
                fields="nextPageToken, files(id, name, mimeType, size)",
                pageToken=page_token,
            ).execute()

            files_list = result.get("files", [])
            for file_item in files_list:
                if "name" not in file_item or "id" not in file_item:
                    continue

                mime = file_item.get("mimeType", "")
                guessed_mime, _ = mimetypes.guess_type(file_item["name"])

                is_video = (mime in VIDEO_MIMETYPES) or (guessed_mime and guessed_mime in VIDEO_MIMETYPES)
                if is_video:
                    videos.append(file_item)

            page_token = result.get("nextPageToken")
            if not page_token or not files_list:
                break
    except Exception as e:
        sys.exit(f"Error querying files from Google Drive API: {e}")

    return videos


def download_file(drive, file_id, save_path):
    """Downloads a file from Drive in 10MB chunks safely."""
    request = drive.files().get_media(fileId=file_id)

    with open(save_path, "wb") as f:
        downloader = MediaIoBaseDownload(f, request, chunksize=10 * 1024 * 1024)
        done = False
        while not done:
            progress, done = downloader.next_chunk()
            if progress:
                pct = int(progress.progress() * 100)
                print(f"    {pct}% downloaded...", end="\r")
    print()  # newline after progress execution clears lines


# ── Vimeo Helpers ─────────────────────────────────────────────────────────────

def upload_to_vimeo(client, file_path, title):
    """
    Uploads a local file to Vimeo using the TUS resumable upload protocol.
    Returns the Vimeo video URI e.g. '/videos/123456789'.
    """
    uri = client.upload(
        file_path,
        data={
            "name": title,
            "privacy": {"view": "anybody"},
        },
    )
    return uri


def vimeo_link(uri):
    """Converts '/videos/123456789' → 'https://vimeo.com/123456789'"""
    if not uri:
        return ""
    video_id = uri.strip("/").split("/")[-1]
    return f"https://vimeo.com/{video_id}"


# ── Main Runtime Execution ────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Upload all videos from a Google Drive folder to Vimeo."
    )
    parser.add_argument("--folder-id",   required=True, help="Google Drive folder ID (from the URL)")
    parser.add_argument("--vimeo-token", default=os.environ.get("VIMEO_ACCESS_TOKEN"), help="Vimeo access token")
    parser.add_argument("--output-csv",  default="vimeo_links.csv", help="Where to save results (default: vimeo_links.csv)")
    args = parser.parse_args()

    if not args.vimeo_token:
        sys.exit(
            "\nError: Vimeo token is required.\n"
            "Pass it with --vimeo-token or set the VIMEO_ACCESS_TOKEN environment variable.\n"
            "Get a token at: https://developer.vimeo.com/apps"
        )

    # ── Connect to Google Drive ──────────────────────────────────────────────
    print("\nConnecting to Google Drive...")
    drive = get_drive_service()
    print("Connected.")

    # ── Connect to Vimeo ─────────────────────────────────────────────────────
    print("Connecting to Vimeo...")
    vimeo_client = vimeo.VimeoClient(token=args.vimeo_token)

    try:
        me = vimeo_client.get("/me")
        if me.status_code != 200:
            sys.exit(f"Vimeo auth failed: {me.json()}")
        print(f"Logged in as: {me.json().get('name', 'unknown')}\n")
    except Exception as e:
        sys.exit(f"Critical error connecting to Vimeo API server: {e}")

    # ── Find videos ──────────────────────────────────────────────────────────
    print(f"Looking for videos in folder: {args.folder_id}")
    videos = list_videos_in_folder(drive, args.folder_id)

    if not videos:
        sys.exit("No videos found. Double-check the folder ID and make sure files exist inside.")

    print(f"Found {len(videos)} video(s):\n")
    for v in videos:
        size_mb = int(v.get("size", 0)) / (1024 * 1024)
        print(f"  • {v['name']}  ({size_mb:.1f} MB)")
    print()

    # ── Process & Stream Logs Dynamically ─────────────────────────────────────
    csv_file_exists = os.path.exists(args.output_csv)
    
    with open(args.output_csv, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "vimeo_url", "status"])
        if not csv_file_exists or os.path.getsize(args.output_csv) == 0:
            writer.writeheader()

        results_summary = []
        
        with tempfile.TemporaryDirectory() as tmp:
            for i, video in enumerate(videos, start=1):
                name = video["name"]
                title = os.path.splitext(name)[0]

                print(f"[{i}/{len(videos)}] {name}")
                local_path = os.path.join(tmp, name)

                try:
                    print("  Downloading from Google Drive...")
                    download_file(drive, video["id"], local_path)

                    print("  Uploading to Vimeo...")
                    uri = upload_to_vimeo(vimeo_client, local_path, title)
                    link = vimeo_link(uri)

                    print(f"  Done! → {link}\n")
                    row = {"file": name, "vimeo_url": link, "status": "success"}
                except Exception as e:
                    print(f"  Failed: {e}\n")
                    row = {"file": name, "vimeo_url": "", "status": f"error: {e}"}
                
                # Write row immediately after execution to prevent data drops on unexpected timeouts
                writer.writerow(row)
                f.flush()
                results_summary.append(row)
                
                # Cleanup single file manually out of memory context block footprint
                if os.path.exists(local_path):
                    try:
                        os.unlink(local_path)
                    except Exception:
                        pass

    # ── Summary Reports ──────────────────────────────────────────────────────────
    success = [r for r in results_summary if r["status"] == "success"]
    failed = [r for r in results_summary if r["status"] != "success"]

    print("─" * 50)
    print(f"Done! {len(success)}/{len(videos)} uploaded successfully.")
    print(f"Links saved to: {args.output_csv}\n")

    if success:
        print("Vimeo links:")
        for r in success:
            print(f"  {r['file']}\n    → {r['vimeo_url']}")

    if failed:
        print(f"\nFailed ({len(failed)}):")
        for r in failed:
            print(f"  {r['file']}: {r['status']}")


if __name__ == "__main__":
    main()