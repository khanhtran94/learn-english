export interface DictionaryEntry {
  term: string;
  found: boolean;
  ipa: string | null;
  meanings: {
    part_of_speech: string;
    vietnamese: string;
    examples: { english: string; vietnamese: string }[];
  }[];
  cached: boolean;
  source: "gemini";
}
