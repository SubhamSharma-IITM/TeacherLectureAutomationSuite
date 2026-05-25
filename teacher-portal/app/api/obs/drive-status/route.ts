import { supabaseAdmin } from "@/src/server/db/supabaseAdmin";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/** OBS UI: whether a teacher has connected Google Drive. */
export async function GET() {
  const { data, error } = await supabaseAdmin
    .from("teachers")
    .select("email, name")
    .not("google_refresh_token", "is", null)
    .order("id", { ascending: false })
    .limit(1)
    .maybeSingle();

  if (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }

  if (!data?.email) {
    return Response.json({ connected: false });
  }

  return Response.json({
    connected: true,
    email: data.email as string,
    name: (data.name as string | null) ?? null,
  });
}
