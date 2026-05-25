import { supabaseAdmin } from "@/src/server/db/supabaseAdmin";
import { startDriveResumableSession } from "@/src/server/drive/resumableUpload";
import { getTeacherAccessToken } from "@/src/server/drive/teacherOAuthDrive";

export type InitUploadBody = {
  fileName: string;
  mimeType: string;
  fileSize: number;
  lectureTitle: string;
  subject?: string;
  chapter?: string;
  idempotencyKey?: string;
};

export type InitUploadResult = {
  jobId: string;
  reused: boolean;
};

/** Uses the teacher who connected Google Drive (refresh token set). Email optional for OBS. */
export async function resolveConnectedTeacherEmail(
  teacherEmail?: string | null
): Promise<string> {
  const explicit = teacherEmail?.trim().toLowerCase();
  if (explicit) return explicit;

  const { data, error } = await supabaseAdmin
    .from("teachers")
    .select("email")
    .not("google_refresh_token", "is", null)
    .order("id", { ascending: false })
    .limit(1)
    .maybeSingle();

  if (error) throw new Error(error.message);
  if (!data?.email) {
    throw new Error(
      "No Google Drive connection found. In Acadza Studio click Connect Google Drive and sign in, then try again."
    );
  }
  return (data.email as string).trim().toLowerCase();
}

export async function initUploadJob(
  body: InitUploadBody,
  teacherEmail?: string | null
): Promise<InitUploadResult> {
  const email = await resolveConnectedTeacherEmail(teacherEmail);

  const { data: teacher, error: teacherErr } = await supabaseAdmin
    .from("teachers")
    .select("id, google_refresh_token")
    .eq("email", email)
    .maybeSingle();

  if (teacherErr) {
    throw new Error(teacherErr.message);
  }

  if (!teacher?.id) {
    throw new Error(
      "No teacher profile for this email. Sign in with Google in the browser first (Connect Google Drive)."
    );
  }

  if (!teacher.google_refresh_token) {
    throw new Error(
      "Google Drive not connected. Open Connect Google Drive and approve access, then try again."
    );
  }

  const teacherId = teacher.id as string;

  if (
    !body.fileName?.trim() ||
    !body.mimeType?.trim() ||
    typeof body.fileSize !== "number" ||
    body.fileSize <= 0
  ) {
    throw new Error("fileName, mimeType, and positive fileSize are required");
  }

  if (!body.lectureTitle?.trim()) {
    throw new Error("lectureTitle is required");
  }

  if (!body.mimeType.startsWith("video/")) {
    throw new Error("Only video uploads are allowed");
  }

  const idempotencyKey = body.idempotencyKey?.trim();
  if (idempotencyKey) {
    const { data: existing } = await supabaseAdmin
      .from("upload_jobs")
      .select("id,status")
      .eq("idempotency_key", idempotencyKey)
      .maybeSingle();
    if (existing?.id && existing.status !== "failed") {
      return { jobId: existing.id as string, reused: true };
    }
  }

  const accessToken = await getTeacherAccessToken(
    teacher.google_refresh_token as string
  );

  const resumableUrl = await startDriveResumableSession({
    fileName: body.fileName.trim(),
    mimeType: body.mimeType.trim(),
    fileSize: body.fileSize,
    accessToken,
  });

  const { data: row, error } = await supabaseAdmin
    .from("upload_jobs")
    .insert({
      teacher_id: teacherId,
      status: "uploading",
      progress_percent: 0,
      total_bytes: body.fileSize,
      uploaded_bytes: 0,
      resumable_url: resumableUrl,
      google_file_name: body.fileName.trim(),
      mime_type: body.mimeType.trim(),
      lecture_title: body.lectureTitle.trim(),
      subject: body.subject?.trim() || null,
      chapter: body.chapter?.trim() || null,
      idempotency_key: idempotencyKey || null,
      updated_at: new Date().toISOString(),
    })
    .select("id")
    .single();

  if (error || !row) {
    throw new Error(error?.message || "Failed to create upload job");
  }

  return { jobId: row.id as string, reused: false };
}
