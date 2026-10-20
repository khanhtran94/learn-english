import EnrichmentQueue from "./EnrichmentQueue";
import StoredAudio from "./StoredAudio";
import { useCallback, useEffect, useState } from "react";
import {
  Alert, Box, Button, Card, CardContent, Chip, CircularProgress, Dialog,
  DialogActions, DialogContent, DialogTitle, MenuItem, Pagination,
  Stack, Tab, Tabs, Table, TableBody, TableCell, TableContainer, TableHead,
  TableRow, TextField, Typography,
} from "@mui/material";
import { API_URL, apiFetch } from "../services/api";
import type { LibraryPage, SavedEntry } from "../types/library";
const audioLabels: Record<string, string> = { pending: "Chưa có audio", processing: "Đang tạo audio", not_found: "Không có audio", failed: "Tạo audio thất bại" };
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
            <Typography>Đã học/ôn {progress.review_count} lần · Đúng {progress.correct_count ?? 0} lần · Quên {progress.lapse_count} lần</Typography>
          </>
        )}
      </Box>
    </Stack>
  );
}
function LibraryResults({ kind, ignored }: { kind: string; ignored: boolean }) {
  const [hasMeaning, setHasMeaning] = useState(true);
  const [page, setPage] = useState(1);
  const [data, setData] = useState<LibraryPage | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [version, setVersion] = useState(0);
  const [selected, setSelected] = useState<SavedEntry | null>(null);
  const [enrich, setEnrich] = useState<SavedEntry | null>(null);
  const [confirm, setConfirm] = useState<SavedEntry | null>(null);
  const [saving, setSaving] = useState(false);
  const [actionError, setActionError] = useState("");
  const [notice, setNotice] = useState("");
  const refresh = useCallback(() => { setLoading(true); setError(""); setVersion(v => v + 1); }, []);
  useEffect(() => {
    const controller = new AbortController();
    const params = new URLSearchParams({ page: String(page), page_size: "20", ignored: String(ignored) });
    if (kind) params.set("kind", kind);
    if (!ignored) params.set("has_meaning", String(hasMeaning));
    apiFetch(`${API_URL}/entries?${params}`, { signal: controller.signal }).then(readResponse)
      .then((result: LibraryPage) => {
        if (controller.signal.aborted) return;
        const lastPage = Math.max(1, Math.ceil(result.total / result.page_size));
        if (page > lastPage) { setPage(lastPage); return; }
        setData(result);
      })
      .catch((err: unknown) => { if (!controller.signal.aborted) setError(err instanceof Error ? err.message : "Không kết nối được backend."); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [page, kind, ignored, hasMeaning, version]);
  async function moveEntry() {
    if (!confirm || saving) return;
    setSaving(true); setActionError("");
    try {
      await readResponse(await apiFetch(`${API_URL}/entries/${confirm.id}/${ignored ? "restore" : "ignore"}`, { method: "POST" }));
      setNotice(`${confirm.normalized_text}: ${ignored ? "đã khôi phục vào kho từ" : "đã chuyển vào danh sách bỏ qua"}.`);
      setConfirm(null); refresh();
    } catch (err) { setActionError(err instanceof Error ? err.message : "Không cập nhật được dữ liệu."); }
    finally { setSaving(false); }
  }
  return <Box>
    {data && <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: "wrap", mb: 2 }}>
      <Chip label={`Tổng: ${(data.with_meanings + data.without_meanings).toLocaleString("vi-VN")}`} />
      <Chip color="success" variant="outlined" label={`Đã có nghĩa: ${data.with_meanings.toLocaleString("vi-VN")}`} />
      <Chip variant="outlined" label={`Chưa có nghĩa: ${data.without_meanings.toLocaleString("vi-VN")}`} />
    </Stack>}
    {!ignored && <Tabs value={hasMeaning ? "ready" : "pending"} onChange={(_, value) => {
      setHasMeaning(value === "ready"); setPage(1); setData(null); setLoading(true); setError("");
    }} sx={{ mb: 2 }}>
      <Tab value="ready" label="Đã có nghĩa" />
      <Tab value="pending" label="Chưa có nghĩa" />
    </Tabs>}
    {!ignored && hasMeaning && <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>Đã học: đã trả lời đúng ít nhất một lần.</Typography>}
    <Stack direction="row" sx={{ alignItems: "center", justifyContent: "space-between", mb: 2 }}>
      <Typography variant="body2" color="text.secondary">{data ? `${data.total.toLocaleString("vi-VN")} từ/cụm · Tần suất cao trước` : "Kho từ của bạn"}</Typography>
      <Button onClick={refresh} disabled={loading}>Tải lại</Button>
    </Stack>
    {notice && <Alert severity="success" onClose={() => setNotice("")} sx={{ mb: 2 }}>{notice}</Alert>}
    {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
    {loading && <Stack direction="row" spacing={1} sx={{ mb: 2 }} role="status"><CircularProgress size={20} /><Typography>Đang tải kho từ…</Typography></Stack>}
    <TableContainer sx={{ border: 1, borderColor: "divider", borderRadius: 2 }}>
      <Table size="small" aria-label={ignored ? "Danh sách từ bỏ qua" : "Kho từ đã lưu"} sx={{ minWidth: 680 }}>
        <TableHead sx={{ bgcolor: "action.hover" }}><TableRow>
          {["Từ", "Loại", "Tần suất", "Chi tiết", ignored ? "Trạng thái" : hasMeaning ? "Học tập" : "Tra nghĩa và lưu audio", ignored ? "Khôi phục" : "Delete"].map(label => <TableCell key={label} sx={{ fontWeight: 700, py: 2, whiteSpace: "nowrap" }}>{label}</TableCell>)}
        </TableRow></TableHead>
        <TableBody>
          {!loading && !error && !data?.items.length && <TableRow><TableCell colSpan={6} sx={{ py: 5, textAlign: "center", color: "text.secondary" }}>Chưa có từ/cụm trong danh sách này.</TableCell></TableRow>}
          {data?.items.map(entry => <TableRow key={entry.id} hover>
            <TableCell sx={{ fontWeight: 700, overflowWrap: "anywhere", maxWidth: 240, py: 2 }}>{entry.normalized_text}</TableCell>
            <TableCell><Chip size="small" variant="outlined" label={entry.kind === "word" ? "Từ" : "Cụm từ"} /></TableCell>
            <TableCell sx={{ fontVariantNumeric: "tabular-nums" }}>{entry.frequency.toLocaleString("vi-VN")}</TableCell>
            <TableCell><Button size="small" onClick={() => setSelected(entry)}>Chi tiết</Button></TableCell>
            <TableCell>{ignored ? <Typography variant="body2" color="text.secondary">Đã bỏ qua</Typography> : entry.meanings.length > 0 ?
              <Chip size="small" color={(entry.learning_progress?.correct_count ?? 0) > 0 ? "success" : "default"} variant="outlined" label={(entry.learning_progress?.correct_count ?? 0) > 0 ? "Đã học" : "Chưa học"} /> :
              <Button size="small" variant="outlined" disabled={loading} onClick={() => setEnrich(entry)}>Tra nghĩa và lưu audio</Button>}</TableCell>
            <TableCell><Button size="small" color={ignored ? "primary" : "error"} disabled={loading} onClick={() => { setActionError(""); setConfirm(entry); }}>{ignored ? "Khôi phục" : "Delete"}</Button></TableCell>
          </TableRow>)}
        </TableBody>
      </Table>
    </TableContainer>
    {data && data.total > data.page_size && <Pagination sx={{ mt: 3 }} disabled={loading} count={Math.ceil(data.total / data.page_size)} page={page} onChange={(_, next) => { setLoading(true); setError(""); setPage(next); }} />}
    <Dialog open={!!selected} onClose={() => setSelected(null)} fullWidth maxWidth="sm">
      <DialogTitle>{selected?.normalized_text}</DialogTitle>
      <DialogContent dividers>{selected && <EntryDetails entry={selected} />}</DialogContent>
      <DialogActions><Button onClick={() => setSelected(null)}>Đóng</Button></DialogActions>
    </Dialog>
    <Dialog open={!!enrich} onClose={() => { setEnrich(null); refresh(); }} fullWidth maxWidth="sm">
      <DialogTitle>Tra nghĩa: {enrich?.normalized_text}</DialogTitle>
      <DialogContent dividers>{enrich && <EnrichmentQueue key={enrich.id} entryIds={[enrich.id]} autoStart onComplete={refresh} />}</DialogContent>
      <DialogActions><Button onClick={() => { setEnrich(null); refresh(); }}>Đóng / dừng chờ</Button></DialogActions>
    </Dialog>
    <Dialog open={!!confirm} onClose={() => { if (!saving) setConfirm(null); }} fullWidth maxWidth="xs">
      <DialogTitle>{ignored ? "Khôi phục vào kho từ?" : "Chuyển vào danh sách bỏ qua?"}</DialogTitle>
      <DialogContent><Typography sx={{ fontWeight: 700, mb: 1 }}>{confirm?.normalized_text}</Typography>
        <Typography>{ignored ? "Giữ lại toàn bộ dữ liệu đã lưu và tiếp tục đếm tần suất khi gặp lại." : "Mục này sẽ không xuất hiện trong kho, bài học mới hoặc kết quả quét sau. Nghĩa, audio và lịch sử học vẫn được giữ. Phiên học đang chờ câu hỏi về mục này sẽ kết thúc."}</Typography>
        {actionError && <Alert severity="error" sx={{ mt: 2 }}>{actionError}</Alert>}
      </DialogContent>
      <DialogActions><Button disabled={saving} onClick={() => setConfirm(null)}>Hủy</Button><Button disabled={saving} color={ignored ? "primary" : "error"} variant="contained" onClick={moveEntry}>{saving ? "Đang lưu…" : ignored ? "Khôi phục" : "Chuyển vào bỏ qua"}</Button></DialogActions>
    </Dialog>
  </Box>;
}
export default function VocabularyLibrary() {
  const [kind, setKind] = useState("");
  const [ignored, setIgnored] = useState(false);
  return <Card sx={{ mt: 3, borderRadius: 3 }}><CardContent sx={{ p: { xs: 2, sm: 3 } }}>
    <Typography variant="h5" component="h2" sx={{ fontWeight: 700 }}>Kho từ đã lưu</Typography>
    <Typography color="text.secondary" sx={{ mt: 1, mb: 2 }}>Xem chi tiết, bổ sung nghĩa và audio hoặc bỏ qua những mục không cần học.</Typography>
    <Tabs value={ignored ? "ignored" : "library"} onChange={(_, value) => setIgnored(value === "ignored")} sx={{ mb: 2 }}><Tab value="library" label="Kho từ" /><Tab value="ignored" label="Danh sách bỏ qua" /></Tabs>
    <TextField select size="small" label="Loại" value={kind} onChange={e => setKind(e.target.value)} sx={{ minWidth: 160, mb: 2 }}><MenuItem value="">Tất cả</MenuItem><MenuItem value="word">Từ</MenuItem><MenuItem value="phrase">Cụm từ</MenuItem></TextField>
    <LibraryResults key={`${kind}-${ignored}`} kind={kind} ignored={ignored} />
  </CardContent></Card>;
}
