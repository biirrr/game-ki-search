# Planning & Background — Search Processes for Post-Play Game Identification

## 1. Project summary

Participants played two games (order rotated across participants) and were then
given up to 10 minutes to find each game's name using whatever search
strategy they liked. Their screen activity was annotated by human coders into
a controlled action vocabulary. We want to characterize the resulting search
*processes* — not just outcomes — at the level of individual actions,
sequences/patterns, cross-game differences, cross-user (dis)similarity,
annotator effects, and (added 2026-08-19) whether game order/carryover
between the two games shapes strategy.

## 2. Dataset snapshot (updated 2026-08-19, after file regeneration)

From `data/search_process/*.tsv`:

- 21 files, 21 distinct `participant_id` values, one ID per file (regenerated
  by the researcher to fix earlier inconsistent IDs).
- Columns: `participant_id`, `rank` (step order within a session),
  `annotator`, `game`, `language` (only populated for `Query` rows: `EN`/`NE`),
  `action`.
- Controlled action vocabulary (8 values, `Experiment ended` being a
  non-search marker rather than a real action — see §4.2/§6): `Query`,
  `View result list`, `View single result`, `Platform switch`,
  `View AI response`, `View info box`, `Browsing`, `Experiment ended`.
- 5 annotators (`annotator1`–`annotator5`). Each of the 21 main files is
  annotated by a single annotator, and annotators map onto contiguous blocks
  of participant IDs (`annotator1`→ID2–5, `annotator2`→ID6–10,
  `annotator4`→ID11–15, `annotator3`→ID16–21, `annotator5`→ID1). **This
  block structure means annotator is confounded with participant-ID order**
  (and, presumably, with data-collection batch/date) — a limitation to keep
  in mind for RQ5 (§4.5). Re-checking after the ID1/ID6 fix: ID6 is now
  clean (single annotator), but ID1 still has one stray `annotator1` row
  (out of 56) against 54 `annotator5` rows — worth a second look on your
  end, though it's a single row and unlikely to matter.
  - A **fourth data source** exists for RQ5 specifically: the same session
    (ID13) independently annotated by four annotators, kept separately and
    not yet anonymized/added to `data/search_process/`. Once added, this is
    the actual basis for inter-annotator agreement (Cohen's kappa /
    Krippendorff's alpha) — the cross-annotator comparisons on the 21 main
    files (§4.5) remain a confounded, secondary check.
- Two games: *Best Buds vs Bad Guys* (949 annotated events) and *Townscaper*
  (360 annotated events). This volume asymmetry now has a clear
  explanation: **20 of 21 participants found Townscaper (usually in a few
  steps), and 0 of 21 found Best Buds vs Bad Guys.** So the asymmetry isn't
  just "harder" — Best Buds sessions are, without exception, unresolved
  10-minute searches. This reframes RQ3 (see §4.3): success rate can't be
  used as an outcome variable for Best Buds (no variance), and the
  interesting question shifts toward *how* an unresolved search
  unfolds/exhausts itself vs. a resolved one, not just process-shape
  differences between two comparably-solved tasks.
- `Experiment ended` occurs exactly twice per participant (once per game) in
  20/21 files; `ID12` has three occurrences — a minor data quirk worth
  flagging to the researcher, not silently correcting.

**Update 2026-08-19 (RQ7):** two columns added —
`action_details_clean` (destination platform / source site) and
`action_details_num_tokens` (query/text length in tokens); see §4.7.
`ID12`'s duplicate `Experiment ended` is now fixed at the source (2
occurrences, as expected). Total clean event count is now 1,298 (was
1,294) — see §4.7 for the row-count and `#REF!` details.

## 3. How this task differs from the literature we're building on

Two families of prior work are relevant: (a) **stage models** of information
seeking, which give us vocabulary and expectations for what a search process
*should* look like; and (b) **transition/sequence-analysis studies**, which
give us the actual quantitative toolkit. Neither family studied a task quite
like ours, and the differences matter for method choice, so they're made
explicit below rather than left implicit.

Structural features of our task that recur as points of contrast:

- **Closed, ground-truth target.** Participants are searching for the name of
  a specific game they just played — the target exists, is unambiguous, and
  the participant has first-hand experiential knowledge of it (visuals,
  mechanics, characters) rather than a topical information need. Most cited
  studies involve open-ended topical or work-task search where "success" is
  fuzzier.
- **Hard time cap (≤10 min) and a controlled, closed action vocabulary.**
  Our 8 actions are assigned by expert annotators from screen recordings,
  not inferred from system transaction logs (as in log-based studies) or
  self-reported/coded from think-aloud protocols (as in some tactic studies).
  This gives us cleaner, denser labels but a much smaller N.
- **Repeated-measures, two-item design.** The same participants each
  searched for two specific, known games (order rotated) — a controlled
  within-subject comparison that most cited studies don't have, since they
  either study one search domain/task or aggregate heterogeneous queries
  from many unrelated tasks.
- **Small N (21 participants).** Several methods below come from
  large-scale log studies (hundreds of thousands of users) or from social
  science sequence analysis (typically dozens to hundreds of trajectories);
  our N is at the small end, so clustering/statistical results should be
  treated as descriptive/exploratory rather than confirmatory.
- **Annotator as an explicit variable.** None of the cited transition/tactic
  studies model the human coder as a source of variance in the action labels
  themselves — that's usually addressed (if at all) as a one-off
  inter-rater-reliability check before analysis, not as a research question
  in its own right. RQ5 treats it as one.

### 3.1 Stage/process models (theoretical framing)

- Kuhlthau, C. C. (1991). Inside the search process: Information seeking
  from the user's perspective. *Journal of the American Society for
  Information Science*, 42(5), 361–371.
- Ellis, D. (1989). A behavioural approach to information retrieval system
  design. *Journal of Documentation*, 45(3), 171–212.
- Bates, M. J. (1989). The design of browsing and berrypicking techniques
  for the online search interface. *Online Review*, 13(5), 407–424.
- Marchionini, G. (1995). *Information Seeking in Electronic Environments*.
  Cambridge University Press.

**How our project compares.** These models describe multi-stage,
often multi-session research/learning processes (topic selection →
exploration → formulation → collection → presentation, or evolving,
opportunistic "berrypicking" through an information space as the need
itself shifts). Our sessions are single-sitting, time-boxed, and the
information need does *not* evolve — the participant already knows what
they're looking for experientially, they just need to externalize it into a
findable name. We expect a compressed subset of these stages (little to no
"initiation"/problem-formulation phase, no topic drift) and will use these
models mainly to name/interpret phases we *do* see (e.g., early `Query` +
`View result list` cycling as "formulation/exploration", late `View single
result` clusters as "collection/verification") rather than to test the
stage models themselves.

### 3.2 Transition- and tactic-based sequence studies (methodological basis)

- Xie, I., & Joo, S. (2010). Transitions in search tactics during the
  Web-based search process. *Journal of the American Society for
  Information Science and Technology*, 61(11), 2188–2205.
- Goodrum, A. A., Bejune, M. M., & Siochi, A. C. (2003). A state transition
  analysis of image search patterns on the Web. In *Image and Video
  Retrieval* (LNCS 2728, pp. 281–290). Springer.
- Jansen, B. J., Zhang, M., & Spink, A. (2007). Patterns and transitions of
  query reformulation during web searching. *International Journal of Web
  Information Systems*, 3(4), 328–340.
- Liu, J., Sarkar, S., & Shah, C. (2020). Identifying and predicting the
  states of complex search tasks. In *Proceedings of CHIIR '20* (pp.
  193–202). ACM.
- Han, S., Yue, Z., & He, D. (2013). Automatic detection of search tactic
  in individual information seeking: A hidden Markov model approach.
  arXiv:1304.1924.

**How our project compares.**

- *Xie & Joo (2010)* is the closest methodological precedent: manually
  coded search tactics + Markov-chain transition analysis on 31
  participants doing general web search tasks. Our design is smaller but
  more controlled (fixed time cap, fixed closed action set, two known
  targets vs. Xie & Joo's more open task set), so we can push further on
  the *within-subject, cross-item* comparison (RQ3) than they could.
- *Goodrum et al. (2003)* and *Jansen et al. (2007)* both do state/query
  transition analysis, but on unconstrained, large-N web/image search logs
  with no experimental control and no verified ground-truth target — their
  "state" categories are inferred from log signals rather than
  human-annotated from screen recordings. Our data is lower-volume but
  higher-fidelity per session, which pushes us toward exact/small-sample
  methods (exact tests, permutation tests) rather than the asymptotic
  large-sample statistics those studies can rely on.
- *Liu, Sarkar & Shah (2020)* model latent *states* of complex,
  multi-session work tasks and predict transitions between them — a richer
  latent-state framing than plain first-order Markov chains over surface
  actions. Their tasks are complex/exploratory (open-ended, multi-day);
  ours are short, closed, single-target searches, so we likely need far
  fewer latent states, if any — but their state-identification approach is
  a natural extension if a plain action-level Markov chain (RQ2) turns out
  to be too shallow.
- *Han, Yue & He (2013)* apply an HMM to recover latent search tactics from
  behavior sequences and validate against Marchionini's stage model. This
  is a plausible fallback/extension for RQ2 if we want latent states rather
  than surface-action transitions, but with our small N and short
  sequences (session lengths in the 5–50 action range), an HMM is likely
  under-identified unless heavily regularized or fit across pooled
  participants rather than per participant.

### 3.3 Sequence-comparison and clustering methodology

- Abbott, A., & Forrest, J. (1986). Optimal matching methods for
  historical sequence data. *Journal of Interdisciplinary History*, 16(3),
  471–494.
- Gabadinho, A., Ritschard, G., Müller, N. S., & Studer, M. (2011).
  Analyzing and visualizing state sequences in R with TraMineR. *Journal of
  Statistical Software*, 40(4), 1–37.

**How our project compares.** Optimal matching and TraMineR were developed
for social-science *life-course* trajectories (e.g., decades-long
employment/family sequences across hundreds of people), where sequences are
long, states are few, and the research question is about population-level
typologies. Our sequences are much shorter (tens of actions, not tens of
years) and our N is much smaller, so distance-matrix clustering (RQ4) here
is exploratory pattern-finding rather than typology discovery in the
TraMineR sense — we'll validate cluster stability explicitly rather than
treating clusters as a settled typology, and will consider a feature-based
alternative (bag-of-actions/bigrams) as a simpler, more interpretable
complement given the small N.

## 4. Planned methods per research question

### 4.1 RQ1 — How common are the actions individually?
Descriptive statistics: per-action counts and proportions, sliced by
participant, game, and annotator; raw counts and per-session-normalized
rates (session lengths vary considerably, from short Townscaper sessions to
much longer Best Buds sessions).

### 4.2 RQ2 — Typical action patterns or sequences?
- First-order Markov transition matrices, visualized as directed graphs
  (`networkx`, `graphviz`/`pygraphviz`) and/or Sankey diagrams (`plotly`).
  `Experiment ended` is kept in as an explicit **absorbing end-state**
  (per-task terminator, confirmed to occur ~twice per participant) rather
  than stripped out — it's not a search action, but it anchors the chain
  and lets us read off "distance to completion" from any state.
- Frequent/closed sequential pattern mining for multi-step patterns beyond
  single transitions (`prefixspan`), following the "maximal repeating
  pattern" logic of Goodrum et al. (2003).
- If first-order transitions look too shallow, consider latent-state
  modeling (HMM, per Han, Yue & He 2013) fit across pooled sessions rather
  than per participant, given session length.
- Treat `language` (EN/NE, on `Query` rows) as an exploratory covariate
  here rather than a success predictor (confirmed: success is entirely
  game-dependent, not language-dependent — see §4.3) — e.g. does a
  language switch co-occur with a change in action pattern (more
  `Platform switch`/`Browsing`), and does that differ by game?

### 4.3 RQ3 — Differences in strategy between the two games?
- **Reframed given the success split**: 20/21 participants solved
  Townscaper, 0/21 solved Best Buds vs Bad Guys. Success rate itself has no
  variance within Best Buds, so it can't be modeled as a per-game outcome —
  instead, treat Townscaper sessions as (mostly) *resolved* searches and
  Best Buds sessions as uniformly *unresolved, time-capped* searches, and
  compare process shape between those two regimes rather than between two
  comparably-successful tasks.
- Compare per-game transition matrices: chi-square test of independence
  (`scipy.stats.chi2_contingency`) and Jensen–Shannon divergence
  (`scipy.spatial.distance.jensenshannon`) for robustness to sparse cells.
- Compare session-level features (length, action-entropy, query-reformulation
  rate, `Platform switch` proportion) between games with paired tests
  (Wilcoxon signed-rank — within-subject, since the same participants did
  both games).
- For Best Buds specifically, characterize *what an unresolved 10-minute
  search looks like*: does it plateau (repeating the same action loop) or
  keep exploring (novel query/platform combinations until the clock runs
  out)? This is a distinct question from "how does a solved search unfold,"
  and neither Xie & Joo (2010) nor Goodrum et al. (2003) had a task with a
  guaranteed-unresolved arm to compare against.

### 4.4 RQ4 — Clusters of users with similar search processes?
- Sequence-distance clustering: edit distance / optimal matching
  (`textdistance`, `python-Levenshtein`, `edlib`) or DTW (`dtaidistance`,
  `tslearn`) → hierarchical clustering (`scipy.cluster.hierarchy`) or
  k-medoids (`sklearn_extra.cluster.KMedoids`).
- Feature-based alternative: bag-of-actions/bigram vectors → `KMeans` /
  `AgglomerativeClustering` / `HDBSCAN`.
- Explicit cluster-stability check (bootstrap or leave-one-out) given N≈21–22.

### 4.5 RQ5 — Annotator influence?
- **Primary analysis** (data landed 2026-08-19: `data/agreement/`, four
  annotators independently coding participant ID13, both games).
  **Revised from the original plan**: the four annotators' files have
  different row counts (they independently *segmented* the recording, not
  just labeled a shared fixed set of events), so a plain per-`rank`-position
  Cohen's kappa isn't possible — there's no shared item to rate without
  first deciding which events correspond across annotators. Actual method:
  (1) align annotators 1–3 against annotator4 (the annotator who coded
  ID13 in the main dataset) via minimum-edit-distance sequence alignment
  (`Levenshtein.opcodes`); (2) Krippendorff's alpha (`krippendorff`,
  nominal) on the resulting aligned matrix, unmatched positions coded
  missing; (3) pairwise alignment-free sequence similarity (all 6 pairs)
  as a complementary view that doesn't let missing-data handling hide
  segmentation disagreement; (4) a pooled confusion table and per-action
  count comparison to see *where* and *how much* annotators diverge.
- **Secondary/confounded check** on the 21 main files: compare each
  annotator's marginal action distribution and transition matrix pairwise
  (chi-square/G-test, Jensen–Shannon divergence), and a mixed-effects model
  (`statsmodels` `MixedLM`) with annotator as a random effect on
  action/transition counts. Because annotator maps onto contiguous
  participant-ID blocks (§2), any effect found here is annotator
  **confounded with** participant batch/order and cannot be attributed to
  the annotator alone — report it as a secondary, caveated observation, not
  as evidence of annotator effect on its own.

**Both implemented 2026-09-07** (`analysis/rq5_annotator_agreement.py`,
`analysis/rq5b_annotator_confound.py`; results in `results/rq5_annotator_agreement/` and
`results/rq5b_annotator_confound/`; write-up in `reports/report.md` §6). Two things
prompted the follow-up: the agreement sample grew from 4 to 6 annotators
(`annotator5`/`annotator6` added to `data/agreement/` — extra
independent coders on ID13, not annotators of any other participant),
and the secondary check had never actually been built despite being
planned above. Implementation notes:
- Primary analysis re-run cleanly across all 15 annotator pairs; the
  "one bad apple" framing softens to a spectrum — annotator2 is still
  the extreme case (42% Townscaper coverage) but annotator5/6 also
  undercount moderately (56%), worse than annotator1/annotator3
  (78–82%).
- Secondary check's per-participant-first normalization (normalize each
  session before averaging within an annotator's block) is the answer to
  "we can't just look at simple counts" — otherwise whichever annotator's
  block happened to include the longest session would dominate.
  `MixedLM` converged for 6 of 8 features (`View result list` and
  `Platform switch` hit boundary solutions — report those ICCs as
  unreliable, not exactly zero).
- The secondary check's own result argues for caution using it at all:
  annotator2's block has the *longest* Townscaper sessions of any
  annotator, the opposite direction from what the (unconfounded) primary
  finding predicts — most likely genuine participant-level variation
  (ID6–10 searching longer) swamping any segmentation-style signal in
  that particular measure. Take this as confirmation the confound is
  real and non-trivial, not as a contradiction to resolve.
- Cross-checked RQ4 directly, since the secondary check's clearest
  signal (`View AI response`/`View info box`, ICC ≈ 0.13) sits exactly on
  RQ4's cluster-defining actions: RQ4's "AI-assisted"/"AI-quick" cluster
  membership vs. annotator crosstab is close to uniform (not one
  annotator's block) — a real, if partial, reassurance that RQ4's
  individual-style finding isn't primarily an annotator artifact.

### 4.6 RQ6 — Does game order affect strategy, and do participants carry a strategy over? (added 2026-08-19)
Researcher's motivating hypothesis: participants who played Townscaper
first started on a successful, positive note; participants who played
Best Buds first may have built up frustration before reaching Townscaper.
Related: do participants open each game the same way irrespective of
order, or does the second game's opening resemble the first (a carried-over
strategy) more than chance predicts? Game order is derived from the data
itself — `rank` is a single counter spanning both games per participant,
so whichever game has the lower starting rank was played first; no
separate order field is needed.
- **Order effect on session-level features**: for each game, split
  participants into "played this game first" vs. "played it second"
  (unpaired — a participant contributes to only one side per game) and
  compare length/entropy/query-rate/platform-switch-rate with Mann-Whitney
  U (unpaired analogue of RQ3's paired Wilcoxon tests, §4.3).
- **Opening-strategy carryover**: represent each session's opening as its
  first 3 actions; compute each participant's own first-game-opening vs.
  second-game-opening distance (normalized positional mismatch), and
  compare the observed mean against a permutation-test null built by
  randomly re-pairing participants' openings — tests whether people are
  more self-consistent than chance, not just "everyone opens the same
  way" (the null is built from the same real openings, so it already
  absorbs population-wide openers like a near-universal `Platform switch →
  Query` start). Also split carryover strength by which game came first,
  to test the frustration/positive-note hypothesis directly.
- **Order vs. RQ4 cluster membership**: crosstab play position against
  each game's feature-based cluster label from RQ4 (§4.4) — does order
  predict which behavioral subtype a participant falls into? Fisher's
  exact test where the table is 2×2; report as descriptive only where
  cell counts are too small to test (this will bite for Townscaper's
  4-person "AI-quick" cluster).

#### RQ6.4 — Does order change *how* people search within each game, not just whether they do? (added 2026-08-19)
Researcher's follow-up, sharpening the original order hypothesis: is
there a difference between searching Best Buds first vs. searching it
*after* a positive Townscaper experience — and, especially, between
searching Townscaper first vs. searching it *after* the potentially
frustrating experience of Best Buds? The order-effect check above
(session-level features) already came back null, but that's only four
summary numbers; this asks the sharper question with RQ3's full toolkit,
applied *within* each game and split by order, rather than RQ6's
between-game summary stats.

Two comparisons:
- **A. Best Buds: played first (n=10) vs. played second, after a
  Townscaper win (n=11).**
- **B. Townscaper: played first (n=11) vs. played second, after Best
  Buds frustration (n=10).**

Methods, reusing RQ3's machinery but sliced by order instead of by game:
1. **Action-mix comparison** per order-group (like RQ1 §2.2, sliced by
   order): chi-square + Jensen–Shannon divergence on the pooled
   action-count table.
2. **Transition-matrix comparison** per order-group, same per-from-state
   chi-square + JS divergence as RQ3 §4.1 — the real test of "different
   strategy," not just different amounts.
3. **Townscaper closing-move check**: which action precedes
   `Experiment ended`, split by order — does a positive start or Best-Buds
   frustration change *how* Townscaper gets closed out (cf. RQ3 §3.2/§4.1's
   `View info box`/`View single result` exit-probability finding)?
4. **Best Buds half-split, redone per order group**: repeat RQ3 §4.3's
   first-half-vs-second-half entropy/novel-bigram analysis separately for
   BB-first and BB-second — does "running out of steam" look different
   depending on whether Best Buds is a participant's first task ever or
   their second, after already winning once?
5. **Townscaper's one non-solver**: note their order condition as a
   descriptive aside (n=1, not a test).

Caveats to carry into the write-up, not discover after:
- Splitting 21 participants by order leaves ~10–11 per cell, on top of an
  already-small study. RQ3 found only 2 of 7 states statistically robust
  with the *full* 21-vs-21 sample (§4.1) — this will have less power
  still. Lead with effect sizes (JS divergence) over p-values, and be
  explicit about what doesn't survive correction; treat as
  exploratory/descriptive.
- **Confounded with RQ6.2's opening-carryover finding**: if order changes
  the *opening move* (which §4.6 already found — carryover is
  near-perfect for Best-Buds-first participants), that alone could shift
  the whole-session transition matrix without reflecting a genuinely
  different strategy beyond the first step or two. Check whether any
  order effect found here survives after excluding the first 3 actions,
  so opening-carryover and "real" strategy divergence downstream of it
  don't get conflated.

### 4.7 RQ7 — Enriching the action analyses with destination and query-length data (added 2026-08-19)
Two new columns landed in `data/search_process/`: `action_details_clean`
(destination platform for `Platform switch`; source site for
`View single result`) and `action_details_num_tokens` (length of the
withheld free-text `action_details` field — most meaningful for `Query`,
per the researcher). Three uses:
- **Platform-switch destinations, categorized** (search engine / AI
  assistant / storefront / community / game database — built from the 23
  observed values, all mapped; unrecognized future values fall back to
  "Other" rather than being guessed at) — overall, by game, and by RQ4
  cluster. Ground-truths the RQ4 cluster names: does the "AI-assisted"/
  "AI-quick" cluster's platform-switches actually skew toward AI
  assistants?
- **Query length (tokens)**: by game; first-half vs. second-half of Best
  Buds sessions (does RQ3 §4.3's entropy rise come with longer queries,
  or just more varied actions?); by RQ4 cluster, using each
  participant's *median* query length (not mean) as the unit before
  comparing clusters — a per-instance-level test would pseudo-replicate
  (treating each of one participant's many queries as an independent
  observation), inflating significance artificially.
- **View-single-result self-loops** (Townscaper played-second, the
  strongest RQ6.4 finding — 47% self-loop rate): same source repeated
  (double-checking) or different sources (browsing)? `View single
  result`'s source values are long-tailed (60+ distinct values, many
  singleton gaming blogs/forums) so this uses only same/different
  comparison, not a forced taxonomy — the data can't support one for that
  column.

**Data quality, found while wiring this up**: loading the updated files
crashed on a `#REF!` value (an Excel broken-reference error) in
`ID12`'s `rank` column, for the 3 rows right after where that
participant's now-fixed duplicate `Experiment ended` row used to be —
consistent with a formula-based rank column breaking when the researcher
deleted that row upstream. Verified `rank` equals each row's 1-indexed
position in every file wherever `rank` isn't broken, so
`analysis/data.py` now repairs any non-numeric `rank` value by falling
back to row position for that file (flagged via a printed message, not
silent). Also: `ID1` gained 3 events and `ID20` gained 1, both alongside
this same re-export — read as genuine re-annotation corrections (the
sequences remain well-formed) rather than errors, but worth a confirming
glance from the researcher. Net effect on prior results is small
(re-ran RQ1–RQ6.4: all headline numbers hold within rounding) with one
exception: RQ4's Townscaper clustering's optimal k shifted from 3 to 2
(the small "wanderers" outlier pair no longer separates from the
majority cluster at this silhouette-optimal k) — everything downstream
that cites that 3-way split (§4.4, §4.6 RQ6.3, RQ6.4) needs updating to
the 2-cluster result.

### 4.8 RQ11 — Search tactics as recurring action sub-sequences (added 2026-09-09)
Researcher-proposed, inspired by Wildemuth, Oh & Marchionini (2010, in
`literature/`), who derived named search "tactics" from Maximal Repeating
Patterns (MRP) in coded action sequences — found with Siochi & Ehrich's
(1991) suffix-based tool, then **manually** deduplicated so that any MRP
occurrence subsumed by (contained within) a longer MRP at the same
position was discarded, before grouping survivors into tactics by hand.
The open methods question was whether that manual dedup step has an
automatable, principled equivalent. Two complementary answers, both
per-game, both built on the same sentinel-separated per-participant
corpus (`Experiment ended` dropped first — it's a fixed absorbing
bookkeeping marker, not a search move, and would otherwise generate a
trivial "whatever preceded the end" pseudo-tactic in every session):

- **Supermaximal repeats**, via a suffix array + LCP array. A repeat is
  *maximal* if it's both right-maximal (can't extend right without
  losing an occurrence — captured directly by the LCP-array-interval
  structure) and left-maximal (can't extend left without losing one —
  checked by comparing preceding characters); it's *supermaximal* if no
  single occurrence is contained inside an occurrence of another, longer
  maximal repeat. That occurrence-level containment check is the direct
  automated analogue of Wildemuth's manual step — arguably closer to
  what she actually did than a *pattern*-level supermaximal definition
  would be, since she discarded specific instances, not whole patterns.
  Verified against a brute-force reference implementation (exhaustive
  substring enumeration + maximality checks) on a hand-worked example and
  30 random trials — exact match throughout. Naive O(n² log n)
  suffix-array construction (sorting all suffixes directly) is easily
  fast enough at this scale (~340–920 actions per game after dropping
  `Experiment ended`); a doubling algorithm would only be needed for a
  much larger corpus.
- **RE-PAIR grammar compression** (Larsson & Moffat, 1999), a
  Sequitur-family algorithm: repeatedly replace the most frequent
  adjacent symbol pair with a new grammar rule, until no pair repeats.
  Chosen over implementing Sequitur itself — Sequitur's online algorithm
  needs cascading digram-uniqueness repair bookkeeping on every insert,
  which is easy to get subtly wrong, whereas RE-PAIR's offline
  "replace-then-repeat" loop is simple to verify directly (checked by
  reconstructing the original sequence from the grammar, and confirming
  no rule's expansion crosses a sentinel). Every rule has exactly two
  symbols on its right-hand side, so a rule referencing another rule *is*
  the "tactic built from smaller tactics" structure the researcher was
  after — this is the one thing supermaximal repeats can't show, since
  they only return a flat list.

**Occurrences vs. participants (correction, added 2026-09-09 same day)**:
the first pass of this analysis ranked and filtered tactics by raw
occurrence count — how many times a pattern survives subsumption in the
corpus. That over-counts: if one participant's session happens to contain
the same tactic twice, it counts twice even though only one person
actually used it. Fixed by computing, for every repeat (both
supermaximal repeats and RE-PAIR rules), the corpus positions of its
occurrences (`session_of()`, mapping a corpus offset back to the
participant whose sentinel-delimited span contains it) and reporting
`n_participants` — the count of *distinct* participants — alongside the
raw `n_occurrences`. The two are usually equal but not always: Best
Buds' 8-step pattern `Platform switch → View result list → Platform
switch → Query → View result list → Platform switch → View result list
→ Query` has `n_occurrences=3` but `n_participants=2` (one participant
repeated it within their own session). The reporting cutoff (below) now
uses `n_participants`, which changed the headline numbers non-trivially
— see Finding.

**Reporting cutoff**: supermaximal repeats are reported as "tactics"
only at length ≥3 (bigrams are already covered by RQ2's n-gram tables)
and used by ≥3 distinct participants. This is far more conservative
than Wildemuth's count-≥5 cutoff on 141 sequences, but this dataset has
13–21 sequences per game, not 141 — a fixed absolute threshold from a
~7x larger corpus would empty the table. In this data, every pattern
that clears the length filter and reaches the participant cutoff turns
out to have *exactly* 3 participants (nothing reaches 4+) — so the
tactics table currently has no frequency variation to rank by; row order
is then effectively by pattern length (longest first), which is worth
being explicit about rather than implying a frequency ranking that isn't
there. A **building-blocks** summary (`tactic_building_blocks()`)
compensates for the flat list's main weakness — that "dominated by X"
isn't visually obvious from strips alone — by counting, for each
short (2-step) sub-pattern, in how many of the reported tactics it
appears at least once (tactic-level coverage, not raw count): for Best
Buds, `Query → View result list` appears in 7 of the 9 tactics and
`View result list → Query` in 6, confirming the "grinding loop" reading
quantitatively rather than by eyeballing the strips.

**Finding**: the two games' tactic counts diverge sharply, and the
participant-count correction *sharpened* rather than weakened this —
Best Buds vs Bad Guys (unsolved, 0/21) has 143 supermaximal repeats
overall (longest 16 actions), of which **9** are used by ≥3 distinct
participants (longest such tactic: 7 actions); Townscaper (solved,
20/21) has 48 supermaximal repeats overall, but **none** reach 3
participants — its best candidate, a 4-step check-and-move-on pattern,
tops out at 2. Read together with RQ3's plateau finding (§4.3) and RQ4's
clustering, this is a third, independent signal that Best Buds sessions
loop and backtrack in ways Townscaper sessions mostly don't — and unlike
the pre-correction "12 vs. 1" reading, "9 vs. 0" no longer needs a caveat
about what "1" actually meant.

The RE-PAIR trees make the *composition* of that looping visible
directly, now with a participant count on every internal node (not just
the root), so a nested sub-tactic can be read on its own terms: Best
Buds' rule `R25` factors "Query → View result list" repeated twice
(n=11 participants at that sub-tactic level), itself nested two levels
deeper inside `R42`, a 12-step grinding block (n=2 participants) — a
loop built out of a much more common smaller loop. The clearest single
example of within-session repetition surfaced by this fix is `R41`, a
10-step pattern with `n_occurrences=2` but `n_participants=1`: participant
`ID4` performed this exact 10-step sequence twice in a row (corpus
positions 27 apart) within their own Best Buds session — a genuine
stuck-in-a-loop moment, not a cross-participant tactic at all, which the
old occurrence-only count would have silently folded into the same
"used 3 times" bucket as genuinely shared tactics.

### 4.9 RQ10 — Finer-grained platform categories (added 2026-09-09)
Researcher-provided `data/platform_map.json` splits the RQ7/RQ8
"Platform switch" destination into finer categories (Web search / Image
search / Conversational search / Game search / etc.) instead of RQ7's
coarser search-engine/AI-assistant/storefront/community buckets — motivated
by an impression from re-watching sessions that image search specifically
was doing a lot of work RQ7's coarser categories couldn't see. Implemented
via a new `context` column in `analysis/data.py` (`add_platform_context`):
for every action, the platform/website it happens on, reconstructed by
forward-filling the most recent `Platform switch` destination within a
(participant, game) session, except `View single result` rows, which
take their own `action_details_clean` value as context since that's the
one action where the participant is looking at a *different* site than
the one they switched to.

**Correction (added 2026-09-10)**: the original overall-share figures
below used the wrong denominator -- `context.notna()` (1,286 rows)
rather than the actual categorizable subset used everywhere else in this
analysis (`context.notna()` minus `View single result` rows, which are
deliberately left uncategorized, minus `Experiment ended` -- 1,087 rows).
Every share in the Finding below is now computed on the correct 1,087.
Separately, the researcher fixed both data-quality issues this section
used to flag at the source rather than leaving them normalized in code:
the `"Conservational search"` typo is corrected in `platform_map.json`
directly, and `"Moby Games"` / `"MobyGames"` are now both present as
keys mapping to the same category. The researcher also simplified the
map itself, merging every rare category (video/news/list/product/forum
search, TikTok, etc.) into one `Other` bucket, leaving five categories
total: Web / Image / Conversational / Game search, plus Other.

**Finding**: image search is the second most-used category overall (312
of 1,087 categorizable events, **29%**, behind web search's 46%) —
confirming the motivating impression. Cross-checked against RQ4's
clusters: in Townscaper, the "AI-quick" feature-cluster (`n=4`: ID6, ID7,
ID15, ID18) uses image search **0% of the time, unanimously**, while the
majority cluster (`n=16`) averages 35.2%; Best Buds shows the same
direction more weakly (15.4% vs. 29.7%) -- both figures were already
computed on the correctly-scoped per-session subset and are unaffected
by the denominator fix. Read together with RQ4's original AI-vs-majority
split (§5, main report), this suggests image-search reliance and
AI-assistant reliance are two distinct, largely mutually exclusive search
styles rather than something people mix.

### 4.10 RQ12 — Tactics with `Platform switch` split by finer category (added 2026-09-10)
Direct extension of RQ11 (§4.8), reusing its exact machinery (supermaximal
repeats via suffix array + LCP array, RE-PAIR grammar, participant-count
reporting) but with the `Platform switch` state itself expanded into its
`platform_map.json` category wherever known -- `Platform switch: Web
search`, `: Image search`, etc. -- matching RQ9's `build_state` convention
rather than RQ10's broader `context`-recoloring (only the switch event's
own state changes; `Query`, `View result list`, etc. are untouched, so
this stays a direct, comparable variant of RQ11 rather than a different
question). Motivated by RQ11's building-blocks table showing generic
`Platform switch` steps threading through most of Best Buds' reported
tactics -- the open question was whether those were genuinely shared
tactics or just different participants' different platform choices
collapsing to the same coarse label.

Implemented in `analysis/rq12_platform_tactics.py`. The five platform-switch
states get shades of RQ11/RQ2's original `Platform switch` green (Web
search = the original green, progressively lighter through Other) rather
than unrelated hues, so the plots read as "still a platform switch, this
flavor" -- done by extending `rq11_maximal_repeats.MPL_ACTION_COLOR` in
place, since RQ11's plotting functions are reused unmodified.

**Finding**: both true and false. Best Buds' tactic count does drop once
the platform is visible (9 → **7** reported tactics), confirming some of
RQ11's coarse-label matches were really different participants' different
platform choices. But it's not a full collapse: **3 of the 7 survivors
still name a specific platform and still clear the ≥3-participant bar**
(`Conversational search` once, `Image search` twice, `Web search` once)
-- switching to image search specifically (not just "switching" in
general) is itself a tactic several participants converge on
independently. The RE-PAIR tree surfaces a genuinely new composite not
visible in RQ11: rule `R34` (3 participants, 8 steps) chains a web-search
detour *into* an image-search detour within one recurring tactic. Townscaper
goes the other way: RQ11 had zero qualifying tactics, RQ12 has **one**
(`Query → View AI response → View single result`, no platform switch
involved) -- it wasn't visible in RQ11 because a longer, platform-switch-
involving pattern used to subsume its occurrences; splitting the alphabet
broke that containment and let the shorter pattern surface on its own. A
useful methodological note for future granularity changes: finer states
don't only fragment tactics, they can also un-bury shorter ones that a
coarser alphabet's subsumption step had been hiding.

## 5. Python toolkit shortlist

| Purpose | Library |
|---|---|
| Transition graphs | `networkx`, `graphviz` / `pygraphviz` |
| Sankey diagrams | `plotly` |
| Stats (chi-square, entropy, JS-divergence, Wilcoxon) | `scipy.stats`, `scipy.spatial.distance` |
| Sequential pattern mining | `prefixspan` |
| Sequence distances (OM/edit distance/DTW) | `textdistance`, `python-Levenshtein`, `edlib`, `dtaidistance`, `tslearn` |
| Clustering | `scikit-learn`, `sklearn_extra`, `hdbscan` |
| Latent-state modeling | `hmmlearn` |
| Process mining (alternative lens) | `pm4py` |
| Annotator agreement / mixed models | `krippendorff`, `statsmodels` |

## 6. Open decisions before RQ1

Resolved (2026-08-19):
- Participant/annotator mapping is now one ID per file, 21 participants
  total; annotator confound with participant-ID blocks noted in §2/§4.5.
- `language` is treated as an exploratory process covariate, not a success
  predictor (§4.2).
- `Experiment ended` is kept as an explicit absorbing end-state in the
  Markov chain, not stripped out (§4.2).

Resolved (2026-08-19, during RQ2): `ID1.tsv`'s stray `annotator1` row was
fixed by the researcher (confirmed). `ID12.tsv`'s duplicate
`Experiment ended` is still pending the annotator's fix; the dedupe rule
in `analysis/data.py` handles it in the meantime. A second, related data
issue surfaced while building the RQ2 transition graph: `ID10`/Townscaper
had a `Platform switch` recorded *after* `Experiment ended` — breaking the
absorbing-end-state assumption used for the Markov analysis. Per the same
"only the last/first end-marker counts" logic, `analysis/data.py` now
truncates any row after the (deduped) `Experiment ended` marker per
(participant, game). This dropped 1 more event (1,295 → 1,294 total).

Resolved (2026-08-19, during RQ5): four-annotator ID13 agreement files
landed in `data/agreement/`. They confirmed the row-count mismatch flagged
above (53/32/54/62 rows) — annotators segmented independently, not just
labeled a shared set — which is why the RQ5 method (§4.5) uses sequence
alignment rather than a plain per-position Cohen's kappa.

Still open: none. **Resolved 2026-08-19**: the researcher confirmed
`ID1`/`ID20`'s added events and fixed `ID12`'s `rank` column at the
source (the `#REF!` values are gone, real ranks in place) — `data.py`'s
fallback repair no longer triggers for any file. This is now the final,
stable dataset (1,298 clean events); no further "may be slightly off"
caveats needed in the report.
