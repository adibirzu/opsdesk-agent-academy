import { createMiddleware, createServerFn } from "@tanstack/react-start";
import { requireSupabaseAuth } from "@/integrations/supabase/auth-middleware";
import { requestSchema } from "./opsdesk-contract";
import { analyzeOnServer, MODEL } from "./opsdesk-agent.server";
import { createWorkshopTelemetry } from "./langfuse.server";

const telemetryRequest = createMiddleware({ type: "function" }).server(async ({ next }) => {
  const telemetry = createWorkshopTelemetry({ baseUrl: process.env["LANGFUSE_BASE_URL"], publicKey: process.env["LANGFUSE_PUBLIC_KEY"], secretKey: process.env["LANGFUSE_SECRET_KEY"] });
  try { return await next({ context: { telemetry } }); }
  catch (error) {
    telemetry.authorization(false);
    await telemetry.finish("unauthorized", 0);
    throw error;
  }
});

export const analyzeTicket = createServerFn({ method: "POST" })
  .middleware([telemetryRequest, requireSupabaseAuth])
  .inputValidator((input: unknown) => requestSchema.parse(input))
  .handler(async ({ data, context }) => {
    if (context.claims.is_anonymous === true) throw new Error("A non-anonymous signed-in account is required.");
    context.telemetry.authorization(true);
    return analyzeOnServer(data, {
      telemetry: context.telemetry,
      apiKey: () => process.env["LOVABLE_API_KEY"],
      reserve: async () => {
        const { data: allowed, error } = await context.supabase.rpc("opsdesk_take_analysis_slot");
        if (error) throw new Error("The analysis request limiter is unavailable; no AI request was sent.");
        return allowed === true;
      },
      accessBlock: async () => {
        // Internal security state is privileged; not ordinary user data.
        const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
        const { data: block, error } = await supabaseAdmin.from("opsdesk_ai_access").select("blocked,reason,upstream_status").eq("model", MODEL).maybeSingle();
        if (error) throw new Error("AI access safety check unavailable; no model was called.");
        return block?.blocked ? { reason: block.reason, status: block.upstream_status } : null;
      },
      persistBlock: async (reason, status) => {
        const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
        const { error } = await supabaseAdmin.from("opsdesk_ai_access").upsert({ model: MODEL, blocked: true, reason, upstream_status: status });
        if (error) throw new Error("AI access denied; safety-state persistence failed. Do not retry until configuration is repaired.");
      },
    });
  });