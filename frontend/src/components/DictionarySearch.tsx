import { useState } from "react";
import { Box, Button, Card, CardContent, TextField, Typography } from "@mui/material";

type Props = { onLookup: (term: string) => void };

export default function DictionarySearch({ onLookup }: Props) {
  const [term, setTerm] = useState("");
  return (
    <Card sx={{ mt: 3, borderRadius: 3 }}>
      <CardContent sx={{ p: 3 }}>
        <Typography variant="h6" component="h2" sx={{ mb: 1 }}>Từ điển Anh–Việt</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Tra một từ hoặc cụm từ mỗi lần. Bạn cũng có thể bấm vào từ trong kết quả phân tích.
        </Typography>
        <Box component="form" onSubmit={(event) => { event.preventDefault(); if (term.trim()) onLookup(term.trim()); }} sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
          <TextField size="small" label="Từ hoặc cụm tiếng Anh" value={term} onChange={(event) => setTerm(event.target.value)} slotProps={{ htmlInput: { maxLength: 120 } }} sx={{ flex: 1, minWidth: 180 }} />
          <Button type="submit" variant="contained" disabled={!term.trim()}>Tra nghĩa</Button>
        </Box>
      </CardContent>
    </Card>
  );
}
