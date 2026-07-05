# Intake classifier: baselines versus InLegalBERT

InLegalBERT (law-ai/InLegalBERT) fine-tuned for 4-class sequence
classification on the pinned train split, 5 runs with seeds
[42, 43, 44, 45, 46]. Checkpoint selection per run: best val macro-F1
(epochs=4, batch=16, lr=2e-05,
weight_decay=0.01, warmup=0.1,
max_length=256, truncation only, no tuning against test
or probe). Texts exceeding max_length before truncation:
train 0, val 0, test 0, probe 0.

Baseline rows are single fixed-split runs (deterministic given the
seed); InLegalBERT rows are mean +/- std across the fine-tune seeds.

## Combined comparison (fixed split)

| model | eval set | accuracy | macro-F1 | other recall |
|---|---|---|---|---|
| majority | test | 0.250 | 0.100 | 0.000 |
| majority | probe | 0.250 | 0.100 | 0.000 |
| tfidf_logreg | test | 0.812 | 0.808 | 0.750 |
| tfidf_logreg | probe | 0.896 | 0.898 | 1.000 |
| tfidf_linearsvc | test | 0.833 | 0.829 | 0.750 |
| tfidf_linearsvc | probe | 0.917 | 0.917 | 1.000 |
| inlegalbert | test | 0.921 +/- 0.024 | 0.920 +/- 0.025 | 0.900 +/- 0.033 |
| inlegalbert | probe | 0.917 +/- 0.023 | 0.915 +/- 0.024 | 1.000 +/- 0.000 |

## InLegalBERT on test: pooled over 5 runs

Confusion matrix (counts summed across runs):

```
            consumer    cheque   tenancy     other
consumer          50         0         3         7
cheque             0        60         0         0
tenancy            0         3        57         0
other              6         0         0        54
```

| class | precision | recall | F1 | support |
|---|---|---|---|---|
| consumer | 0.893 | 0.833 | 0.862 | 60 |
| cheque | 0.952 | 1.000 | 0.976 | 60 |
| tenancy | 0.950 | 0.950 | 0.950 | 60 |
| other | 0.885 | 0.900 | 0.893 | 60 |

## InLegalBERT on probe: pooled over 5 runs

Confusion matrix (counts summed across runs):

```
            consumer    cheque   tenancy     other
consumer          50         1         5         4
cheque             0        60         0         0
tenancy            0         5        50         5
other              0         0         0        60
```

| class | precision | recall | F1 | support |
|---|---|---|---|---|
| consumer | 1.000 | 0.833 | 0.909 | 60 |
| cheque | 0.909 | 1.000 | 0.952 | 60 |
| tenancy | 0.909 | 0.833 | 0.870 | 60 |
| other | 0.870 | 1.000 | 0.930 | 60 |

## Honest comparison writeup

Against the linear reference (TF-IDF + LogReg, the better CV other-class
recall of the two baselines), InLegalBERT lands at macro-F1 0.920 +/- 0.025 on the authored test set versus 0.808 for LogReg (delta +0.112), and 0.915 +/- 0.024 on the probe set versus 0.898 (delta +0.017).
Measured against the baseline CV fold std of 0.033, the test-set difference is clearly ahead (more than one CV std) and the probe difference is within noise (less than one CV std).

Reading either way: complaints are short and keyword-dense, which is
close to the best case for a TF-IDF linear model, while InLegalBERT is
pretrained on formal judgment prose (a register mismatch with colloquial
and Hinglish complaint text) and fine-tuned here on only about 224
original seeds per class plus surface-level variants. A transformer win
would need to come from reading context rather than keywords, for
example separating a bounced rent cheque from a plain deposit dispute,
or catching vague other-class texts that share no vocabulary with
training. Sample sizes are small (n=48 per eval set, about 12 per
class), so probe numbers are directional and only differences well
beyond one CV std should be taken as real.

That is the pattern observed here: the transformer pulls clearly
ahead on the authored test set, which deliberately concentrates
boundary cases and vaguer phrasings, while on the keyword-dense
probe set the linear model already captures most of the signal
and the difference stays within noise.
