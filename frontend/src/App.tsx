
import { useRef, useState } from "react";
import type { ChangeEvent } from "react";

import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Container,
  CssBaseline,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import {
  AutoStories,
  CloudUpload,
  Description,
  PlayArrow,
} from "@mui/icons-material";

import DeleteIcon from "@mui/icons-material/Delete";

type AnalyzeResponse = {
  source: string;
  filename: string | null;
  text: string;
  character_count: number;
};

const API_URL = "http://localhost:8000";
const MAX_FILE_SIZE = 10 * 1024 * 1024;

function App() {
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<AnalyzeResponse | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (
    event: ChangeEvent<HTMLInputElement>
  ) => {
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

  const clearFile = () => {
    setFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
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
          <Stack direction="row" spacing={2} sx={{ mb: 4,  alignItems:"center" }}>
            <AutoStories color="primary" sx={{ fontSize: 40 }} />
            <Box>
              <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
                Learn English
              </Typography>
              <Typography color="text.secondary">
                Build vocabulary from your own documents
              </Typography>
            </Box>
          </Stack>

          <Card sx={{ borderRadius: 3, boxShadow: 3 }}>
            <CardContent sx={{ p: { xs: 3, md: 5 } }}>
              <Typography variant="h5" sx={{ fontWeight: 700, mb: 1 }}>
                Import Learning Material
              </Typography>

              <Typography color="text.secondary" sx={{ mb: 4 }}>
                Paste English text or upload a document.
              </Typography>

              <TextField
                label="English text"
                placeholder="Paste your English article here..."
                multiline
                minRows={7}
                fullWidth
                value={text}
                disabled={!!file || loading}
                onChange={(e) => {
                  setText(e.target.value);
                  setResult(null);
                }}
              />

              <Typography             
                sx={{ my: 3, fontWeight: 600, color: "text.secondary", textAlign: "center" }}
              >
                OR
              </Typography>

              <Box
                sx={{
                  border: "2px dashed",
                  borderColor: "divider",
                  borderRadius: 3,
                  p: 4,
                  textAlign: "center",
                  bgcolor: "#fafbff",
                }}
              >
                <CloudUpload
                  color="primary"
                  sx={{ fontSize: 52, mb: 1 }}
                />

                <Typography  sx={{ fontWeight: 600 }}>
                  Upload a document
                </Typography>

                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ mb: 2 }}
                >
                  PDF, DOCX, DOC - Maximum 10 MB
                </Typography>

                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.docx,.doc"
                  hidden
                  onChange={handleFileChange}
                />

                <Button
                  variant="outlined"
                  startIcon={<CloudUpload />}
                  disabled={loading}
                  onClick={() => fileInputRef.current?.click()}
                >
                  Choose File
                </Button>

                {file && (
                  <Stack
                    direction="row"                  
                    sx={{ alignItems:"center", mt: 2, spacing: 1, flexWrap: "wrap", justifyContent: "center" }}
                  >
                    <Chip
                      icon={<Description />}
                      label={file.name}
                      onDelete={clearFile}
                      deleteIcon={<DeleteIcon />}
                    />
                  </Stack>
                )}
              </Box>

              {error && (
                <Alert severity="error" sx={{ mt: 3 }}>
                  {error}
                </Alert>
              )}

              <Button
                fullWidth
                size="large"
                variant="contained"
                startIcon={
                  loading ? (
                    <CircularProgress size={20} color="inherit" />
                  ) : (
                    <PlayArrow />
                  )
                }
                sx={{ mt: 4, py: 1.5 }}
                disabled={loading || (!file && !text.trim())}
                onClick={handleAnalyze}
              >
                {loading ? "Processing..." : "Analyze Vocabulary"}
              </Button>
            </CardContent>
          </Card>

          {result && (
            <Card sx={{ mt: 3, borderRadius: 3 }}>
              <CardContent sx={{ p: 3 }}>
                <Alert severity="success" sx={{ mb: 2 }}>
                  Document processed successfully!
                </Alert>

                <Typography sx={{ fontWeight: 600 }}>
                  Characters: {result.character_count}
                </Typography>

                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ mt: 1 }}
                >
                  Source: {result.filename ?? result.source}
                </Typography>

                <TextField
                  fullWidth
                  multiline
                  minRows={5}
                  maxRows={12}
                  label="Extracted text"
                  value={result.text}
                  slotProps={{
                    input: { readOnly: true },
                  }}
                  sx={{ mt: 2 }}
                />
              </CardContent>
            </Card>
          )}
        </Container>
      </Box>
    </>
  );
}

export default App;
