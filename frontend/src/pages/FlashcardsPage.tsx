import { useEffect, useState } from "react";
import { Alert, Box, Button, Card, CardContent, MenuItem, Stack, TextField, Typography } from "@mui/material";
import StoredAudio from "../components/StoredAudio";
import { API_URL } from "../services/api";

type Mode = "en_vi" | "listening" | "vi_en";
type Session = { id: string; status: string; mode: Mode; summary: { total: number; answered: number; correct: number; incorrect: number; words: number }; question: null | { id: string; is_retry: boolean; prompt: string; audio_id: string | null; options: { id: string; text: string }[] } };
type Feedback = { correct: boolean; word: string; accepted: string[]; correct_count: number; next_review_at: string; retry_added: boolean; audio_id: string | null; ipa: string | null; meanings: { meaning_vi: string; part_of_speech: string; examples: { english?: string; vietnamese?: string }[] }[] };
async function api<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${API_URL}/study${path}`, body === undefined ? undefined : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const result = await response.json();
  if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : "Không thực hiện được yêu cầu. Vui lòng thử lại.");
  return result;
}
export default function FlashcardsPage() {
  const [session, setSession] = useState<Session | null>(null);
  const [mode, setMode] = useState<Mode>("en_vi");
  const [scope, setScope] = useState("due_new");
  const [size, setSize] = useState(10);
  const [answer, setAnswer] = useState("");
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [busy, setBusy] = useState(true);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    api<Session | null>("/sessions/current").then(value => { if (active) { setSession(value); setReady(true); } }).catch((err: Error) => { if (active) setError(err.message); }).finally(() => { if (active) setBusy(false); });
    return () => { active = false; };
  }, []);
  async function act(action: () => Promise<void>) {
    setBusy(true); setError("");
    try { await action(); } catch (err) { setError(err instanceof Error ? err.message : "Không kết nối được backend."); } finally { setBusy(false); }
  }
  function receive(value: Session | null) { setSession(value); setAnswer(""); setFeedback(null); }
  const question = session?.question;
  return <Box>
    <Typography variant="h5" component="h1" sx={{ fontWeight: 700, mb: 2 }}>Học và ôn flashcard</Typography>
    <Typography color="text.secondary" sx={{ mb: 2 }}>Ưu tiên từ đến hạn ôn, sau đó từ mới theo tần suất. Mỗi câu đúng tính một lần học; lịch ôn tăng tối đa một mốc cho mỗi từ trong phiên.</Typography>
    {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
    {!ready && <Button disabled={busy} onClick={() => act(async () => { receive(await api<Session | null>("/sessions/current")); setReady(true); })}>{busy ? "Đang tải…" : "Tải lại phiên học"}</Button>}
    {ready && (!session || session.status !== "active") && <Stack spacing={2}>
      {session && <Alert severity="success">Đã kết thúc phiên: {session.summary.words} từ/cụm, {session.summary.correct} câu đúng, {session.summary.incorrect} câu sai (gồm câu luyện lại).</Alert>}
      <TextField select label="Dạng bài" value={mode} onChange={e => setMode(e.target.value as Mode)}>
        <MenuItem value="en_vi">Tiếng Anh → chọn nghĩa tiếng Việt</MenuItem><MenuItem value="listening">Nghe → nhập tiếng Anh</MenuItem><MenuItem value="vi_en">Tiếng Việt → nhập tiếng Anh</MenuItem>
      </TextField>
      <TextField select label="Nội dung" value={scope} onChange={e => setScope(e.target.value)}><MenuItem value="due_new">Đến hạn ôn và từ mới</MenuItem><MenuItem value="learned">Ôn lại các từ đã học</MenuItem></TextField>
      <TextField select label="Số từ/cụm mỗi phiên" value={size} onChange={e => setSize(Number(e.target.value))}>{[5,10,20,30].map(n => <MenuItem key={n} value={n}>{n}</MenuItem>)}</TextField>
      <Typography variant="body2">Ôn sớm và luyện lại vẫn cộng lần trả lời đúng, nhưng không tăng mốc lịch ôn. Trả lời sai đưa từ về mốc 1 ngày. Bài nghe chỉ dùng thẻ đã có audio.</Typography>
      <Button disabled={busy} variant="contained" onClick={() => act(async () => receive(await api<Session>("/sessions", { mode, scope, size })))}>Bắt đầu học</Button>
    </Stack>}
    {session?.status === "active" && question && <>
      <Typography sx={{ mb: 1 }}>Đã trả lời {session.summary.answered}/{session.summary.total} câu · {session.summary.words} từ/cụm{question.is_retry ? " · Luyện lại câu sai" : ""}</Typography>
      <Card variant="outlined"><CardContent>
        <Typography variant="h4" sx={{ mb: 3, overflowWrap: "anywhere" }}>{question.prompt}</Typography>
        {question.audio_id && <StoredAudio key={question.id} id={question.audio_id} />}
        <Box component="form" onSubmit={e => { e.preventDefault(); if (!busy && !feedback && answer.trim()) void act(async () => setFeedback(await api<Feedback>(`/sessions/${session.id}/questions/${question.id}/answer`, { answer }))); }}>
          {session.mode === "en_vi" ? <Stack spacing={1} sx={{ my: 2 }}>{question.options.map((option, i) => <Button key={option.id} disabled={busy || !!feedback} variant={answer === option.id ? "contained" : "outlined"} aria-pressed={answer === option.id} onClick={() => setAnswer(option.id)} sx={{ justifyContent: "flex-start", textTransform: "none" }}>{String.fromCharCode(65 + i)}. {option.text}</Button>)}</Stack> : <TextField fullWidth label="Đáp án tiếng Anh" value={answer} onChange={e => setAnswer(e.target.value)} disabled={busy || !!feedback} autoComplete="off" slotProps={{ htmlInput: { spellCheck: false, autoCapitalize: "none" } }} sx={{ my: 2 }} />}
          {!feedback && <Button type="submit" variant="contained" disabled={busy || !answer.trim()}>Kiểm tra đáp án</Button>}
        </Box>
        {feedback && <Box sx={{ mt: 3 }} aria-live="polite">
          <Alert severity={feedback.correct ? "success" : "warning"}>{feedback.correct ? "Chính xác!" : "Chưa đúng."} Đáp án: {feedback.accepted.join(" / ")}{feedback.retry_added ? ". Thẻ này sẽ xuất hiện lại cuối phiên." : ""}</Alert>
          <Typography variant="h5" sx={{ mt: 2 }}>{feedback.word} {feedback.ipa}</Typography>
          {feedback.audio_id && session.mode !== "listening" && <StoredAudio id={feedback.audio_id} />}
          {feedback.meanings.map((meaning, index) => <Box key={index} sx={{ my: 2 }}><Typography sx={{ fontWeight: 600 }}>{meaning.meaning_vi} ({meaning.part_of_speech})</Typography>{meaning.examples.map((ex, i) => <Box key={i} sx={{ mt: 1 }}><Typography>{ex.english}</Typography><Typography color="text.secondary">{ex.vietnamese}</Typography></Box>)}</Box>)}
          <Typography sx={{ mb: 2 }}>Đã trả lời đúng: {feedback.correct_count} lần · Ôn tiếp: {new Date(feedback.next_review_at).toLocaleString("vi-VN")}</Typography>
          <Button disabled={busy} variant="contained" onClick={() => act(async () => receive(await api<Session>(`/sessions/${session.id}`)))}>Tiếp tục</Button>
        </Box>}
      </CardContent></Card>
      <Button sx={{ mt: 2 }} disabled={busy} onClick={() => act(async () => receive(await api<Session>(`/sessions/${session.id}/finish`, {})))}>Kết thúc phiên</Button>
    </>}
  </Box>;
}
