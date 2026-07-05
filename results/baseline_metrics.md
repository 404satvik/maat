# Intake baseline metrics

Seed 42, 5-fold group-aware stratified CV over the 320
seed originals with 3 augmentation variants applied inside each
fold to training seeds only. Fixed-split rows train on the pinned train
split and evaluate on the authored test set (n=48) and the real-world
probe set (n=48). Probe numbers are directional at this sample size;
the authored-versus-probe gap is the insight, not small model deltas.

## Cross-validation (held-out originals)

| model | macro-F1 | other recall |
|---|---|---|
| majority | 0.098 +/- 0.003 | 0.200 +/- 0.400 |
| tfidf_logreg | 0.862 +/- 0.033 | 0.724 +/- 0.081 |
| tfidf_linearsvc | 0.858 +/- 0.034 | 0.686 +/- 0.093 |

## Fixed split (train on pinned train split)

| model | eval set | accuracy | macro-P | macro-R | macro-F1 | other recall |
|---|---|---|---|---|---|---|
| majority | test | 0.250 | 0.062 | 0.250 | 0.100 | 0.000 |
| majority | probe | 0.250 | 0.062 | 0.250 | 0.100 | 0.000 |
| tfidf_logreg | test | 0.812 | 0.823 | 0.812 | 0.808 | 0.750 |
| tfidf_logreg | probe | 0.896 | 0.917 | 0.896 | 0.898 | 1.000 |
| tfidf_linearsvc | test | 0.833 | 0.839 | 0.833 | 0.829 | 0.750 |
| tfidf_linearsvc | probe | 0.917 | 0.931 | 0.917 | 0.917 | 1.000 |

### Confusion matrix: tfidf_logreg on test

```
            consumer    cheque   tenancy     other
consumer           7         1         0         4
cheque             0        12         0         0
tenancy            0         0        11         1
other              1         1         1         9
```

### Confusion matrix: tfidf_logreg on probe

```
            consumer    cheque   tenancy     other
consumer          10         0         0         2
cheque             0        11         0         1
tenancy            0         1        10         1
other              0         0         0        12
```

### Confusion matrix: tfidf_linearsvc on test

```
            consumer    cheque   tenancy     other
consumer           8         2         0         2
cheque             0        12         0         0
tenancy            0         0        11         1
other              1         1         1         9
```

### Confusion matrix: tfidf_linearsvc on probe

```
            consumer    cheque   tenancy     other
consumer          10         0         0         2
cheque             0        12         0         0
tenancy            0         1        10         1
other              0         0         0        12
```

### Per-class metrics (fixed split)

| model | eval set | class | precision | recall | F1 | support |
|---|---|---|---|---|---|---|
| tfidf_logreg | test | consumer | 0.875 | 0.583 | 0.700 | 12 |
| tfidf_logreg | test | cheque | 0.857 | 1.000 | 0.923 | 12 |
| tfidf_logreg | test | tenancy | 0.917 | 0.917 | 0.917 | 12 |
| tfidf_logreg | test | other | 0.643 | 0.750 | 0.692 | 12 |
| tfidf_logreg | probe | consumer | 1.000 | 0.833 | 0.909 | 12 |
| tfidf_logreg | probe | cheque | 0.917 | 0.917 | 0.917 | 12 |
| tfidf_logreg | probe | tenancy | 1.000 | 0.833 | 0.909 | 12 |
| tfidf_logreg | probe | other | 0.750 | 1.000 | 0.857 | 12 |
| tfidf_linearsvc | test | consumer | 0.889 | 0.667 | 0.762 | 12 |
| tfidf_linearsvc | test | cheque | 0.800 | 1.000 | 0.889 | 12 |
| tfidf_linearsvc | test | tenancy | 0.917 | 0.917 | 0.917 | 12 |
| tfidf_linearsvc | test | other | 0.750 | 0.750 | 0.750 | 12 |
| tfidf_linearsvc | probe | consumer | 1.000 | 0.833 | 0.909 | 12 |
| tfidf_linearsvc | probe | cheque | 0.923 | 1.000 | 0.960 | 12 |
| tfidf_linearsvc | probe | tenancy | 1.000 | 0.833 | 0.909 | 12 |
| tfidf_linearsvc | probe | other | 0.800 | 1.000 | 0.889 | 12 |
