import type { ChangeEvent } from "react";
import { PlayArrow } from "@mui/icons-material";
import {
  Alert,
  Button,
  Card,
  CardContent,
  CircularProgress,
  TextField,
  Typography,
} from "@mui/material";
import FileUploadField from "./FileUploadField";

type MaterialInputFormProps = {
  text: string;
  file: File | null;
  loading: boolean;
  error: string;
  onTextChange: (value: string) => void;
  onFileChange: (event: ChangeEvent<HTMLInputElement>) => void;
  onClearFile: () => void;
  onAnalyze: () => void;
};

function MaterialInputForm({
  text,
  file,
  loading,
  error,
  onTextChange,
  onFileChange,
  onClearFile,
  onAnalyze,
}: MaterialInputFormProps) {
  return (
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
          onChange={(event) => onTextChange(event.target.value)}
        />

        <Typography
          sx={{
            my: 3,
            fontWeight: 600,
            color: "text.secondary",
            textAlign: "center",
          }}
        >
          OR
        </Typography>

        <FileUploadField
          file={file}
          disabled={loading}
          onFileChange={onFileChange}
          onClearFile={onClearFile}
        />

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
          onClick={onAnalyze}
        >
          {loading ? "Đang phân tích và lưu..." : "Phân tích và lưu vào kho"}
        </Button>
      </CardContent>
    </Card>
  );
}

export default MaterialInputForm;
