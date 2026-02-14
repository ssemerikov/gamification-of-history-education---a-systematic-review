#!/usr/bin/env python3
"""
Aggregate all study extraction JSONs into summary tables and master dataset.
Produces:
  - data/aggregated/all_studies.json (master dataset)
  - data/aggregated/characteristics_table.csv (PRISMA Item 17)
  - data/aggregated/risk_of_bias_table.csv (PRISMA Item 18)
  - data/aggregated/country_distribution.csv
  - data/aggregated/yearly_distribution.csv
  - data/aggregated/education_level_distribution.csv
  - data/aggregated/eligibility_summary.csv
  - data/aggregated/summary_stats.txt
"""

import json
import csv
import os
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
EXTRACTIONS_DIR = BASE / "data" / "extractions"
OUTPUT_DIR = BASE / "data" / "aggregated"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_all_studies():
    studies = []
    for f in sorted(EXTRACTIONS_DIR.glob("study_*.json")):
        with open(f) as fh:
            studies.append(json.load(fh))
    return studies


def write_master(studies):
    with open(OUTPUT_DIR / "all_studies.json", "w") as f:
        json.dump(studies, f, indent=2)


def write_eligibility_summary(studies):
    with open(OUTPUT_DIR / "eligibility_summary.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["study_id", "bibtex_key", "title", "meets_criteria",
                     "is_history_education", "is_primary_study", "has_gamification", "concerns"])
        for s in studies:
            e = s.get("eligibility", {})
            bib = s.get("bibliographic", {})
            w.writerow([
                s["study_id"],
                s.get("bibtex_key", ""),
                bib.get("title", ""),
                e.get("meets_criteria", ""),
                e.get("is_history_education", ""),
                e.get("is_primary_study", ""),
                e.get("has_gamification", ""),
                e.get("concerns", ""),
            ])


def write_characteristics_table(studies):
    with open(OUTPUT_DIR / "characteristics_table.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["study_id", "authors", "year", "country", "education_level",
                     "sample_size", "study_design", "game_type", "game_name",
                     "meets_criteria"])
        for s in studies:
            bib = s.get("bibliographic", {})
            sc = s.get("study_characteristics", {})
            e = s.get("eligibility", {})
            authors = "; ".join(bib.get("authors", []))
            countries = ", ".join(sc.get("countries", []))
            w.writerow([
                s["study_id"],
                authors,
                bib.get("year", ""),
                countries,
                sc.get("education_level", ""),
                sc.get("sample_size", ""),
                sc.get("study_design", ""),
                sc.get("game_type", ""),
                sc.get("game_name", ""),
                e.get("meets_criteria", ""),
            ])


def write_risk_of_bias_table(studies):
    with open(OUTPUT_DIR / "risk_of_bias_table.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["study_id", "bibtex_key", "domain1_judgment", "domain2_judgment",
                     "domain3_judgment", "overall", "meets_criteria"])
        for s in studies:
            rob = s.get("risk_of_bias", {})
            e = s.get("eligibility", {})
            w.writerow([
                s["study_id"],
                s.get("bibtex_key", ""),
                rob.get("domain1", {}).get("judgment", ""),
                rob.get("domain2", {}).get("judgment", ""),
                rob.get("domain3", {}).get("judgment", ""),
                rob.get("overall", ""),
                e.get("meets_criteria", ""),
            ])


def write_country_distribution(eligible):
    counter = Counter()
    for s in eligible:
        sc = s.get("study_characteristics", {})
        for c in sc.get("countries", []):
            counter[c] += 1
    with open(OUTPUT_DIR / "country_distribution.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["country", "count"])
        for country, count in counter.most_common():
            w.writerow([country, count])


def write_yearly_distribution(eligible):
    counter = Counter()
    for s in eligible:
        year = s.get("bibliographic", {}).get("year")
        if year:
            counter[year] += 1
    with open(OUTPUT_DIR / "yearly_distribution.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["year", "count"])
        for year in sorted(counter.keys()):
            w.writerow([year, count := counter[year]])


def write_education_level_distribution(eligible):
    counter = Counter()
    for s in eligible:
        level = s.get("study_characteristics", {}).get("education_level", "Not specified")
        if level is None:
            level = "Not specified"
        # Normalize
        level_lower = level.lower()
        if "primary" in level_lower or "elementary" in level_lower:
            counter["Primary"] += 1
        elif "secondary" in level_lower or "high school" in level_lower or "middle school" in level_lower:
            counter["Secondary"] += 1
        elif "higher" in level_lower or "university" in level_lower or "undergraduate" in level_lower or "tertiary" in level_lower:
            counter["Higher education"] += 1
        elif "mixed" in level_lower or "multiple" in level_lower:
            counter["Mixed"] += 1
        else:
            counter[level] += 1
    with open(OUTPUT_DIR / "education_level_distribution.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["education_level", "count"])
        for level, count in counter.most_common():
            w.writerow([level, count])


def write_summary_stats(studies, eligible):
    lines = []
    lines.append(f"Total studies in extraction: {len(studies)}")
    lines.append(f"Eligible studies: {len(eligible)}")
    lines.append(f"Ineligible studies: {len(studies) - len(eligible)}")
    lines.append("")

    # Ineligible details
    ineligible = [s for s in studies if not s.get("eligibility", {}).get("meets_criteria", True)]
    lines.append("Ineligible studies:")
    for s in ineligible:
        e = s.get("eligibility", {})
        lines.append(f"  Study {s['study_id']}: {s.get('bibliographic', {}).get('title', 'Unknown')}")
        lines.append(f"    is_history_education={e.get('is_history_education')}, "
                      f"is_primary_study={e.get('is_primary_study')}, "
                      f"has_gamification={e.get('has_gamification')}")
        lines.append(f"    Concerns: {e.get('concerns', '')}")
    lines.append("")

    # Year range
    years = [s.get("bibliographic", {}).get("year") for s in eligible if s.get("bibliographic", {}).get("year")]
    if years:
        lines.append(f"Year range: {min(years)}-{max(years)}")
    lines.append("")

    # Countries
    country_counter = Counter()
    for s in eligible:
        for c in s.get("study_characteristics", {}).get("countries", []):
            country_counter[c] += 1
    lines.append(f"Countries represented: {len(country_counter)}")
    for c, n in country_counter.most_common():
        lines.append(f"  {c}: {n}")
    lines.append("")

    # Risk of bias summary
    rob_counter = Counter()
    for s in eligible:
        rob_counter[s.get("risk_of_bias", {}).get("overall", "Unknown")] += 1
    lines.append("Risk of bias (overall) distribution:")
    for level, n in rob_counter.most_common():
        lines.append(f"  {level}: {n}")
    lines.append("")

    # Has explicit definition
    has_def = sum(1 for s in eligible if s.get("rq1", {}).get("has_explicit_definition"))
    lines.append(f"Studies with explicit gamification definition: {has_def}/{len(eligible)} ({100*has_def/len(eligible):.1f}%)")
    lines.append("")

    # Sample sizes
    samples = [s.get("study_characteristics", {}).get("sample_size") for s in eligible
               if s.get("study_characteristics", {}).get("sample_size") is not None]
    if samples:
        lines.append(f"Sample sizes reported: {len(samples)}/{len(eligible)}")
        lines.append(f"  Min: {min(samples)}, Max: {max(samples)}, Median: {sorted(samples)[len(samples)//2]}")

    with open(OUTPUT_DIR / "summary_stats.txt", "w") as f:
        f.write("\n".join(lines))
    return "\n".join(lines)


def main():
    studies = load_all_studies()
    eligible = [s for s in studies if s.get("eligibility", {}).get("meets_criteria", True)]

    write_master(studies)
    write_eligibility_summary(studies)
    write_characteristics_table(studies)
    write_risk_of_bias_table(studies)
    write_country_distribution(eligible)
    write_yearly_distribution(eligible)
    write_education_level_distribution(eligible)
    summary = write_summary_stats(studies, eligible)

    print(summary)
    print(f"\nAll output written to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
