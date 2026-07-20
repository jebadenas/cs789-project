"""Hand-labelling tooling for the RQ3 team-dynamics anchor set (handoff-4).

Three small, independently runnable modules that produce a ~40-team hand-labelled
validation set, blind to model output, per notes/labelling-rubric.md:

    sample.py   stratified team-level sampler        -> labelling_sample.csv
    cards.py    blinded one-page-per-team PDF + key   -> cards.pdf, card_key.csv
    kappa.py    two-rater agreement scorer            -> Cohen's kappa + disagreements

See README.md for the rater workflow and docs/labelling-design.md for the
design decisions (unit, strata, quota, blinding, reliability).
"""
