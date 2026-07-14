"""
synonyms.py
===========
Comprehensive synonym and query expansion module for the USCIS RAG system.

Two primary functions:
1. expand_query()     — normalize/expand user queries before retrieval
2. tag_sections()     — analyze corpus coverage by topic using synonym matching

Synonym categories cover:
- F-1 student status and terminology
- Employment during F-1 (CPT, OPT, STEM OPT, EAD)
- H-1B petition and lottery terminology
- F-1 → H-1B transition path
- Green card / immigrant visa terms
- USCIS forms and their common names
- Intent-based user language → legal concepts
"""

import re
import pandas as pd
from typing import Optional

# ── Synonym Registry ───────────────────────────────────────────────────────────
# Structure:
#   "CANONICAL_TERM": {
#       "corpus_terms":  terms USCIS uses in the policy manual
#       "user_terms":    informal terms users type in queries
#       "forms":         related form numbers
#       "abbreviations": common abbreviations
#   }
#
# expand_query() uses all four lists to normalize user input.
# tag_sections() uses corpus_terms to find relevant sections in the DataFrame.

SYNONYM_REGISTRY = {

    # ── F-1 Student Status ─────────────────────────────────────────────────────

    "F-1 Student": {
        "corpus_terms": [
            "F-1 student", "F-1 nonimmigrant", "nonimmigrant student",
            "F-1 status", "student status", "F-1 visa",
        ],
        "user_terms": [
            "international student", "student visa holder", "F1 visa",
            "F1 student", "foreign student", "visa student",
        ],
        "forms": ["I-20", "Form I-20"],
        "abbreviations": ["F-1", "F1"],
    },

    "Designated School Official": {
        "corpus_terms": [
            "Designated School Official", "DSO", "principal designated school official",
            "PDSO", "school official",
        ],
        "user_terms": [
            "international student advisor", "school immigration officer",
            "international student office", "ISO", "ISSS",
        ],
        "forms": [],
        "abbreviations": ["DSO", "PDSO"],
    },

    "SEVIS": {
        "corpus_terms": [
            "SEVIS", "Student and Exchange Visitor Information System",
            "SEVIS record", "SEVIS ID", "SEVIS fee",
        ],
        "user_terms": [
            "student database", "student record system", "student tracking system",
            "immigration student record",
        ],
        "forms": ["I-901"],
        "abbreviations": ["SEVIS"],
    },

    "Form I-20": {
        "corpus_terms": [
            "Form I-20", "I-20", "Certificate of Eligibility for Nonimmigrant Student Status",
            "certificate of eligibility",
        ],
        "user_terms": [
            "student immigration form", "school form", "I20",
            "student eligibility form",
        ],
        "forms": ["I-20"],
        "abbreviations": ["I-20"],
    },

    "Full Course of Study": {
        "corpus_terms": [
            "full course of study", "full-time enrollment", "full-time student",
            "minimum course load", "reduced course load",
        ],
        "user_terms": [
            "full time classes", "full time school", "required credits",
            "minimum classes",
        ],
        "forms": [],
        "abbreviations": ["RCL"],
    },

    "Duration of Status": {
        "corpus_terms": [
            "duration of status", "D/S", "authorized period of admission",
        ],
        "user_terms": [
            "how long can I stay", "visa length", "status duration",
            "length of stay",
        ],
        "forms": [],
        "abbreviations": ["D/S"],
    },

    "Reinstatement": {
        "corpus_terms": [
            "reinstatement", "reinstate F-1 status", "out of status",
            "failure to maintain status", "status violation",
        ],
        "user_terms": [
            "regain status", "restore F-1 status", "fix visa status",
            "lost my status", "out of status fix",
        ],
        "forms": ["I-539"],
        "abbreviations": [],
    },

    "Grace Period": {
        "corpus_terms": [
            "grace period", "60-day grace period", "30-day grace period",
            "authorized grace period",
        ],
        "user_terms": [
            "time after graduation", "days after program ends",
            "how long after school", "after graduation stay",
        ],
        "forms": [],
        "abbreviations": [],
    },

    # ── Employment During F-1 ──────────────────────────────────────────────────

    "On-Campus Employment": {
        "corpus_terms": [
            "on-campus employment", "on-campus work", "on-campus job",
            "employment on campus",
        ],
        "user_terms": [
            "campus job", "work on campus", "student worker",
            "university job", "college job",
        ],
        "forms": [],
        "abbreviations": [],
    },

    "Curricular Practical Training": {
        "corpus_terms": [
            "Curricular Practical Training", "CPT", "cooperative education",
            "work-study program", "alternating employment",
        ],
        "user_terms": [
            "internship authorization", "CPT internship", "school internship",
            "authorized internship", "co-op program", "can I intern",
            "first semester internship", "Day-1 CPT", "immediate CPT",
        ],
        "forms": ["I-20"],
        "abbreviations": ["CPT"],
    },

    "Optional Practical Training": {
        "corpus_terms": [
            "Optional Practical Training", "OPT", "practical training",
            "pre-completion OPT", "post-completion OPT",
            "OPT employment authorization", "OPT period",
        ],
        "user_terms": [
            "work authorization after school", "work after graduation",
            "work permit after degree", "OPT during school",
            "OPT after graduation", "can I work after graduation",
            "how long can I work after school",
        ],
        "forms": ["I-765", "I-20"],
        "abbreviations": ["OPT"],
    },

    "STEM OPT Extension": {
        "corpus_terms": [
            "STEM OPT extension", "STEM OPT", "24-month extension",
            "science technology engineering mathematics",
            "STEM degree", "e-verify employer",
        ],
        "user_terms": [
            "STEM extension", "extend OPT", "extra OPT time",
            "2 year OPT extension", "extend work permit",
            "OPT renewal",
        ],
        "forms": ["I-765", "I-983"],
        "abbreviations": ["STEM OPT"],
    },

    "Employment Authorization Document": {
        "corpus_terms": [
            "Employment Authorization Document", "EAD", "Form I-766",
            "employment authorization card", "employment authorization",
        ],
        "user_terms": [
            "work permit", "EAD card", "employment card",
            "work authorization card", "legal work permission",
            "can I get a work permit",
        ],
        "forms": ["I-765", "I-766"],
        "abbreviations": ["EAD"],
    },

    "OPT Unemployment": {
        "corpus_terms": [
            "unemployment days", "90-day unemployment limit",
            "150-day unemployment limit", "unemployment clock",
            "periods of unemployment",
        ],
        "user_terms": [
            "OPT unemployment clock", "days without job on OPT",
            "OPT job requirement", "must have job on OPT",
            "how long without work on OPT",
        ],
        "forms": [],
        "abbreviations": [],
    },

    "Cap-Gap": {
        "corpus_terms": [
            "cap-gap", "cap gap extension", "automatic extension",
            "cap-gap relief", "bridging F-1 and H-1B",
        ],
        "user_terms": [
            "extend OPT while waiting for H1B", "bridge F1 to H1B",
            "keep working after OPT ends", "gap between OPT and H1B",
            "automatic OPT extension H1B",
        ],
        "forms": [],
        "abbreviations": [],
    },

    # ── H-1B Petition ──────────────────────────────────────────────────────────

    "H-1B Specialty Occupation": {
        "corpus_terms": [
            "H-1B", "specialty occupation", "H-1B nonimmigrant",
            "H-1B status", "H-1B classification",
            "theoretical and practical application",
            "attainment of a bachelor's degree",
        ],
        "user_terms": [
            "H1B visa", "H1-B", "skilled worker visa",
            "professional work visa", "work visa",
            "employer sponsored visa", "H1B status",
        ],
        "forms": ["I-129"],
        "abbreviations": ["H-1B", "H1B"],
    },

    "H-1B Petition": {
        "corpus_terms": [
            "H-1B petition", "Petition for a Nonimmigrant Worker",
            "H-1B filing", "petitioner", "beneficiary",
            "sponsoring employer", "employer sponsor",
        ],
        "user_terms": [
            "H1B application", "H1B filing", "employer H1B",
            "company sponsor H1B", "does my employer file H1B",
            "how does employer file H1B",
        ],
        "forms": ["I-129"],
        "abbreviations": [],
    },

    "H-1B Lottery": {
        "corpus_terms": [
            "H-1B cap", "numerical limitation", "random selection",
            "cap-subject", "65,000", "20,000",
            "advanced degree exemption", "master's cap",
            "regular cap", "H-1B registration",
        ],
        "user_terms": [
            "H1B lottery", "H1B annual limit", "H1B annual quota",
            "picked in lottery", "not selected lottery",
            "lottery rejection", "H1B random selection",
            "H1B cap exempt", "cap exempt H1B",
        ],
        "forms": [],
        "abbreviations": [],
    },

    "Labor Condition Application": {
        "corpus_terms": [
            "Labor Condition Application", "LCA", "ETA-9035",
            "prevailing wage", "Department of Labor",
            "wage level", "area of intended employment",
        ],
        "user_terms": [
            "H1B wage requirement", "minimum H1B wage",
            "labor certification for H1B", "DOL H1B",
            "required wage H1B",
        ],
        "forms": ["ETA-9035"],
        "abbreviations": ["LCA"],
    },

    "H-1B Portability": {
        "corpus_terms": [
            "H-1B portability", "change employer", "new employer",
            "H-1B transfer", "AC21", "American Competitiveness in the 21st Century",
        ],
        "user_terms": [
            "change jobs on H1B", "switch employer H1B",
            "can I change companies H1B", "H1B job transfer",
            "new job H1B",
        ],
        "forms": ["I-129"],
        "abbreviations": ["AC21"],
    },

    "H-1B Extension": {
        "corpus_terms": [
            "extension of stay", "H-1B extension", "extend H-1B status",
            "H-1B amendment", "material change",
        ],
        "user_terms": [
            "H1B renewal", "renew H1B", "H1B extension filing",
            "extend H1B", "H1B amendment filing",
        ],
        "forms": ["I-129"],
        "abbreviations": [],
    },

    # ── F-1 → H-1B Transition ──────────────────────────────────────────────────

    "Change of Status": {
        "corpus_terms": [
            "change of status", "change nonimmigrant status",
            "Form I-539", "change of nonimmigrant classification",
            "nonimmigrant status change",
        ],
        "user_terms": [
            "switch from F1 to H1B", "F1 to H1B",
            "change visa type", "move from F1 to H1B",
            "convert F1 to H1B", "COS", "status conversion",
            "switch visa",
        ],
        "forms": ["I-129", "I-539"],
        "abbreviations": ["COS"],
    },

    "Consular Processing": {
        "corpus_terms": [
            "consular processing", "consular notification",
            "visa stamp", "visa stamping", "embassy processing",
            "consulate", "nonimmigrant visa application",
        ],
        "user_terms": [
            "H1B visa stamp", "get H1B visa abroad",
            "embassy H1B interview", "visa stamping route",
            "H1B outside US",
        ],
        "forms": ["DS-160"],
        "abbreviations": [],
    },

    "Dual Intent": {
        "corpus_terms": [
            "dual intent", "immigrant intent", "nonimmigrant intent",
            "preconceived intent",
        ],
        "user_terms": [
            "can I apply for green card on H1B",
            "H1B and green card at same time",
            "immigrant intent F1",
        ],
        "forms": [],
        "abbreviations": [],
    },

    # ── Green Card / Immigrant Visa ────────────────────────────────────────────

    "PERM Labor Certification": {
        "corpus_terms": [
            "PERM", "Program Electronic Review Management",
            "labor certification", "ETA-9089",
            "Department of Labor certification",
        ],
        "user_terms": [
            "green card labor certification", "PERM process",
            "employer green card sponsorship first step",
        ],
        "forms": ["ETA-9089"],
        "abbreviations": ["PERM"],
    },

    "Immigrant Petition": {
        "corpus_terms": [
            "Immigrant Petition for Alien Workers", "I-140",
            "employment-based immigrant petition",
            "priority date", "visa bulletin",
        ],
        "user_terms": [
            "employer green card petition", "I-140 filing",
            "green card waiting line", "priority date check",
        ],
        "forms": ["I-140"],
        "abbreviations": ["EB-1", "EB-2", "EB-3"],
    },

    "Adjustment of Status": {
        "corpus_terms": [
            "adjustment of status", "adjust status",
            "lawful permanent resident", "permanent residence",
            "Form I-485",
        ],
        "user_terms": [
            "green card application", "apply for green card",
            "AOS", "get green card inside US",
            "permanent resident application",
        ],
        "forms": ["I-485"],
        "abbreviations": ["AOS", "LPR"],
    },

    # ── Common Forms ───────────────────────────────────────────────────────────

    "Form I-765": {
        "corpus_terms": ["Form I-765", "I-765", "Application for Employment Authorization"],
        "user_terms": ["work permit application", "EAD application", "apply for work permit"],
        "forms": ["I-765"],
        "abbreviations": [],
    },

    "Form I-129": {
        "corpus_terms": ["Form I-129", "I-129", "Petition for Nonimmigrant Worker"],
        "user_terms": ["H1B petition form", "H1B application form", "employer H1B form"],
        "forms": ["I-129"],
        "abbreviations": [],
    },

    "Form I-94": {
        "corpus_terms": ["Form I-94", "I-94", "arrival/departure record", "admission record"],
        "user_terms": ["arrival record", "entry record", "immigration arrival form"],
        "forms": ["I-94"],
        "abbreviations": [],
    },
}


# ── Relevance Scoring ─────────────────────────────────────────────────────────

IRRELEVANT_TOPICS = [
    "J-1", "J-2", "J exchange visitor",
    "B-1", "B-2", "tourist visa", "visitor visa",
    "asylum", "refugee", "asylee",
    "T visa", "T nonimmigrant", "trafficking victim",
    "U visa", "crime victim",
    "adoption", "EB-5", "investor visa",
    "military", "armed forces",
    "religious worker", "R-1",
]

RELEVANT_TOPICS = [
    "F-1", "H-1B", "OPT", "CPT", "STEM OPT",
    "EAD", "change of status", "cap-gap",
    "employment authorization", "practical training",
    "nonimmigrant student", "specialty occupation",
]


def is_relevant_chunk(text: str) -> bool:
    """
    Returns False if the chunk is dominated by off-scope visa category content.
    Blocks only when irrelevant terms appear AND outnumber relevant terms 3:1.
    """
    text_lower = text.lower()
    irrelevant_score = sum(text_lower.count(t.lower()) for t in IRRELEVANT_TOPICS)
    relevant_score   = sum(text_lower.count(t.lower()) for t in RELEVANT_TOPICS)
    return not (irrelevant_score > 0 and irrelevant_score > relevant_score * 3)


# ── Query Expansion ────────────────────────────────────────────────────────────

def _build_query_expansion_map() -> dict[str, str]:
    """
    Build a flat regex → replacement map from the synonym registry
    for use in expand_query().

    Maps all user_terms and abbreviations to their corpus_terms equivalent
    so user queries are normalized to match USCIS language before retrieval.
    """
    expansion_map = {}
    for canonical, data in SYNONYM_REGISTRY.items():
        # Get the primary corpus term (first in list)
        primary_corpus_term = data["corpus_terms"][0] if data["corpus_terms"] else canonical

        # Map abbreviations to primary corpus term
        for abbr in data["abbreviations"]:
            # Word boundary match, case insensitive
            pattern = rf'\b{re.escape(abbr)}\b'
            if pattern not in expansion_map:
                expansion_map[pattern] = primary_corpus_term

        # Map user terms to primary corpus term
        for user_term in data["user_terms"]:
            pattern = rf'\b{re.escape(user_term)}\b'
            if pattern not in expansion_map:
                expansion_map[pattern] = primary_corpus_term

    return expansion_map


# Build once at import time
_EXPANSION_MAP = _build_query_expansion_map()


def expand_query(query: str, verbose: bool = True) -> str:
    """
    Normalize and expand a user query to match USCIS corpus terminology.

    Handles:
    - Abbreviation normalization (H1B → H-1B, F1 → F-1)
    - User language → legal language (work permit → Employment Authorization Document)
    - Intent-based expansion (switch from F1 to H1B → change of status)

    Args:
        query:   Raw user query string
        verbose: If True, prints the expansion when a change is made

    Returns:
        Expanded query string with normalized/enriched terminology
    """
    expanded = query
    for pattern, replacement in _EXPANSION_MAP.items():
        expanded = re.sub(pattern, replacement, expanded, flags=re.IGNORECASE)

    if verbose and expanded != query:
        print(f"  📝 Query expanded:")
        print(f"     Original: '{query}'")
        print(f"     Expanded: '{expanded}'")

    return expanded


# ── Corpus Tagging / Coverage Analysis ────────────────────────────────────────

def tag_sections(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tag each section in the DataFrame with relevant topic categories
    based on synonym matching against the corpus_terms in the registry.

    Adds a 'topics' column containing a list of matched canonical terms,
    useful for coverage analysis and filtering by topic.

    Args:
        df: DataFrame with a 'text' column from parse_sections()

    Returns:
        DataFrame with an added 'topics' column
    """
    print("Tagging sections with topic categories ...")

    def match_topics(text: str) -> list[str]:
        if not isinstance(text, str) or not text.strip():
            return []
        matched = []
        text_lower = text.lower()
        for canonical, data in SYNONYM_REGISTRY.items():
            all_terms = data["corpus_terms"] + data["abbreviations"] + data["forms"]
            for term in all_terms:
                if term.lower() in text_lower:
                    matched.append(canonical)
                    break  # One match per category is enough
        return matched

    df = df.copy()
    df["topics"] = df["text"].apply(match_topics)
    df["topic_count"] = df["topics"].apply(len)

    print(f"✅ Tagging complete.")
    print(f"   Sections with at least 1 topic tag: {(df['topic_count'] > 0).sum():,}")
    print(f"   Sections with no topic tag:          {(df['topic_count'] == 0).sum():,}")
    return df


def print_coverage_report(df: pd.DataFrame) -> None:
    """
    Print a coverage report showing how many sections match each topic category.

    Helps identify gaps in corpus coverage before deployment — if a category
    has very few matching sections, the tool may struggle with those queries.

    Args:
        df: DataFrame with 'topics' column from tag_sections()
    """
    print("\n── Topic Coverage Report ────────────────────────────────────────")
    print(f"  {'Topic':<40} {'Sections':>8}  {'Relevance'}")
    print(f"  {'-'*40}  {'-'*8}  {'-'*20}")

    counts = {}
    for topics_list in df["topics"]:
        for topic in topics_list:
            counts[topic] = counts.get(topic, 0) + 1

    # Sort by section count descending
    for topic, count in sorted(counts.items(), key=lambda x: -x[1]):
        bar = "█" * min(20, count // 5)
        print(f"  {topic:<40} {count:>8}  {bar}")

    # Flag low-coverage topics
    print("\n── Low Coverage Warnings (< 10 sections) ───────────────────────")
    low = {t: c for t, c in counts.items() if c < 10}
    if low:
        for topic, count in sorted(low.items(), key=lambda x: x[1]):
            print(f"  ⚠️  {topic}: only {count} section(s)")
    else:
        print("  ✅ All topics have adequate coverage.")


def get_sections_by_topic(df: pd.DataFrame, topic: str) -> pd.DataFrame:
    """
    Filter the DataFrame to sections matching a specific topic.

    Args:
        df:    DataFrame with 'topics' column from tag_sections()
        topic: Canonical topic name from SYNONYM_REGISTRY

    Returns:
        Filtered DataFrame of matching sections
    """
    return df[df["topics"].apply(lambda topics: topic in topics)][
        ["title", "level", "token_count", "citation_url", "text"]
    ].reset_index(drop=True)


# ── Test query expansion ───────────────────────────────────────────────────────

if __name__ == "__main__":
    test_queries = [
        "Can a F1 student work off campus?",
        "What are H1B requirements?",
        "How do I apply for optional practical training?",
        "How do I switch from F1 to H1B?",
        "Can I get a work permit after graduation?",
        "What is the H1B lottery?",
        "Can I change jobs on H1B?",
        "How do I apply for a green card after H1B?",
        "What happens to my student visa after graduation?",
        "Can I do an internship in my first year?",
    ]

    print("── Query Expansion Tests ─────────────────────────────────────────\n")
    for q in test_queries:
        expand_query(q, verbose=True)
        print()
