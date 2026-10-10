import { useEffect, useState } from "react";
import { Box, Container, CssBaseline, Paper, Tab, Tabs } from "@mui/material";
import { AutoStories, CloudUpload, School } from "@mui/icons-material";
import AppHeader from "./components/AppHeader";
import DictionaryDialog from "./components/DictionaryDialog";
import LibraryPage from "./pages/LibraryPage";
import UploadPage from "./pages/UploadPage";
import FlashcardsPage from "./pages/FlashcardsPage";

type Screen = "library" | "upload" | "flashcards";
const screens: { id: Screen; label: string; icon: React.ReactElement }[] = [
  { id: "library", label: "Kho từ", icon: <AutoStories /> },
  { id: "upload", label: "Tải tài liệu", icon: <CloudUpload /> },
  { id: "flashcards", label: "Học flashcard", icon: <School /> },
];
function currentScreen(): Screen {
  const value = window.location.hash.slice(1);
  return value === "upload" || value === "flashcards" ? value : "library";
}

export default function App() {
  const [screen, setScreen] = useState<Screen>(currentScreen);
  const [uploadVisited, setUploadVisited] = useState(() => currentScreen() === "upload");
  const [dictionaryTerm, setDictionaryTerm] = useState<string | null>(null);
  useEffect(() => {
    const navigate = () => {
      const next = currentScreen();
      setScreen(next);
      if (next === "upload") setUploadVisited(true);
      setDictionaryTerm(null);
    };
    window.addEventListener("hashchange", navigate);
    return () => window.removeEventListener("hashchange", navigate);
  }, []);
  return (
    <>
      <CssBaseline />
      <Box sx={{ minHeight: "100vh", bgcolor: "#f5f7fb", py: { xs: 3, md: 6 } }}>
        <Container maxWidth="md">
          <AppHeader />
          <Paper component="nav" aria-label="Chức năng chính" sx={{ mb: 3, borderRadius: 3 }}>
            <Tabs value={screen} variant="fullWidth" aria-label="Màn hình chức năng">
              {screens.map(({ id, label, icon }) => <Tab key={id} value={id} label={label} icon={icon} iconPosition="top" component="a" href={`#${id}`} id={`tab-${id}`} aria-controls={`panel-${id}`} sx={{ minWidth: 0, textTransform: "none" }} />)}
            </Tabs>
          </Paper>
          <Box component="main">
            <Box role="tabpanel" id="panel-library" aria-labelledby="tab-library" hidden={screen !== "library"}>
              {screen === "library" && <LibraryPage onLookup={setDictionaryTerm} />}
            </Box>
            <Box role="tabpanel" id="panel-upload" aria-labelledby="tab-upload" hidden={screen !== "upload"}>
              {uploadVisited && <UploadPage onLookup={setDictionaryTerm} />}
            </Box>
            <Box role="tabpanel" id="panel-flashcards" aria-labelledby="tab-flashcards" hidden={screen !== "flashcards"}>
              {screen === "flashcards" && <FlashcardsPage />}
            </Box>
          </Box>
          {dictionaryTerm && <DictionaryDialog key={dictionaryTerm} term={dictionaryTerm} onClose={() => setDictionaryTerm(null)} />}
        </Container>
      </Box>
    </>
  );
}
