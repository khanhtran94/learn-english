import VocabularyLibrary from "../components/VocabularyLibrary";
import DictionarySearch from "../components/DictionarySearch";

export default function LibraryPage({ onLookup }: { onLookup: (term: string) => void }) {
  return <><VocabularyLibrary /><DictionarySearch onLookup={onLookup} /></>;
}
