# Teacher portal (Acadza upload backend)

Next.js service for Google sign-in, resumable lecture uploads to Drive, Supabase metadata, optional Vimeo publish, and token-gated student watch pages.

**Full setup (clone, build Acadza Studio, OAuth, workflow):** see the [repository root README](../README.md).

## Quick start

```bash
cp .env.example .env
# fill in env vars — see root README
npm install
npm run dev
```

Open http://localhost:3000 — UI is minimal; **Acadza Studio** is the main interface.

## Supabase migrations

Run in SQL Editor:

- `supabase/schema_teachers_google_oauth.sql`
- `supabase/schema_upload_jobs.sql`
- `supabase/add_vimeo_columns.sql` (Vimeo)

## API routes used by Acadza Studio

| Route | Purpose |
|-------|---------|
| `GET /api/obs/drive-status` | Whether a teacher has connected Drive |
| `POST /api/obs/upload/init` | Start upload job |
| `POST /api/upload/[jobId]/chunk` | Upload chunks |
| `POST /api/upload/[jobId]/finalize` | Finish Drive upload, create lecture, enqueue Vimeo |
