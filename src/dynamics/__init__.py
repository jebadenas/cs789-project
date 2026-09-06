"""Score-matrix feature extraction + degeneracy classification.

Retained utility only: ``features.extract_features`` (behavioural + triad
fingerprint) and ``classifier.is_degenerate``, which together define the RQ1
attack "clean set" (see ``src.attacks.runner``). The archetypal-analysis /
atypicality lane this package used to host was cut (scope revision 2026-08-18);
its modules were removed. The current state cascade lives in ``src.dynamics2``.
"""
