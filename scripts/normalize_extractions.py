#!/usr/bin/env python3
"""
Normalize inconsistent values across extraction JSONs.
Fixes:
  - Risk of bias labels (High/high/High risk/High concern -> High)
  - Country names (USA -> United States, The Netherlands -> Netherlands)
  - Education level labels
"""

import json
import os
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
EXTRACTIONS_DIR = BASE / "data" / "extractions"

ROB_MAPPING = {
    "high": "High",
    "high risk": "High",
    "high concern": "High",
    "high risk of bias": "High",
    "moderate": "Moderate",
    "moderate concern": "Moderate",
    "moderate risk": "Moderate",
    "some concerns": "Moderate",
    "some concern": "Moderate",
    "low-moderate concern": "Moderate",
    "medium": "Moderate",
    "unclear": "Unclear",
    "unclear risk": "Unclear",
    "low": "Low",
    "low risk": "Low",
    "low concern": "Low",
    "low risk of bias": "Low",
}

COUNTRY_MAPPING = {
    "USA": "United States",
    "US": "United States",
    "U.S.": "United States",
    "U.S.A.": "United States",
    "The Netherlands": "Netherlands",
    "the Netherlands": "Netherlands",
    "Hong Kong, China": "China (Hong Kong)",
    "Republic of China (Taiwan)": "Taiwan",
    "UK": "United Kingdom",
    "U.K.": "United Kingdom",
}


def normalize_rob(value):
    if value is None:
        return None
    return ROB_MAPPING.get(value.lower().strip(), value)


def normalize_country(value):
    return COUNTRY_MAPPING.get(value, value)


def normalize_study(data):
    changed = False

    # Normalize risk of bias
    rob = data.get("risk_of_bias", {})
    for domain_key in ["domain1", "domain2", "domain3"]:
        domain = rob.get(domain_key, {})
        if "judgment" in domain:
            old = domain["judgment"]
            new = normalize_rob(old)
            if new != old:
                domain["judgment"] = new
                changed = True
    if "overall" in rob:
        old = rob["overall"]
        new = normalize_rob(old)
        if new != old:
            rob["overall"] = new
            changed = True

    # Normalize countries
    sc = data.get("study_characteristics", {})
    if "countries" in sc:
        new_countries = [normalize_country(c) for c in sc["countries"]]
        if new_countries != sc["countries"]:
            sc["countries"] = new_countries
            changed = True
    if "country_of_application" in sc:
        old = sc["country_of_application"]
        new = normalize_country(old)
        if new != old:
            sc["country_of_application"] = new
            changed = True

    return changed


def main():
    total_changed = 0
    for f in sorted(EXTRACTIONS_DIR.glob("study_*.json")):
        with open(f) as fh:
            data = json.load(fh)
        if normalize_study(data):
            with open(f, "w") as fh:
                json.dump(data, fh, indent=2)
            total_changed += 1
            print(f"  Updated: {f.name}")

    print(f"\nTotal files updated: {total_changed}")


if __name__ == "__main__":
    main()
