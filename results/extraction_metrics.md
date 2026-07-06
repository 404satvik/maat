# Extraction eval (25 hand-annotated complaints)

Anchor date 2026-07-07. Gold includes known-hard items (Hindi relative
dates, sub-1000 amounts, Hinglish role words), so these numbers reflect
real weaknesses, not a friendly subset.

| field | precision | recall | F1 | tp | fp | fn |
|---|---|---|---|---|---|---|
| amounts | 1.000 | 0.880 | 0.936 | 22 | 0 | 3 |
| dates | 1.000 | 0.700 | 0.824 | 14 | 0 | 6 |
| parties | 0.536 | 0.556 | 0.545 | 15 | 13 | 12 |
| places | 1.000 | 1.000 | 1.000 | 3 | 0 | 0 |

Party role accuracy on matched parties: 0.933
Timeline event recall: 0.825 (47/57)
