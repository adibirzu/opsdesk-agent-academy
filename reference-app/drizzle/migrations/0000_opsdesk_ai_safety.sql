CREATE TABLE public.opsdesk_ai_limits (user_id uuid PRIMARY KEY, minute_start timestamptz NOT NULL DEFAULT now(), minute_count integer NOT NULL DEFAULT 0, day_start date NOT NULL DEFAULT (now() AT TIME ZONE 'UTC')::date, day_count integer NOT NULL DEFAULT 0);
GRANT SELECT ON public.opsdesk_ai_limits TO authenticated;
GRANT ALL ON public.opsdesk_ai_limits TO service_role;
ALTER TABLE public.opsdesk_ai_limits ENABLE ROW LEVEL SECURITY;
CREATE POLICY own_limits ON public.opsdesk_ai_limits FOR SELECT TO authenticated USING (auth.uid() = user_id);
CREATE FUNCTION public.opsdesk_take_analysis_slot() RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE u uuid := auth.uid(); r public.opsdesk_ai_limits%ROWTYPE; t timestamptz := now();
BEGIN
 IF u IS NULL THEN RAISE EXCEPTION 'Unauthenticated'; END IF;
 INSERT INTO public.opsdesk_ai_limits(user_id) VALUES (u) ON CONFLICT DO NOTHING;
 SELECT * INTO r FROM public.opsdesk_ai_limits WHERE user_id=u FOR UPDATE;
 IF t >= r.minute_start + interval '1 minute' THEN r.minute_start:=t; r.minute_count:=0; END IF;
 IF r.day_start <> (t AT TIME ZONE 'UTC')::date THEN r.day_start:=(t AT TIME ZONE 'UTC')::date; r.day_count:=0; END IF;
 IF r.minute_count >= 2 OR r.day_count >= 10 THEN RETURN false; END IF;
 UPDATE public.opsdesk_ai_limits SET minute_start=r.minute_start, minute_count=r.minute_count+1, day_start=r.day_start, day_count=r.day_count+1 WHERE user_id=u;
 RETURN true;
END $$;
REVOKE ALL ON FUNCTION public.opsdesk_take_analysis_slot() FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.opsdesk_take_analysis_slot() TO authenticated;
CREATE TABLE public.opsdesk_ai_access (model text PRIMARY KEY, blocked boolean NOT NULL DEFAULT false, reason text NOT NULL, upstream_status integer NOT NULL);
GRANT ALL ON public.opsdesk_ai_access TO service_role;
ALTER TABLE public.opsdesk_ai_access ENABLE ROW LEVEL SECURITY;
COMMENT ON TABLE public.opsdesk_ai_access IS 'Server-only persistent provider access blocks; clear only after workspace access is restored. No user content stored.';