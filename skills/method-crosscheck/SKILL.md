---
name: method-crosscheck
description: |
  Investigate a disagreement between two ways of getting the same result - two software packages (R vs Python vs
  SPSS, two solvers or simulators), two analysts or coders, a simulation vs a measurement, this study vs a published
  value - by aligning the model, definitions, data and settings step by step before blaming either tool. Use when a
  result differs from a reference, before claiming agreement or replication in a paper, or when a reviewer doubts a
  number.
---

# Cross-checking methods

Most disagreements come from the comparison, not from the tool. Typical causes are:
- a different dataset or filtering;
- another definition of the quantity;
- a different default setting;
- another stopping or convergence rule.

Check those first, in order. Talk to the user in their language, Indonesian by default.

## Hard rules

1. **Do not change a validated tool to make numbers agree.** Do not patch a library, a solver or an `edu-stats`
   function to force a match. Change the analysis settings or the model through their documented options, or report
   the difference.
2. **Long or heavy jobs run one at a time**, with a time estimate given to the user before starting.
3. **Report, don't hide.** If a tool still looks wrong after alignment, write a minimal reproducible example (data,
   call, expected and actual values, versions) and help the user report it upstream.

## Checklist (in this order)

1. **Same data?** Same file and version (compare hashes), same cases after filtering, same handling of missing values
   (listwise vs pairwise), same coding of reverse items and categories, same weights.
2. **Same model or quantity?** Write down the definition each tool uses. Common traps:
   - Welch vs Student t;
   - Type I vs Type III sums of squares;
   - population vs sample SD;
   - Cohen's d vs Hedges' g vs d_z for paired data;
   - Pearson vs Spearman;
   - one-sided vs two-sided tests;
   - exact vs asymptotic p;
   - continuity correction;
   - the omega vs alpha estimator;
   - a different reference category or contrast.
   For simulations, check that the geometry, boundary conditions, sources, ports or feeds, material models and output
   definition match.
3. **Same settings?** Defaults differ between packages: ties handling, the degrees-of-freedom correction
   (Greenhouse-Geisser), rotation in factor analysis, the estimator (ML vs WLSMV), random seeds, and the number of
   bootstrap samples. For simulations: the stop criterion, the time step and the solver tolerance.
4. **Same resolution or convergence?** For numerical work, compare converged or extrapolated values, or state the
   discretisation error. A crossing at one mesh level proves nothing.
5. **Same rounding and reporting?** Compare unrounded values. Check units, percent vs fraction, and log vs linear
   scale.
6. **Coders or raters.** For qualitative coding or ratings, compute agreement (Cohen's κ, Krippendorff's α, ICC)
   with `edu-stats` where available. Discuss and resolve disagreements against a written codebook, and report both
   the agreement and the resolution process.
7. **Only now suspect a tool.** Reproduce the difference on the smallest example and check a textbook or reference
   value (for example R's `stats` results or a published worked example). Then report it.

## Output

- A short table: quantity | value A (tool, version, settings) | value B | difference | what was aligned | what
  remains.
- For the paper: the difference after alignment, with the remaining causes named. It is the narrowest true
  statement, for example "agrees within 0.2 % after extrapolation; the remaining gap is due to the port model".
- If needed, a reproducible report for the tool's maintainers.

## With the MCP-dan-Skill-AI-Kependidikan tools (optional)

If the edu-stats and Zetta MCP servers from this toolkit are connected, use them for these steps:

- edu-stats functions are tested against R, pingouin, scipy and G*Power; `replay` reruns a result and checks the
  data hash and library versions, which settles "did the data or the software change?" quickly.
- Rater agreement: edu-stats `inter_rater_kappa` and `icc`.

## When a tool is not available

- If the edu-stats MCP server is not connected, use its command line, which gives the same results and writes
  the same audit log: `python -m edu_stats.cli run <tool> key=value`. If neither works, do not compute the number
  yourself: say which number is missing.
