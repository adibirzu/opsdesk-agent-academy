import { createServerFn } from "@tanstack/react-start";
import { requireSupabaseAuth } from "@/integrations/supabase/auth-middleware";
import { telemetrySetupInput } from "./telemetry-setup-contract";
import { telemetrySetupPresence } from "./telemetry-setup.server";

export const checkTelemetrySetup = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((input: unknown) => telemetrySetupInput.parse(input))
  .handler(async ({ context }) => {
    if (context.claims.is_anonymous === true) throw new Error("A non-anonymous signed-in account is required.");
    return telemetrySetupPresence(process.env["LANGFUSE_BASE_URL"], process.env["LANGFUSE_PUBLIC_KEY"], process.env["LANGFUSE_SECRET_KEY"]);
  });