import { useEffect, useState } from "react";
import { Alert, Box, Button, Card, CardContent, Chip, CircularProgress, Stack, Typography } from "@mui/material";
import StoredAudio from "../components/StoredAudio";
import { API_URL } from "../services/api";
import type { LibraryPage, SavedEntry } from "../types/library";

function Flashcard({ entry }: { entry: SavedEntry }) {
  const [revealed, setRevealed] = useState(false);
  return (
    <Card variant="outlined" sx={{ borderRadius: 3, mt: 2 }}>
      <CardContent sx={{ p: { xs: 3, sm: 5 }, minHeight: 280 }}>
        <Stack direction="row" spacing={1} sx={{ mb: 3 }}>
          <Chip label={entry.kind === "word" ? "Từ" : "Cụm từ"} size="small" />
          <Chip label={`${entry.frequency.toLocaleString("vi-VN")} lần xuất hiện`} size="small" variant="outlined" />
        </Stack>
        <Typography variant="h3" component="h2" sx={{ fontWeight: 700, overflowWrap: "anywhere", mb: 2 }}>{entry.normalized_text}</Typography>
        {entry.pronunciations.map((pronunciation) => (
          <Box key={pronunciation.id} sx={{ mb: 2 }}>
            <Typography color="text.secondary">{pronunciation.accent} · {pronunciation.ipa || "Chưa có IPA"}</Typography>
            {pronunciation.audio_status === "ready" && <StoredAudio id={pronunciation.id} />}
          </Box>
        ))}
        <Button variant="contained" onClick={() => setRevealed((value) => !value)} aria-expanded={revealed} aria-controls="flashcard-answer">
          {revealed ? "Ẩn nghĩa" : "Lật thẻ — xem nghĩa"}
        </Button>
        {revealed && <Box id="flashcard-answer" sx={{ mt: 3 }}>
          {entry.meanings.map((meaning, index) => (
            <Box key={meaning.id} sx={{ mb: 2 }}>
              <Typography sx={{ fontWeight: 600 }}>{index + 1}. {meaning.meaning_vi} ({meaning.part_of_speech})</Typography>
              {meaning.examples.map((example, i) => <Box key={i} sx={{ mt: 1, pl: 2 }}>
                <Typography>{example.english}</Typography>
                <Typography color="text.secondary">{example.vietnamese}</Typography>
              </Box>)}
            </Box>
          ))}
        </Box>}
      </CardContent>
    </Card>
  );
}

export default function FlashcardsPage() {
  const [page, setPage] = useState(1);
  const [data, setData] = useState<LibraryPage | null>(null);
  const [index, setIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_URL}/entries?page=${page}&page_size=20`, { signal: controller.signal })
      .then(async (response) => {
        const result = await response.json();
        if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : "Không tải được thẻ học.");
        return result as LibraryPage;
      })
      .then((result) => { if (!controller.signal.aborted) setData(result); })
      .catch((err: unknown) => { if (!controller.signal.aborted) setError(err instanceof Error ? err.message : "Không thể kết nối backend."); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [page, attempt]);
  const cards = data?.items.filter((entry) => entry.meanings.length > 0) ?? [];
  const card = cards[index];
  const loadPage = (value: number) => { setLoading(true); setError(""); setData(null); setIndex(0); setPage(value); };
  return (
    <Box>
      <Typography variant="h5" component="h1" sx={{ fontWeight: 700, mb: 1 }}>Học flashcard</Typography>
      <Typography color="text.secondary" sx={{ mb: 2 }}>Nhớ nghĩa tiếng Việt trước khi lật thẻ. Từ và cụm từ được xếp theo tần suất cao xuống thấp.</Typography>
      <Alert severity="info" sx={{ mb: 2 }}>Chế độ luyện tập: chưa ghi nhận kết quả nhớ/quên hoặc thay đổi lịch ôn.</Alert>
      {loading && <Box role="status"><CircularProgress size={24} /> Đang tải thẻ…</Box>}
      {error && <Alert severity="error" action={<Button onClick={() => { setError(""); setLoading(true); setAttempt((value) => value + 1); }}>Thử lại</Button>}>{error}</Alert>}
      {!loading && !error && data && <>
        {data.total === 0 ? <Alert severity="info">Kho từ đang trống. Thêm từ và nghĩa vào kho để bắt đầu học.</Alert> : <>
          <Typography variant="body2">Nhóm {page}/{Math.max(1, Math.ceil(data.total / data.page_size))} · {cards.length} thẻ có nghĩa trong {data.items.length} từ/cụm</Typography>
          {!card && <Alert severity="info" sx={{ mt: 2 }}>Nhóm này chưa có từ/cụm đã lưu nghĩa. Bạn có thể xem nhóm khác hoặc kiểm tra Kho từ.</Alert>}
          {card && <>
            <Flashcard key={card.id} entry={card} />
            <Stack direction="row" spacing={2} sx={{ mt: 2, alignItems: "center", justifyContent: "space-between" }}>
              <Button disabled={index === 0} onClick={() => setIndex((value) => value - 1)}>Thẻ trước</Button>
              <Typography aria-live="polite">{index + 1}/{cards.length}</Typography>
              <Button disabled={index === cards.length - 1} onClick={() => setIndex((value) => value + 1)}>Thẻ tiếp</Button>
            </Stack>
          </>}
          <Stack direction="row" spacing={2} sx={{ mt: 3 }}>
            <Button disabled={page === 1} onClick={() => loadPage(page - 1)}>Nhóm trước</Button>
            <Button disabled={page * data.page_size >= data.total} onClick={() => loadPage(page + 1)}>Nhóm tiếp</Button>
            <Button onClick={() => { loadPage(1); setAttempt((value) => value + 1); }}>Tải lại</Button>
          </Stack>
        </>}
      </>}
    </Box>
  );
}
