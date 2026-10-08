import { Alert, Card, CardContent, TextField, Typography } from "@mui/material";
import type { AnalyzeResponse } from "../types/analysis";

type AnalysisResultProps = {
  result: AnalyzeResponse;
};

function AnalysisResult({ result }: AnalysisResultProps) {
  return (
    <Card sx={{ mt: 3, borderRadius: 3 }}>
      <CardContent sx={{ p: 3 }}>
        <Alert severity="success" sx={{ mb: 2 }}>
          Document processed successfully!
        </Alert>

        <Typography sx={{ fontWeight: 600 }}>
          Characters: {result.character_count}
        </Typography>

        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
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
  );
}

export default AnalysisResult;
