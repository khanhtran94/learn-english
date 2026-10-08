export interface VocabularyWord {
  word: string;
  frequency: number;
  forms: string[];
  part_of_speech: string;
  example: string;
}

export interface VocabularyAnalysis {
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
