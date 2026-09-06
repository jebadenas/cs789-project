# Project Setup & Repository Initialisation

**Date:** 15 March 2026  

## What I Did

Set up the initial project repository for the CS 789 peer-assessment grading engine.

- Created the GitHub repository (`jebadenas/cs789-project`)
- Added `.gitignore` for Python artifacts, data files, and output directories
- Created `requirements.txt` with core dependencies: numpy, pandas, pydantic, networkx, plotly
- Initialised empty `README.md`

## Decisions Made

- **Python + NumPy/Pandas stack** for numerical computation — familiar from coursework and well-suited for matrix operations on score data
- **Pydantic** for data validation — will enforce schema constraints on parsed CSV data
- **NetworkX + Plotly** for graph-based analysis and interactive visualisation
- **Git branching model:** feature branches with PRs to main

## Next Steps

- Parse the COMPSCI 399 peer review CSV exports into a structured format
- Define the ScoreMatrix data model
