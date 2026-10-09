import { useEffect, useState } from "react";
import { Alert, Box, Button, LinearProgress, Stack, Typography } from "@mui/material";
import { API_URL } from "../services/api";

type Props = { entryIds: string[]; autoStart?: boolean; onComplete?: () => void };

export default function EnrichmentQueue({ entryIds, autoStart = false, onComplete }: Props) {
  const [running, setRunning] = useState(autoStart);
  const [index, setIndex] = useState(0);
  const [attempt, setAttempt] = useState(0);
  const [retryAt, setRetryAt] = useState(0);
  const [error, setError] = useState("");
  const [waiting, setWaiting] = useState(false);
  const [notFound, setNotFound] = useState(0);
  const entryId = entryIds[index];
  const total = entryIds.length;

  useEffect(() => {
    if (!running || !entryId) return;
    const controller = new AbortController();
    const run = async () => {
      setWaiting(false);
      try {
        const response = await fetch(`${API_URL}/entries/${entryId}/enrich`, { method: "POST", signal: controller.signal });
        const data = await response.json().catch(() => null);
        if (controller.signal.aborted) return;
        if (response.status === 429 || response.status === 409 || data?.retry_after > 0) {
          const delay = Number(response.headers.get("Retry-After")) || data?.retry_after || 60;
          setWaiting(true);
          setRetryAt(Date.now() + Math.max(1, delay) * 1000);
          return;
        }
        if (!response.ok || !data || data.status === "partial") {
          throw new Error(data?.message || (typeof data?.detail === "string" ? data.detail : "Không xử lý được dữ liệu. Vui lòng thử lại."));
        }
        if (data.status === "not_found") setNotFound((value) => value + 1);
        setIndex((value) => value + 1);
        setRetryAt(0);
        if (index + 1 === total) {
          setRunning(false);
          onComplete?.();
        }
      } catch (err) {
        if (controller.signal.aborted) return;
        setRunning(false);
        setError(err instanceof Error ? err.message : "Không kết nối được backend.");
      }
    };
    // Cleanup before a request starts also avoids duplicate StrictMode requests.
    const timer = window.setTimeout(() => { void run(); }, Math.max(0, retryAt - Date.now()));
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [running, entryId, index, total, retryAt, attempt, onComplete]);

  if (!total) return null;
  const complete = index >= total;
  return (
    <Box sx={{ my: 2 }}>
      <Typography sx={{ fontWeight: 600 }}>Tra nghĩa và lưu audio</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        {index}/{total} mục đã xử lý. Dùng lại nghĩa và audio đã lưu; tối đa 15 lượt gọi Gemini/phút.
      </Typography>
      {running && <LinearProgress variant="determinate" value={index / total * 100} sx={{ mb: 1 }} />}
      {waiting && running && <Alert severity="info">Đang chờ lượt gọi tiếp theo. Bạn có thể tạm dừng.</Alert>}
      {error && <Alert severity="warning" sx={{ my: 1 }}>{error} Nghĩa đã lưu sẽ được giữ lại khi thử tiếp phần audio.</Alert>}
      {complete && <Alert severity={notFound ? "info" : "success"}>
        {notFound ? `Đã xử lý xong; ${notFound} mục chưa tìm thấy nghĩa.` : "Đã lưu nghĩa và audio. Có thể xem trong Kho từ hoặc học flashcard."}
      </Alert>}
      {!complete && <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
        {running ? <Button onClick={() => setRunning(false)}>Tạm dừng</Button> : <Button variant="contained" onClick={() => { setError(""); setRunning(true); setAttempt((value) => value + 1); }}>
          {index || error ? "Tiếp tục / thử lại" : "Tra nghĩa và lưu audio"}
        </Button>}
        <Typography variant="caption" color="text.secondary" sx={{ alignSelf: "center" }}>Giữ trang mở để xử lý các mục tiếp theo.</Typography>
      </Stack>}
    </Box>
  );
}
