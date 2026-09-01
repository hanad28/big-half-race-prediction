# big-half-race-prediction

Predicting my Big Half finish time from a small, honestly-reported training dataset.

## Predicted finish time

**1:58 to 2:05**, from the two training anchors closest to race distance (see Calibration below). The full baseline range across all three anchors, a more conservative but less informative figure, is 1:47:00 to 2:07:26.

| Stage | Range | Date |
|---|---|---|
| Baseline (2 anchors) | 1:47:00 to 2:07:26 | 2026-08-30 |
| Calibrated (3 anchors, tightened) | 1:58 to 2:05 | 2026-09-01 |
| Actual result | pending | race day |

Full derivation and the reasoning behind each figure is in Method and Calibration below.

## Overview

This project predicts my finish time for the Big Half (21.0975 km) from 11 logged training runs. The dataset is genuinely small, so it deliberately avoids fitting a supervised machine learning model, which would be statistically indefensible at n = 11. Instead it applies an established sports-science extrapolation method (Riegel's formula) from two different anchor efforts, reconciles the two answers, and reports an honest uncertainty range rather than a single number.

The project is staged on purpose:

1. **Baseline (this stage).** A prediction from the 11-run dataset, generated, timestamped and committed before my final long training run and before race day. The artefact lives at [`results/baseline_prediction.md`](results/baseline_prediction.md).
2. **Calibration (later, separate step).** When the final long run's data arrives, it will be added as a clearly separate calibration step. The baseline artefact will not be edited or overwritten, so the repo history shows what was predicted, and when, before each new piece of evidence arrived.

## Method

### Riegel's formula

Riegel (1981) observed that record times across endurance running distances follow a simple power law:

```
t2 = t1 * (d2 / d1) ^ b
```

where `t1` is a known time over distance `d1`, `t2` is the predicted time over distance `d2`, and `b` is a "fatigue factor" of about 1.06 for running events lasting roughly 3.5 to 230 minutes. Intuitively: if you double the distance, your time slightly more than doubles, because pace degrades as distance grows. The exponent 1.06 quantifies how quickly it degrades.

### Two anchors, two answers

The formula needs a known effort to extrapolate from. This dataset offers two natural anchors, and they disagree:

| Anchor | What it is | Prediction (b = 1.06) |
|---|---|---|
| Fastest 5k effort | Strava's best-effort estimate, 23:35 | 1:48:29 |
| Longest training run | 15.04 km in 88:58 | 2:07:22 |

That is a 19-minute gap, and it is not a bug. It comes from what each anchor actually measures:

- The **5k anchor** is close to a maximal effort, which is what Riegel's model assumes. Extrapolating a short maximal effort out to 21.1 km asks the formula to stretch over a 4x distance ratio, and it implicitly assumes the endurance base to hold that extrapolated pace. Vickers and Vertosick (2016), in a study of 2,303 recreational runners, found the standard 1.06 exponent well calibrated up to the half marathon on average, but optimistic for runners with lower training volume, who are better described by larger exponents. With a short training history like mine, the 5k-based figure is best read as the fast end of the plausible range.
- The **long-run anchor** is much closer to race distance (only a 1.4x extrapolation), which makes the formula more reliable. But it was a steady solo training run, not a race effort, and Riegel's formula assumes maximal efforts at both ends. Feeding it a sub-maximal time inflates the prediction, so the 2:07 figure is best read as the slow end.

The truth plausibly sits between the two, and the honest output is a range, not a midpoint.

### Uncertainty quantification

With n = 11 there is nothing to bootstrap in the usual sense, so the uncertainty comes from a Monte Carlo simulation over the assumptions themselves (20,000 draws per anchor):

- **Exponent:** drawn uniformly from 1.05 to 1.10, spanning Riegel's fitted 1.06 and the higher values Vickers and Vertosick (2016) found for recreational runners.
- **5k anchor time:** scaled by 0.98 to 1.04, because Strava's estimate is a best-effort extraction from within training runs, not a standalone time trial.
- **Long-run effort:** scaled by 0.90 to 1.00, reflecting that a race effort over 15 km would plausibly be up to 10% faster than the logged steady training time.

The reported range for each anchor is the 5th to 95th percentile of the simulated times. To be clear about what that is: the inputs are subjective uniform bounds on the assumptions, so this is a Monte Carlo range under stated assumptions, not a calibrated confidence interval derived from observed sampling uncertainty. It says "if the assumptions are in these ranges, the finish time lands here", nothing stronger.

## Results (baseline, generated 2026-08-30 15:32 UTC)

Full artefact: [`results/baseline_prediction.md`](results/baseline_prediction.md). The artefact was regenerated once at 16:42 UTC the same day, pre-race, to correct the interval labelling; the values are unchanged and no further regeneration will happen before the calibration step.

| Anchor | Point (Riegel, b = 1.06) | Monte Carlo range |
|---|---|---|
| Fastest 5k effort (23:35) | 1:48:29 | 1:47:00 to 1:57:04 |
| Longest training run (15.04 km) | 2:07:22 | 1:55:48 to 2:07:26 |

**Overall baseline range: 1:47:00 to 2:07:26** (union of the two anchor intervals). The overlap zone, roughly 1:56 to 1:57, is where both anchors agree and is a reasonable central expectation.

![Baseline prediction comparison](results/figures/baseline_comparison.png)

To regenerate:

```bash
pip install -r requirements.txt
pip install -e .
python -m big_half.baseline
```

## Calibration (generated 2026-09-01 13:31 UTC)

The final pre-race training run arrived on 2026-08-30: a 10.00 km progression run in 55:54 ([`data/final_long_run.csv`](data/final_long_run.csv)). It is added here as a third Riegel anchor, in a separate artefact at [`results/calibration_prediction.md`](results/calibration_prediction.md). The baseline artefact is untouched, as promised in the Overview.

### Three anchors side by side

| Anchor | Effort type | Point (b = 1.06) | Monte Carlo range |
|---|---|---|---|
| Fastest 5k effort (23:35) | Near-maximal | 1:48:29 | 1:47:00 to 1:57:04 |
| Final progression run (10.00 km, 55:54) | Mixed, partly race effort | 2:03:20 | 1:57:55 to 2:05:20 |
| Longest training run (15.04 km, 88:58) | Steady, sub-maximal | 2:07:22 | 1:55:48 to 2:07:26 |

![Calibration prediction comparison](results/figures/calibration_comparison.png)

### What changed, and what did not

The overall range is unchanged: **1:47:00 to 2:07:26**, still the union of the anchor intervals, because the new anchor's interval sits entirely inside the baseline's overall range. What the third anchor adds is agreement in the middle. Its range (1:57:55 to 2:05:20) sits entirely within the long-run anchor's and starts just above where the 5k anchor's ends, so the two anchors closest to race distance now agree on roughly 1:58 to 2:05. The baseline's central expectation of "roughly 1:56 to 1:57" was set by where its only two anchors overlapped; the new anchor, closer to race distance than the 5k and harder-run than the 15 km, pulls that central expectation towards the low 2:00s.

### Why this anchor's effort assumption differs

The 15 km long run was a steady solo effort throughout, so the baseline assumed a race over that distance could be up to 10% faster (effort scale 0.90 to 1.00). The progression run was not steady: it was comfortable through km 1 to 6, built deliberately hard through km 7 to 9 (HR climbing from 167 to 177), and eased slightly in km 10. Since part of the run was already at or near race effort, assuming a further 10% improvement would double-count effort the athlete has already spent. This anchor instead assumes a race could be up to 5% faster (effort scale 0.95 to 1.00). The 5% figure is a judgement call, not a measured quantity: it says the plausible race-versus-logged gap is about half the steady-run gap, because roughly the later half of the run was already run hard. Reasonable alternatives (say 0.93 or 0.97 at the low end) would shift this anchor's lower bound by a couple of minutes without changing the overall range.

One data-cleaning note for provenance: the raw watch recording continued after the run finished, capturing car travel (pace 3:42/km, cadence 62 against about 77 for every genuine running lap, near-zero power, max speed 38.5 km/h). That segment was removed at source before the data entered this repo, so the 10.00 km / 55:54 figures are the complete, correct run.

## Limitations

- **This prediction is a solo-training baseline.** Every run in the dataset was solo. Race day involves crowds, other runners and pacing off strangers, none of which solo training data can capture. The sports-science literature calls the performance effect of the presence of others social facilitation (Triplett, 1898; Zajonc, 1965). If the actual result comes in faster than predicted, that is consistent with this effect, not proof of it, since a single race is a single data point.
- **The 5k anchor is an estimate, not a race.** Strava's 23:35 is extracted from within training runs. It anchors the fast end of the range but should not be treated as a verified standalone time trial.
- **No half marathon history.** This is a first half marathon build-up, so there is no prior race at or near the target distance to calibrate against, which is exactly the situation where Riegel extrapolation is weakest.
- **Course and conditions ignored.** The model knows nothing about the Big Half's course profile, weather on the day, or fuelling.

## Future Work

- After the race, compare solo training paces against group and event paces over multiple future races. That would turn the social-facilitation point above from a stated limitation into a testable hypothesis with more than one data point.
- Once two or three race results exist at different distances, fit a personal Riegel exponent instead of borrowing the population value.

## References

- Riegel, P.S. (1981) 'Athletic records and human endurance', *American Scientist*, 69(3), pp. 285-290. PMID: 7235349. Available at: https://pubmed.ncbi.nlm.nih.gov/7235349/. Note: this paper predates DOIs; it is the original peer-published source of the formula and is widely cited.
- Vickers, A.J. and Vertosick, E.A. (2016) 'An empirical study of race times in recreational endurance runners', *BMC Sports Science, Medicine and Rehabilitation*, 8, 26. doi: 10.1186/s13102-016-0052-y.
- Triplett, N. (1898) 'The dynamogenic factors in pacemaking and competition', *American Journal of Psychology*, 9(4), pp. 507-533. doi: 10.2307/1412188.
- Zajonc, R.B. (1965) 'Social facilitation', *Science*, 149(3681), pp. 269-274. doi: 10.1126/science.149.3681.269.
