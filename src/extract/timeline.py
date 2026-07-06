"""Timeline assembly: event sentences in narrative order, with dated
runs reordered by resolved date.

An event is a sentence containing an event-cue verb. The description is
the source sentence verbatim; nothing is generated.
"""

from __future__ import annotations

from src.extract.schema import Amount, DateMention, TimelineEvent

EVENT_CUES: frozenset[str] = frozenset(
    {
        "buy", "order", "purchase", "pay", "give", "issue", "deliver",
        "arrive", "bounce", "dishonour", "return", "vacate", "send",
        "receive", "file", "complain", "register", "refuse", "reject",
        "stop", "deduct", "promise", "sign", "book", "cancel", "terminate",
        "move", "leave", "take", "borrow", "lend", "repay", "deposit",
        "demand", "threaten", "lock", "seize", "settle", "supply", "hire",
        "install", "break", "damage", "fail", "expire", "renew", "evict",
        "transfer", "collect", "charge", "claim", "serve", "date",
    }
)


def build_timeline(
    doc,
    dates: list[DateMention],
    amounts: list[Amount],
) -> list[TimelineEvent]:
    """Assemble ordered timeline events from sentences with event cues."""
    events: list[TimelineEvent] = []
    for sent in doc.sents:
        if sent.text.rstrip().endswith("?"):
            continue
        cues = [t.lemma_.lower() for t in sent if t.lemma_.lower() in EVENT_CUES and t.pos_ in ("VERB", "AUX")]
        if not cues:
            continue
        start, end = sent.start_char, sent.end_char
        date_index = next(
            (i for i, d in enumerate(dates) if start <= d.span[0] and d.span[1] <= end),
            None,
        )
        amount_indices = [
            i for i, a in enumerate(amounts) if start <= a.span[0] and a.span[1] <= end
        ]
        events.append(
            TimelineEvent(
                order=0,
                event_cue=cues[0],
                description=sent.text.strip(),
                date_index=date_index,
                amount_indices=amount_indices,
                date_basis="narrative",
                span=[start, end],
            )
        )

    # Reorder maximal contiguous runs where every event has a resolved date.
    i = 0
    while i < len(events):
        j = i
        while (
            j < len(events)
            and events[j].date_index is not None
            and dates[events[j].date_index].iso is not None
        ):
            j += 1
        if j - i >= 2:
            run = sorted(events[i:j], key=lambda e: dates[e.date_index].iso)
            if [e.span for e in run] != [e.span for e in events[i:j]]:
                events[i:j] = run
            for event in events[i:j]:
                event.date_basis = "resolved"
        i = max(j, i + 1)

    for order, event in enumerate(events, start=1):
        event.order = order
    return events
