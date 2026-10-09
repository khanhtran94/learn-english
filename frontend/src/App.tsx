
import { useState } from "react";
import type { ChangeEvent } from "react";
import { Box, Container, CssBaseline } from "@mui/material";
import AppHeader from "./components/AppHeader";
import AnalysisResult from "./components/AnalysisResult";
import MaterialInputForm from "./components/MaterialInputForm";
import type { AnalyzeResponse } from "./types/analysis";

import { API_URL } from "./services/api";
import DictionarySearch from "./components/DictionarySearch";
import DictionaryDialog from "./components/DictionaryDialog";
const MAX_FILE_SIZE = 10 * 1024 * 1024;

function App() {
  const [dictionaryTerm, setDictionaryTerm] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<AnalyzeResponse | null>(null);

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (!selectedFile) return;

    setError("");
    setResult(null);
    setFile(null);

    const extension = selectedFile.name
      .split(".")
      .pop()
      ?.toLowerCase();

    if (!["pdf", "docx", "doc"].includes(extension ?? "")) {
      setError("Chỉ hỗ trợ PDF, DOCX hoặc DOC.");
      event.target.value = "";
      return;
    }

    if (selectedFile.size > MAX_FILE_SIZE) {
      setError("File không được vượt quá 10 MB.");
      event.target.value = "";
      return;
    }

    setFile(selectedFile);
    setText("");
  };

  const handleTextChange = (value: string) => {
    setText(value);
    setResult(null);
  };

  const clearFile = () => {
    setFile(null);
  };

  const handleAnalyze = async () => {
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const formData = new FormData();

      if (file) {
        formData.append("file", file);
      } else {
        formData.append("text", text);
      }

      const response = await fetch(`${API_URL}/analyze`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Không thể xử lý tài liệu."
        );
      }

      setResult(data as AnalyzeResponse);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Có lỗi xảy ra."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <CssBaseline />

      <Box sx={{ minHeight: "100vh", bgcolor: "#f5f7fb", py: 6 }}>
        <Container maxWidth="md">
          <AppHeader />

          <MaterialInputForm
            text={text}
            file={file}
            loading={loading}
            error={error}
            onTextChange={handleTextChange}
            onFileChange={handleFileChange}
            onClearFile={clearFile}
            onAnalyze={handleAnalyze}
          />

          <DictionarySearch onLookup={setDictionaryTerm} />
          {result && <AnalysisResult result={result} onLookup={setDictionaryTerm} />}
          {dictionaryTerm && <DictionaryDialog key={dictionaryTerm} term={dictionaryTerm} onClose={() => setDictionaryTerm(null)} />}
        </Container>
      </Box>
    </>
  );
}

export default App;
