import PptxGenJS from "pptxgenjs";
import path from "node:path";
import fs from "node:fs";

// Hackathon presentation in Uzbek (Latin alphabet).
// 8 slides — problem framing, solution, algorithm, demo results, tech stack.

const pptx = new PptxGenJS();
pptx.layout = "LAYOUT_WIDE"; // 13.333 x 7.5 inches
pptx.title = "Manfaatlar to'qnashuvini aniqlash tizimi";
pptx.author = "Anti-corruption Hackathon";

const COLORS = {
  bg: "0B1020",
  panel: "121830",
  border: "1F2747",
  text: "E6E9F4",
  muted: "8C93B3",
  accent: "6EA8FE",
  high: "EF4444",
  medium: "F59E0B",
  low: "38BDF8",
};

function addBackground(slide: PptxGenJS.Slide) {
  slide.background = { color: COLORS.bg };
}

function addFooter(slide: PptxGenJS.Slide, n: number, total: number) {
  slide.addText(`openinfo.uz · Manfaatlar to'qnashuvi`, {
    x: 0.4, y: 7.05, w: 8, h: 0.3, fontSize: 10, color: COLORS.muted, fontFace: "Calibri",
  });
  slide.addText(`${n} / ${total}`, {
    x: 12.4, y: 7.05, w: 0.6, h: 0.3, fontSize: 10, color: COLORS.muted, align: "right", fontFace: "Calibri",
  });
}

function addTitle(slide: PptxGenJS.Slide, title: string) {
  slide.addText(title, {
    x: 0.6, y: 0.5, w: 12.1, h: 0.9,
    fontSize: 32, bold: true, color: COLORS.text, fontFace: "Calibri",
  });
  // Accent bar
  slide.addShape(pptx.ShapeType.rect, {
    x: 0.6, y: 1.4, w: 0.6, h: 0.08, fill: { color: COLORS.accent }, line: { color: COLORS.accent, width: 0 },
  });
}

const TOTAL = 8;

// ------------------------------------------------------------ SLIDE 1 — title
{
  const s = pptx.addSlide();
  addBackground(s);

  s.addShape(pptx.ShapeType.rect, {
    x: 0, y: 0, w: 13.333, h: 7.5, fill: { color: COLORS.bg }, line: { color: COLORS.bg, width: 0 },
  });

  s.addText("MANFAATLAR\nTO'QNASHUVINI\nANIQLASH TIZIMI", {
    x: 0.8, y: 1.6, w: 11.5, h: 3.2,
    fontSize: 56, bold: true, color: COLORS.text, fontFace: "Calibri", lineSpacingMultiple: 1.0,
  });

  s.addShape(pptx.ShapeType.rect, {
    x: 0.8, y: 4.7, w: 1.5, h: 0.08, fill: { color: COLORS.accent }, line: { color: COLORS.accent, width: 0 },
  });

  s.addText("openinfo.uz ma'lumotlari asosida\nyashirin kelishuvlar va aile aloqalarini avtomatik aniqlash", {
    x: 0.8, y: 4.95, w: 11.5, h: 1.2,
    fontSize: 22, color: COLORS.muted, fontFace: "Calibri",
  });

  s.addText("Anti-corruption Hackathon · 2026", {
    x: 0.8, y: 6.6, w: 11.5, h: 0.5,
    fontSize: 14, color: COLORS.accent, fontFace: "Calibri", bold: true,
  });
}

// ------------------------------------------------------------ SLIDE 2 — muammo
{
  const s = pptx.addSlide();
  addBackground(s);
  addTitle(s, "Muammo: yashirin manfaatlar to'qnashuvi");

  const bullets = [
    "O'zbekistonda yuzlab aksiyadorlik jamiyatlari mavjud — bank, sug'urta, telekom, energetika.",
    "Bir shaxs bir vaqtning o'zida bir nechta raqobatchi yoki bog'liq tashkilotlarda rahbar yoki kuzatuv kengashi a'zosi bo'lishi mumkin.",
    "Bu yashirin kelishuvlar, ichki ma'lumotlardan foydalanish va korrupsiya uchun qulay muhit yaratadi.",
    "Aile aloqalari (ota-bola, aka-uka) ham xuddi shunday xavfli — qarindoshlar orqali ta'sir o'tkaziladi.",
    "Hozirda bunday holatlarni qo'lda tekshirish deyarli imkonsiz: kichkina jamoa minglab juftliklarni solishtira olmaydi.",
  ];

  s.addText(bullets.map((t) => ({ text: t, options: { bullet: { code: "25CF" }, paraSpaceAfter: 10 } })), {
    x: 0.8, y: 1.9, w: 11.7, h: 4.6,
    fontSize: 20, color: COLORS.text, fontFace: "Calibri", lineSpacingMultiple: 1.25,
  });

  addFooter(s, 2, TOTAL);
}

// ------------------------------------------------------------ SLIDE 3 — nima uchun muhim
{
  const s = pptx.addSlide();
  addBackground(s);
  addTitle(s, "Nima uchun bu muhim?");

  // Three stat cards
  const cards: { num: string; label: string; color: string }[] = [
    { num: "600+",    label: "openinfo.uz da ro'yxatdan o'tgan emitentlar",         color: COLORS.accent },
    { num: "10 000+", label: "rahbar va kuzatuv kengashi a'zolari",                 color: COLORS.medium },
    { num: "≈ 50 mln", label: "tekshirilishi kerak bo'lgan juftliklar (qo'lda imkonsiz)", color: COLORS.high },
  ];

  cards.forEach((c, i) => {
    const x = 0.8 + i * 4.05;
    s.addShape(pptx.ShapeType.roundRect, {
      x, y: 1.9, w: 3.85, h: 2.3,
      fill: { color: COLORS.panel }, line: { color: COLORS.border, width: 1 },
      rectRadius: 0.12,
    });
    s.addText(c.num, {
      x, y: 2.05, w: 3.85, h: 1.1, fontSize: 44, bold: true, color: c.color, fontFace: "Calibri", align: "center",
    });
    s.addText(c.label, {
      x: x + 0.2, y: 3.15, w: 3.45, h: 1.0, fontSize: 14, color: COLORS.text, fontFace: "Calibri", align: "center",
    });
  });

  s.addText([
    { text: "Ma'lumotlar OCHIQ — ", options: { bold: true, color: COLORS.text } },
    { text: "lekin tarqoq holatda. Inson hech qachon ularni to'liq solishtira olmaydi.", options: { color: COLORS.text } },
  ], {
    x: 0.8, y: 4.6, w: 11.7, h: 0.7, fontSize: 20, fontFace: "Calibri",
  });

  s.addText(
    "Aynan o'zbekcha ismlarning tuzilishi (familiya + ism + otasining ismi) qarindoshlikni topish uchun juda qulay imkoniyat beradi — uni avtomatlashtirish kerak.",
    { x: 0.8, y: 5.4, w: 11.7, h: 1.4, fontSize: 18, color: COLORS.muted, fontFace: "Calibri", italic: true },
  );

  addFooter(s, 3, TOTAL);
}

// ------------------------------------------------------------ SLIDE 4 — yechim
{
  const s = pptx.addSlide();
  addBackground(s);
  addTitle(s, "Bizning yechimimiz");

  const steps = [
    { n: "1", title: "Yig'ish",      text: "openinfo.uz saytidan har bir kompaniyaning rahbariyat va kuzatuv kengashi ma'lumotlarini avtomatik yuklab olish (scraper)." },
    { n: "2", title: "Tahlil qilish", text: "Har bir ismni komponentlarga ajratish: familiya, ism, otasining ismining ildizi (-ovich/-qizi qo'shimchalari olib tashlanadi)." },
    { n: "3", title: "Solishtirish", text: "Turli kompaniyalardagi har bir juftlikni 4 turdagi mezon bo'yicha tekshirish." },
    { n: "4", title: "Ogohlantirish", text: "Shubhali holatlarni dashboard'da xavfsizlik darajasi bo'yicha (HIGH / MEDIUM / LOW) ko'rsatish." },
  ];

  steps.forEach((st, i) => {
    const y = 1.9 + i * 1.15;
    // Number circle
    s.addShape(pptx.ShapeType.ellipse, {
      x: 0.8, y, w: 0.8, h: 0.8,
      fill: { color: COLORS.accent }, line: { color: COLORS.accent, width: 0 },
    });
    s.addText(st.n, {
      x: 0.8, y, w: 0.8, h: 0.8, fontSize: 28, bold: true, color: COLORS.bg, align: "center", valign: "middle", fontFace: "Calibri",
    });
    s.addText(st.title, {
      x: 1.9, y: y - 0.05, w: 4, h: 0.5, fontSize: 22, bold: true, color: COLORS.text, fontFace: "Calibri",
    });
    s.addText(st.text, {
      x: 1.9, y: y + 0.4, w: 10.7, h: 0.7, fontSize: 16, color: COLORS.muted, fontFace: "Calibri",
    });
  });

  addFooter(s, 4, TOTAL);
}

// ------------------------------------------------------------ SLIDE 5 — algoritm
{
  const s = pptx.addSlide();
  addBackground(s);
  addTitle(s, "Algoritm: o'zbekcha ismlarni qanday tushunamiz?");

  // Code-like example block
  s.addShape(pptx.ShapeType.roundRect, {
    x: 0.8, y: 1.9, w: 11.7, h: 1.6,
    fill: { color: COLORS.panel }, line: { color: COLORS.border, width: 1 }, rectRadius: 0.1,
  });
  s.addText([
    { text: "Misol:  ", options: { color: COLORS.muted, fontSize: 16 } },
    { text: "Karimova Madina Akmalovna", options: { bold: true, color: COLORS.text, fontSize: 22 } },
  ], { x: 1.0, y: 2.05, w: 11.3, h: 0.5, fontFace: "Consolas" });

  s.addText([
    { text: "→ familiya ildizi: ", options: { color: COLORS.muted, fontSize: 16 } },
    { text: "karimov", options: { bold: true, color: COLORS.accent, fontSize: 18 } },
    { text: "    ·    ism: ", options: { color: COLORS.muted, fontSize: 16 } },
    { text: "madina", options: { bold: true, color: COLORS.accent, fontSize: 18 } },
    { text: "    ·    otasining ismi: ", options: { color: COLORS.muted, fontSize: 16 } },
    { text: "akmal", options: { bold: true, color: COLORS.accent, fontSize: 18 } },
  ], { x: 1.0, y: 2.65, w: 11.3, h: 0.6, fontFace: "Consolas" });

  s.addText("Shu uch belgi orqali har qanday juftlikni tezda solishtirib, qarindoshlikni aniqlash mumkin.", {
    x: 1.0, y: 3.2, w: 11.3, h: 0.4, fontSize: 14, color: COLORS.muted, italic: true, fontFace: "Calibri",
  });

  // Three rules
  const rules: { title: string; rule: string }[] = [
    { title: "Familiyaning gender bo'yicha o'zgarishi",   rule: "Karimov ↔ Karimova   (oxirgi -a olib tashlanadi)" },
    { title: "Otasining ismi (patronim) ildizi",            rule: "Bakhtiyorovich → bakhtiyor   ·   Akmalovna → akmal" },
    { title: "Qo'shimchalarni tanib olish",                 rule: "-ovich, -ovna, -evich, -evna, -o'g'li, -qizi, -ugli, -kizi" },
  ];

  rules.forEach((r, i) => {
    const y = 4.0 + i * 0.95;
    s.addShape(pptx.ShapeType.rect, {
      x: 0.8, y, w: 0.1, h: 0.7, fill: { color: COLORS.accent }, line: { color: COLORS.accent, width: 0 },
    });
    s.addText(r.title, {
      x: 1.05, y, w: 11.5, h: 0.35, fontSize: 18, bold: true, color: COLORS.text, fontFace: "Calibri",
    });
    s.addText(r.rule, {
      x: 1.05, y: y + 0.35, w: 11.5, h: 0.35, fontSize: 14, color: COLORS.muted, fontFace: "Consolas",
    });
  });

  addFooter(s, 5, TOTAL);
}

// ------------------------------------------------------------ SLIDE 6 — conflict turlari
{
  const s = pptx.addSlide();
  addBackground(s);
  addTitle(s, "Aniqlanadigan to'rt turdagi shubha");

  const kinds: { sev: string; sevColor: string; title: string; desc: string; example: string }[] = [
    {
      sev: "HIGH", sevColor: COLORS.high,
      title: "Bir xil shaxs ikki kengashda",
      desc: "Aynan o'sha ism-familiya ikki turli kompaniyada — eng kuchli xavf signali.",
      example: "Karimov Akmal Bakhtiyorovich → Bank A va Sug'urta B",
    },
    {
      sev: "HIGH", sevColor: COLORS.high,
      title: "Ota va farzand",
      desc: "Bir kishining ismi ikkinchisining patronim ildizi bilan mos keladi, familiya bir.",
      example: "Karimov Akmal → Karimova Madina Akmalovna",
    },
    {
      sev: "MEDIUM", sevColor: COLORS.medium,
      title: "Aka-uka / opa-singil",
      desc: "Familiya ham, otasining ismi ham bir xil — demak, otasi bitta.",
      example: "Rakhimova Dilnoza Akmalovna ↔ Rakhimov Sherzod Akmalovich",
    },
    {
      sev: "LOW", sevColor: COLORS.low,
      title: "Faqat familiya bir xil",
      desc: "Qarindosh bo'lishi mumkin, lekin tasodif ham bo'lishi mumkin — qo'shimcha tekshiruv talab qilinadi.",
      example: "Tashkentov Aziz ↔ Tashkentov Jamshid",
    },
  ];

  kinds.forEach((k, i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = 0.8 + col * 6.05;
    const y = 1.9 + row * 2.4;

    s.addShape(pptx.ShapeType.roundRect, {
      x, y, w: 5.85, h: 2.2,
      fill: { color: COLORS.panel }, line: { color: COLORS.border, width: 1 }, rectRadius: 0.1,
    });
    // Severity pill
    s.addShape(pptx.ShapeType.roundRect, {
      x: x + 0.25, y: y + 0.2, w: 1.1, h: 0.4,
      fill: { color: k.sevColor }, line: { color: k.sevColor, width: 0 }, rectRadius: 0.05,
    });
    s.addText(k.sev, {
      x: x + 0.25, y: y + 0.2, w: 1.0, h: 0.4, fontSize: 11, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: "Calibri",
    });
    s.addText(k.title, {
      x: x + 1.4, y: y + 0.18, w: 4.3, h: 0.45, fontSize: 18, bold: true, color: COLORS.text, fontFace: "Calibri",
    });
    s.addText(k.desc, {
      x: x + 0.25, y: y + 0.7, w: 5.4, h: 0.7, fontSize: 13, color: COLORS.text, fontFace: "Calibri",
    });
    s.addText(k.example, {
      x: x + 0.25, y: y + 1.5, w: 5.4, h: 0.5, fontSize: 12, color: COLORS.accent, fontFace: "Consolas", italic: true,
    });
  });

  addFooter(s, 6, TOTAL);
}

// ------------------------------------------------------------ SLIDE 7 — demo natija
{
  const s = pptx.addSlide();
  addBackground(s);
  addTitle(s, "Demo natijalari (sinov ma'lumotlarida)");

  // Top row: 3 stat cards
  const stats: { num: string; label: string }[] = [
    { num: "4",  label: "kompaniya" },
    { num: "16", label: "rahbar / kengash a'zosi" },
    { num: "9",  label: "shubhali juftlik aniqlandi" },
  ];
  stats.forEach((st, i) => {
    const x = 0.8 + i * 4.05;
    s.addShape(pptx.ShapeType.roundRect, {
      x, y: 1.9, w: 3.85, h: 1.4, fill: { color: COLORS.panel }, line: { color: COLORS.border, width: 1 }, rectRadius: 0.1,
    });
    s.addText(st.num, { x, y: 1.95, w: 3.85, h: 0.8, fontSize: 38, bold: true, color: COLORS.accent, align: "center", fontFace: "Calibri" });
    s.addText(st.label, { x, y: 2.7, w: 3.85, h: 0.5, fontSize: 14, color: COLORS.muted, align: "center", fontFace: "Calibri" });
  });

  // Severity breakdown
  const sev: { count: string; sev: string; color: string }[] = [
    { count: "6", sev: "YUQORI",  color: COLORS.high   },
    { count: "1", sev: "O'RTA",   color: COLORS.medium },
    { count: "2", sev: "PAST",    color: COLORS.low    },
  ];
  sev.forEach((sv, i) => {
    const x = 0.8 + i * 4.05;
    s.addShape(pptx.ShapeType.roundRect, {
      x, y: 3.5, w: 3.85, h: 1.3, fill: { color: sv.color, transparency: 80 }, line: { color: sv.color, width: 1 }, rectRadius: 0.1,
    });
    s.addText(sv.count, { x: x + 0.2, y: 3.6, w: 1.0, h: 1.1, fontSize: 38, bold: true, color: sv.color, align: "center", valign: "middle", fontFace: "Calibri" });
    s.addText(`${sv.sev}\ndarajadagi shubha`, { x: x + 1.3, y: 3.7, w: 2.4, h: 0.9, fontSize: 14, color: COLORS.text, valign: "middle", fontFace: "Calibri" });
  });

  // Example findings
  s.addText("Topilgan eng yorqin holatlar:", {
    x: 0.8, y: 5.0, w: 11.7, h: 0.4, fontSize: 16, bold: true, color: COLORS.text, fontFace: "Calibri",
  });

  const findings = [
    "Karimov Akmal Bakhtiyorovich — bir vaqtda Bank A raisi va Sug'urta B kengashi a'zosi (HIGH).",
    "Karimov Akmal → Karimova Madina Akmalovna (Telekom C) — ota-bola aloqasi (HIGH).",
    "Rakhimova Dilnoza ↔ Rakhimov Sherzod — Bank A va Neftgaz D'da aka-singil (MEDIUM).",
  ];
  s.addText(findings.map((t) => ({ text: t, options: { bullet: { code: "25CF" }, paraSpaceAfter: 6 } })), {
    x: 0.8, y: 5.45, w: 11.7, h: 1.5, fontSize: 14, color: COLORS.text, fontFace: "Calibri",
  });

  addFooter(s, 7, TOTAL);
}

// ------------------------------------------------------------ SLIDE 8 — texnologiya va kelajak
{
  const s = pptx.addSlide();
  addBackground(s);
  addTitle(s, "Texnologiya va keyingi qadamlar");

  // Tech stack column
  s.addText("Texnologiyalar", {
    x: 0.8, y: 1.9, w: 5.8, h: 0.5, fontSize: 20, bold: true, color: COLORS.accent, fontFace: "Calibri",
  });
  const tech = [
    "Next.js 15 — frontend va backend bitta loyihada",
    "TypeScript — kod xavfsiz va o'qish oson",
    "Cheerio — openinfo.uz HTML sahifalarini o'qish",
    "Tailwind CSS — toza, javob beradigan dizayn",
    "JSON ombor — server kerak emas, tezkor ishga tushiradi",
  ];
  s.addText(tech.map((t) => ({ text: t, options: { bullet: { code: "25CF" }, paraSpaceAfter: 6 } })), {
    x: 0.8, y: 2.45, w: 5.8, h: 3.2, fontSize: 14, color: COLORS.text, fontFace: "Calibri",
  });

  // Future column
  s.addText("Keyingi qadamlar", {
    x: 7.0, y: 1.9, w: 5.8, h: 0.5, fontSize: 20, bold: true, color: COLORS.medium, fontFace: "Calibri",
  });
  const future = [
    "Barcha 600+ emitentlarni qamrab olish",
    "Real vaqtda yangilanish va e-mail ogohlantirishlar",
    "Fuzzy matching (transliteratsiya, harf xatolari)",
    "Davlat reyestri bilan integratsiya — qarindoshlik bazasi",
    "Tekshiruvchilar uchun eksport (CSV, PDF hisobotlar)",
  ];
  s.addText(future.map((t) => ({ text: t, options: { bullet: { code: "25CF" }, paraSpaceAfter: 6 } })), {
    x: 7.0, y: 2.45, w: 5.8, h: 3.2, fontSize: 14, color: COLORS.text, fontFace: "Calibri",
  });

  // Closing line
  s.addShape(pptx.ShapeType.roundRect, {
    x: 0.8, y: 5.9, w: 11.7, h: 1.0,
    fill: { color: COLORS.accent, transparency: 85 }, line: { color: COLORS.accent, width: 1 }, rectRadius: 0.1,
  });
  s.addText("Ochiq ma'lumot + avtomatik tahlil = shaffof iqtisodiyot uchun real qadam.", {
    x: 0.8, y: 5.9, w: 11.7, h: 1.0, fontSize: 18, bold: true, italic: true, color: COLORS.text, align: "center", valign: "middle", fontFace: "Calibri",
  });

  addFooter(s, 8, TOTAL);
}

// ----------------------------------------------------------------- save file
const outDir = path.resolve(process.cwd(), "slides");
if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });
const outPath = path.join(outDir, "Manfaatlar-toqnashuvi.pptx");

pptx.writeFile({ fileName: outPath }).then((f) => {
  console.log(`Slides saved: ${f}`);
});
