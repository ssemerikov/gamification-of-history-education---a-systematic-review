#!/usr/bin/env python3
"""
Comprehensive claim verification script for the systematic review.
Cross-references all claims in paper.tex against study JSON data.

Produces:
  - data/aggregated/study_claims_catalog.json
  - data/aggregated/aggregate_stats_verified.json
  - data/aggregated/verification_report.txt
"""

import json
import re
import os
from pathlib import Path
from collections import Counter, defaultdict
from statistics import median, mean

BASE = Path(__file__).resolve().parent.parent
EXTRACTIONS_DIR = BASE / "data" / "extractions"
OUTPUT_DIR = BASE / "data" / "aggregated"
PAPER_PATH = BASE / "review_draft" / "paper.tex"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_all_studies():
    studies = []
    for f in sorted(EXTRACTIONS_DIR.glob("study_*.json"), key=lambda x: int(x.stem.split("_")[1])):
        with open(f) as fh:
            studies.append(json.load(fh))
    return studies


def get_eligible(studies):
    return [s for s in studies if s.get("eligibility", {}).get("meets_criteria", True)]


def load_paper():
    with open(PAPER_PATH) as f:
        return f.read()


def compute_aggregate_stats(eligible):
    """Compute all aggregate statistics from JSON data."""
    stats = {}
    n_total = len(eligible)
    stats["n_eligible"] = n_total

    # Sample sizes
    samples = []
    no_sample = 0
    for s in eligible:
        n = s.get("study_characteristics", {}).get("sample_size")
        if n is not None:
            samples.append(n)
        else:
            no_sample += 1

    samples_sorted = sorted(samples)
    stats["n_reporting_sample"] = len(samples)
    stats["n_not_reporting_sample"] = no_sample
    stats["pct_reporting_sample"] = round(100 * len(samples) / n_total, 1)
    stats["sample_min"] = min(samples_sorted) if samples_sorted else None
    stats["sample_max"] = max(samples_sorted) if samples_sorted else None
    stats["sample_median"] = median(samples_sorted) if samples_sorted else None
    stats["sample_mean"] = round(mean(samples_sorted), 1) if samples_sorted else None

    # Sample size bins
    below_30 = sum(1 for x in samples_sorted if x < 30)
    below_50 = sum(1 for x in samples_sorted if x < 50)
    range_30_99 = sum(1 for x in samples_sorted if 30 <= x <= 99)
    range_100_499 = sum(1 for x in samples_sorted if 100 <= x <= 499)
    above_500 = sum(1 for x in samples_sorted if x >= 500)
    above_100 = sum(1 for x in samples_sorted if x > 100)

    stats["n_below_30"] = below_30
    stats["pct_below_30_of_reporting"] = round(100 * below_30 / len(samples), 1) if samples else 0
    stats["n_below_50"] = below_50
    stats["pct_below_50_of_reporting"] = round(100 * below_50 / len(samples), 1) if samples else 0
    stats["pct_below_50_of_all"] = round(100 * below_50 / n_total, 1)
    stats["n_30_99"] = range_30_99
    stats["n_100_499"] = range_100_499
    stats["n_above_500"] = above_500
    stats["n_above_100"] = above_100
    stats["pct_above_100_of_reporting"] = round(100 * above_100 / len(samples), 1) if samples else 0

    # Risk of bias
    rob_counts = Counter()
    for s in eligible:
        rob_counts[s.get("risk_of_bias", {}).get("overall", "Unknown")] += 1
    stats["rob_high"] = rob_counts.get("High", 0)
    stats["rob_moderate"] = rob_counts.get("Moderate", 0)
    stats["rob_low"] = rob_counts.get("Low", 0)
    stats["rob_unclear"] = rob_counts.get("Unclear", 0)
    stats["pct_rob_high"] = round(100 * stats["rob_high"] / n_total, 1)
    stats["pct_rob_moderate"] = round(100 * stats["rob_moderate"] / n_total, 1)
    stats["pct_rob_low"] = round(100 * stats["rob_low"] / n_total, 1)
    stats["pct_rob_unclear"] = round(100 * stats["rob_unclear"] / n_total, 1)

    # Definitions
    has_def = sum(1 for s in eligible if s.get("rq1", {}).get("has_explicit_definition"))
    stats["n_has_definition"] = has_def
    stats["n_no_definition"] = n_total - has_def
    stats["pct_has_definition"] = round(100 * has_def / n_total, 1)
    stats["pct_no_definition"] = round(100 * (n_total - has_def) / n_total, 1)

    # Countries
    country_counter = Counter()
    for s in eligible:
        for c in s.get("study_characteristics", {}).get("countries", []):
            country_counter[c] += 1
    stats["n_countries"] = len(country_counter)
    stats["country_distribution"] = dict(country_counter.most_common())

    # Education levels
    edu_counter = Counter()
    for s in eligible:
        level = s.get("study_characteristics", {}).get("education_level", "not_specified")
        edu_counter[level] += 1
    stats["education_levels"] = dict(edu_counter.most_common())

    # Publication types
    pub_counter = Counter()
    for s in eligible:
        pub_type = s.get("bibliographic", {}).get("publication_type", "unknown")
        pub_counter[pub_type] += 1
    stats["publication_types"] = dict(pub_counter.most_common())

    # Study designs
    design_counter = Counter()
    for s in eligible:
        design = s.get("study_characteristics", {}).get("study_design", "unknown")
        design_counter[design] += 1
    stats["study_designs"] = dict(design_counter.most_common())

    # Game types
    game_counter = Counter()
    for s in eligible:
        gt = s.get("study_characteristics", {}).get("game_type", "unknown")
        game_counter[gt] += 1
    stats["game_types"] = dict(game_counter.most_common())

    # Control groups (from comparative_methodology)
    has_control = 0
    no_control = 0
    control_studies = []
    for s in eligible:
        cm = s.get("rq2", {}).get("comparative_methodology") or ""
        if any(term in cm.lower() for term in [
            "control group", "comparison group", "control class", "control condition",
            "experimental group", "two groups", "experimental and control", "randomized",
            "comparison class", "control school", "between-group", "two classes"
        ]):
            has_control += 1
            control_studies.append(s["study_id"])
        else:
            no_control += 1
    stats["n_with_control_group"] = has_control
    stats["n_without_control_group"] = no_control
    stats["pct_with_control_group"] = round(100 * has_control / n_total, 1)
    stats["control_group_study_ids"] = control_studies

    # Year distribution
    year_counter = Counter()
    for s in eligible:
        y = s.get("bibliographic", {}).get("year")
        if y:
            year_counter[y] += 1
    stats["year_distribution"] = dict(sorted(year_counter.items()))

    # Theoretical frameworks (RQ1)
    framework_counter = Counter()
    for s in eligible:
        for fw in s.get("rq1", {}).get("theoretical_frameworks", []):
            framework_counter[fw] += 1
    stats["theoretical_frameworks"] = dict(framework_counter.most_common(30))

    # Game design elements (RQ3)
    gde_counter = Counter()
    for s in eligible:
        for el in s.get("rq3", {}).get("game_design_elements", []):
            gde_counter[el] += 1
    stats["game_design_elements_raw_count"] = len(gde_counter)

    # Implementation barriers (RQ4)
    barrier_counter = Counter()
    for s in eligible:
        for b in s.get("rq4", {}).get("implementation_barriers", []):
            barrier_counter[b] += 1
    stats["implementation_barriers_raw_count"] = len(barrier_counter)

    # Negative effects (RQ4)
    neg_counter = Counter()
    studies_with_neg = 0
    for s in eligible:
        negs = s.get("rq4", {}).get("negative_effects", [])
        if negs:
            studies_with_neg += 1
        for ne in negs:
            neg_counter[ne] += 1
    stats["studies_with_negative_effects"] = studies_with_neg
    stats["negative_effects_raw_count"] = len(neg_counter)

    return stats


def build_study_claims_catalog(eligible):
    """Build a per-study catalog of citable claims."""
    catalog = []
    for s in eligible:
        entry = {
            "study_id": s["study_id"],
            "bibtex_key": s.get("bibtex_key", ""),
            "title": s.get("bibliographic", {}).get("title", ""),
            "year": s.get("bibliographic", {}).get("year"),
            "sample_size": s.get("study_characteristics", {}).get("sample_size"),
            "study_design": s.get("study_characteristics", {}).get("study_design"),
            "education_level": s.get("study_characteristics", {}).get("education_level"),
            "has_explicit_definition": s.get("rq1", {}).get("has_explicit_definition", False),
            "explicit_definition": s.get("rq1", {}).get("explicit_definition"),
            "statistical_results": s.get("rq2", {}).get("statistical_results"),
            "key_outcomes": s.get("rq2", {}).get("key_outcomes"),
            "engagement_results": s.get("rq2", {}).get("engagement_results"),
            "comparative_methodology": s.get("rq2", {}).get("comparative_methodology"),
            "overall_rob": s.get("risk_of_bias", {}).get("overall"),
            "countries": s.get("study_characteristics", {}).get("countries", []),
            "game_type": s.get("study_characteristics", {}).get("game_type"),
            "n_design_elements": len(s.get("rq3", {}).get("game_design_elements", [])),
            "n_barriers": len(s.get("rq4", {}).get("implementation_barriers", [])),
            "n_negative_effects": len(s.get("rq4", {}).get("negative_effects", [])),
        }
        catalog.append(entry)
    return catalog


def extract_paper_citations(paper_text):
    """Extract all \citet{key} and \cite{key} references from paper text."""
    # Match \citet{key} and \cite{key1, key2, ...}
    citet_pattern = re.compile(r'\\citet\{([^}]+)\}')
    cite_pattern = re.compile(r'\\cite(?:\[[^\]]*\])?\{([^}]+)\}')

    citations = defaultdict(list)
    lines = paper_text.split('\n')
    for i, line in enumerate(lines, 1):
        for m in citet_pattern.finditer(line):
            key = m.group(1).strip()
            citations[key].append({"line": i, "context": line.strip()[:200]})
        for m in cite_pattern.finditer(line):
            keys = [k.strip() for k in m.group(1).split(',')]
            for key in keys:
                if key and not key.startswith('%'):
                    citations[key].append({"line": i, "context": line.strip()[:200]})

    return dict(citations)


def verify_paper_claims(paper_text, stats, eligible):
    """Check specific claims in the paper against verified data."""
    issues = []
    lines = paper_text.split('\n')

    # Build bibtex_key -> study lookup
    key_to_study = {}
    for s in eligible:
        key_to_study[s.get("bibtex_key", "")] = s

    # E1: "47 studies (63.5%) below 50 participants"
    for i, line in enumerate(lines, 1):
        if "47 studies" in line and "63.5" in line:
            issues.append({
                "id": "E1",
                "line": i,
                "claim": "47 studies (63.5%) below 50 participants",
                "verified": f"{stats['n_below_50']} studies ({stats['pct_below_50_of_reporting']}% of {stats['n_reporting_sample']} reporting; {stats['pct_below_50_of_all']}% of {stats['n_eligible']})",
                "severity": "ERROR",
                "status": "NEEDS_FIX"
            })

    # E2: "14 studies (22.6%) > 100 participants"
    for i, line in enumerate(lines, 1):
        if "14 studies" in line and "22.6" in line:
            issues.append({
                "id": "E2",
                "line": i,
                "claim": "14 studies (22.6%) > 100 participants",
                "verified": f"{stats['n_above_100']} studies ({stats['pct_above_100_of_reporting']}%)",
                "severity": "ERROR",
                "status": "NEEDS_FIX"
            })

    # E3: Median sample size
    for i, line in enumerate(lines, 1):
        if "median" in line.lower() and "sample" in line.lower():
            if "34" in line and "33.5" not in line:
                issues.append({
                    "id": "E3",
                    "line": i,
                    "claim": "Median sample size 34",
                    "verified": f"Actual median: {stats['sample_median']} — use 'approximately 34' or report 33.5",
                    "severity": "MINOR",
                    "status": "NEEDS_FIX"
                })

    # E4: "44.4% provided no explicit definition"
    for i, line in enumerate(lines, 1):
        if "44.4" in line and ("definition" in line.lower() or "defined" in line.lower()):
            issues.append({
                "id": "E4",
                "line": i,
                "claim": "44.4% provided no explicit definition",
                "verified": f"{stats['pct_no_definition']}% ({stats['n_no_definition']}/{stats['n_eligible']}) — 44.4% has no basis in data",
                "severity": "CRITICAL",
                "status": "NEEDS_FIX"
            })

    # E5: Study 77 "dramatic gain from 31.33 to 88.50"
    for i, line in enumerate(lines, 1):
        if "31.33" in line or "88.50" in line:
            issues.append({
                "id": "E5",
                "line": i,
                "claim": "Ramansyah2021's dramatic gain from 31.33 to 88.50",
                "verified": "FABRICATED — Study 77 is a design-based R&D study with expert validation scores (84-91%), no pre-post learning test",
                "severity": "CRITICAL",
                "status": "NEEDS_FIX"
            })

    # E6: Orphaned sentence "acknowledged challenges with student refusal"
    for i, line in enumerate(lines, 1):
        if "acknowledged challenges with student refusal" in line:
            issues.append({
                "id": "E6",
                "line": i,
                "claim": "Fragment: 'acknowledged challenges with student refusal...'",
                "verified": "Orphaned sentence fragment from removed \\citet{68cole2015end}",
                "severity": "ERROR",
                "status": "NEEDS_FIX"
            })

    # E7: "n=19, 23.4% employed no comparative methodologies"
    for i, line in enumerate(lines, 1):
        if "23.4" in line and "comparative" in line.lower():
            issues.append({
                "id": "E7",
                "line": i,
                "claim": "n=19, 23.4% employed no comparative methodologies",
                "verified": "Needs recount — actual number of studies without comparative methodology is likely different",
                "severity": "ERROR",
                "status": "NEEDS_RECOUNT"
            })

    # Check for "63.5%" with n<50 in abstract
    for i, line in enumerate(lines, 1):
        if "63.5" in line and "n<50" in line.replace(" ", "").replace("\\", "").replace("$", ""):
            issues.append({
                "id": "E9",
                "line": i,
                "claim": "Abstract: 63.5% with n<50",
                "verified": f"Should be {stats['pct_below_50_of_reporting']}% of reporting ({stats['pct_below_50_of_all']}% of all)",
                "severity": "ERROR",
                "status": "NEEDS_FIX"
            })

    return issues


def count_no_comparative_methodology(eligible):
    """Count studies with no comparative methodology."""
    no_comp = 0
    no_comp_studies = []
    for s in eligible:
        cm = s.get("rq2", {}).get("comparative_methodology") or ""
        if not cm.strip() or "no comparative" in cm.lower() or "no control" in cm.lower() or cm.lower().startswith("none"):
            no_comp += 1
            no_comp_studies.append(s["study_id"])
    return no_comp, no_comp_studies


def generate_report(stats, issues, eligible, catalog, paper_citations):
    """Generate a comprehensive verification report."""
    lines = []
    lines.append("=" * 70)
    lines.append("SYSTEMATIC REVIEW CLAIM VERIFICATION REPORT")
    lines.append("=" * 70)
    lines.append("")

    # Aggregate stats
    lines.append("VERIFIED AGGREGATE STATISTICS")
    lines.append("-" * 40)
    lines.append(f"Total eligible studies: {stats['n_eligible']}")
    lines.append(f"Year range: {min(stats['year_distribution'])}–{max(stats['year_distribution'])}")
    lines.append(f"Countries: {stats['n_countries']}")
    lines.append(f"Sample sizes reported: {stats['n_reporting_sample']}/{stats['n_eligible']} ({stats['pct_reporting_sample']}%)")
    lines.append(f"Median sample size: {stats['sample_median']}")
    lines.append(f"Mean sample size: {stats['sample_mean']}")
    lines.append(f"Sample range: {stats['sample_min']}–{stats['sample_max']}")
    lines.append(f"Below 30: {stats['n_below_30']} ({stats['pct_below_30_of_reporting']}% of reporting)")
    lines.append(f"Below 50: {stats['n_below_50']} ({stats['pct_below_50_of_reporting']}% of reporting, {stats['pct_below_50_of_all']}% of all)")
    lines.append(f"30–99: {stats['n_30_99']}")
    lines.append(f"100–499: {stats['n_100_499']}")
    lines.append(f">=500: {stats['n_above_500']}")
    lines.append(f">100: {stats['n_above_100']} ({stats['pct_above_100_of_reporting']}% of reporting)")
    lines.append(f"Not reporting: {stats['n_not_reporting_sample']}")
    lines.append("")
    lines.append(f"Has explicit definition: {stats['n_has_definition']}/{stats['n_eligible']} ({stats['pct_has_definition']}%)")
    lines.append(f"No explicit definition: {stats['n_no_definition']}/{stats['n_eligible']} ({stats['pct_no_definition']}%)")
    lines.append("")
    lines.append(f"Risk of bias - High: {stats['rob_high']} ({stats['pct_rob_high']}%)")
    lines.append(f"Risk of bias - Moderate: {stats['rob_moderate']} ({stats['pct_rob_moderate']}%)")
    lines.append(f"Risk of bias - Low: {stats['rob_low']} ({stats['pct_rob_low']}%)")
    lines.append(f"Risk of bias - Unclear: {stats['rob_unclear']} ({stats['pct_rob_unclear']}%)")
    lines.append("")
    lines.append(f"With control/comparison groups: {stats['n_with_control_group']} ({stats['pct_with_control_group']}%)")
    lines.append(f"Control group study IDs: {stats['control_group_study_ids']}")
    lines.append("")

    # No comparative methodology
    no_comp, no_comp_ids = count_no_comparative_methodology(eligible)
    lines.append(f"No comparative methodology: {no_comp}/{stats['n_eligible']} ({round(100*no_comp/stats['n_eligible'], 1)}%)")
    lines.append(f"  Study IDs: {no_comp_ids}")
    lines.append("")

    # Publication types
    lines.append("Publication types:")
    for pt, count in stats["publication_types"].items():
        lines.append(f"  {pt}: {count}")
    lines.append("")

    # Study designs
    lines.append("Study designs:")
    for sd, count in stats["study_designs"].items():
        lines.append(f"  {sd}: {count}")
    lines.append("")

    # Education levels
    lines.append("Education levels:")
    for el, count in stats["education_levels"].items():
        lines.append(f"  {el}: {count}")
    lines.append("")

    # Issues found
    lines.append("")
    lines.append("ISSUES FOUND IN PAPER")
    lines.append("-" * 40)
    critical = [i for i in issues if i["severity"] == "CRITICAL"]
    errors = [i for i in issues if i["severity"] == "ERROR"]
    minor = [i for i in issues if i["severity"] == "MINOR"]

    lines.append(f"Critical: {len(critical)}")
    lines.append(f"Errors: {len(errors)}")
    lines.append(f"Minor: {len(minor)}")
    lines.append("")

    for issue in issues:
        lines.append(f"[{issue['severity']}] {issue['id']} (line {issue['line']}):")
        lines.append(f"  Paper claims: {issue['claim']}")
        lines.append(f"  Verified: {issue['verified']}")
        lines.append(f"  Status: {issue['status']}")
        lines.append("")

    # Citation coverage
    lines.append("")
    lines.append("CITATION COVERAGE")
    lines.append("-" * 40)
    study_keys = {s.get("bibtex_key") for s in eligible if s.get("bibtex_key")}
    cited_keys = set(paper_citations.keys())
    # Filter to only study keys (numbered prefix)
    study_cited = cited_keys & study_keys
    study_not_cited = study_keys - cited_keys
    lines.append(f"Study keys in JSON: {len(study_keys)}")
    lines.append(f"Study keys cited in paper: {len(study_cited)}")
    lines.append(f"Study keys NOT cited: {len(study_not_cited)}")
    if study_not_cited:
        for k in sorted(study_not_cited):
            # Find the study
            for s in eligible:
                if s.get("bibtex_key") == k:
                    lines.append(f"  {k} (Study {s['study_id']}): {s['bibliographic']['title'][:60]}")
                    break
    lines.append("")

    return "\n".join(lines)


def main():
    print("Loading studies...")
    studies = load_all_studies()
    eligible = get_eligible(studies)
    print(f"Loaded {len(studies)} studies, {len(eligible)} eligible")

    print("Loading paper...")
    paper_text = load_paper()

    print("Computing aggregate statistics...")
    stats = compute_aggregate_stats(eligible)

    print("Building study claims catalog...")
    catalog = build_study_claims_catalog(eligible)

    print("Extracting paper citations...")
    paper_citations = extract_paper_citations(paper_text)

    print("Verifying paper claims...")
    issues = verify_paper_claims(paper_text, stats, eligible)

    print("Generating report...")
    report = generate_report(stats, issues, eligible, catalog, paper_citations)

    # Write outputs
    with open(OUTPUT_DIR / "study_claims_catalog.json", "w") as f:
        json.dump(catalog, f, indent=2)

    with open(OUTPUT_DIR / "aggregate_stats_verified.json", "w") as f:
        json.dump(stats, f, indent=2, default=str)

    with open(OUTPUT_DIR / "verification_report.txt", "w") as f:
        f.write(report)

    print(report)
    print(f"\nOutputs written to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
