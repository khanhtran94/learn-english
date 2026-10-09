import { useState } from "react";
import type { ChangeEvent } from "react";
import { Typography } from "@mui/material";
import MaterialInputForm from "../components/MaterialInputForm";
import AnalysisResult from "../components/AnalysisResult";
import type { AnalyzeResponse } from "../types/analysis";
import { API_URL } from "../services/api";

const MAX_FILE_SIZE = 10 * 1024 * 1024;

export default function UploadPage({ onLookup }: { onLookup: (term: string) => void }) {
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
      <Typography variant="h5" component="h1" sx={{ fontWeight: 700, mb: 2 }}>Tải tài liệu</Typography>
      <MaterialInputForm
        text={text} file={file} loading={loading} error={error}
        onTextChange={handleTextChange} onFileChange={handleFileChange}
        onClearFile={clearFile} onAnalyze={handleAnalyze}
      />
      {result && <AnalysisResult result={result} onLookup={onLookup} />}
    </>
  );
}
