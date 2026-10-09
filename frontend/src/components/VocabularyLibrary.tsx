import StoredAudio from "./StoredAudio";
import { useEffect, useState } from "react";
import {
  Accordion, AccordionDetails, AccordionSummary, Alert, Box, Button,
  Card, CardContent, Chip, CircularProgress, MenuItem, Pagination,
  Stack, TextField, Typography,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { API_URL } from "../services/api";
import type { LibraryPage, SavedEntry } from "../types/library";

const lookupLabels: Record<string, string> = {
  pending: "Chưa tra nghĩa", processing: "Đang tra nghĩa", ready: "Đã có dữ liệu từ điển",
  not_found: "Chưa tìm thấy nghĩa", failed: "Tra nghĩa thất bại",
};
const audioLabels: Record<string, string> = {
  pending: "Chưa có audio", processing: "Đang tạo audio", not_found: "Không có audio", failed: "Tạo audio thất bại",
};
const dateLabel = (value: string) => new Date(value).toLocaleString("vi-VN");

async function readResponse(response: Response) {
  const data = await response.json().catch(() => null);
  if (!response.ok || !data) throw new Error(typeof data?.detail === "string" ? data.detail : "Không tải được dữ liệu từ backend.");
  return data;
}

function EntryDetails({ entry }: { entry: SavedEntry }) {
  const progress = entry.learning_progress;
  return (
    <Stack spacing={2}>
      <Typography variant="body2" color="text.secondary">
        Gặp lần đầu: {dateLabel(entry.first_seen_at)} · Gặp gần nhất: {dateLabel(entry.last_seen_at)}
      </Typography>
      <Box>
        <Typography sx={{ fontWeight: 700 }}>Nghĩa và ví dụ</Typography>
        {entry.meanings.length === 0 && <Typography color="text.secondary">Chưa có nghĩa được lưu trong DB.</Typography>}
        {entry.meanings.map((meaning, index) => (
          <Box key={meaning.id} sx={{ mt: 1 }}>
            <Typography>{index + 1}. {meaning.meaning_vi} <Typography component="span" color="text.secondary">({meaning.part_of_speech})</Typography></Typography>
            {meaning.examples.map((example, i) => (
              <Box key={i} sx={{ pl: 2, mt: 1, borderLeft: 2, borderColor: "divider" }}>
                <Typography>{example.english}</Typography>
                <Typography variant="body2" color="text.secondary">{example.vietnamese}</Typography>
              </Box>
            ))}
          </Box>
        ))}
      </Box>
      <Box>
        <Typography sx={{ fontWeight: 700 }}>Phát âm</Typography>
        {entry.pronunciations.length === 0 && <Typography color="text.secondary">Chưa có phiên âm hoặc audio được lưu.</Typography>}
        {entry.pronunciations.map((pronunciation) => (
          <Box key={pronunciation.id} sx={{ mt: 1 }}>
            <Typography>{pronunciation.accent} · {pronunciation.ipa || "Chưa có IPA"}</Typography>
            {pronunciation.audio_status === "ready" ? <StoredAudio id={pronunciation.id} /> : <Typography color="text.secondary">{audioLabels[pronunciation.audio_status] || pronunciation.audio_status}</Typography>}
          </Box>
        ))}
      </Box>
      <Box>
        <Typography sx={{ fontWeight: 700 }}>Tiến độ học</Typography>
        {!progress ? <Typography color="text.secondary">Chưa tạo tiến độ học cho từ/cụm này.</Typography> : progress.status === "new" ? <Typography>Chưa học</Typography> : (
          <>
            <Typography>Bước {progress.review_step} · Khoảng ôn {progress.interval_days} ngày</Typography>
            <Typography>Ôn tiếp: {progress.next_review_at ? dateLabel(progress.next_review_at) : "Chưa lên lịch"}</Typography>
            <Typography>Đã học/ôn {progress.review_count} lần · Quên {progress.lapse_count} lần</Typography>
          </>
        )}
      </Box>
    </Stack>
  );
}

function LibraryResults({ kind }: { kind: string }) {
  const [page, setPage] = useState(1);
  const [data, setData] = useState<LibraryPage | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [version, setVersion] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    const params = new URLSearchParams({ page: String(page), page_size: "20" });
    if (kind) params.set("kind", kind);
    fetch(`${API_URL}/entries?${params}`, { signal: controller.signal })
      .then(readResponse)
      .then((result: LibraryPage) => { if (!controller.signal.aborted) setData(result); })
      .catch((err: unknown) => { if (!controller.signal.aborted) setError(err instanceof Error ? err.message : "Không thể kết nối backend."); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [page, kind, version]);
  const refresh = () => { setLoading(true); setError(""); setData(null); setVersion((value) => value + 1); };
  return (
    <Box>
      <Button onClick={refresh} disabled={loading} sx={{ mb: 2 }}>Tải lại dữ liệu</Button>
      {loading && <Stack direction="row" spacing={1} sx={{ alignItems: "center" }} role="status"><CircularProgress size={20} /><Typography>Đang tải kho từ…</Typography></Stack>}
      {error && <Alert severity="error">{error}</Alert>}
      {!loading && !error && data && (
        <>
          <Typography variant="body2" sx={{ mb: 2 }}>Tổng {data.total.toLocaleString("vi-VN")} từ/cụm · Tần suất cao trước</Typography>
          {data.items.length === 0 && <Alert severity="info">Chưa có từ/cụm trong danh sách này.</Alert>}
          {data.items.map((entry) => (
            <Accordion key={entry.id} disableGutters>
              <AccordionSummary expandIcon={<ExpandMoreIcon />} aria-controls={`entry-${entry.id}`} id={`heading-${entry.id}`}>
                <Stack direction="row" useFlexGap spacing={1} sx={{ flexWrap: "wrap", alignItems: "center" }}>
                  <Typography sx={{ fontWeight: 700, overflowWrap: "anywhere" }}>{entry.normalized_text}</Typography>
                  <Chip size="small" label={entry.kind === "word" ? "Từ" : "Cụm từ"} />
                  <Chip size="small" color="primary" variant="outlined" label={`${entry.frequency.toLocaleString("vi-VN")} lần`} />
                  <Typography variant="body2" color="text.secondary">{lookupLabels[entry.lookup_status] || entry.lookup_status}</Typography>
                </Stack>
              </AccordionSummary>
              <AccordionDetails id={`entry-${entry.id}`}><EntryDetails entry={entry} /></AccordionDetails>
            </Accordion>
          ))}
          {data.total > data.page_size && <Pagination sx={{ mt: 2 }} count={Math.ceil(data.total / data.page_size)} page={page} onChange={(_, value) => { setLoading(true); setError(""); setData(null); setPage(value); }} />}
          {data.items.length === 0 && page > 1 && <Button onClick={() => { setLoading(true); setPage(1); }}>Về trang đầu</Button>}
        </>
      )}
    </Box>
  );
}

export default function VocabularyLibrary() {
  const [kind, setKind] = useState("");
  return (
    <Card sx={{ mt: 3, borderRadius: 3 }}>
      <CardContent sx={{ p: 3 }}>
        <Typography variant="h5" component="h2" sx={{ fontWeight: 700 }}>Kho từ đã lưu</Typography>
        <Typography color="text.secondary" sx={{ mt: 1, mb: 2 }}>Bấm vào từ/cụm để xem nghĩa, phát âm và lịch ôn đã lưu.</Typography>
        <TextField select size="small" label="Loại" value={kind} onChange={(event) => setKind(event.target.value)} sx={{ minWidth: 160, mb: 2 }}>
          <MenuItem value="">Tất cả</MenuItem><MenuItem value="word">Từ</MenuItem><MenuItem value="phrase">Cụm từ</MenuItem>
        </TextField>
        <LibraryResults key={kind} kind={kind} />
      </CardContent>
    </Card>
  );
}
