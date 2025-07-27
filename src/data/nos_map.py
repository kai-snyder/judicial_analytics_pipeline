# src/data/nos_map.py
# ------------------------------------------------------------------
#  Official “Nature-of-Suit” lookup table  (last synchronised: 2025-07-14)
#  ── Keys:   3-digit integer NOS codes
#  ── Values: human-readable titles (title-case, no trailing dashes)
# ------------------------------------------------------------------

NOS_MAP: dict[int, str] = {
    # ───────────────────── Contract (110-199) ─────────────────────
    110: "Insurance",
    120: "Marine",
    130: "Miller Act",
    140: "Negotiable Instrument",
    150: "Recovery of Overpayment & Enforcement of Judgment",
    151: "Medicare Act",
    152: "Recovery of Defaulted Student Loans (Excl. Veterans)",
    153: "Recovery of Overpayment of Veteran’s Benefits",
    160: "Stockholders’ Suits",
    190: "Other Contract",
    195: "Contract Product Liability",
    196: "Franchise",

    # ──────────────────── Real Property (210-299) ─────────────────
    210: "Land Condemnation",
    220: "Foreclosure",
    230: "Rent Lease & Ejectment",
    240: "Torts to Land",
    245: "Tort Product Liability",
    290: "All Other Real Property",

    # ──────────────── Torts – Personal Injury (310-369) ───────────
    310: "Airplane",
    315: "Airplane Product Liability",
    320: "Assault, Libel, & Slander",
    330: "Federal Employers’ Liability",
    340: "Marine",
    345: "Marine Product Liability",
    350: "Motor Vehicle",
    355: "Motor Vehicle Product Liability",
    360: "Other Personal Injury",
    362: "Personal Injury – Medical Malpractice",
    365: "Personal Injury – Product Liability",
    367: "Personal Injury – Health Care/Pharmaceutical Product Liability",
    368: "Asbestos Personal Injury Product Liability",
    375: "False Claims Act",

    # ─────────────── Torts – Personal Property (370-385) ──────────
    370: "Other Fraud",
    371: "Truth in Lending",
    380: "Other Personal Property Damage",
    385: "Property Damage Product Liability",

    # ───────────────────── Bankruptcy (422-423) ───────────────────
    422: "Appeal 28 USC 158",
    423: "Withdrawal 28 USC 157",

    # ───────────────────── Civil Rights (440-448) ─────────────────
    440: "Other Civil Rights",
    441: "Voting",
    442: "Employment",
    443: "Housing/Accommodations",
    444: "Welfare",
    445: "Americans with Disabilities – Employment",
    446: "Americans with Disabilities – Other",
    448: "Education",

    # ───────────────────── Immigration (462-465) ──────────────────
    462: "Naturalization Application",
    463: "Habeas Corpus – Alien Detainee",
    465: "Other Immigration Actions",

    # ──────────────── Prisoner Petitions (510-560) ────────────────
    510: "Motions to Vacate Sentence",
    530: "Habeas Corpus – General",
    535: "Habeas Corpus – Death Penalty",
    540: "Mandamus & Other",
    550: "Prisoner Civil Rights",
    555: "Prison Condition",
    560: "Civil Detainee – Conditions of Confinement",

    # ─────────────── Forfeiture / Penalty (610-690) ───────────────
    610: "Agriculture (eliminated)",
    620: "Other Food & Drug (eliminated)",
    625: "Drug-Related Seizure of Property 21 USC 881",
    630: "Liquor Laws (eliminated)",
    640: "Railroad & Truck (eliminated)",
    650: "Airline Regulations (eliminated)",
    660: "Occupational Safety/Health (eliminated)",
    690: "Other Forfeiture/Penalty",

    # ─────────────────────── Labor (710-799) ──────────────────────
    710: "Fair Labor Standards Act",
    720: "Labor/Management Relations",
    730: "Labor/Mgmt. Reporting & Disclosure Act (eliminated)",
    740: "Railway Labor Act",
    751: "Family and Medical Leave Act",
    790: "Other Labor Litigation",
    791: "Employee Retirement Income Security Act",

    # ─────────────────── Property Rights (820-840) ────────────────
    820: "Copyrights",
    830: "Patent",
    840: "Trademark",

    # ──────────────────── Social Security (861-865) ───────────────
    861: "HIA (1395ff)",
    862: "Black Lung (923)",
    863: "DIWC/DIWW (405(g))",
    864: "SSID Title XVI",
    865: "RSI (405(g))",

    # ─────────────────── Federal Tax Suits (870-871) ──────────────
    870: "Taxes (U.S. Plaintiff or Defendant)",
    871: "IRS Third-Party 26 USC 7609",

    # ──────────────────── Other Statutes (400-999) ────────────────
    400: "State Reapportionment",
    410: "Antitrust",
    430: "Banks & Banking",
    450: "Commerce",
    460: "Deportation",
    470: "RICO",
    480: "Consumer Credit",
    490: "Cable/Satellite TV",
    810: "Selective Service (eliminated)",
    850: "Securities/Commodities/Exchange",
    875: "Customer Challenge 12 USC 3410",
    890: "Other Statutory Actions",
    891: "Agricultural Acts",
    892: "Economic Stabilization Act (eliminated)",
    893: "Environmental Matters",
    894: "Energy Allocation Act (eliminated)",
    895: "Freedom of Information Act",
    896: "Arbitration",
    899: "Administrative Procedure Act / Review or Appeal of Agency Decision",
    900: "EAJA Fee Appeal (eliminated)",
    950: "Constitutionality of State Statutes",
}
