import {
  Alert, Button, Box, Chip, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, Typography,
} from "@mui/material";
import type { VocabularyAnalysis } from "../types/analysis";

type PhraseResultsProps = {
  analysis: VocabularyAnalysis;
  onLookup: (term: string) => void;
};

function PhraseResults({ analysis, onLookup }: PhraseResultsProps) {
  return (
    <Box sx={{ mt: 4 }}>
      <Typography variant="h6" component="h3" sx={{ fontWeight: 700 }}>
        Phrases ({analysis.unique_phrases.toLocaleString()})
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {analysis.total_phrases.toLocaleString()} phrase occurrences. Noun chunks and
        candidate phrases are grouped by base form. Overlapping phrases may appear;
        candidates are not necessarily fixed expressions.
      </Typography>
      {analysis.phrases.length === 0 ? (
        <Alert severity="info">No multi-word phrases were found in this text.</Alert>
      ) : (
        <TableContainer sx={{ maxHeight: 560 }} tabIndex={0} role="region" aria-label="Phrases">
          <Table stickyHeader size="small" aria-label="Phrase analysis results" sx={{ minWidth: 650 }}>
            <TableHead>
              <TableRow>
                <TableCell>Phrase</TableCell>
                <TableCell align="right">Frequency</TableCell>
                <TableCell>Forms</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Example</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {analysis.phrases.map((entry) => (
                <TableRow key={entry.phrase} hover sx={{ "& > *": { verticalAlign: "top", overflowWrap: "anywhere" } }}>
                  <TableCell component="th" scope="row" sx={{ fontWeight: 600 }}><Button onClick={() => onLookup(entry.forms[0] || entry.phrase)} sx={{ textTransform: "none", justifyContent: "flex-start", p: 0, minWidth: 0 }}>{entry.phrase}</Button></TableCell>
                  <TableCell align="right">{entry.frequency.toLocaleString()}</TableCell>
                  <TableCell>{entry.forms.join(", ")}</TableCell>
                  <TableCell>
                    <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
                      {entry.types.map((type) => (
                        <Chip key={type} label={type === "noun_chunk" ? "Noun chunk" : "Candidate"} size="small" variant="outlined" />
                      ))}
                    </Box>
                  </TableCell>
                  <TableCell sx={{ minWidth: 220 }}>{entry.example || "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );
}

export default PhraseResults;
