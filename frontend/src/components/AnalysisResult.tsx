import {
  Alert, Box, Card, CardContent, Chip, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, TextField, Typography,
} from "@mui/material";
import type { AnalyzeResponse } from "../types/analysis";

type AnalysisResultProps = {
  result: AnalyzeResponse;
};

function AnalysisResult({ result }: AnalysisResultProps) {
  const { analysis } = result;
  const statistics = [
    { label: "Characters", value: result.character_count },
    { label: "Total tokens", value: analysis.total_tokens },
    { label: "Vocabulary occurrences", value: analysis.total_words },
    { label: "Unique words", value: analysis.unique_words },
  ];

  return (
    <Card sx={{ mt: 3, borderRadius: 3 }}>
      <CardContent sx={{ p: 3 }}>
        <Alert severity="success" sx={{ mb: 2 }}>
          Document processed successfully!
        </Alert>

        <Typography variant="h5" component="h2" sx={{ fontWeight: 700 }}>
          Vocabulary analysis
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          Source: {result.source}
        </Typography>
        {result.filename && (
          <Typography variant="body2" color="text.secondary" sx={{ overflowWrap: "anywhere" }}>
            File: {result.filename}
          </Typography>
        )}

        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "repeat(2, 1fr)", sm: "repeat(4, 1fr)" }, gap: 2, my: 3 }}>
          {statistics.map(({ label, value }) => (
            <Box key={label} sx={{ p: 2, bgcolor: "grey.50", borderRadius: 2 }}>
              <Typography variant="h5" sx={{ fontWeight: 700 }}>
                {value.toLocaleString()}
              </Typography>
              <Typography variant="body2" color="text.secondary">{label}</Typography>
            </Box>
          ))}
        </Box>

        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Vocabulary counts exclude common stop words, numbers, and punctuation.
          Word forms are grouped under their base word.
        </Typography>

        {analysis.words.length === 0 ? (
          <Alert severity="info">No vocabulary words were found in this text.</Alert>
        ) : (
          <TableContainer sx={{ maxHeight: 560 }} tabIndex={0} role="region" aria-label="Vocabulary words">
            <Table stickyHeader size="small" aria-label="Vocabulary analysis results" sx={{ minWidth: 650 }}>
              <TableHead>
                <TableRow>
                  <TableCell>Word</TableCell>
                  <TableCell align="right">Frequency</TableCell>
                  <TableCell>Forms</TableCell>
                  <TableCell>Part of speech</TableCell>
                  <TableCell>Example</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {analysis.words.map((entry) => (
                  <TableRow key={entry.word} hover sx={{ "& > *": { verticalAlign: "top" } }}>
                    <TableCell component="th" scope="row" sx={{ fontWeight: 600, overflowWrap: "anywhere" }}>
                      {entry.word}
                    </TableCell>
                    <TableCell align="right">{entry.frequency.toLocaleString()}</TableCell>
                    <TableCell sx={{ overflowWrap: "anywhere" }}>{entry.forms.join(", ") || "—"}</TableCell>
                    <TableCell>
                      {entry.part_of_speech ? <Chip label={entry.part_of_speech} size="small" variant="outlined" /> : "—"}
                    </TableCell>
                    <TableCell sx={{ minWidth: 220, overflowWrap: "anywhere" }}>{entry.example || "—"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}

        <TextField
          fullWidth
          multiline
          minRows={5}
          maxRows={12}
          label="Extracted text"
          value={result.text}
          slotProps={{ input: { readOnly: true } }}
          sx={{ mt: 3 }}
        />
      </CardContent>
    </Card>
  );
}

export default AnalysisResult;
