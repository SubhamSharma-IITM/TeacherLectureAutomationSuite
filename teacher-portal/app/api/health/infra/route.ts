import { sendLectureAccessEmail } from "@/src/server/email/mailer";
import { supabaseAdmin } from "@/src/server/db/supabaseAdmin";
import { getDriveFolderId } from "@/src/server/drive/driveConfig";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function getEnv(name: string): string | undefined {
  const v = process.env[name];
  if (!v) return undefined;
  const trimmed = v.trim();
  return trimmed.length ? trimmed : undefined;
}

async function checkSupabaseTable(table: string) {
  const result = await supabaseAdmin.from(table).select("id").limit(1);
  if (!result.error) {
    return { ok: true, rowCount: result.data?.length ?? 0 };
  }

  const message = result.error.message || "Unknown Supabase error";
  const isMissingRelation =
    /relation .* does not exist|does not exist/i.test(message) ||
    /UndefinedTable|42P01/i.test(message) ||
    /Could not find the table/i.test(message);

  return {
    ok: false,
    missingTable: isMissingRelation,
    message,
  };
}

export async function GET() {
  const appUrl = getEnv("APP_URL") ?? "http://localhost:3000";

  const [supabaseLectures, supabaseLectureAccess, teachers] = await Promise.all([
    checkSupabaseTable("lectures").catch((e) => ({
      ok: false,
      message: e instanceof Error ? e.message : String(e),
      missingTable: false,
    })),
    checkSupabaseTable("lecture_access").catch((e) => ({
      ok: false,
      message: e instanceof Error ? e.message : String(e),
      missingTable: false,
    })),
    supabaseAdmin
      .from("teachers")
      .select("email")
      .not("google_refresh_token", "is", null)
      .limit(1)
      .maybeSingle()
      .then((r) => ({
        ok: !r.error && Boolean(r.data?.email),
        connectedEmail: r.data?.email ?? null,
        error: r.error?.message ?? null,
      }))
      .catch((e) => ({
        ok: false,
        connectedEmail: null,
        error: e instanceof Error ? e.message : String(e),
      })),
  ]);

  const supabaseTables = {
    lectures: supabaseLectures,
    lecture_access: supabaseLectureAccess,
  };

  const supabaseReachable =
    supabaseLectures.ok ||
    supabaseLectureAccess.ok ||
    (supabaseLectures.missingTable && supabaseLectureAccess.missingTable);

  let driveFolder: { ok: boolean; folderId?: string; error?: string } = { ok: false };
  try {
    driveFolder = { ok: true, folderId: getDriveFolderId() };
  } catch (e) {
    driveFolder = {
      ok: false,
      error: e instanceof Error ? e.message : String(e),
    };
  }

  const resendTestTo = getEnv("RESEND_TEST_TO");
  let email: { status: string; reason?: string; messageId?: string | null; error?: string } = {
    status: "skipped",
    reason: "RESEND_TEST_TO not set",
  };
  if (resendTestTo) {
    try {
      const res = await sendLectureAccessEmail({
        to: resendTestTo,
        lectureTitle: "Infra test lecture",
        watchUrl: `${appUrl}/watch/infra-test`,
      });
      email = { status: "sent", messageId: res.messageId ?? null };
    } catch (e) {
      email = {
        status: "failed",
        error: e instanceof Error ? e.message : String(e),
      };
    }
  }

  const vimeoConfigured = Boolean(getEnv("VIMEO_ACCESS_TOKEN"));

  const ok =
    supabaseReachable &&
    teachers.ok &&
    driveFolder.ok &&
    (email.status === "skipped" || email.status === "sent");

  return Response.json({
    ok,
    supabase: { reachable: supabaseReachable, tables: supabaseTables },
    googleDrive: { teacherConnected: teachers.ok, email: teachers.connectedEmail },
    driveFolder,
    vimeo: { configured: vimeoConfigured },
    email,
  });
}
