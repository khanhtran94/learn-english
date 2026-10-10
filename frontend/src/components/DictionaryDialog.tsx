import { useEffect, useRef, useState } from "react";
import {
  Alert, Box, Button, Chip, CircularProgress, Dialog, DialogActions,
  DialogContent, DialogTitle, Divider, Typography,
} from "@mui/material";
import { ApiError, dictionaryRequest } from "../services/api";
import type { DictionaryEntry } from "../types/dictionary";

type Props = { term: string; onClose: () => void };

export default function DictionaryDialog({ term, onClose }: Props) {
  const [entry, setEntry] = useState<DictionaryEntry | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [cooldown, setCooldown] = useState(0);
  const [audioLoading, setAudioLoading] = useState(false);
  const [audioError, setAudioError] = useState("");
  const [audioUrl, setAudioUrl] = useState("");
  const audioRequest = useRef<AbortController | null>(null);
  const audioObjectUrl = useRef("");

  useEffect(() => {
    const controller = new AbortController();
    dictionaryRequest("lookup", term, controller.signal)
      .then((response) => response.json())
      .then((data: DictionaryEntry) => { if (!controller.signal.aborted) setEntry(data); })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        setError(err instanceof Error ? err.message : "Không thể tra từ.");
        if (err instanceof ApiError) setCooldown(err.retryAfter);
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [term, attempt]);

  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = window.setTimeout(() => setCooldown((value) => Math.max(0, value - 1)), 1000);
    return () => window.clearTimeout(timer);
  }, [cooldown]);

  useEffect(() => () => {
    audioRequest.current?.abort();
    if (audioObjectUrl.current) URL.revokeObjectURL(audioObjectUrl.current);
  }, []);

  const loadAudio = async () => {
    if (audioRequest.current) return;
    const controller = new AbortController();
    audioRequest.current = controller;
    setAudioLoading(true);
    setAudioError("");
    try {
      const response = await dictionaryRequest("audio", term, controller.signal);
      const blob = await response.blob();
      if (!controller.signal.aborted) {
        const url = URL.createObjectURL(blob);
        audioObjectUrl.current = url;
        setAudioUrl(url);
      }
    } catch (err) {
      if (!controller.signal.aborted) {
        setAudioError(err instanceof Error ? err.message : "Không có audio.");
        if (err instanceof ApiError) setCooldown(err.retryAfter);
      }
    } finally {
      if (!controller.signal.aborted) setAudioLoading(false);
      audioRequest.current = null;
    }
  };

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="sm" aria-labelledby="dictionary-title">
      <DialogTitle id="dictionary-title" sx={{ overflowWrap: "anywhere" }}>{term}</DialogTitle>
      <DialogContent dividers>
        {loading && <Box role="status" sx={{ display: "flex", alignItems: "center", gap: 2 }}><CircularProgress size={24} />Đang tra nghĩa…</Box>}
        {error && <Alert severity="error">{error}</Alert>}
        {cooldown > 0 && <Alert severity="info" sx={{ mt: 2 }}>Có thể thử lại sau {cooldown} giây.</Alert>}
        {entry && !entry.found && <Alert severity="info">Chưa tìm thấy nghĩa cho từ/cụm này. Hãy kiểm tra chính tả hoặc thử một cụm khác.</Alert>}
        {entry?.found && (
          <>
            <Typography sx={{ mb: 1 }}>IPA: {entry.ipa || "Chưa có phiên âm"}</Typography>
            {audioUrl ? (
              <Box component="audio" controls src={audioUrl} aria-label={`Phát âm ${term}`} onError={() => setAudioError("Trình duyệt không phát được audio.")} sx={{ width: "100%", mb: 2 }} />
            ) : (
              <Button onClick={loadAudio} disabled={audioLoading || cooldown > 0} sx={{ mb: 2 }}>
                {audioLoading ? "Đang tạo audio…" : "Nghe phát âm"}
              </Button>
            )}
            {audioError && <Alert severity="warning" sx={{ mb: 2 }}>{audioError}</Alert>}
            {entry.meanings.map((meaning, index) => (
              <Box key={index} sx={{ mb: 3 }}>
                <Chip size="small" label={meaning.part_of_speech} sx={{ mb: 1 }} />
                <Typography sx={{ fontWeight: 600 }}>{index + 1}. {meaning.vietnamese}</Typography>
                {meaning.examples.length === 0 && <Typography variant="body2" color="text.secondary">Chưa có ví dụ.</Typography>}
                {meaning.examples.map((example, exampleIndex) => (
                  <Box key={exampleIndex} sx={{ mt: 1, pl: 2, borderLeft: 2, borderColor: "divider" }}>
                    <Typography>{example.english}</Typography>
                    <Typography variant="body2" color="text.secondary">{example.vietnamese}</Typography>
                  </Box>
                ))}
              </Box>
            ))}
          </>
        )}
        {entry && <><Divider sx={{ my: 2 }} /><Typography variant="caption" color="text.secondary">Nghĩa và phiên âm do Gemini tạo{entry.cached ? " · Kết quả đã lưu" : ""}. Audio được tạo khi bạn bấm nghe.</Typography></>}
      </DialogContent>
      <DialogActions>
        {error && <Button disabled={loading || cooldown > 0} onClick={() => { setError(""); setLoading(true); setAttempt((value) => value + 1); }}>Thử lại</Button>}
        <Button onClick={onClose}>Đóng</Button>
      </DialogActions>
    </Dialog>
  );
}
