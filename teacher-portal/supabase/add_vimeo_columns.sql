-- Run once in Supabase SQL Editor (lectures table).
alter table public.lectures
  add column if not exists vimeo_url text,
  add column if not exists vimeo_video_id text,
  add column if not exists vimeo_uri text,
  add column if not exists vimeo_status text,
  add column if not exists vimeo_error text;
