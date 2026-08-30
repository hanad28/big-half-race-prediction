# big-half-race-prediction

Predicting my Big Half finish time from a small, honestly-reported training dataset.

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

The reported range for each anchor is the 5th to 95th percentile of the simulated times.

## Results (baseline, generated 2026-08-30 15:32 UTC)

Full artefact: [`results/baseline_prediction.md`](results/baseline_prediction.md)

| Anchor | Point (Riegel, b = 1.06) | 90% range |
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
