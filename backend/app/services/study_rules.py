"""Pure exercise generation and review rules. No model calls during study."""
import random
import re
import unicodedata
from datetime import timedelta
from uuid import uuid4

INTERVALS = (1, 3, 5, 7, 9, 14, 21, 30, 60, 90)


def normalize(value):
    value = unicodedata.normalize('NFC', value).casefold().replace('’', "'")
    return ' '.join(value.strip(' .!?;:').split())


def short_answers(meanings):
    answers = {}
    for meaning in meanings:
        values = meaning.get('short_answers') or re.split(r'[,;\n]', re.sub(r'\([^)]*\)', '', meaning['meaning_vi']))
        for value in values:
            value = value.strip(' .;:')
            if value and len(value) <= 80 and len(value.split()) <= 12:
                answers.setdefault(normalize(value), value)
    return list(answers.values())


def build_question(entry, catalog, mode):
    answers = short_answers(entry['meanings'])
    if not answers and mode != 'cloze':
        return None
    question = {
        'word': entry['normalized_text'], 'meanings': entry['meanings'],
        'ipa': entry.get('ipa'), 'audio_id': entry.get('audio_id'),
        'mode': mode, 'options': [], 'accepted': [],
    }
    if mode == 'cloze':
        # Match whole words/phrases, never a substring such as 'learn' in 'learned'.
        target = entry['normalized_text'].strip()
        if not target:
            return None
        pattern = re.compile(r"(?<![\w'-])" + r'\s+'.join(re.escape(part) for part in target.split()) + r"(?![\w'-])", re.IGNORECASE)
        candidates = []
        for meaning in entry['meanings']:
            for example in meaning.get('examples', []):
                sentence = example.get('english')
                if not isinstance(sentence, str):
                    continue
                matches = list(pattern.finditer(sentence))
                if matches:
                    candidates.append((sentence, matches[0].group()))
        if not candidates:
            return None
        sentence, answer = random.choice(candidates)
        question.update(prompt=pattern.sub('_____', sentence), accepted=[answer], example_sentence=sentence)
    elif mode == 'listening':
        if not question['audio_id']:
            return None
        question.update(prompt='Nghe và nhập từ/cụm tiếng Anh', accepted=[entry['normalized_text']])
    elif mode == 'vi_en':
        prompt = answers[0]
        # Accept other stored English words with the same short Vietnamese meaning.
        accepted = [other['normalized_text'] for other in catalog
                    if normalize(prompt) in {normalize(a) for a in short_answers(other['meanings'])}]
        question.update(prompt=prompt, accepted=list(dict.fromkeys([entry['normalized_text'], *accepted])))
    else:
        valid = {normalize(answer) for answer in answers}
        distractors = {}
        for other in catalog:
            if other['id'] == entry['id']:
                continue
            other_answers = short_answers(other['meanings'])
            # A synonym entry is not used as a source of distractors.
            if valid.intersection(map(normalize, other_answers)):
                continue
            for answer in other_answers:
                if normalize(answer) not in valid:
                    distractors.setdefault(normalize(answer), answer)
        if not distractors:
            return None
        options = [answers[0], *random.sample(list(distractors.values()), min(3, len(distractors)))]
        random.shuffle(options)
        question['options'] = [{'id': str(uuid4()), 'text': value} for value in options]
        question.update(prompt=entry['normalized_text'], accepted=answers)
    return question


def grade(payload, answer):
    if payload['mode'] == 'en_vi':
        option = next((item for item in payload['options'] if item['id'] == answer), None)
        if option is None:
            raise ValueError('Chọn một đáp án trong câu hỏi.')
        answer = option['text']
    return normalize(answer) in {normalize(value) for value in payload['accepted']}


def review_update(progress, correct, is_retry, now):
    before = progress['interval_days']
    step, days, due = progress['review_step'], before, progress['next_review_at']
    eligible = progress['status'] == 'new' or due is None or due <= now
    if not is_retry:
        if not correct:
            step, days = 1, 1
            due = now + timedelta(days=1)
        elif eligible:
            step = min(step + 1, len(INTERVALS))
            days = INTERVALS[step - 1]
            due = now + timedelta(days=days)
    return {'review_step': step, 'interval_days': days, 'next_review_at': due,
            'interval_before': before, 'schedule_changed': due != progress['next_review_at']}
