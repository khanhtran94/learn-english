import { useEffect, useState, type ReactNode } from "react";
import { Alert, Box, Button, CircularProgress, Container, CssBaseline, Paper, Stack, TextField, Typography } from "@mui/material";
import { API_URL, apiFetch, AUTH_CHANGED, sessionToken, setSessionToken } from "../services/api";

export default function AuthGate({ children }: { children: ReactNode }) {
  const [token, setToken] = useState(sessionToken);
  const [verified, setVerified] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const changed = () => { setToken(sessionToken()); setVerified(false); setError(""); };
    window.addEventListener(AUTH_CHANGED, changed);
    return () => window.removeEventListener(AUTH_CHANGED, changed);
  }, []);
  useEffect(() => {
    if (!token) return;
    const controller = new AbortController();
    apiFetch(`${API_URL}/auth/session`, { signal: controller.signal }).then(async response => {
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Không kiểm tra được phiên đăng nhập.");
      }
      if (!controller.signal.aborted) setVerified(true);
    }).catch((err: unknown) => {
      if (!controller.signal.aborted) setError(err instanceof Error ? err.message : "Không kết nối được backend.");
    });
    return () => controller.abort();
  }, [token, retry]);

  async function login() {
    setBusy(true); setError("");
    try {
      const response = await fetch(`${API_URL}/auth/login`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Không đăng nhập được.");
      setSessionToken(data.access_token);
      setPassword("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không kết nối được backend.");
    } finally { setBusy(false); }
  }

  async function logout() {
    setBusy(true); setError("");
    try {
      const response = await apiFetch(`${API_URL}/auth/logout`, { method: "POST" });
      if (!response.ok && response.status !== 401) throw new Error("Không đăng xuất được. Vui lòng thử lại.");
      setSessionToken(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không kết nối được backend.");
    } finally { setBusy(false); }
  }

  if (token && verified) return <>
    <Box sx={{ display: "flex", justifyContent: "flex-end", p: 1 }}>
      <Button disabled={busy} onClick={logout}>Đăng xuất</Button>
    </Box>
    {error && <Alert severity="error">{error}</Alert>}
    {children}
  </>;

  return <>
    <CssBaseline />
    <Container maxWidth="xs" sx={{ py: 8 }}>
      <Paper sx={{ p: 4, borderRadius: 3 }}>
        <Typography variant="h5" component="h1" sx={{ mb: 3 }}>Đăng nhập để học</Typography>
        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
        {token ? <Stack spacing={2}>
          {!error && <><CircularProgress size={24} /><Typography>Đang kiểm tra phiên đăng nhập…</Typography></>}
          {error && <Button onClick={() => { setError(""); setRetry(value => value + 1); }}>Thử lại</Button>}
          <Button onClick={() => setSessionToken(null)}>Về màn hình đăng nhập</Button>
        </Stack> : <Box component="form" onSubmit={event => { event.preventDefault(); if (!busy) void login(); }}>
          <Stack spacing={2}>
            <TextField required label="Tên đăng nhập" autoComplete="username" value={username} onChange={event => setUsername(event.target.value)} disabled={busy} slotProps={{ htmlInput: { maxLength: 200 } }} />
            <TextField required label="Mật khẩu" type="password" autoComplete="current-password" value={password} onChange={event => setPassword(event.target.value)} disabled={busy} slotProps={{ htmlInput: { maxLength: 1024 } }} />
            <Button type="submit" variant="contained" disabled={busy || !username || !password}>{busy ? "Đang đăng nhập…" : "Đăng nhập"}</Button>
          </Stack>
        </Box>}
      </Paper>
    </Container>
  </>;
}
