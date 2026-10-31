import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import type { User } from "@supabase/supabase-js";
import { supabase } from "@/integrations/supabase/client";
import { useRouter } from "@tanstack/react-router";

const SessionContext = createContext<{ user: User | null; ready: boolean }>({ user: null, ready: false });
export function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const router = useRouter();
  useEffect(() => {
    const { data } = supabase.auth.onAuthStateChange((event, session) => {
      setUser(session?.user ?? null);
      setReady(true);
      if (event === "SIGNED_IN" || event === "SIGNED_OUT" || event === "USER_UPDATED") void router.invalidate();
    });
    return () => data.subscription.unsubscribe();
  }, [router]);
  return <SessionContext.Provider value={{ user, ready }}>{children}</SessionContext.Provider>;
}
export const useWorkshopSession = () => useContext(SessionContext);