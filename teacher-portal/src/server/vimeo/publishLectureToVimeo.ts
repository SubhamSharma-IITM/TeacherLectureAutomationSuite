import { supabaseAdmin } from "@/src/server/db/supabaseAdmin";
import { getTeacherDrive } from "@/src/server/drive/teacherOAuthDrive";
import {
  createVimeoTusUpload,
  tusUploadBuffer,
  vimeoPublicLink,
} from "@/src/server/vimeo/vimeoUpload";

import type { Readable } from "node:stream";

function getEnv(name: string): string | undefined {
  const v = process.env[name];
  if (!v?.trim()) return undefined;
  return v.trim();
}

async function readDriveFileBuffer(
  refreshToken: string,
  fileId: string
): Promise<{ buffer: Buffer; name: string; size: number }> {
  const drive = await getTeacherDrive(refreshToken);

  const meta = await drive.files.get({
    fileId,
    fields: "name,size,mimeType",
    supportsAllDrives: true,
  });

  const name = meta.data.name || "lecture.mp4";
  const size = Number(meta.data.size || 0);
  if (!size) {
    throw new Error("Drive file has unknown size");
  }

  const media = await drive.files.get(
    { fileId, alt: "media", supportsAllDrives: true },
    { responseType: "stream" }
  );

  const stream = media.data as Readable;
  const chunks: Buffer[] = [];

  await new Promise<void>((resolve, reject) => {
    stream.on("data", (c: Buffer) => chunks.push(c));
    stream.on("error", reject);
    stream.on("end", resolve);
  });

  const buffer = Buffer.concat(chunks);
  if (buffer.length !== size) {
    console.warn(
      `Drive download size mismatch for ${fileId}: expected ${size}, got ${buffer.length}`
    );
  }

  return { buffer, name, size: buffer.length };
}

export type PublishToVimeoInput = {
  lectureId: string;
  teacherId: string;
  googleDriveFileId: string;
  title: string;
};

export type PublishToVimeoResult = {
  vimeoUrl: string;
  vimeoVideoId: string;
  vimeoUri: string;
};

/** Drive → buffer → Vimeo TUS. Updates `lectures` when done. */
export async function publishLectureToVimeo(
  input: PublishToVimeoInput
): Promise<PublishToVimeoResult | null> {
  const token = getEnv("VIMEO_ACCESS_TOKEN");
  if (!token) {
    console.info("Vimeo upload skipped: VIMEO_ACCESS_TOKEN not set");
    return null;
  }

  const { data: teacher, error: teacherErr } = await supabaseAdmin
    .from("teachers")
    .select("google_refresh_token")
    .eq("id", input.teacherId)
    .single();

  if (teacherErr || !teacher?.google_refresh_token) {
    throw new Error("Teacher Google token missing for Vimeo pipeline");
  }

  await supabaseAdmin
    .from("lectures")
    .update({ vimeo_status: "uploading" })
    .eq("id", input.lectureId);

  const { buffer, name, size } = await readDriveFileBuffer(
    teacher.google_refresh_token as string,
    input.googleDriveFileId
  );

  const title = input.title?.trim() || name.replace(/\.[^/.]+$/, "");

  const session = await createVimeoTusUpload({
    token,
    title,
    size,
  });

  await tusUploadBuffer(session.uploadLink, buffer, size);

  const vimeoUrl = session.link ?? vimeoPublicLink(session.uri);
  const vimeoVideoId = session.uri.replace(/\/$/, "").split("/").pop() || "";

  if (!vimeoUrl) {
    throw new Error("Vimeo upload finished but no public link");
  }

  const { error: updateErr } = await supabaseAdmin
    .from("lectures")
    .update({
      vimeo_url: vimeoUrl,
      vimeo_video_id: vimeoVideoId,
      vimeo_uri: session.uri,
      vimeo_status: "complete",
    })
    .eq("id", input.lectureId);

  if (updateErr) {
    console.error("Vimeo upload OK but DB update failed:", updateErr.message);
    throw new Error(updateErr.message);
  }

  console.info(`Vimeo publish complete lecture=${input.lectureId} url=${vimeoUrl}`);

  return {
    vimeoUrl,
    vimeoVideoId,
    vimeoUri: session.uri,
  };
}

/** Fire-and-forget wrapper; logs errors without failing finalize. */
export function enqueueVimeoPublish(input: PublishToVimeoInput): void {
  void publishLectureToVimeo(input).catch(async (e) => {
    const message = e instanceof Error ? e.message : String(e);
    console.error("Vimeo publish failed:", message);
    await supabaseAdmin
      .from("lectures")
      .update({
        vimeo_status: "failed",
        vimeo_error: message.slice(0, 500),
      })
      .eq("id", input.lectureId)
      .then(({ error }) => {
        if (error) console.error("Failed to record vimeo_error:", error.message);
      });
  });
}
