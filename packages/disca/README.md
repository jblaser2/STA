# DISCA

**Algorithm:** Template-free deep unsupervised clustering (pytorch)  
**Environment:** `disca` conda env  
**Status:** ✅ T4P k=2 complete (did not separate two phases) — lower priority for remaining datasets

---

## Results Summary

| Dataset | Status | k (run / reported) | Mask | ARI | Split | Notes |
|---------|--------|--------------------|------|-----|-------|-------|
| **T4P** | ✅ | k=3 / k=2 | none | — (no GT) | ~630/42 (+junk) | All k values collapse to ~94% dominant class; no structural separation |
| **FM_easy** | ⬜ | k=3 / k=3 | none | — | — | Lower priority given T4P result |
| **FM_hard** | ⬜ | — | — | — | — | Not yet run |
| **T4SS** | ⬜ | — | — | — | — | Not yet run |

> T4P: ran k=2, k=3, k=4 historically — all showed same collapse pattern (~94% dominant class).
> Protocol run (k=3 with junk) not yet done. Given the T4P result, FM_easy is lower priority.

---

## Key Findings

- Template-free deep clustering not competitive with alignment-based methods at this SNR.
- ~94% dominant class pattern at all k — method defaults to trivial solution without domain priors.
- Provides useful lower bound: purely learned features without alignment-based focus mask fail here.

---

## Next Steps

- T4P: run k=3 (2+junk) per protocol with `--nclass 3`.
- FM_easy: run k=3 when bandwidth allows (lower priority).

---

## Files

| Path | Description |
|------|-------------|
| `T4P/results/disca_k2_classes.png` | k=2 result figure |
| `T4P/results/RESULTS.md` | Run notes and output details |
| `research.md` | Package notes, installation, run commands |
| `scripts/data_prep/build_disca_input.py` | Input preparation script |
