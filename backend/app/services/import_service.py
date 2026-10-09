"""Persist one analysis atomically without resetting existing learning data."""
from collections import Counter

from psycopg2.extras import execute_values

from app.database import database_cursor


def save_analysis(analysis: dict) -> dict:
    frequencies = Counter()
    for kind, collection, field in (
        ('word', analysis['words'], 'word'),
        ('phrase', analysis['phrases'], 'phrase'),
    ):
        for item in collection:
            term = ' '.join(item[field].lower().split())
            frequency = item['frequency']
            if not term or not isinstance(frequency, int) or frequency <= 0:
                raise ValueError('Invalid analyzed entry')
            frequencies[(term, kind)] += frequency

    summary = {
        'saved': True,
        'entry_ids': [],
        'word_count': sum(kind == 'word' for _, kind in frequencies),
        'phrase_count': sum(kind == 'phrase' for _, kind in frequencies),
        'occurrences_added': sum(frequencies.values()),
    }
    if not frequencies:
        return summary

    # Consistent ordering reduces deadlocks for concurrent overlapping imports.
    rows = [(term, kind, frequency) for (term, kind), frequency in sorted(frequencies.items())]
    with database_cursor(readonly=False) as cursor:
        entries = execute_values(cursor, '''
            insert into public.entries (normalized_text, kind, frequency)
            values %s
            on conflict (normalized_text, kind) do update set
                frequency = public.entries.frequency + excluded.frequency,
                last_seen_at = now()
            returning id, frequency
        ''', rows, page_size=500, fetch=True)
        execute_values(cursor, '''
            insert into public.learning_progress (entry_id)
            values %s
            on conflict (entry_id) do nothing
        ''', [(row['id'],) for row in entries], page_size=500)
    summary['entry_ids'] = [str(row['id']) for row in sorted(entries, key=lambda row: (-row.get('frequency', 0), str(row['id'])))]
    # Return success only after the transaction context has committed.
    return summary
