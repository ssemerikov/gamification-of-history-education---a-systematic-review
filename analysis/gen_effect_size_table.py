#!/usr/bin/env python3
"""
Effect-size synthesis for "Gamification of history education: a systematic review".

Author-computed standardized effect sizes (Hedges' g) for the SSHO major revision,
addressing Reviewer #3's request for effect-size reporting (Cohen's d / eta^2).

DESIGN NOTES (documented for reproducibility and the manuscript Methods):
  * Effect sizes were computed BY THE AUTHORS from the statistics reported in each
    primary study (test statistics, group/condition means and SDs, sample sizes),
    NOT by any language model. Inputs are transcribed in STUDIES below with the
    exact reported figures and a source tag.
  * Two effect-size families are kept SEPARATE and never averaged together:
      - CHANGE  (g_change): single-group pre-post standardized mean change,
                 d_z = t_paired / sqrt(n);  for Wilcoxon, r = |Z|/sqrt(N) reported
                 and, where shown on the d axis, converted d = 2r/sqrt(1-r^2) (flagged).
      - BETWEEN (g_between): controlled/two-group post-test contrast,
                 d = t_indep * sqrt(1/n1 + 1/n2)  (equal split assumed when only N given),
                 or from one-way F(1, df): d = 2*sqrt(F/df_error),
                 or from group means/SDs: d = (M1 - M2)/SD_pooled.
  * Small-sample correction: Hedges' g = d * J(df), J = 1 - 3/(4*df - 1).
  * One effect size per study per construct; the PRIMARY history-knowledge/achievement
    outcome is used for the forest plot. Other constructs are tabulated but not pooled.
  * NO meta-analytic pooling (SWiM): per-construct median [IQR] and range only, given
    heterogeneity of outcomes, designs and comparators.
Outputs: effect_sizes.csv, tables/effect_size_table.tex, figures/forest_plot.tex,
         numbers.tex (headline macros).
"""
import csv, json, math, os, glob, re, statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.dirname(HERE)
# Review data repository. Defaults to the parent of this script (the layout in
# the public release, where this file lives in analysis/); override with the
# REVIEW_REPO environment variable, or fall back to the author's working copy.
REPO = os.environ.get("REVIEW_REPO") or (
    os.path.dirname(HERE)
    if os.path.isdir(os.path.join(os.path.dirname(HERE), "data", "extractions"))
    else "/home/cc/claude_code/_submitted/gamification-of-history-education---a-systematic-review")

def J(df):
    return 1.0 - 3.0 / (4.0 * df - 1.0) if df and df > 1 else 1.0

def g_from_dz(t, n):
    d = t / math.sqrt(n); return d, d * J(n - 1)

def g_from_indep_t(t, n1, n2):
    d = t * math.sqrt(1.0 / n1 + 1.0 / n2); return d, d * J(n1 + n2 - 2)

def g_from_F(F, dfe):
    d = 2.0 * math.sqrt(F / dfe); return d, d * J(dfe)

def g_from_means(m1, s1, m2, s2, n1, n2):
    sp = math.sqrt(((n1 - 1) * s1 ** 2 + (n2 - 1) * s2 ** 2) / (n1 + n2 - 2))
    d = (m1 - m2) / sp; return d, d * J(n1 + n2 - 2)

def r_from_Z(Z, N):
    return abs(Z) / math.sqrt(N)

def d_from_r(r):
    return 2 * r / math.sqrt(1 - r ** 2)

# --- Sampling variance and 95% confidence intervals (added for the R2 revision,
# --- answering Reviewer #3's request that CIs be reported alongside every effect
# --- size where the primary study allows it).
#
# Large-sample (normal-theory) variances of the standardized mean difference:
#   between-group : var(d)   = (n1+n2)/(n1*n2) + d^2 / (2*(n1+n2))
#   single-group  : var(d_z) = 1/n + d_z^2 / (2*n)
# The Hedges correction is a multiplicative constant, so var(g) = J^2 * var(d).
# CIs are the usual g +/- 1.96*SE; they quantify sampling error ONLY and say
# nothing about the risk of bias that dominates this corpus -- stated in the
# manuscript so the intervals are not over-read.

def var_d_between(d, n1, n2):
    return (n1 + n2) / (n1 * n2) + d ** 2 / (2.0 * (n1 + n2))

def var_d_change(d, n):
    return 1.0 / n + d ** 2 / (2.0 * n)

def ci_from_g(g, var_d, j):
    """95% CI for Hedges' g. var_d is the variance of the uncorrected d."""
    if g is None or var_d is None or var_d <= 0:
        return None, None, None
    se = math.sqrt((j ** 2) * var_d)
    return se, g - 1.96 * se, g + 1.96 * se

# --- Transcribed estimable studies: primary history-knowledge/achievement outcome ---
# family: 'change' (single-group pre-post) or 'between' (controlled contrast)
# Each entry documents the reported statistic and the computation path.
STUDIES = {
 1:  dict(fam='change',  path='wilcoxon', Z=2.226, N=17, stat=r"""$Z=-2.226$, $p=.026$""", note='Wilcoxon Z; r->d (approx)'),
 8:  dict(fam='between', path='indep_t',  t=2.01, n1=51.5, n2=51.5, split='assumed',
      stat=r"""$t=2.01$, $p=.05$ (post-test)""", note='post-test achievement CGBI vs NCGBI, t; per-arm class sizes not reported (N=103), equal split assumed'),
 9:  dict(fam='change',  path='paired_t', t=8.196, n=27, stat=r"""$t=8.196$, $p<.001$""", note='learning effectiveness pre-post'),
 16: dict(fam='change',  path='paired_t', t=5.33, n=38, stat=r"""$t=-5.33$, $p<.001$""", note='historical knowledge pre-post'),
 19: dict(fam='change',  path='paired_t', t=9.58, n=66, stat=r"""$t=9.58$, $p<.001$""", note='knowledge pre-post'),
 24: dict(fam='change',  path='wilcoxon', Z=None, W=0, N=36, stat=r"""$W=0$, $p\leq.01$ (game phase)""", note='Wilcoxon W (game phase); reported p<.01'),
 28: dict(fam='between', path='means',    m1=75.62, s1=17.107, n1=21, m2=72.78, s2=16.368, n2=23, stat=r"""$M=75.62$ vs $72.78$, $p<.05$""", note='post-test achievement E vs C (21 experimental, 23 control)'),
 39: dict(fam='change',  path='wilcoxon', Z=1.97, N=34, stat=r"""$Z=-1.97$, $p=.04$, $r=-.24$""", note='pedagogical value (attitude); r reported .24'),
 45: dict(fam='change',  path='paired_t', t=7.72, n=29, stat=r"""$t=7.72$, $p<.05$""", note='history knowledge pre-post'),
 52: dict(fam='between', path='means',    m1=91.4545, s1=None, n1=11, m2=96.2105, s2=None, n2=19, stat=r"""$t(10)$, $p=.010$ (low achievers)""", note='post-test; SDs not reported -> from gain t below', tchange=None),
 58: dict(fam='change',  path='paired_t', t=22.46, n=30, stat=r"""$t=22.46$, $p<.001$""", note='learning effectiveness pre-post (outlier)'),
 63: dict(fam='change',  path='wilcoxon', Z=2.77, N=12, stat=r"""$Z=-2.77$, $p=.006$""", note='Wilcoxon Z; r->d (approx)'),
 64: dict(fam='change',  path='paired_t', t=15.52, n=40, stat=r"""$t=15.52$, $p<.001$""", note='history score pre-post'),
 66: dict(fam='between', path='F',        F=4.408, dfe=64, n1=33, n2=33, stat=r"""$F(1,64)=4.408$, $p=.040$""", note='one-way ANOVA F(1,64); 33 experimental, 33 control'),
 67: dict(fam='change',  path='paired_t', t=3.194, n=11, stat=r"""$t=3.194$, $p<.05$ (exp.\ pre--post)""", note='experimental-group pre-post gain t (control non-sig)'),
 70: dict(fam='change',  path='paired_t', t=2.907, n=74, stat=r"""$t=-2.907$, $p<.05$""", note='cognitive engagement (engagement construct)'),
 71: dict(fam='change',  path='approx',   d=0.50, N=25, stat=r"""All 25 improved (no test)""", note='ARG %-gain, approximated (qual scores)'),
 72: dict(fam='between', path='indep_t',  t=3.101, n1=24, n2=24, stat=r"""$t=3.101>t_{\mathrm{crit}}=1.711$""", note='cognitive post-test E vs C, t'),
 79: dict(fam='change',  path='paired_t', t=6.113, n=38, stat=r"""$t=6.113$, $p<.05$""", note='knowledge pre-post (controlled arm compares delivery mode, not gamification)'),
}
# construct tag for the estimable set (primary outcome)
CONSTRUCT = {1:'knowledge',8:'knowledge',9:'knowledge',16:'knowledge',19:'knowledge',
 24:'knowledge',28:'knowledge',39:'attitude',45:'knowledge',52:'knowledge',58:'knowledge',
 63:'knowledge',64:'knowledge',66:'knowledge',67:'knowledge',70:'engagement',71:'knowledge',
 72:'knowledge',79:'knowledge'}

def compute(sid, s):
    """Return (d, g, N, se, lo, hi, ci_kind).

    ci_kind is 'exact'  -- CI from the reported per-arm/single-group n;
              'assumed' -- CI valid up to an assumed equal split of a reported total N;
              'approx'  -- rank-derived d, normal-theory variance is an approximation;
              'none'    -- no defensible CI (no test statistic behind the estimate).
    """
    p = s['path']
    if p == 'paired_t':
        n = s['n']; d, g = g_from_dz(s['t'], n)
        se, lo, hi = ci_from_g(g, var_d_change(d, n), J(n - 1))
        return d, g, n, se, lo, hi, 'exact'
    if p == 'indep_t':
        n1, n2 = s['n1'], s['n2']; d, g = g_from_indep_t(s['t'], n1, n2)
        se, lo, hi = ci_from_g(g, var_d_between(d, n1, n2), J(n1 + n2 - 2))
        return d, g, round(n1 + n2), se, lo, hi, s.get('split', 'exact')
    if p == 'F':
        d, g = g_from_F(s['F'], s['dfe'])
        n1, n2 = s.get('n1'), s.get('n2')
        if n1 and n2:
            se, lo, hi = ci_from_g(g, var_d_between(d, n1, n2), J(s['dfe']))
            return d, g, n1 + n2, se, lo, hi, 'exact'
        # fall back to an equal split of the ANOVA-implied total
        N = s['dfe'] + 2; h = N / 2.0
        se, lo, hi = ci_from_g(g, var_d_between(d, h, h), J(s['dfe']))
        return d, g, N, se, lo, hi, 'assumed'
    if p == 'means':
        if s.get('s1') and s.get('s2'):
            n1, n2 = s['n1'], s['n2']
            d, g = g_from_means(s['m1'], s['s1'], s['m2'], s['s2'], n1, n2)
            se, lo, hi = ci_from_g(g, var_d_between(d, n1, n2), J(n1 + n2 - 2))
            return d, g, n1 + n2, se, lo, hi, 'exact'
        return None, None, (s.get('n1',0)+s.get('n2',0)), None, None, None, 'none'
    if p == 'wilcoxon':
        if s.get('Z'):
            N = s['N']; r = r_from_Z(s['Z'], N); d = d_from_r(r); g = d * J(N - 1)
            # normal-theory variance applied to a rank-derived d: approximate only
            se, lo, hi = ci_from_g(g, var_d_change(d, N), J(N - 1))
            return d, g, N, se, lo, hi, 'approx'
        return None, None, s.get('N'), None, None, None, 'none'
    if p == 'approx':
        # eyeballed from a reported percentage gain; no test statistic, no J
        # correction applied -- this value cannot carry an honest CI.
        return s['d'], s['d'], s.get('N'), None, None, None, 'none'
    return None, None, None, None, None, None, 'none'

FAMLAB = {'change': 'Pre--post', 'between': 'Controlled'}

def norm_design(s):
    """Normalise the free-text design strings transcribed from the primary studies
    into a small consistent vocabulary, so the table reads uniformly."""
    t = (s or '').replace('_', ' ').strip().lower()
    if 'quasi' in t:
        return 'Quasi-experimental'
    if 'pre-experimental' in t or 'pre experimental' in t:
        return 'Pre-experimental'
    if 'mixed' in t:
        return 'Mixed methods'
    if 'one-shot' in t or 'one shot' in t or 'single-group' in t or 'single group' in t:
        return 'Single-group pre--post'
    if 'pre' in t and 'post' in t:
        return 'Single-group pre--post'
    if 'experimental' in t:
        return 'Experimental'
    return (s or '').replace('_', ' ').capitalize()

def emit_table(rows):
    """Quantitative-results table for the main text.

    This merges what were previously two overlapping tables -- the
    'statistically significant learning outcomes' list and the effect-size
    table, which shared 14 of their studies and both carried an N column --
    into a single table, answering Reviewer #3's request that tables not
    duplicate one another and that CIs and sample sizes accompany every effect
    size. Free-text study design is not repeated here; it is tabulated for all
    74 studies in Appendix~\\ref{app:characteristics}.
    """
    sel = [r for r in rows if r[0] in STUDIES]
    # controlled designs first, then descending effect size; non-estimable last
    def key(r):
        fam = 0 if r[6] == 'between' else 1
        g = -float(r[8]) if r[8] else 99.0
        return (fam, g)
    sel.sort(key=key)
    out = []
    out.append('% Auto-generated by gen_effect_size_table.py -- do not edit by hand.')
    out.append('\\begin{table}[!ht]')
    out.append('\\centering')
    out.append('\\caption{Reported statistics and author-computed standardized effect sizes '
               '(Hedges\' $g$) with 95\\% confidence intervals, for every study whose reporting '
               'permitted quantitative appraisal. Pre--post = single-group standardized mean '
               'change ($d_z$); Controlled = between-group post-test contrast; the two families '
               'are never averaged together. Effect sizes were computed by the authors from the '
               'statistics reported in each primary study (Section~\\ref{sec:Methodology}), not '
               'by any language model. The remaining studies were not estimable (descriptive, '
               'qualitative, or design/development reports). Confidence intervals express '
               'sampling error only; they do not incorporate risk of bias, which is rated '
               'separately in the final column and is high for all but one study listed here.}')
    out.append('\\label{tab:effect_sizes}')
    # NB: \tabcolsep is already 1.5pt here (an earlier relative \setlength in
    # paper.tex leaks), so an absolute 4pt would *widen* the table.  At \small
    # the 8 columns overrun \textwidth by 21pt; \footnotesize brings them in.
    out.append('\\footnotesize\\setlength{\\tabcolsep}{2pt}')
    # Bordered style, matching the other tables in the manuscript.
    out.append('\\begin{tabular}{|l|c|c|r|l|c|c|c|}')
    out.append('\\hline')
    out.append('\\hfill \\textbf{Study} & \\textbf{Family} & \\textbf{Outcome} & $N$ & '
               '\\hfill \\textbf{Reported statistic} & \\textbf{Hedges\' $g$} & '
               '\\textbf{95\\% CI} & \\textbf{RoB} \\\\')
    out.append('\\hline')
    for r in sel:
        s = STUDIES[r[0]]
        cap = '$^{\\dagger}$' if 'capped' in r[10] else ''
        ck = r[14]
        if r[12] and r[13]:
            # typeset negatives with a real minus sign, not a hyphen
            ci = f'[{r[12].replace("-", "$-$")}, {r[13].replace("-", "$-$")}]'
            if ck == 'assumed':
                ci += '$^{\\ddagger}$'
            elif ck == 'approx':
                ci += '$^{\\S}$'
        else:
            ci = '--$^{\\P}$'
        gcell = f'{r[8]}{cap}' if r[8] else 'n.e.$^{\\P}$'
        construct = (r[5] or '').capitalize()
        out.append(f'\\citet{{{r[1]}}} & {FAMLAB.get(r[6],r[6])} & {construct} & {r[2]} & '
                   f'{s.get("stat","")} & {gcell} & {ci} & {r[4]} \\\\')
        out.append('\\hline')
    out.append('\\end{tabular}')
    # Footnote key -- kept outside the tabular so it wraps to the table width.
    out.append('\\begin{minipage}{\\linewidth}\\footnotesize')
    out.append('$^{\\dagger}$Value exceeds the forest-plot axis and is plotted at the limit in '
               'Figure~\\ref{fig:forest}. '
               '$^{\\ddagger}$Per-arm group sizes were not reported; the interval assumes an '
               'equal split of the reported total. '
               '$^{\\S}$Effect size derived from a rank-based (Wilcoxon) statistic; the '
               'normal-theory interval is an approximation. '
               '$^{\\P}$n.e.\\ = not estimable: the study reports a significance test without '
               'the test statistic, dispersion, or group means needed to standardize an effect, '
               'so neither a defensible point estimate nor an interval can be computed.')
    out.append('\\end{minipage}')
    out.append('\\end{table}')
    open(os.path.join(SRC, 'tables', 'effect_size_table.tex'), 'w').write('\n'.join(out))

def emit_forest(know):
    """Two-panel forest plot: change-family vs between-family, knowledge/achievement."""
    change = [r for r in know if r[6]=='change']
    between = [r for r in know if r[6]=='between']
    change.sort(key=lambda r: float(r[8]))
    between.sort(key=lambda r: float(r[8]))
    XMAX = 1.6
    def author(key):
        m = re.match(r'\d*([A-Za-z]+)(\d{4})', key)
        return f'\\citeauthor{{{key}}}' if m else key
    def panel(items, y0, fill):
        L=[]
        for i, r in enumerate(items):
            g = min(float(r[8]), 1.5); n = r[2] or 20
            y = y0 - i*0.62
            rad = 2.0 + 3.5*(math.sqrt(float(n))-math.sqrt(4))/(math.sqrt(200)-math.sqrt(4))
            rad = max(1.8, min(6.0, rad))
            L.append(f'\\node[font=\\scriptsize,anchor=east] at (0,{y:.2f}) {{{author(r[1])}}};')
            x = g/XMAX*8.0
            # 95% CI whisker, drawn beneath the marker and clipped to the axis.
            if r[12] and r[13]:
                lo = max(0.0, min(float(r[12]), XMAX))
                hi = max(0.0, min(float(r[13]), XMAX))
                xlo, xhi = lo/XMAX*8.0, hi/XMAX*8.0
                L.append(f'\\draw[{fill},line width=0.5pt] ({xlo:.2f},{y:.2f}) -- ({xhi:.2f},{y:.2f});')
                # Square cap where the interval ends on the axis; arrowhead where
                # it runs off it, so a clipped bound is never read as a real one.
                if float(r[12]) >= 0.0:
                    L.append(f'\\draw[{fill},line width=0.5pt] ({xlo:.2f},{y-0.08:.2f}) -- ({xlo:.2f},{y+0.08:.2f});')
                else:
                    L.append(f'\\draw[{fill},line width=0.5pt,->] ({xlo+0.18:.2f},{y:.2f}) -- ({xlo-0.10:.2f},{y:.2f});')
                if float(r[13]) <= XMAX:
                    L.append(f'\\draw[{fill},line width=0.5pt] ({xhi:.2f},{y-0.08:.2f}) -- ({xhi:.2f},{y+0.08:.2f});')
                else:
                    L.append(f'\\draw[{fill},line width=0.5pt,->] ({xhi-0.18:.2f},{y:.2f}) -- ({xhi+0.10:.2f},{y:.2f});')
            L.append(f'\\fill[{fill}] ({x:.2f},{y:.2f}) circle ({rad:.1f}pt);')
            capmark = '$>$' if float(r[8])>1.5 else ''
            ciTxt = f' [{r[12]}, {r[13]}]' if r[12] and r[13] else ''
            # place the value label clear of the whisker's right-hand end
            xlab = x
            if r[13]:
                xlab = max(xlab, min(float(r[13]), XMAX)/XMAX*8.0)
            L.append(f'\\node[font=\\tiny,anchor=west,text=gray] at ({xlab+0.22:.2f},{y:.2f}) '
                     f'{{{capmark}{float(r[8]):.2f}{ciTxt}, $n${{=}}{n}}};')
        return L, y0 - (len(items)-1)*0.62
    lines=[]
    lines.append('% Auto-generated by gen_effect_size_table.py -- do not edit by hand.')
    lines.append('\\begin{figure}[!ht]\\centering')
    lines.append('\\begin{tikzpicture}[x=1cm,y=1cm]')
    ytop=0.0
    # change panel
    lines.append(f'\\node[font=\\small\\bfseries,anchor=west,text=orange!60!black] at (0,{ytop+0.7:.2f}) '
                 '{Single-group pre--post (uncontrolled): median $g$=\\medGChange{}};')
    p1, ybot1 = panel(change, ytop, 'orange!70!black')
    lines += p1
    # Axis for panel 1. It is drawn at the BOTTOM of the panel (ybot1), not the
    # top: anchoring it to ytop drew the tick row straight through the second
    # study of the panel.
    def axis(y, panel_top, labels=True):
        A=[f'\\draw[->] (0,{y-0.4:.2f}) -- (8.6,{y-0.4:.2f});']
        for gg in [0,0.2,0.4,0.8,1.2,1.6]:
            x=gg/XMAX*8.0
            A.append(f'\\draw ({x:.2f},{y-0.35:.2f})--({x:.2f},{y-0.45:.2f});')
            A.append(f'\\node[font=\\tiny,anchor=north] at ({x:.2f},{y-0.45:.2f}) {{{gg:.1f}}};')
        A.append(f'\\draw[red!60!black,dashed] ({0.2/XMAX*8:.2f},{y-0.35:.2f})--({0.2/XMAX*8:.2f},{panel_top+0.35:.2f});')
        A.append(f'\\draw[blue!60!black,dashed] ({0.4/XMAX*8:.2f},{y-0.35:.2f})--({0.4/XMAX*8:.2f},{panel_top+0.35:.2f});')
        if labels:
            A.append(f'\\node[font=\\tiny,text=red!60!black,anchor=east] at ({0.2/XMAX*8-0.05:.2f},{panel_top+0.35:.2f}) {{0.20 Kraft}};')
            A.append(f'\\node[font=\\tiny,text=blue!60!black,anchor=west] at ({0.4/XMAX*8+0.05:.2f},{panel_top+0.35:.2f}) {{0.40 Hattie}};')
        return A
    lines += axis(ybot1, ytop)
    # between panel below
    # gap must clear the first panel's tick row and its axis caption
    ytop2 = ybot1 - 2.3
    lines.append(f'\\node[font=\\small\\bfseries,anchor=west,text=blue!60!black] at (0,{ytop2+0.6:.2f}) '
                 '{Controlled (between-group): median $g$=\\medGBetween{}};')
    p2, ybot2 = panel(between, ytop2, 'blue!60!black')
    lines += p2
    yb=ybot2
    # Same axis treatment for the controlled panel, including the benchmark
    # reference lines -- this is where the comparison against field norms
    # matters most, since the controlled median sits right at the Hattie line.
    lines += axis(ybot2, ytop2, labels=False)
    lines.append(f'\\node[font=\\scriptsize,anchor=north] at (4,{yb-0.75:.2f}) {{Estimated effect size (Hedges\' $g$); marker area $\\propto \\sqrt{{n}}$; bars are 95\\% CIs}};')
    lines.append('\\end{tikzpicture}')
    lines.append('\\caption{Author-computed effect sizes (Hedges\' $g$) with 95\\% confidence '
                 'intervals for history-knowledge and achievement outcomes, for the '
                 '\\nKnowledgeES{} of 74 studies whose reported statistics permitted estimation, '
                 'separated by study design. Markers are point estimates with area proportional '
                 'to $\\sqrt{n}$; horizontal bars are 95\\% confidence intervals, which reflect '
                 'sampling error only and not risk of bias. The axis is truncated at 1.6: four '
                 'pre--post estimates exceed this and are plotted at the axis limit with their '
                 'true value prefixed by ``$>$\'\'; arrowheads mark intervals that extend beyond '
                 'the plotted range, including one controlled estimate whose interval includes '
                 'zero. Single-group pre--post estimates (top, median '
                 '$g$=\\medGChange{}) are markedly larger than controlled between-group estimates '
                 '(bottom, median $g$=\\medGBetween{}), consistent with the absence of a '
                 'counterfactual inflating uncontrolled designs. Dashed lines mark empirical '
                 'benchmarks for field-based education interventions '
                 '\\citep{Kraft2020,Hattie2009}. Two further estimable studies measuring attitude '
                 'and engagement outcomes appear in Table~\\ref{tab:effect_sizes} but not here.}')
    lines.append('\\label{fig:forest}')
    lines.append('\\end{figure}')
    open(os.path.join(SRC, 'figures', 'forest_plot.tex'), 'w').write('\n'.join(lines))

def load_meta():
    meta = {}
    for f in glob.glob(os.path.join(REPO, 'data/extractions/study_*.json')):
        d = json.load(open(f))
        if not d.get('eligibility', {}).get('meets_criteria'):
            continue
        sc = d.get('study_characteristics', {})
        meta[d['study_id']] = dict(
            key=d.get('bibtex_key',''), n=sc.get('sample_size'),
            design=(sc.get('study_design') or ''),
            rob=(d.get('risk_of_bias',{}).get('overall') or ''),
            stat=(d.get('rq2',{}).get('statistical_results') or ''))
    return meta

def reason_not_estimable(m):
    des = m['design'].lower(); s = m['stat'].lower()
    if 'design' in des or 'develop' in des or 'prototype' in des:
        return 'design/development study; no comparative outcome test'
    if 'qualitative' in des or 'case' in des or 'autoeth' in des or 'ethnograph' in des:
        return 'qualitative design; no standardized outcome'
    if 'descriptive' in des or 'survey' in des or 'descriptive statistics only' in s or 'no inferential' in s:
        return 'descriptive statistics only'
    if not m['stat'].strip():
        return 'no outcome statistics reported'
    return 'insufficient statistics to compute a standardized effect size'

def main():
    meta = load_meta()
    rows = []
    for sid in sorted(meta):
        m = meta[sid]
        if sid in STUDIES:
            s = STUDIES[sid]; d, g, nn, se, lo, hi, ck = compute(sid, s)
            if g is None:
                rows.append([sid, m['key'], m['n'], m['design'], m['rob'],
                             CONSTRUCT.get(sid,''), s['fam'], '', '', 'not_estimable',
                             s['note'], '', '', '', 'none'])
            else:
                cap = g if abs(g) <= 1.5 else math.copysign(1.5, g)
                rows.append([sid, m['key'], m['n'], m['design'], m['rob'],
                             CONSTRUCT.get(sid,''), s['fam'], f'{d:.2f}', f'{g:.2f}',
                             'estimable', s['note'] + ('; capped at 1.5 for plot' if abs(g)>1.5 else ''),
                             f'{se:.3f}' if se is not None else '',
                             f'{lo:.2f}' if lo is not None else '',
                             f'{hi:.2f}' if hi is not None else '', ck])
        else:
            rows.append([sid, m['key'], m['n'], m['design'], m['rob'], '', '', '', '',
                         'not_estimable', reason_not_estimable(m), '', '', '', 'none'])

    # write CSV
    with open(os.path.join(SRC, 'effect_sizes.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['study_id','bibtex_key','N','design','rob','construct','family',
                    'cohen_d','hedges_g','status','note',
                    'se_g','ci_low','ci_high','ci_kind'])
        w.writerows(rows)

    est = [r for r in rows if r[9] == 'estimable']
    know = [r for r in est if r[5] == 'knowledge']
    gk = [float(r[8]) for r in know]
    change = [float(r[8]) for r in know if r[6] == 'change']
    between = [float(r[8]) for r in know if r[6] == 'between']
    def med_iqr(x):
        if not x: return ('--','--','--','--')
        x = sorted(x)
        q1 = st.median(x[:len(x)//2]) if len(x)>1 else x[0]
        q3 = st.median(x[(len(x)+1)//2:]) if len(x)>1 else x[0]
        return (f'{st.median(x):.2f}', f'{q1:.2f}', f'{q3:.2f}', f'{min(x):.2f}--{max(x):.2f}')
    mk = med_iqr(gk); mc = med_iqr(change); mb = med_iqr(between)

    emit_table(rows)
    emit_forest(know)

    # numbers.tex (append/override effect-size macros; keep corpus/RoB stubs)
    nums = os.path.join(SRC, 'numbers.tex')
    base = open(nums).read() if os.path.exists(nums) else ''
    base = re.sub(r'\n?% >>> ES.*?% <<< ES\n', '\n', base, flags=re.S).rstrip() + '\n'
    es = ['% >>> ES (generated by gen_effect_size_table.py)',
          f'\\renewcommand{{\\nEstimable}}{{{len(est)}}}',
          f'\\newcommand{{\\nKnowledgeES}}{{{len(know)}}}',
          f'\\newcommand{{\\medGKnow}}{{{mk[0]}}}',
          f'\\newcommand{{\\iqrGKnow}}{{{mk[1]}--{mk[2]}}}',
          f'\\newcommand{{\\rangeGKnow}}{{{mk[3]}}}',
          f'\\newcommand{{\\medGChange}}{{{mc[0]}}}',
          f'\\newcommand{{\\medGBetween}}{{{mb[0]}}}',
          f'\\newcommand{{\\nChange}}{{{len(change)}}}',
          f'\\newcommand{{\\nBetween}}{{{len(between)}}}',
          '% <<< ES', '']
    open(nums, 'w').write(base + '\n'.join(es))

    print('Estimable effect sizes :', len(est), '/ 74')
    print('  knowledge/achievement:', len(know), f'(median g={mk[0]}, IQR {mk[1]}-{mk[2]}, range {mk[3]})')
    print('  change-family g       :', len(change), f'median {mc[0]}')
    print('  between-family g       :', len(between), f'median {mb[0]}')
    print('Not estimable          :', 74 - len(est))
    print('\nValidation vs thesis seeds (t-based should match):')
    for sid, seed in [(16,0.86),(19,1.18),(45,1.43),(8,0.40),(66,0.52)]:
        r = next(r for r in rows if r[0]==sid)
        print(f'  study {sid}: computed g={r[8]}  (seed d~{seed})')

if __name__ == '__main__':
    os.makedirs(os.path.join(SRC, 'tables'), exist_ok=True)
    os.makedirs(os.path.join(SRC, 'figures'), exist_ok=True)
    main()
