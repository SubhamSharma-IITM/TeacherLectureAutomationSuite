# Teacher Lecture Automation Suite (Acadza Studio)

Monorepo for **Acadza Studio** (OBS-based desktop app) and the **teacher portal** (Next.js upload backend). Teachers record in Acadza Studio, upload lectures to Google Drive, and the portal can publish to Vimeo after upload.

**Repository:** https://github.com/SubhamSharma-IITM/TeacherLectureAutomationSuite  
**Branch:** `tushar_one`

---

## Repository layout

| Path | What it is |
|------|------------|
| `frontend/`, `libobs/`, `plugins/`, `cmake/`, … | **Acadza Studio** — OBS Studio fork (C++/Qt) |
| `teacher-portal/` | **Teacher portal** — Next.js API + Google sign-in + upload + Vimeo |
| `upload.py`, `viemo.md` | Optional manual Drive → Vimeo script (not used by OBS at runtime) |

---

## Prerequisites

### Acadza Studio (Windows x64)

- Windows 10/11 (64-bit)
- **Visual Studio 2022** with workload **Desktop development with C++**
- **CMake 3.28+** (Visual Studio installer or standalone)
- **Git** (with submodule support)
- Enough disk space (~15–20 GB for deps + build)
- Optional: increase Windows **page file** if the linker runs out of memory

### Teacher portal

- **Node.js 18+** and **npm**
- **Supabase** project (PostgreSQL)
- **Google Cloud** OAuth 2.0 **Web** client (for NextAuth)
- **Google Drive** folder ID (same account teachers sign in with)
- Optional: **Vimeo** access token (`upload`, `edit`, `video_files` scopes)
- Optional: SMTP or Resend for student watch-link emails

---

## 1. Clone the repository

```powershell
git clone --branch tushar_one --recurse-submodules https://github.com/SubhamSharma-IITM/TeacherLectureAutomationSuite.git
cd TeacherLectureAutomationSuite
```

If you already cloned without submodules:

```powershell
git submodule update --init --recursive
```

> **Important for builds:** `plugins/obs-browser`, `plugins/obs-websocket`, and `deps/libdshowcapture` are Git submodules. Without `--recurse-submodules`, the OBS build will fail.

---

## 2. Build Acadza Studio (OBS)

From the **repository root** (not `teacher-portal/`):

### Configure (first time)

CMake downloads OBS prebuilt dependencies (Qt, FFmpeg, etc.) automatically. This can take a while.

```powershell
cmake --preset windows-x64
```

### Build

Use low parallelism if you hit out-of-memory errors during linking:

```powershell
cmake --build build_x64 --config RelWithDebInfo --target obs-studio --parallel 1
```

### Run

```powershell
.\build_x64\rundir\RelWithDebInfo\bin\64bit\obs64.exe
```

The app window title and branding show **Acadza Studio**.

### Point Acadza Studio at your portal (optional)

Default portal URL is `http://localhost:3000`. To change it, edit the user config after first run:

- File: `%APPDATA%\obs-studio\global.ini` (section `[Acadza]`)
- Example:

```ini
[Acadza]
PortalUrl=http://localhost:3000
```

For production, set this to your deployed portal URL (e.g. `https://your-portal.vercel.app`).

---

## 3. Teacher portal — setup and run

```powershell
cd teacher-portal
copy .env.example .env
# Edit .env — see checklist below
npm install
npm run dev
```

Open: http://localhost:3000

### Supabase (run once in SQL Editor)

Run these files in order:

1. Your base `teachers` / `lectures` / `students` schema (if not already applied)
2. `teacher-portal/supabase/schema_teachers_google_oauth.sql`
3. `teacher-portal/supabase/schema_upload_jobs.sql`
4. `teacher-portal/supabase/add_vimeo_columns.sql` (if using Vimeo)

### `.env` checklist

| Variable | Required | Notes |
|----------|----------|--------|
| `NEXTAUTH_SECRET` | Yes | `openssl rand -base64 32` |
| `NEXTAUTH_URL` | Yes | `http://localhost:3000` in dev |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Yes | OAuth **Web** client |
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Server-side only — keep secret |
| `GOOGLE_DRIVE_FOLDER_ID` | Yes | Folder ID from Drive URL where lectures are stored |
| `APP_URL` | Yes | Same as portal base URL (watch links in email) |
| `VIMEO_ACCESS_TOKEN` | Optional | Must include **`upload`** scope |
| `SMTP_*` or `RESEND_API_KEY` | Optional | For emailing watch links |

### Google OAuth (Cloud Console)

1. APIs & Services → enable **Google Drive API**
2. Credentials → **OAuth 2.0 Client ID** → type **Web application**
3. **Authorized redirect URI** (exact):

   ```
   http://localhost:3000/api/auth/callback/google
   ```

4. Copy Client ID and Secret into `.env`

### Google Drive folder

1. Create a folder in the **same Google account** teachers will use to sign in
2. Open the folder in Drive; copy the ID from the URL:

   `https://drive.google.com/drive/folders/FOLDER_ID_HERE`

3. Set `GOOGLE_DRIVE_FOLDER_ID` in `.env`

---

## 4. End-to-end workflow

```text
1. Start portal:     cd teacher-portal && npm run dev
2. Run Acadza Studio: obs64.exe from build output
3. In Acadza Studio:  click "Connect Google Drive"
                      → browser opens portal Google sign-in
                      → approve Drive access
4. Set up scene/sources and start **Recording**
5. When class ends:   click **End class** → confirm
                      → recording stops, file uploads to portal
                      → portal saves to Drive + Supabase lecture row
                      → background job uploads to Vimeo (if token set)
6. Students:          watch link from email → /watch/[token]
                      (Vimeo embed when publish completed, else Drive preview)
```

### Acadza Studio controls

| Control | Action |
|---------|--------|
| **Connect Google Drive** | Opens portal sign-in; stores teacher refresh token in Supabase |
| **End class** | Stops recording and uploads the recording file to the portal |

Upload uses the **raw recording file** (e.g. `.mkv`) while remux may still run in the background.

---

## 5. Verify Vimeo (optional)

After finalize, check the portal terminal:

- Success: `Vimeo publish complete lecture=... url=https://vimeo.com/...`
- Wrong token scope: `Your access token does not have the "upload" scope` → regenerate token at [developer.vimeo.com/apps](https://developer.vimeo.com/apps) with **upload**, **edit**, **video_files**

Check Supabase `lectures` table: `vimeo_status`, `vimeo_url`.

---

## 6. Production build (portal)

```powershell
cd teacher-portal
npm run build
npm start
```

Set `NEXTAUTH_URL`, `APP_URL`, and OAuth redirect URIs to your production domain.

> Large videos: the portal buffers the full file for Vimeo TUS in dev. For production on serverless hosts, consider a background worker or streaming upload.

---

## Troubleshooting

| Issue | What to try |
|-------|-------------|
| OBS configure fails | Install VS 2022 C++ tools; run `git submodule update --init --recursive` |
| OBS link OOM | `--parallel 1`; increase Windows page file |
| Connect Drive / sign-in fails | Check Supabase env vars and `teachers` table; redirect URI must match exactly |
| Upload stuck at 0% | Ensure portal is running; check `Connect Google Drive` completed; see Acadza log |
| Vimeo failed | Fix `VIMEO_ACCESS_TOKEN` scopes; run `add_vimeo_columns.sql` |
| OBS can’t reach portal | `PortalUrl` in `global.ini` must match running portal |

Logs: Acadza Studio → **Help → Log Files**, or `%APPDATA%\obs-studio\logs`.

---

## Manual Vimeo tool (optional)

From repo root (separate Python env):

```powershell
pip install google-api-python-client google-auth-oauthlib google-auth-httplib2 PyVimeo
python upload.py --folder-id YOUR_FOLDER_ID --vimeo-token YOUR_TOKEN
```

See `viemo.md` for details. The **live OBS workflow** uses the portal TypeScript pipeline, not this script.

---

## For maintainers / CI

- Full OBS tree is included on `tushar_one` (not just patches).
- Build with preset `windows-x64` and target `obs-studio`.
- Do not commit `build_x64/`, `teacher-portal/node_modules/`, or `.env` files.
- Acadza-specific sources: `frontend/widgets/OBSBasic_Acadza*.cpp`, `frontend/cmake/ui-widgets.cmake`, locale strings in `frontend/data/locale/en-US.ini`.

---

## License

Acadza Studio is based on [OBS Studio](https://obsproject.com) (GPLv2). See `COPYING` in the repository root.
