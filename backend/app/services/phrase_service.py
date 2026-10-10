from collections import Counter, defaultdict

from spacy.tokens import Doc


def analyze_phrases(doc: Doc) -> dict:
    """Extract noun chunks and 2–4 token nominal candidates from one parsed doc.

    Count each normalized token span once, even when both extractors find it.
    Distinct overlapping spans are separate candidates, not proven collocations.
    """
    counts = Counter()
    forms = defaultdict(set)
    kinds = defaultdict(set)
    examples = {}
    seen = set()

    def add_phrase(start: int, end: int, kind: str) -> None:
        span = doc[start:end]
        if len(span) < 2 or not all(token.is_alpha for token in span):
            return
        phrase = " ".join((token.lemma_ or token.text).lower() for token in span)
        kinds[phrase].add(kind)
        location = (start, end)
        if location in seen:
            return
        seen.add(location)
        counts[phrase] += 1
        forms[phrase].add(span.text.lower())
        examples.setdefault(phrase, span.sent.text.strip())

    for chunk in doc.noun_chunks:
        start, end = chunk.start, chunk.end
        # Remove boundary stop words, without joining nonadjacent tokens.
        while start < end and doc[start].is_stop:
            start += 1
        while end > start and doc[end - 1].is_stop:
            end -= 1
        add_phrase(start, end, "noun_chunk")

    for sentence in doc.sents:
        for start in range(sentence.start, sentence.end):
            for size in range(2, 5):
                end = start + size
                if end > sentence.end:
                    break
                span = doc[start:end]
                if (
                    span[-1].pos_ in {"NOUN", "PROPN"}
                    and all(
                        token.is_alpha and not token.is_stop
                        and token.pos_ in {"ADJ", "NOUN", "PROPN"}
                        for token in span
                    )
                ):
                    add_phrase(start, end, "candidate")

    phrases = [
        {
            "phrase": phrase,
            "frequency": frequency,
            "forms": sorted(forms[phrase]),
            "types": sorted(kinds[phrase]),
            "example": examples[phrase],
        }
        for phrase, frequency in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]
    return {
        "total_phrases": sum(counts.values()),
        "unique_phrases": len(phrases),
        "phrases": phrases,
    }
