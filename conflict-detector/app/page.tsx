import { readStore } from "@/lib/storage";
import { detectConflicts, summarize, type Conflict, type Severity } from "@/lib/matcher";
import ScrapeButton from "@/components/ScrapeButton";

export const dynamic = "force-dynamic";

const SEVERITY_LABEL: Record<Severity, string> = {
  high: "HIGH",
  medium: "MEDIUM",
  low: "LOW",
};

const SEVERITY_BG: Record<Severity, string> = {
  high: "bg-red-500/15 border-red-500/40 text-red-300",
  medium: "bg-amber-500/15 border-amber-500/40 text-amber-300",
  low: "bg-sky-500/15 border-sky-500/40 text-sky-300",
};

const KIND_LABEL: Record<Conflict["kind"], string> = {
  same_person: "Same person on both boards",
  parent_child: "Parent / child relation",
  siblings: "Likely siblings or close relatives",
  shared_surname: "Shared surname",
};

export default function Page() {
  const store = readStore();
  const conflicts = detectConflicts(store.organizations, store.people);
  const counts = summarize(conflicts);

  return (
    <main className="max-w-6xl mx-auto px-6 py-10">
      <header className="flex items-start justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">
            Conflict-of-Interest Detector
          </h1>
          <p className="text-[var(--muted)] mt-1">
            Cross-organization name matching for Uzbek joint-stock companies
            listed on{" "}
            <a className="underline" href="https://openinfo.uz/ru?tab=stock&page=1&type=stocks" target="_blank" rel="noreferrer">
              openinfo.uz
            </a>
            .
          </p>
        </div>
        <ScrapeButton />
      </header>

      <section className="grid grid-cols-3 gap-4 mb-8">
        <Stat label="Organizations" value={store.organizations.length} />
        <Stat label="People on boards" value={store.people.length} />
        <Stat label="Conflicts flagged" value={conflicts.length} />
      </section>

      <section className="grid grid-cols-3 gap-4 mb-8">
        <SeverityCard severity="high" count={counts.high} />
        <SeverityCard severity="medium" count={counts.medium} />
        <SeverityCard severity="low" count={counts.low} />
      </section>

      <section>
        <h2 className="text-xl font-semibold mb-3">Flagged conflicts</h2>
        {conflicts.length === 0 && (
          <div className="rounded border border-[var(--border)] bg-[var(--panel)] p-6 text-[var(--muted)]">
            No conflicts found yet. If the database is empty, run{" "}
            <code className="text-[var(--accent)]">npm run seed</code> for
            sample data, or click <em>Scrape openinfo.uz</em> above.
          </div>
        )}

        <ul className="space-y-3">
          {conflicts.map((c, i) => (
            <li
              key={i}
              className={`rounded border p-4 ${SEVERITY_BG[c.severity]}`}
            >
              <div className="flex items-center gap-3 mb-2">
                <span className="text-xs font-semibold tracking-wider px-2 py-0.5 rounded bg-black/30">
                  {SEVERITY_LABEL[c.severity]}
                </span>
                <span className="text-sm uppercase tracking-wide text-[var(--muted)]">
                  {KIND_LABEL[c.kind]}
                </span>
              </div>
              <p className="text-sm mb-3">{c.reason}</p>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <PersonCard person={c.personA} orgName={c.orgA.name} orgUrl={c.orgA.url} />
                <PersonCard person={c.personB} orgName={c.orgB.name} orgUrl={c.orgB.url} />
              </div>
            </li>
          ))}
        </ul>
      </section>

      <footer className="mt-10 text-xs text-[var(--muted)]">
        Last data refresh:{" "}
        {store.scrapedAt
          ? new Date(store.scrapedAt).toLocaleString()
          : "never (seed or scrape to populate)"}
      </footer>
    </main>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded border border-[var(--border)] bg-[var(--panel)] p-4">
      <div className="text-[var(--muted)] text-xs uppercase tracking-wider">{label}</div>
      <div className="text-3xl font-semibold mt-1">{value}</div>
    </div>
  );
}

function SeverityCard({ severity, count }: { severity: Severity; count: number }) {
  return (
    <div className={`rounded border p-4 ${SEVERITY_BG[severity]}`}>
      <div className="text-xs uppercase tracking-wider opacity-80">
        {SEVERITY_LABEL[severity]} severity
      </div>
      <div className="text-3xl font-semibold mt-1">{count}</div>
    </div>
  );
}

function PersonCard({
  person,
  orgName,
  orgUrl,
}: {
  person: { fullName: string; role: string };
  orgName: string;
  orgUrl?: string;
}) {
  return (
    <div className="rounded bg-black/20 border border-white/5 p-3">
      <div className="font-medium">{person.fullName}</div>
      <div className="text-xs text-[var(--muted)] mt-0.5">
        {person.role || "—"}
      </div>
      <div className="text-xs mt-2">
        {orgUrl ? (
          <a className="underline" href={orgUrl} target="_blank" rel="noreferrer">
            {orgName}
          </a>
        ) : (
          orgName
        )}
      </div>
    </div>
  );
}
