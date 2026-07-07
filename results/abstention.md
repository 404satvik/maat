# Retrieval abstention thresholds

PROVISIONAL: these thresholds are fit on the existing 18
proxy-labelled eval queries plus 30 forced out-of-scope probes.
They are not human-calibrated and this is not calibration; they are
a first, auditable cut at refusing to show weak results.

## Score distributions (minilm / facts-synthesized / full chunks)

| distribution | n | min | p25 | median | p75 | max |
|---|---|---|---|---|---|---|
| retrieved, proxy-relevant | 105 | 0.298 | 0.496 | 0.559 | 0.6 | 0.677 |
| retrieved, proxy-irrelevant | 75 | 0.302 | 0.489 | 0.547 | 0.595 | 0.684 |
| in-scope query top-1 | 18 | 0.327 | 0.534 | 0.602 | 0.634 | 0.684 |
| out-of-scope query top-1 | 30 | 0.264 | 0.356 | 0.414 | 0.472 | 0.557 |

The relevant and irrelevant distributions among retrieved results
overlap almost completely, so a similarity threshold CANNOT improve
precision within retrieved results and is not claimed to. What
separates cleanly is in-scope versus out-of-scope query top-1
similarity, once queries are content-only (issue-keyword boilerplate
removed after it was measured to inflate off-topic scores).

## Thresholds and their anchors

- Similarity floor 0.44: just above the out-of-scope median
  top-1 (0.414). Below the floor nothing is shown.
- Confidence level 0.54: just above the out-of-scope maximum
  top-1 (0.557). No out-of-scope probe can present
  as confident.
- Minimum query content: 5 words of extractable dispute
  content. Below that, the query falls back to the complaint's
  non-question sentences (amounts stripped); only text still under the
  minimum after fallback abstains outright.
- Fallback cap: queries built from raw-text fallback are capped at
  weak confidence. Fallback text never earned structured extraction,
  and without the cap a vague-but-wordy probe (oth-076) scored 0.557
  against the tenancy corpus and presented as confident.

## Resulting rates

- In-scope (18 eval queries): {'confident': 0.667, 'weak': 0.222, 'abstain': 0.111}
- Out-of-scope (30 forced probes): {'confident': 0.0, 'weak': 0.367, 'abstain': 0.633}

In-scope abstentions are thin-coverage fact patterns (for example a
defective-appliance complaint against a Supreme Court appeals corpus)
where declining to show cases is more honest than showing loose ones.

## Effect on known weak spots

| query | subtopic | state | P@10 unfloored | retained | P among retained |
|---|---|---|---|---|---|
| chq-003 | signature mismatch | confident | 0.1 | 10 | 0.1 |
| probe-chq-010 | security cheque defence | confident | 0.1 | 10 | 0.1 |
| ten-001 | security deposit | weak | 0.1 | 10 | 0.1 |
| ten-060 | commercial premises eviction | abstain | 0.5 | 0 | 0.0 |

The floor mostly does not rescue precision on these (the overlap
finding above predicts exactly that); its value is the abstain and
weak states, not reranking.
