# Data Availability Statement

The analysis draws on anonymised peer-feedback exports from five COMPSCI 399
capstone cohorts (S1-2023, S1-2024, S1-2025, S2-2023, S2-2024): 137 teams,
417 team-question score matrices, of which 217 carry usable peer-rating signal.
The raw CSVs contain identifiable student names and university email addresses
and are therefore **not publicly redistributable** under the project's ethics
approval; they are held in the private `data/` directory and excluded from
version control. De-identified derived artifacts (feature matrices, atypicality
scores, attack-Δ summaries, convergence statistics) are regenerated
deterministically from the code and are written to the git-ignored `output/`
directory. All results in this dissertation are fully reproducible from the
committed source: with the pinned `requirements.txt` environment (Python 3.11)
and the source CSVs placed in `data/`, running `python3 -m src report`,
`python3 -m src.dynamics`, `python3 -m src attack --clean-only`,
`python3 -m src.attacks.profile_sweep`, `python3 -m src.evaluation.convergence`,
and `python3 -m src.reporting.aggregate_tables` reproduces every reported
number. All stochastic steps are seeded (attack Monte-Carlo `seed=0`;
archetypal analysis, PCA and UMAP `random_state=42`), so repeated runs are
bit-for-bit identical. Requests for access to the underlying data should be
directed to the course coordinator and are subject to the original ethics
approval and student consent terms.
