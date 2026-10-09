export interface SavedEntry {
  id: string;
  normalized_text: string;
  kind: "word" | "phrase";
  frequency: number;
  lookup_status: string;
  first_seen_at: string;
  last_seen_at: string;
  meanings: {
    id: string;
    part_of_speech: string;
    meaning_vi: string;
    sort_order: number;
    examples: { english?: string; vietnamese?: string }[];
  }[];
  pronunciations: {
    id: string;
    ipa: string | null;
    accent: string;
    voice: string;
    audio_status: string;
  }[];
  learning_progress: {
    status: string;
    review_step: number;
    interval_days: number;
    next_review_at: string | null;
    last_review_at: string | null;
    review_count: number;
    lapse_count: number;
  } | null;
}

export interface LibraryPage {
  items: SavedEntry[];
  total: number;
  page: number;
  page_size: number;
}
