
from collections import Counter, defaultdict

import spacy

from app.services.phrase_service import analyze_phrases

# Load model một lần khi module được import.
# Không load lại mỗi khi có request.
nlp = spacy.load("en_core_web_sm")

MAX_TEXT_LENGTH = 200_000


def analyze_vocabulary(text: str) -> dict:
    if not text or not text.strip():
        return {
            "total_tokens": 0,
            "total_words": 0,
            "unique_words": 0,
            "words": [],
            "total_phrases": 0,
            "unique_phrases": 0,
            "phrases": [],
        }

    if len(text) > MAX_TEXT_LENGTH:
        raise ValueError(
            f"Text exceeds {MAX_TEXT_LENGTH} characters"
        )

    doc = nlp(text)

    word_counter = Counter()
    word_forms = defaultdict(set)
    word_pos = {}
    examples = {}

    for token in doc:
        # Bỏ số, dấu câu và ký tự không phải chữ
        if not token.is_alpha:
            continue

        # Bỏ các stop words như the, is, a...
        if token.is_stop:
            continue

        # Chuẩn hóa về dạng gốc
        lemma = token.lemma_.lower().strip()

        if not lemma:
            continue

        # Đếm số lần xuất hiện
        word_counter[lemma] += 1

        # Lưu các dạng từ đã gặp
        word_forms[lemma].add(token.text.lower())

        # Lưu từ loại
        word_pos.setdefault(lemma, token.pos_)

        # Lưu câu ngữ cảnh đầu tiên
        examples.setdefault(lemma, token.sent.text.strip())

    # Sắp xếp giảm dần theo tần suất
    sorted_words = sorted(
        word_counter.items(),
        key=lambda item: (-item[1], item[0]),
    )

    words = [
        {
            "word": lemma,
            "frequency": frequency,
            "forms": sorted(word_forms[lemma]),
            "part_of_speech": word_pos[lemma],
            "example": examples[lemma],
        }
        for lemma, frequency in sorted_words
    ]

    return {
        "total_tokens": len(doc),
        "total_words": sum(word_counter.values()),
        "unique_words": len(words),
        "words": words,
        **analyze_phrases(doc),
    }
