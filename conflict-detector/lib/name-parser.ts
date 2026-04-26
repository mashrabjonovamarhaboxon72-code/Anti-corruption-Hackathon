// Parse Uzbek/Russian-style names like "Karimov Akmal Bakhtiyorovich"
// or "Yusupova Dilnoza Akmalovna" or "Akmal Karimov o'g'li".
// Returns { surname, firstName, patronymicRoot, gender? } where patronymicRoot
// is the father's first name with the suffix stripped.

const PATRONYMIC_SUFFIXES: { suffix: string; gender: "m" | "f" }[] = [
  { suffix: "ovich", gender: "m" },
  { suffix: "evich", gender: "m" },
  { suffix: "ovna", gender: "f" },
  { suffix: "evna", gender: "f" },
  { suffix: "o'g'li", gender: "m" },
  { suffix: "o`g`li", gender: "m" },
  { suffix: "ogli", gender: "m" },
  { suffix: "ugli", gender: "m" },
  { suffix: "qizi", gender: "f" },
  { suffix: "kizi", gender: "f" },
];

export interface ParsedName {
  raw: string;
  surname: string;
  firstName: string;
  patronymicRoot: string | null;
  gender: "m" | "f" | null;
}

export function normalize(token: string): string {
  // Lowercase, strip punctuation, collapse apostrophe variants.
  return token
    .toLowerCase()
    .replace(/[`’ʻʼ]/g, "'")
    .replace(/[.,]/g, "")
    .trim();
}

function stripPatronymic(token: string): { root: string; gender: "m" | "f" } | null {
  const t = normalize(token);
  for (const { suffix, gender } of PATRONYMIC_SUFFIXES) {
    if (t.endsWith(suffix) && t.length > suffix.length + 1) {
      return { root: t.slice(0, -suffix.length).replace(/[-_]+$/, ""), gender };
    }
  }
  return null;
}

// Heuristic: surnames in Cyrillic/Slavic style end with -ov/-ev/-ova/-eva/-skiy/-skaya.
// Uzbek surnames are similar after transliteration. We use this to distinguish
// "Surname FirstName Patronymic" vs "FirstName Surname".
function looksLikeSurname(token: string): boolean {
  const t = normalize(token);
  return /(?:ov|ev|ova|eva|skiy|skaya|skij|sky|in|ina|yan|yev|yeva)$/.test(t);
}

export function parseName(raw: string): ParsedName {
  const cleaned = raw.replace(/\s+/g, " ").trim();
  const tokens = cleaned.split(" ").filter(Boolean);

  let surname = "";
  let firstName = "";
  let patronymicRoot: string | null = null;
  let gender: "m" | "f" | null = null;

  // Find the patronymic token (anywhere in the name).
  let patIdx = -1;
  for (let i = 0; i < tokens.length; i++) {
    const stripped = stripPatronymic(tokens[i]);
    if (stripped) {
      patronymicRoot = stripped.root;
      gender = stripped.gender;
      patIdx = i;
      break;
    }
  }

  // "o'g'li" / "qizi" sometimes appears as a separate trailing token: "Akmal Bakhtiyor o'g'li"
  if (patIdx === -1 && tokens.length >= 2) {
    const last = normalize(tokens[tokens.length - 1]);
    if (last === "o'g'li" || last === "qizi" || last === "ogli" || last === "kizi" || last === "ugli") {
      patronymicRoot = normalize(tokens[tokens.length - 2]);
      gender = last === "qizi" || last === "kizi" ? "f" : "m";
      // Drop the two trailing tokens for surname/firstName extraction.
      tokens.splice(tokens.length - 2, 2);
    }
  } else if (patIdx !== -1) {
    tokens.splice(patIdx, 1); // remove patronymic token, keep the other tokens
  }

  if (tokens.length === 0) {
    return { raw, surname: "", firstName: "", patronymicRoot, gender };
  }
  if (tokens.length === 1) {
    return { raw, surname: normalize(tokens[0]), firstName: "", patronymicRoot, gender };
  }

  // Two tokens left: figure out which is the surname.
  const [a, b] = [tokens[0], tokens[1]];
  if (looksLikeSurname(a) && !looksLikeSurname(b)) {
    surname = normalize(a);
    firstName = normalize(b);
  } else if (looksLikeSurname(b) && !looksLikeSurname(a)) {
    firstName = normalize(a);
    surname = normalize(b);
  } else {
    // Default to the openinfo.uz convention: Surname FirstName.
    surname = normalize(a);
    firstName = normalize(b);
  }

  return { raw, surname, firstName, patronymicRoot, gender };
}
