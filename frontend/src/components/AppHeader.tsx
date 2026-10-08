import { AutoStories } from "@mui/icons-material";
import { Box, Stack, Typography } from "@mui/material";

function AppHeader() {
  return (
    <Stack
      direction="row"
      spacing={2}
      sx={{ mb: 4, alignItems: "center" }}
    >
      <AutoStories color="primary" sx={{ fontSize: 40 }} />
      <Box>
        <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
          Learn English
        </Typography>
        <Typography color="text.secondary">
          Build vocabulary from your own documents
        </Typography>
      </Box>
    </Stack>
  );
}

export default AppHeader;
