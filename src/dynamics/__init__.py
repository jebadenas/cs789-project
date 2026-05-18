"""Team-dynamics classification pipeline.

Extracts feature vectors from peer-rating score matrices, computes triad-census
fingerprints, fits Archetypal Analysis to discover latent team-dynamic archetypes,
and produces PCA / UMAP visualisations coloured by cross-model disagreement (Δ).

Entry point:
    python3 -m src.dynamics
"""
