import {
  initUploadJob,
  type InitUploadBody,
} from "@/src/server/upload/initUploadJob";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 60;

type ObsInitBody = InitUploadBody & {
  teacherEmail?: string;
};

/** OBS upload — uses whoever connected Google Drive (no manual email in config). */
export async function POST(request: Request) {
  let body: ObsInitBody;
  try {
    body = (await request.json()) as ObsInitBody;
  } catch {
    return Response.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  try {
    const result = await initUploadJob(body, body.teacherEmail);
    return Response.json(result);
  } catch (e) {
    const message = e instanceof Error ? e.message : String(e);
    const status =
      message.includes("No Google Drive") ||
      message.includes("No teacher profile") ||
      message.includes("Google Drive not connected")
        ? 403
        : message.includes("required") || message.includes("Only video")
          ? 400
          : 500;
    return Response.json({ error: message }, { status });
  }
}
