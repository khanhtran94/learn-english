export interface VocabularyWord {
  word: string;
  frequency: number;
  forms: string[];
  part_of_speech: string;
  example: string;
}

export interface VocabularyPhrase {
  phrase: string;
  frequency: number;
  forms: string[];
  types: ("noun_chunk" | "candidate")[];
  example: string;
}

export interface VocabularyAnalysis {
  total_phrases: number;
  unique_phrases: number;
  phrases: VocabularyPhrase[];
  total_tokens: number;
  total_words: number;
  unique_words: number;
  words: VocabularyWord[];
}

export interface AnalyzeResponse {
  source: string;
  filename: string | null;
  text: string;
  character_count: number;
  analysis: VocabularyAnalysis;
}
