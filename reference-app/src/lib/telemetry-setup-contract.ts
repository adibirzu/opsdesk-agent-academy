import { z } from "zod";

export const telemetrySetupInput = z.object({}).strict();
export type TelemetrySetup = {
  LANGFUSE_BASE_URL: boolean;
  LANGFUSE_PUBLIC_KEY: boolean;
  LANGFUSE_SECRET_KEY: boolean;
  validHttpsOrigin: boolean;
  status: "configured" | "not_configured" | "invalid_config";
};