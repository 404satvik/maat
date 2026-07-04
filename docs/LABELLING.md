# Labelling policy for the intake classifier

Four classes: `consumer`, `cheque`, `tenancy`, `other`.

## Decision rule

1. `other` means an out-of-scope legal area (employment, family, criminal,
   property title, cyber fraud, and so on) OR text too vague to identify any
   concrete issue.
2. Anything clearly involving one of the three covered areas gets the label
   of the dominant legal remedy. Ties are broken by the hardest deadline or
   the most specific cause of action. Example: a bounced rent cheque is
   `cheque`, because Section 138 NI Act is the actionable route with the
   strictest clock, even though the relationship is landlord and tenant.
3. The classifier models the user's intake conversation, not the merits.
   Where a claim might ultimately fail on a technicality (for example a
   purchase for commercial purpose under the Consumer Protection Act), the
   label still reflects where the triage conversation starts.

## Boundary decisions

Each row below is a decision applied consistently across the dataset, with
example ids from `data/seed/`.

| Situation | Label | Reasoning | Examples |
|---|---|---|---|
| Rent or deposit paid or refunded by a cheque that bounced | cheque | s.138 has the most specific cause of action and a strict notice deadline | chq-004, chq-007, chq-047, probe-ten-012 |
| Salary or settlement paid by a cheque that bounced | cheque | Same dominant-remedy logic; the s.138 clock beats the employment angle | chq-011, chq-019, probe-chq-004 |
| User is the accused / drawer in a s.138 matter | cheque | Still a cheque-bounce conversation, from the defence side | chq-027, chq-033, chq-052, chq-057, chq-066, probe-chq-010 |
| Security deposit not returned after vacating (no cheque involved) | tenancy | The refund wording sounds consumer-flavoured but the relationship and remedy are landlord-tenant | ten-001, ten-009, ten-059 |
| Paying-guest (PG) and hostel deposit disputes | tenancy | Licence rather than lease in strict law, but the dispute has landlord-tenant character for triage | ten-027, probe-ten-010 |
| Complaints from the landlord's side (non-paying or non-vacating tenant) | tenancy | Same issue area; the tool serves both sides of the tenancy relationship | ten-031, ten-040, ten-058, probe-ten-009 |
| Builder delay / flat possession disputes | consumer | Homebuyers proceed as consumers against builders (alongside RERA) | con-014, probe-con-008 |
| Medical negligence at a private provider | consumer | Deficiency in service under consumer law | con-022, con-052 |
| Insurance claim rejection | consumer | Deficiency in service by the insurer | con-031, probe-con-007 |
| Bank service deficiency (wrong charges, failed reversals) | consumer | Banking services are services under consumer law | con-047, con-071, con-074 |
| Goods bought for a small business (commercial purpose) | consumer | May fail the CPA definition on merits; triage still starts as a consumer conversation (see rule 3) | con-055 |
| E-commerce non-delivery or refund stuck with the platform | consumer | Deficiency in service by seller or platform | con-040, con-063, probe-con-004 |
| Cash loan to a friend or relative, no cheque involved | other | Civil recovery, not one of the three areas; the cheque is what makes it `cheque` | oth-005, oth-062 |
| UPI / OTP / online payment fraud by a stranger | other | Cybercrime route dominates; the bank angle is secondary | oth-007, oth-016 |
| Job or visa agent fraud | other | Cheating (criminal) dominates over any consumer angle | oth-019, oth-072 |
| Unpaid salary, termination, PF, gratuity | other | Employment and labour law, out of scope for v1 | oth-001, oth-009, oth-025, oth-042 |
| Online gaming or app winnings withheld | other | Mixed contract/gaming law questions, not clean consumer scope for v1 | oth-078 |

## Language policy

English-primary with a light minority of romanized Hinglish (`lang` column:
`en` or `hi-rom`), roughly one row in ten. No Devanagari in v1. Future work:
supporting Devanagari input implies moving to a MuRIL or IndicBERT class
encoder, since InLegalBERT is trained on English legal text.

## Probe set provenance

`data/seed/probe.csv` is a separate real-world style test set: complaints
hand-rewritten from the phrasing patterns of public complaint text (consumer
forums, legal advice boards), fully de-identified. No raw text was scraped
or stored; no real names, brands, phone numbers, or case numbers appear.
It is never used for training or model selection, only reported alongside
the authored test set to show the authored-versus-real gap honestly.
