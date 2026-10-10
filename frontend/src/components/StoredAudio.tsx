import { useState } from "react";
import { Alert, Box, Button } from "@mui/material";
import { API_URL } from "../services/api";

async function readResponse(response: Response) {
  const data = await response.json().catch(() => null);
  if (!response.ok || !data) throw new Error(typeof data?.detail === "string" ? data.detail : "Không tải được dữ liệu từ backend.");
  return data;
}

export default function StoredAudio({ id }: { id: string }) {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await fetch(`${API_URL}/entries/pronunciations/${id}/audio`).then(readResponse);
      setUrl(data.url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không tải được audio.");
    } finally { setLoading(false); }
  };
  return (
    <Box>
      {url && <Box component="audio" controls src={url} sx={{ width: "100%", maxWidth: 350 }} onError={() => { setUrl(""); setError("Không phát được audio hoặc liên kết đã hết hạn. Hãy tải lại."); }} />}
      {!url && <Button onClick={load} disabled={loading}>{loading ? "Đang tải…" : "Nghe audio đã lưu"}</Button>}
      {error && <Alert severity="warning">{error}</Alert>}
    </Box>
  );
}
