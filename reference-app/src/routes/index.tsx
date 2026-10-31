import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState, type FormEvent } from "react";
import { OpsdeskAnalysis } from "@/components/opsdesk-analysis";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "OpsDesk Workshop Rehearsal — Synthetic Incident Inbox" },
      { name: "description", content: "Synthetic incident inbox with authenticated, read-only Lovable AI analysis and real execution inspection." },
      { property: "og:title", content: "OpsDesk Workshop Rehearsal" },
      { property: "og:description", content: "Synthetic incident inbox with authenticated, read-only Lovable AI analysis and real execution inspection." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: Index,
});

type Priority = "high" | "medium" | "low";
type Ticket = { id: string; title: string; description: string; service: string; priority: Priority };

const SEED: Ticket[] = [
  { id: "TRAIN-101", title: "Payments slow after a release", description: "Payment requests became slow after the latest release. Cause unconfirmed.", service: "payments", priority: "high" },
  { id: "TRAIN-102", title: "Checkout health check", description: "Routine health check of the checkout service.", service: "checkout", priority: "medium" },
  { id: "TRAIN-103", title: "Catalog availability", description: "Review availability of the product catalog.", service: "catalog", priority: "low" },
];

function Index() {
  const [tickets, setTickets] = useState<Ticket[]>(SEED);
  const [query, setQuery] = useState("");
  const [prio, setPrio] = useState<"all" | Priority>("all");
  const [selectedId, setSelectedId] = useState<string>("TRAIN-101");
  const [form, setForm] = useState({ title: "", description: "", service: "", priority: "medium" as Priority });
  const [formError, setFormError] = useState("");
  const [nextNum, setNextNum] = useState(104);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return tickets.filter(
      (t) =>
        (prio === "all" || t.priority === prio) &&
        (!q || t.title.toLowerCase().includes(q) || t.service.toLowerCase().includes(q)),
    );
  }, [tickets, query, prio]);

  const selected = tickets.find((t) => t.id === selectedId) ?? null;

  function select(id: string) {
    setSelectedId(id);
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!form.title.trim() || !form.description.trim()) {
      setFormError("Title and description are required.");
      return;
    }
    const t: Ticket = {
      id: `TRAIN-${nextNum}`,
      title: form.title.trim(),
      description: form.description.trim(),
      service: form.service.trim() || "unassigned",
      priority: form.priority,
    };
    setTickets((p) => [t, ...p]);
    setNextNum((n) => n + 1);
    setForm({ title: "", description: "", service: "", priority: "medium" });
    setFormError("");
    select(t.id);
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b border-border bg-card">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-3">
          <h1 className="font-heading text-2xl">OpsDesk Workshop Rehearsal</h1>
          <span className="rounded-full border border-primary px-3 py-0.5 text-xs font-semibold uppercase tracking-wide text-primary">
            Synthetic data · in memory
          </span>
        </div>
      </header>

      <main className="mx-auto grid max-w-6xl gap-4 px-4 py-4 md:grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)]">
        <section aria-labelledby="inbox-h" className="space-y-3">
          <h2 id="inbox-h" className="font-heading text-lg">Inbox</h2>
          <div className="grid grid-cols-[1fr_auto] gap-2">
            <div>
              <label htmlFor="search" className="text-xs font-medium text-muted-foreground">Search title or service</label>
              <input id="search" type="search" value={query} onChange={(e) => setQuery(e.target.value)} className="field" placeholder="e.g. payments" />
            </div>
            <div>
              <label htmlFor="prio" className="text-xs font-medium text-muted-foreground">Priority</label>
              <select id="prio" value={prio} onChange={(e) => setPrio(e.target.value as "all" | Priority)} className="field">
                <option value="all">All</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
          </div>
          <ul className="space-y-2" aria-label="Tickets">
            {filtered.length === 0 && <li className="text-sm text-muted-foreground">No tickets match.</li>}
            {filtered.map((t) => (
              <li key={t.id}>
                <button
                  type="button"
                  onClick={() => select(t.id)}
                  aria-pressed={t.id === selectedId}
                  className={`w-full rounded-md border bg-card px-3 py-2 text-left transition-colors hover:border-primary ${t.id === selectedId ? "border-primary ring-1 ring-primary" : "border-border"}`}
                >
                  <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
                    <span>{t.id} · {t.service}</span>
                    <PrioBadge p={t.priority} />
                  </div>
                  <div className="mt-0.5 text-sm font-medium">{t.title}</div>
                </button>
              </li>
            ))}
          </ul>

          <form onSubmit={submit} noValidate className="space-y-2 rounded-md border border-border bg-card p-3" aria-labelledby="new-h">
            <h2 id="new-h" className="font-heading text-lg">New ticket</h2>
            <div>
              <label htmlFor="nt-title" className="text-xs font-medium">Title (required)</label>
              <input id="nt-title" required aria-required="true" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className="field" />
            </div>
            <div>
              <label htmlFor="nt-desc" className="text-xs font-medium">Description (required)</label>
              <textarea id="nt-desc" required aria-required="true" rows={3} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="field" />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label htmlFor="nt-svc" className="text-xs font-medium">Service</label>
                <input id="nt-svc" value={form.service} onChange={(e) => setForm({ ...form, service: e.target.value })} className="field" />
              </div>
              <div>
                <label htmlFor="nt-prio" className="text-xs font-medium">Priority</label>
                <select id="nt-prio" value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value as Priority })} className="field">
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
              </div>
            </div>
            {formError && <p role="alert" className="text-sm text-primary">{formError}</p>}
            <button type="submit" className="btn-primary">Add synthetic ticket</button>
          </form>
        </section>

        <section aria-labelledby="detail-h" className="rounded-md border border-border bg-card p-4">
          <h2 id="detail-h" className="sr-only">Ticket detail</h2>
          {selected ? (
            <div className="space-y-4">
              <div>
                <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                  <span>{selected.id}</span><span>·</span><span>{selected.service}</span>
                  <PrioBadge p={selected.priority} />
                  <span className="rounded bg-muted px-1.5 py-0.5">Synthetic</span>
                </div>
                <h3 className="mt-1 font-heading text-xl">{selected.title}</h3>
                <p className="mt-2 whitespace-pre-wrap text-sm">{selected.description}</p>
              </div>
              <OpsdeskAnalysis key={selected.id} ticket={selected} />
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Select a ticket to see details.</p>
          )}
        </section>
      </main>
    </div>
  );
}

function PrioBadge({ p }: { p: Priority }) {
  const cls = p === "high" ? "bg-primary text-primary-foreground" : p === "medium" ? "bg-accent text-accent-foreground" : "bg-secondary text-secondary-foreground";
  return <span className={`rounded px-1.5 py-0.5 text-[11px] font-semibold uppercase ${cls}`}>{p}</span>;
}
