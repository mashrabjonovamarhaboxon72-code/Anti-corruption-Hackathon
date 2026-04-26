/**
 * Tiny Python tokenizer for the WorkflowExplorer code overlays.
 *
 * Trade-off note: a real syntax highlighter (Prism, Shiki) would be
 * more accurate but adds 30–80 KB to the bundle. The snippets are short
 * enough that a regex-based tokenizer is correct in practice for the
 * patterns we use (function defs, strings, comments, decorators, basic
 * operators). When the snippets are no longer "ours" — i.e. arbitrary
 * user-supplied code — swap for Shiki.
 */

export type TokenType =
  | "comment"
  | "string"
  | "keyword"
  | "builtin"
  | "decorator"
  | "number"
  | "punct"
  | "operator"
  | "ident"
  | "whitespace";

export interface Token {
  type: TokenType;
  value: string;
}

const KEYWORDS = new Set([
  "def", "class", "return", "if", "else", "elif", "with", "from", "import",
  "raise", "try", "except", "for", "in", "while", "None", "True", "False",
  "async", "await", "yield", "pass", "lambda", "not", "and", "or", "is",
  "as", "global", "nonlocal", "finally", "break", "continue",
]);

const BUILTINS = new Set([
  "self", "cls", "len", "str", "int", "float", "list", "dict", "set",
  "tuple", "bool", "bytes", "isinstance", "hasattr", "getattr", "setattr",
  "range", "enumerate", "zip", "map", "filter", "print", "open", "type",
  "object", "min", "max", "sum", "round", "abs",
]);

const PATTERNS: { type: TokenType; re: RegExp }[] = [
  { type: "whitespace", re: /^\s+/ },
  { type: "comment", re: /^#[^\n]*/ },
  { type: "string", re: /^(?:f|r|b|rb|br)?"(?:[^"\\\n]|\\.)*"/i },
  { type: "string", re: /^(?:f|r|b|rb|br)?'(?:[^'\\\n]|\\.)*'/i },
  { type: "decorator", re: /^@[A-Za-z_][\w.]*/ },
  { type: "number", re: /^\b\d+(?:_\d+)*(?:\.\d+)?\b/ },
  { type: "ident", re: /^[A-Za-z_][\w]*/ }, // gets re-classified to keyword/builtin below
  { type: "punct", re: /^[(){}\[\],:;.]/ },
  { type: "operator", re: /^(?:->|<=|>=|==|!=|\*\*|\/\/|\+=|-=|\*=|\/=|%=|&&|\|\|)/ },
  { type: "operator", re: /^[+\-*/%<>=!&|^~]/ },
];

export function tokenizePython(source: string): Token[] {
  const out: Token[] = [];
  let i = 0;
  outer: while (i < source.length) {
    const slice = source.slice(i);
    for (const { type, re } of PATTERNS) {
      const m = re.exec(slice);
      if (m && m.index === 0) {
        let realType: TokenType = type;
        if (type === "ident") {
          if (KEYWORDS.has(m[0])) realType = "keyword";
          else if (BUILTINS.has(m[0])) realType = "builtin";
        }
        out.push({ type: realType, value: m[0] });
        i += m[0].length;
        continue outer;
      }
    }
    // Unrecognized character — emit as plain ident and advance one char so we
    // don't infinite-loop on edge-case input.
    out.push({ type: "ident", value: source[i] });
    i += 1;
  }
  return out;
}
