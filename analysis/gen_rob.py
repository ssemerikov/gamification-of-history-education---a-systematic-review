#!/usr/bin/env python3
"""Study-level risk of bias, re-derived mechanically with the pre-specified rule.

Written for the third revision (R3), answering Reviewer #4 (Q2.5, Q4.4): "A complete
and internally consistent scoring algorithm should be provided", and the figure must
"use exactly the same risk-of-bias categories defined in the Methods".

INPUT
  Primary: the FINAL, human-verified signalling-question answers held in
  REPO/data/extractions/study_N.json (risk_of_bias.domain1..3.q1..q6). The appraisal
  was drafted by GPT-4o (2024) and then verified question by question by a researcher;
  the verified answers were consolidated into the study files in February 2026
  (structured re-extraction with Claude Opus 4.6 via Claude Code, every record checked
  by a researcher). Their free-text vocabulary is normalised to yes / no / unclear:
  "high concern"/"high" -> no; "low concern"/"low" -> yes; "some concern(s)",
  "moderate concern", "partial", "unclear concern" -> unclear.
  Secondary (agreement only): GPT-4o's original 2024 drafts, REPO/early_sheets/Strw103.xlsx,
  sheet "Risk of bias" (yes / no / unclear), with sheet "Аркуш1" giving Paper ID -> title.
  The sheet's Paper IDs are NOT the manuscript's study numbers (one extra row shifts them
  from ID 58 on), so the drafts are aligned to the studies by normalised TITLE.

RULE (Methods, "Rules for domain and overall judgement")
  Domain (two signalling questions each: D1 = q1,q2; D2 = q3,q4; D3 = q5,q6):
    low     if both answers are "yes";
    high    if at least one answer is "no";
    unclear if at least one answer is "unclear" and none is "no".
  Overall: low if all three domains are low; otherwise high.
  Secondary three-level reading (sensitivity analysis only, not a different rating):
    high-risk domain  -- at least one domain high;
    unclear-only      -- no domain high, at least one unclear;
    low               -- all domains low.

OUTPUT (all relative to source/)
  tables/rob_rederived.csv        per-study answers, domain and overall judgements
  tables/rob_macros.tex           \\newcommand block between % >>> ROB and % <<< ROB
  tables/rob_appendix_rows.tex    rows for the appendix risk-of-bias table
  figures/rob_summary_coords.tex  pgfplots coordinates for the summary figure
  tables/rob_lookup.json          study_id -> overall / three-level (for other generators)
  tables/rob_report.md            alignment log, counts, agreement statistics

Run from source/:  python3 scripts/gen_rob.py
"""
import csv, difflib, glob, json, os, re, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.dirname(HERE)
REPO = os.environ.get("REVIEW_REPO") or (
    os.path.dirname(HERE)
    if os.path.isdir(os.path.join(os.path.dirname(HERE), "data", "extractions"))
    else "/home/cc/claude_code/_submitted/gamification-of-history-education---a-systematic-review")

Q = ['q1', 'q2', 'q3', 'q4', 'q5', 'q6']
CATS = ['yes', 'unclear', 'no']


def norm_title(t):
    return re.sub(r'[^a-z0-9]', '', (t or '').lower())


def norm_answer(x):
    """Map both appraisal vocabularies onto yes / no / unclear."""
    x = (str(x) if x is not None else '').strip().lower().replace('_', ' ')
    if x in ('yes', 'low', 'low concern'):
        return 'yes'
    if x in ('no', 'high', 'high concern'):
        return 'no'
    if x in ('unclear', 'partial', 'some concern', 'some concerns',
             'moderate concern', 'unclear concern'):
        return 'unclear'
    raise ValueError(f'unrecognised answer: {x!r}')


def domain(a, b):
    if 'no' in (a, b):
        return 'High'
    if 'unclear' in (a, b):
        return 'Unclear'
    return 'Low'


def overall(doms):
    return 'Low' if all(d == 'Low' for d in doms) else 'High'


def three_level(doms):
    if 'High' in doms:
        return 'High-risk domain'
    if 'Unclear' in doms:
        return 'Unclear only'
    return 'Low'


def kappa(pairs):
    """Cohen's kappa for nominal categories, plus raw proportion of agreement."""
    n = len(pairs)
    po = sum(1 for a, b in pairs if a == b) / n
    ca = Counter(a for a, _ in pairs)
    cb = Counter(b for _, b in pairs)
    pe = sum(ca[c] * cb[c] for c in set(ca) | set(cb)) / (n * n)
    k = (po - pe) / (1 - pe) if pe < 1 else 1.0
    return po, k


def load_sheet():
    import openpyxl
    wb = openpyxl.load_workbook(os.path.join(REPO, 'early_sheets', 'Strw103.xlsx'),
                                read_only=True, data_only=True)
    titles = {}
    for r in list(wb['Аркуш1'].iter_rows(values_only=True))[2:]:
        if len(r) > 1 and r[0] and r[1] is not None:
            try:
                titles[int(float(r[1]))] = str(r[0])
            except ValueError:
                pass
    answers = {}
    for r in list(wb['Risk of bias'].iter_rows(values_only=True))[2:]:
        if r[0] is None:
            continue
        answers[int(float(r[0]))] = [norm_answer(v) for v in r[1:7]]
    return titles, answers


def load_included():
    out = {}
    for f in glob.glob(os.path.join(REPO, 'data', 'extractions', 'study_*.json')):
        d = json.load(open(f, encoding='utf-8'))
        if not d['eligibility'].get('meets_criteria'):
            continue
        rb = d['risk_of_bias']
        later = [rb['domain1'].get('q1_selection_criteria'), rb['domain1'].get('q2_representativeness'),
                 rb['domain2'].get('q3_valid_tools'), rb['domain2'].get('q4_analysis_methods'),
                 rb['domain3'].get('q5_consistent_interpretation'), rb['domain3'].get('q6_limitations_discussed')]
        out[d['study_id']] = dict(key=d['bibtex_key'], title=d['bibliographic']['title'],
                                  later=[norm_answer(x) for x in later],
                                  old_overall=rb.get('overall'))
    return out


def align(inc, titles):
    """One-to-one title alignment, best matches first. Returns {study_id: (paper_id, score)}."""
    cand = []
    for sid, s in inc.items():
        a = norm_title(s['title'])
        for pid, t in titles.items():
            b = norm_title(t)
            if not a or not b:
                continue
            if a[:40] in b or b[:40] in a:
                score = 1.0
            else:
                score = difflib.SequenceMatcher(None, a[:90], b[:90]).ratio()
            cand.append((score, sid, pid))
    cand.sort(reverse=True)
    used_s, used_p, m = set(), set(), {}
    for score, sid, pid in cand:
        if sid in used_s or pid in used_p or score < 0.80:
            continue
        m[sid] = (pid, score)
        used_s.add(sid); used_p.add(pid)
    return m


def pct(k, n):
    v = 100.0 * k / n
    return (f'{v:.0f}' if abs(v - round(v)) < 1e-9 else f'{v:.1f}') + '\\%'


def main():
    titles, answers = load_sheet()
    inc = load_included()
    m = align(inc, titles)
    rows, log = [], []
    for sid in sorted(inc):
        s = inc[sid]
        a, src = s['later'], 'verified'
        if sid in m and m[sid][0] in answers:
            pid, score = m[sid]
            draft = answers[pid]
            log.append(f'| {sid} | {pid} | {score:.2f} | {s["title"][:60]} | {titles[pid][:60]} |')
        else:
            pid, score, draft = None, 0.0, [None] * 6
            log.append(f'| {sid} | — | — | {s["title"][:60]} | NO MATCH: no GPT-4o draft |')
        doms = [domain(a[0], a[1]), domain(a[2], a[3]), domain(a[4], a[5])]
        rows.append(dict(study_id=sid, bibtex_key=s['key'], title=s['title'], sheet_id=pid,
                         match_score=round(score, 3), source=src,
                         **{q: a[i] for i, q in enumerate(Q)},
                         d1=doms[0], d2=doms[1], d3=doms[2],
                         overall=overall(doms), three_level=three_level(doms),
                         old_overall=s['old_overall'],
                         **{f'gpt4o_{q}': draft[i] for i, q in enumerate(Q)}))

    n = len(rows)
    ov = Counter(r['overall'] for r in rows)
    tl = Counter(r['three_level'] for r in rows)
    dc = {d: Counter(r[d] for r in rows) for d in ('d1', 'd2', 'd3')}
    nh, nl = ov['High'], ov['Low']
    nhd, nuo = tl['High-risk domain'], tl['Unclear only']
    nfb = sum(1 for r in rows if r['gpt4o_q1'] is None)

    # agreement between GPT-4o's 2024 drafts and the final verified answers
    drows = [r for r in rows if r['gpt4o_q1'] is not None]
    agree = {}
    for q in Q:
        agree[q] = kappa([(r[f'gpt4o_{q}'], r[q]) for r in drows])
    later_doms = []
    for r in drows:
        la = [r[f'gpt4o_{q}'] for q in Q]
        later_doms.append([domain(la[0], la[1]), domain(la[2], la[3]), domain(la[4], la[5])])
    agree_ov = kappa([(r['three_level'], three_level(ld)) for r, ld in zip(drows, later_doms)])
    later_ov = Counter(overall(ld) for ld in later_doms)
    later_tl = Counter(three_level(ld) for ld in later_doms)
    po_vals = [agree[q][0] for q in Q]
    k_vals = [agree[q][1] for q in Q]

    os.makedirs(os.path.join(SRC, 'tables'), exist_ok=True)
    os.makedirs(os.path.join(SRC, 'figures'), exist_ok=True)

    with open(os.path.join(SRC, 'tables', 'rob_rederived.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    json.dump({r['study_id']: {'overall': r['overall'], 'three_level': r['three_level'],
                               'd1': r['d1'], 'd2': r['d2'], 'd3': r['d3']} for r in rows},
              open(os.path.join(SRC, 'tables', 'rob_lookup.json'), 'w'), indent=1)

    mac = ['% >>> ROB (generated by scripts/gen_rob.py -- pre-specified rule, human-verified answers)',
           f'\\newcommand{{\\nHighRoB}}{{{nh}}}',
           f'\\newcommand{{\\pctHighRoB}}{{{pct(nh, n)}}}',
           f'\\newcommand{{\\nLowRoB}}{{{nl}}}',
           f'\\newcommand{{\\nHighDomRoB}}{{{nhd}}}          % >=1 domain judged high',
           f'\\newcommand{{\\pctHighDomRoB}}{{{pct(nhd, n)}}}',
           f'\\newcommand{{\\nUnclearOnlyRoB}}{{{nuo}}}      % high overall only through unclear reporting',
           f'\\newcommand{{\\pctUnclearOnlyRoB}}{{{pct(nuo, n)}}}',
           f'\\newcommand{{\\nNoHighDomRoB}}{{{nuo + nl}}}     % sensitivity subset: no domain judged high',
           f'\\newcommand{{\\pctNoHighDomRoB}}{{{pct(nuo + nl, n)}}}',
           f'\\newcommand{{\\agreeRoBmin}}{{{100*min(po_vals):.0f}\\%}}   % per-question agreement, GPT-4o draft vs verified',
           f'\\newcommand{{\\agreeRoBmax}}{{{100*max(po_vals):.0f}\\%}}',
           f'\\newcommand{{\\kappaRoBmin}}{{{min(k_vals):.2f}}}',
           f'\\newcommand{{\\kappaRoBmax}}{{{max(k_vals):.2f}}}',
           f'\\newcommand{{\\kappaRoBthree}}{{{agree_ov[1]:.2f}}}  % three-level reading, GPT-4o draft vs verified',
           f'\\newcommand{{\\nHighRoBgpt}}{{{later_ov["High"]}}}  % GPT-4o drafts under the same rule',
           f'\\newcommand{{\\nHighDomRoBgpt}}{{{later_tl["High-risk domain"]}}}',
           '% <<< ROB', '']
    open(os.path.join(SRC, 'tables', 'rob_macros.tex'), 'w').write('\n'.join(mac))

    sup = {'High-risk domain': '', 'Unclear only': '$^{u}$', 'Low': ''}
    app = ['% Auto-generated by scripts/gen_rob.py -- do not edit by hand.']
    for r in rows:
        app.append(f"\\citet{{{r['bibtex_key']}}} & {r['d1']} & {r['d2']} & {r['d3']} & "
                   f"{r['overall']}{sup[r['three_level']]} \\\\")
    open(os.path.join(SRC, 'tables', 'rob_appendix_rows.tex'), 'w').write('\n'.join(app) + '\n')

    def c(cat, lab, cnt):
        return f'({cnt},{lab})'
    # Rows (bottom to top): Domain 1..3, Overall (pre-specified rule), Three-level reading.
    # In the three-level row "High" = at least one domain high; "Unclear" = high overall
    # only through unclear reporting.
    fig = ['% Auto-generated by scripts/gen_rob.py -- stacked bars: High, Unclear, Low',
           '\\addplot[fill=red!70] coordinates {' + ' '.join([
               f'({nhd},Three-level reading)', f'({nh},Overall)', f'({dc["d3"]["High"]},Domain 3)',
               f'({dc["d2"]["High"]},Domain 2)', f'({dc["d1"]["High"]},Domain 1)']) + '};',
           '\\addplot[fill=gray!50] coordinates {' + ' '.join([
               f'({nuo},Three-level reading)', '(0,Overall)', f'({dc["d3"]["Unclear"]},Domain 3)',
               f'({dc["d2"]["Unclear"]},Domain 2)', f'({dc["d1"]["Unclear"]},Domain 1)']) + '};',
           '\\addplot[fill=green!60] coordinates {' + ' '.join([
               f'({nl},Three-level reading)', f'({nl},Overall)', f'({dc["d3"]["Low"]},Domain 3)',
               f'({dc["d2"]["Low"]},Domain 2)', f'({dc["d1"]["Low"]},Domain 1)']) + '};']
    open(os.path.join(SRC, 'figures', 'rob_summary_coords.tex'), 'w').write('\n'.join(fig) + '\n')

    rep = ['# Risk of bias re-derived (scripts/gen_rob.py)', '',
           f'Included studies: {n}; verified answers used for all; GPT-4o drafts aligned for {n - nfb}', '',
           '## Overall (pre-specified rule)', f'- High: {nh} ({100*nh/n:.1f}%)', f'- Low: {nl}', '',
           '## Three-level reading (sensitivity)',
           *[f'- {k}: {v} ({100*v/n:.1f}%)' for k, v in tl.most_common()], '',
           '## Domains', *[f'- {d}: {dict(dc[d])}' for d in ('d1', 'd2', 'd3')], '',
           '## Agreement, GPT-4o 2024 draft vs final verified answer, per signalling question',
           *[f'- {q}: agreement {100*agree[q][0]:.0f}%, kappa {agree[q][1]:.2f}' for q in Q],
           f'- three-level reading: agreement {100*agree_ov[0]:.0f}%, kappa {agree_ov[1]:.2f}',
           f'- GPT-4o drafts under the same rule: overall {dict(later_ov)}; three-level {dict(later_tl)}', '',
           '## Cross-tab: old holistic label (R2 manuscript) x three-level reading',
           *[f'- {k}: {v}' for k, v in sorted(Counter((r["old_overall"], r["three_level"]) for r in rows).items())], '',
           '## Sheet rows not used (excluded studies, or a duplicate row of an included paper)',
           *[f'- sheet {pid}: {titles[pid][:80]} -> {answers.get(pid)}'
             for pid in sorted(set(titles) - {r["sheet_id"] for r in rows})], '',
           '## Title alignment (study | sheet ID | score | study title | sheet title)',
           '| study | sheet | score | study title | sheet title |', '|---|---|---|---|---|', *log]
    open(os.path.join(SRC, 'tables', 'rob_report.md'), 'w').write('\n'.join(rep) + '\n')

    print('\n'.join(rep[:40]))


if __name__ == '__main__':
    main()
