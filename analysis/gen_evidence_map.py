#!/usr/bin/env python3
"""Evidence map: game-mechanic families x outcome families x design family (R3, Reviewer #4 Q4.6).

Inputs (REPO = review data repository): data/extractions/study_N.json, the researcher-checked
per-study records. Coding is deterministic and documented here:

DESIGN FAMILY (per study, assigned from study_design + rq2.comparative_methodology, checked by
hand against the effect-size verification for the quantitative studies):
  controlled -- a gamified condition compared with a NON-gamified control or comparison group
                (randomised or not; includes the pretest-split comparison of 52/67);
  prepost    -- a single group measured before and after the gamified activity;
  other      -- descriptive, qualitative, design-and-development reports, and comparisons
                between two game conditions (no non-gamified comparison).
Reports 52 and 67 describe one experiment and are counted once (as study 67).

MECHANIC FAMILIES: keyword match on rq3.game_design_elements (see MECH).
OUTCOME FAMILIES: keyword match on rq2.quantitative_metrics, key_outcomes, engagement_results
and statistical_results (see OUT): what a study MEASURED or REPORTED, not whether it found
an effect.

Outputs (relative to source/): tables/evidence_map.tex, tables/evidence_map.csv,
tables/design_family.csv, and design macros in tables/design_macros.tex.
Run from source/:  python3 scripts/gen_evidence_map.py
"""
import csv, glob, json, os, re, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.dirname(HERE)
REPO = os.environ.get('REVIEW_REPO') or (
    os.path.dirname(HERE)
    if os.path.isdir(os.path.join(os.path.dirname(HERE), 'data', 'extractions'))
    else '/home/cc/claude_code/_submitted/gamification-of-history-education---a-systematic-review')

CONTROLLED = {8, 24, 28, 41, 49, 52, 66, 67, 72, 74, 76}
PREPOST = {1, 9, 13, 16, 19, 36, 38, 39, 45, 54, 58, 63, 64, 71, 79, 80}
SAME_STUDY = {52: 67}
# design-and-development reports without learner data, and protocols without results:
# they contribute mechanics but no measured outcome
NO_DATA = {17, 18, 20, 53, 73}
# manual corrections to the keyword coding, verified against the full texts:
# study 66 measured engagement only (post-test questionnaire), not knowledge
OVERRIDE = {66: {'Knowledge': 0}}

MECH = [
    ('Narrative and role-play', r'narrat|story|storytell|role[- ]?play|character|npc|plot|dialog'),
    ('Exploration and immersive environments', r'explor|virtual|\bvr\b|augmented|\bar\b|3d|immersi|museum|reconstruct|gps|location'),
    ('Points, levels and rewards', r'point|scor|badge|leaderboard|level|reward|progress|unlock'),
    ('Quizzes, puzzles and challenges', r'quiz|question|puzzle|riddle|trivia|challenge'),
    ('Simulation and strategy', r'simulat|strateg|resource management|decision|economic|civilization|total war'),
    ('Collaboration and competition', r'collaborat|cooperat|team|group|compet|tournament|multiplayer|pair'),
]
OUT = [
    ('Knowledge', r'knowledge|achievement|test score|post-?test|pre-?test|recall|retention|learning (outcome|performance|effectiveness|gain)'),
    ('Engagement and motivation', r'engag|motivat|interest|enjoy|flow|immersion|attention'),
    ('Attitudes and perceptions', r'attitude|percept|perceived|satisf|opinion|usefulness|usability'),
    ('Historical thinking', r'historical thinking|empath|perspective|sourc(e|ing) (analysis|evaluation|work)|contextuali[sz]|corroborat|critical thinking|historical (reasoning|understanding|interpretation|consciousness)|multiperspectiv|causal'),
]
# GRADE-informed certainty from the summary-of-findings table (Table tab:summary_findings)
CERT = {'Knowledge': r'\gradeVL{}', 'Engagement and motivation': r'\gradeVL{}',
        'Attitudes and perceptions': r'\gradeVL{}', 'Historical thinking': r'--'}


def family(sid):
    return 'controlled' if sid in CONTROLLED else ('prepost' if sid in PREPOST else 'other')


def main():
    studies = {}
    for f in glob.glob(os.path.join(REPO, 'data', 'extractions', 'study_*.json')):
        d = json.load(open(f, encoding='utf-8'))
        if not d['eligibility'].get('meets_criteria'):
            continue
        studies[d['study_id']] = d
    ids = sorted(studies)
    reports = {fam: sum(1 for s in ids if family(s) == fam) for fam in ('controlled', 'prepost', 'other')}
    uniq = [s for s in ids if s not in SAME_STUDY]
    rows = []
    for sid in uniq:
        d = studies[sid]
        mech_txt = ' '.join(d['rq3'].get('game_design_elements') or []).lower()
        if sid in SAME_STUDY.values():          # merge the companion report's text
            for a, b in SAME_STUDY.items():
                if b == sid:
                    mech_txt += ' ' + ' '.join(studies[a]['rq3'].get('game_design_elements') or []).lower()
        out_txt = '' if sid in NO_DATA else ' '.join(str(d['rq2'].get(k) or '') for k in
                           ('quantitative_metrics', 'key_outcomes', 'engagement_results', 'statistical_results')).lower()
        r = dict(study_id=sid, key=d['bibtex_key'], design=family(sid))
        for name, pat in MECH:
            r[name] = int(bool(re.search(pat, mech_txt)))
        for name, pat in OUT:
            r[name] = int(bool(re.search(pat, out_txt)))
        for name, val in OVERRIDE.get(sid, {}).items():
            r[name] = val
        rows.append(r)
    n = len(rows)
    os.makedirs(os.path.join(SRC, 'tables'), exist_ok=True)
    with open(os.path.join(SRC, 'tables', 'evidence_map.csv'), 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    with open(os.path.join(SRC, 'tables', 'design_family.csv'), 'w', newline='') as fh:
        w = csv.writer(fh); w.writerow(['study_id', 'bibtex_key', 'design_family'])
        for s in ids:
            w.writerow([s, studies[s]['bibtex_key'], family(s)])

    # LaTeX table: cell = controlled / pre-post / other counts of studies
    def cell(mech, out):
        c = Counter(r['design'] for r in rows if r[mech] and r[out])
        return f"{c['controlled']}\\,/\\,{c['prepost']}\\,/\\,{c['other']}"
    L = ['% Auto-generated by scripts/gen_evidence_map.py -- do not edit by hand.',
         '\\begin{table}[!ht]', '\\centering',
         '\\caption{Evidence map: number of studies using each family of game mechanics that measured '
         'each family of outcomes, by design (controlled\\,/\\,single-group pre--post\\,/\\,other), with the '
         'certainty of the evidence for each outcome family. Controlled = a gamified condition compared '
         'with a non-gamified control or comparison group; other = descriptive, qualitative and '
         'design-and-development reports and comparisons between game conditions. A study appears in '
         'every cell whose mechanic and outcome it reports, so cells overlap. Counts come from keyword '
         'coding of the verified extraction records (script and coding rules in the repository); they '
         'measure what was studied, not what was found, and they use a broader coding unit than '
         f'Figures~\\ref{{fig:outcome_types}} and~\\ref{{fig:game_design_elements}}. $n={n}$ studies.}}',
         '\\label{tab:evidence_map}',
         '\\footnotesize\\setlength{\\tabcolsep}{3pt}',
         '\\begin{tabular}{|p{0.30\\linewidth}|' + 'c|' * len(OUT) + '}', '\\hline',
         '\\textbf{Mechanic family} & ' + ' & '.join('\\textbf{\\makecell{' + o.replace(' and ', ' and\\\\') + '}}' for o, _ in OUT) + ' \\\\', '\\hline']
    for m, _ in MECH:
        L.append(m + ' & ' + ' & '.join(cell(m, o) for o, _ in OUT) + ' \\\\')
        L.append('\\hline')
    tot = []
    for o, _ in OUT:
        c = Counter(r['design'] for r in rows if r[o])
        tot.append(f"{c['controlled']}\\,/\\,{c['prepost']}\\,/\\,{c['other']}")
    L.append('\\textit{Any mechanic} & ' + ' & '.join(tot) + ' \\\\')
    L.append('\\hline')
    L.append('\\textit{Certainty} & ' + ' & '.join(CERT[o] for o, _ in OUT) + ' \\\\')
    L.append('\\hline')
    L.append('\\end{tabular}')
    L.append('\\begin{minipage}{\\linewidth}\\footnotesize Certainty from Table~\\ref{tab:summary_findings} '
             '(\\gradeVL{} very low). Historical thinking is not rated: no controlled study measured it and no study '
             'reported an estimable effect on it.'
             '\\end{minipage}')
    L.append('\\end{table}')
    open(os.path.join(SRC, 'tables', 'evidence_map.tex'), 'w').write('\n'.join(L) + '\n')

    mac = ['% >>> DESIGN (generated by scripts/gen_evidence_map.py)',
           f"\\newcommand{{\\nReportsControlled}}{{{reports['controlled']}}}",
           f"\\newcommand{{\\nReportsPrePost}}{{{reports['prepost']}}}",
           f"\\newcommand{{\\nReportsOther}}{{{reports['other']}}}",
           f"\\newcommand{{\\pctReportsControlled}}{{{100*reports['controlled']/len(ids):.1f}\\%}}",
           f"\\newcommand{{\\pctReportsOther}}{{{100*reports['other']/len(ids):.1f}\\%}}",
           f"\\newcommand{{\\nStudiesControlled}}{{{sum(1 for r in rows if r['design']=='controlled')}}}",
           '% <<< DESIGN', '']
    open(os.path.join(SRC, 'tables', 'design_macros.tex'), 'w').write('\n'.join(mac))
    print('reports by design:', reports, '| studies:', Counter(r['design'] for r in rows), 'n =', n)
    print('marginals mechanics:', {m: sum(r[m] for r in rows) for m, _ in MECH})
    print('marginals outcomes :', {o: sum(r[o] for r in rows) for o, _ in OUT})


if __name__ == '__main__':
    main()
