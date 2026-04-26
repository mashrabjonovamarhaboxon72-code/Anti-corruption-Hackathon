import { writeStore } from "../lib/storage";
import type { Organization, Person } from "../lib/matcher";

// Demonstrates each conflict kind:
//  - Karimov Akmal Bakhtiyorovich on Bank A, Karimov Akmal Bakhtiyorovich on Insurance B  -> SAME PERSON
//  - Yusupov Bakhtiyor Sobirovich on Bank A; Yusupov Akmal Bakhtiyorovich on Telecom C    -> PARENT/CHILD
//  - Rakhimova Dilnoza Akmalovna on Bank A; Rakhimov Sherzod Akmalovich on Refinery D     -> SIBLINGS (same surname + same patronymic root)
//  - Tashkentov Aziz on Bank A; Tashkentov Jamshid on Insurance B                         -> SHARED SURNAME ONLY

const organizations: Organization[] = [
  { id: "org_bank_a",       name: "Bank A — Joint-Stock Bank",            ticker: "BANKA", industry: "Banking",   url: "https://openinfo.uz/" },
  { id: "org_insurance_b",  name: "Insurance B — Insurance JSC",          ticker: "INSB",  industry: "Insurance", url: "https://openinfo.uz/" },
  { id: "org_telecom_c",    name: "Telecom C — Communications JSC",       ticker: "TELC",  industry: "Telecom",   url: "https://openinfo.uz/" },
  { id: "org_refinery_d",   name: "Refinery D — Petrochemical JSC",       ticker: "REFD",  industry: "Energy",    url: "https://openinfo.uz/" },
];

const people: Person[] = [
  // Bank A management
  { id: "p1",  fullName: "Karimov Akmal Bakhtiyorovich",     role: "Chairman",                 organizationId: "org_bank_a" },
  { id: "p2",  fullName: "Yusupov Bakhtiyor Sobirovich",     role: "Member, Supervisory Board",organizationId: "org_bank_a" },
  { id: "p3",  fullName: "Rakhimova Dilnoza Akmalovna",      role: "CFO",                      organizationId: "org_bank_a" },
  { id: "p4",  fullName: "Tashkentov Aziz Rustamovich",      role: "Independent Director",     organizationId: "org_bank_a" },
  { id: "p5",  fullName: "Mirzayev Bobur Olimovich",         role: "Member, Supervisory Board",organizationId: "org_bank_a" },

  // Insurance B management
  { id: "p6",  fullName: "Karimov Akmal Bakhtiyorovich",     role: "Member, Supervisory Board",organizationId: "org_insurance_b" }, // SAME PERSON as p1
  { id: "p7",  fullName: "Tashkentov Jamshid Anvarovich",    role: "CEO",                      organizationId: "org_insurance_b" }, // shared surname with p4
  { id: "p8",  fullName: "Saidova Zulfiya Karimovna",        role: "CFO",                      organizationId: "org_insurance_b" },

  // Telecom C management
  { id: "p9",  fullName: "Yusupov Akmal Bakhtiyorovich",     role: "Chairman",                 organizationId: "org_telecom_c" }, // p2's son (patronymic = p2's first name) -- but different surname; classifier requires same surname so will NOT flag
  { id: "p10", fullName: "Yusupov Sherzod Bakhtiyorovich",   role: "CEO",                      organizationId: "org_telecom_c" }, // siblings with p9 (same surname + patronymic)
  { id: "p11", fullName: "Karimova Madina Akmalovna",        role: "Member, Supervisory Board",organizationId: "org_telecom_c" }, // PARENT/CHILD with p1 (Karimov Akmal -> Karimova Madina Akmalovna)
  { id: "p12", fullName: "Olimov Rustam Karimovich",         role: "Independent Director",     organizationId: "org_telecom_c" },

  // Refinery D management
  { id: "p13", fullName: "Rakhimov Sherzod Akmalovich",      role: "Chairman",                 organizationId: "org_refinery_d" }, // SIBLING with p3
  { id: "p14", fullName: "Mirzayeva Nodira Boburovna",       role: "Member, Supervisory Board",organizationId: "org_refinery_d" }, // PARENT/CHILD with p5 (Mirzayev Bobur -> Mirzayeva ... Boburovna)
  { id: "p15", fullName: "Olimov Sardor Yusufovich",         role: "CFO",                      organizationId: "org_refinery_d" },
  { id: "p16", fullName: "Abdullayev Timur Aliyevich",       role: "Independent Director",     organizationId: "org_refinery_d" },
];

writeStore({
  organizations,
  people,
  scrapedAt: new Date().toISOString(),
});

console.log(`Seeded ${organizations.length} orgs, ${people.length} people.`);
