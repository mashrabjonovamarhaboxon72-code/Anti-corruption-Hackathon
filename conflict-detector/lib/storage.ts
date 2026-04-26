import fs from "node:fs";
import path from "node:path";
import type { Organization, Person } from "./matcher";

export interface Store {
  organizations: Organization[];
  people: Person[];
  scrapedAt: string | null;
}

const DATA_FILE = process.env.DATA_FILE
  ? path.resolve(process.cwd(), process.env.DATA_FILE)
  : path.resolve(process.cwd(), "data/store.json");

export function ensureDir(p: string) {
  const dir = path.dirname(p);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

export function readStore(): Store {
  if (!fs.existsSync(DATA_FILE)) {
    return { organizations: [], people: [], scrapedAt: null };
  }
  try {
    return JSON.parse(fs.readFileSync(DATA_FILE, "utf8"));
  } catch {
    return { organizations: [], people: [], scrapedAt: null };
  }
}

export function writeStore(store: Store): void {
  ensureDir(DATA_FILE);
  fs.writeFileSync(DATA_FILE, JSON.stringify(store, null, 2), "utf8");
}

export function dataFilePath(): string {
  return DATA_FILE;
}
