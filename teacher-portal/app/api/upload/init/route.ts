import { getServerSession } from "next-auth/next";
import { authOptions } from "@/src/lib/auth";
import { initUploadJob, type InitUploadBody } from "@/src/server/upload/initUploadJob";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 60;

export async function POST(request: Request) {
  const session = await getServerSession(authOptions);
  if (!session?.user?.email) {
    return Response.json(
      { error: "Sign in with Google first, then connect Drive (same login)." },
      { status: 401 }
    );
  }

  let body: InitUploadBody;
  try {
    body = (await request.json()) as InitUploadBody;
  } catch {
    return Response.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  try {
    const result = await initUploadJob(body, session.user.email);
    return Response.json(result);
  } catch (e) {
    const message = e instanceof Error ? e.message : String(e);
    const status =
      message.includes("No teacher profile") ||
      message.includes("Google Drive not connected")
        ? 403
        : message.includes("required") || message.includes("Only video")
          ? 400
          : 500;
    return Response.json({ error: message }, { status });
  }
}
