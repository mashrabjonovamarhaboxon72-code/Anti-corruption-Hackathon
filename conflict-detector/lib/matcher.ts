import { parseName, normalize, type ParsedName } from "./name-parser";

export type ConflictKind =
  | "same_person"        // exact full-name match across two orgs
  | "parent_child"       // person A's first name == person B's patronymic root + same surname
  | "siblings"           // same surname AND same patronymic root
  | "shared_surname";    // same surname only, different patronymic

export type Severity = "high" | "medium" | "low";

export interface Person {
  id: string;
  fullName: string;
  role: string;
  organizationId: string;
}

export interface Organization {
  id: string;
  name: string;
  ticker?: string;
  industry?: string;
  url?: string;
}

export interface Conflict {
  kind: ConflictKind;
  severity: Severity;
  reason: string;
  personA: Person;
  personB: Person;
  orgA: Organization;
  orgB: Organization;
}

const SEVERITY_BY_KIND: Record<ConflictKind, Severity> = {
  same_person: "high",
  parent_child: "high",
  siblings: "medium",
  shared_surname: "low",
};

// Common surnames in Uzbekistan that produce too many false positives
// when used alone — we still flag them, but at low severity.
const COMMON_SURNAMES = new Set([
  "karimov", "karimova", "yusupov", "yusupova", "rahimov", "rahimova",
  "kamilov", "kamilova", "akhmedov", "akhmedova", "tashkentov",
]);

// Strip the feminine -a suffix from -ova/-eva/-skaya/-ina/-yeva surnames so
// that "Karimov" and "Karimova" share the same family root. This is the
// Russian/Uzbek convention for gendered surnames.
function familyRoot(surname: string): string {
  const s = surname.toLowerCase();
  if (/(?:ova|eva|yeva)$/.test(s)) return s.slice(0, -1);          // Karimova -> Karimov
  if (/(?:skaya)$/.test(s)) return s.slice(0, -3) + "iy";          // Petrovskaya -> Petrovskiy
  if (/(?:ina)$/.test(s)) return s.slice(0, -1);                   // Nikitina -> Nikitin
  return s;
}

function classify(a: ParsedName, b: ParsedName): { kind: ConflictKind; reason: string } | null {
  const rootA = familyRoot(a.surname);
  const rootB = familyRoot(b.surname);
  const sameSurname = rootA && rootA === rootB;
  if (!sameSurname) {
    // Cross-surname can still flag a "parent-child" relation only when the
    // patronymic root matches the other person's first name. That is rare and
    // strong: it means person B's father is literally person A. But without
    // a shared surname it is a much weaker claim — we skip it to keep the
    // signal-to-noise ratio reasonable.
    return null;
  }

  // Strongest: full identity.
  if (
    a.firstName && a.firstName === b.firstName &&
    a.patronymicRoot && a.patronymicRoot === b.patronymicRoot
  ) {
    return {
      kind: "same_person",
      reason: `Same full name on both boards: ${a.surname} ${a.firstName} (patronymic: ${a.patronymicRoot}).`,
    };
  }

  // Parent-child: A's first name is B's patronymic root, or vice versa.
  if (a.firstName && b.patronymicRoot && a.firstName === b.patronymicRoot) {
    return {
      kind: "parent_child",
      reason: `${a.surname} ${a.firstName} appears to be the parent of ${b.surname} ${b.firstName} (patronymic "${b.patronymicRoot}" matches).`,
    };
  }
  if (b.firstName && a.patronymicRoot && b.firstName === a.patronymicRoot) {
    return {
      kind: "parent_child",
      reason: `${b.surname} ${b.firstName} appears to be the parent of ${a.surname} ${a.firstName} (patronymic "${a.patronymicRoot}" matches).`,
    };
  }

  // Siblings / close relatives: same surname + same patronymic root.
  if (a.patronymicRoot && b.patronymicRoot && a.patronymicRoot === b.patronymicRoot) {
    return {
      kind: "siblings",
      reason: `Same surname (${a.surname}) and same father's name (${a.patronymicRoot}) — likely siblings or close relatives.`,
    };
  }

  // Surname-only fallback (low signal, suppressed for very common surnames? we still flag).
  return {
    kind: "shared_surname",
    reason: `Same surname (${a.surname}) on both boards. Check whether they are related.`,
  };
}

export function detectConflicts(
  organizations: Organization[],
  people: Person[],
): Conflict[] {
  const orgById = new Map(organizations.map((o) => [o.id, o]));
  const parsed = people.map((p) => ({ person: p, parsed: parseName(p.fullName) }));

  const conflicts: Conflict[] = [];

  for (let i = 0; i < parsed.length; i++) {
    for (let j = i + 1; j < parsed.length; j++) {
      const A = parsed[i];
      const B = parsed[j];
      if (A.person.organizationId === B.person.organizationId) continue;

      const result = classify(A.parsed, B.parsed);
      if (!result) continue;

      let severity = SEVERITY_BY_KIND[result.kind];
      // Damp common-surname-only matches.
      if (result.kind === "shared_surname" && COMMON_SURNAMES.has(A.parsed.surname)) {
        severity = "low";
      }

      const orgA = orgById.get(A.person.organizationId);
      const orgB = orgById.get(B.person.organizationId);
      if (!orgA || !orgB) continue;

      conflicts.push({
        kind: result.kind,
        severity,
        reason: result.reason,
        personA: A.person,
        personB: B.person,
        orgA,
        orgB,
      });
    }
  }

  // Sort: severity desc, then kind, then surname.
  const order: Record<Severity, number> = { high: 0, medium: 1, low: 2 };
  conflicts.sort((x, y) => {
    if (order[x.severity] !== order[y.severity]) return order[x.severity] - order[y.severity];
    return x.personA.fullName.localeCompare(y.personA.fullName);
  });

  return conflicts;
}

export function summarize(conflicts: Conflict[]) {
  const counts = { high: 0, medium: 0, low: 0 };
  for (const c of conflicts) counts[c.severity]++;
  return counts;
}

// Re-export for convenience.
export { parseName, normalize };
