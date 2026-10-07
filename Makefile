RQ_TARGETS := rq1 rq2 rq3 rq4 rq5 rq5b rq6 rq6_4 rq7 rq8 rq9 rq10 rq11 rq12 rq13

.PHONY: report latex clean rq-all $(RQ_TARGETS)

# Regenerate reports/report.html from reports/report.md (requires the
# `markdown` package: pip install markdown).
report: reports/report.html

reports/report.html: reports/report.md reports/build_html.py
	python3 reports/build_html.py

# Regenerate reports/tables/*.tex (LaTeX tables for the paper, via \input{})
# from the results/rqN_*/ outputs.
latex:
	python3 reports/build_latex_tables.py

# Rerun individual analysis scripts (each writes its own results/rqN_*/
# directory). Run from the repo root, e.g. `make rq3`.
rq1: ; python3 analysis/rq1_action_frequencies.py
rq2: ; python3 analysis/rq2_patterns.py
rq3: ; python3 analysis/rq3_game_differences.py
rq4: ; python3 analysis/rq4_clustering.py
rq5: ; python3 analysis/rq5_annotator_agreement.py
rq5b: ; python3 analysis/rq5b_annotator_confound.py
rq6: ; python3 analysis/rq6_order_effects.py
rq6_4: ; python3 analysis/rq6_4_order_within_game.py
rq7: ; python3 analysis/rq7_platform_details.py
rq8: ; python3 analysis/rq8_platform_sequence.py
rq9: ; python3 analysis/rq9_expanded_markov.py
rq10: ; python3 analysis/rq10_finer_platform_categories.py
rq11: ; python analysis/rq11_maximal_repeats.py --min-repeat-length 3 --min-participants 3
rq12: ; python3 analysis/rq12_platform_tactics.py
# rq13 reads rq11's tactics_*.csv output, so rq11 must run first.
rq13: rq11 ; python3 analysis/rq13_experience.py

# Rerun every RQ analysis script.
rq-all: $(RQ_TARGETS)

clean:
	rm -f reports/report.html
