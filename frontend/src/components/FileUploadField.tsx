import { useRef } from "react";
import type { ChangeEvent } from "react";
import { CloudUpload, Description } from "@mui/icons-material";
import DeleteIcon from "@mui/icons-material/Delete";
import { Box, Button, Chip, Stack, Typography } from "@mui/material";

type FileUploadFieldProps = {
  file: File | null;
  disabled: boolean;
  onFileChange: (event: ChangeEvent<HTMLInputElement>) => void;
  onClearFile: () => void;
};

function FileUploadField({
  file,
  disabled,
  onFileChange,
  onClearFile,
}: FileUploadFieldProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const clearFile = () => {
    onClearFile();
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <Box
      sx={{
        border: "2px dashed",
        borderColor: "divider",
        borderRadius: 3,
        p: 4,
        textAlign: "center",
        bgcolor: "#fafbff",
      }}
    >
      <CloudUpload color="primary" sx={{ fontSize: 52, mb: 1 }} />

      <Typography sx={{ fontWeight: 600 }}>Upload a document</Typography>

      <Typography
        variant="body2"
        color="text.secondary"
        sx={{ mb: 2 }}
      >
        PDF, DOCX, DOC - Maximum 10 MB
      </Typography>

      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx,.doc"
        hidden
        onChange={onFileChange}
      />

      <Button
        variant="outlined"
        startIcon={<CloudUpload />}
        disabled={disabled}
        onClick={() => fileInputRef.current?.click()}
      >
        Choose File
      </Button>

      {file && (
        <Stack
          direction="row"
          spacing={1}
          sx={{
            alignItems: "center",
            mt: 2,
            flexWrap: "wrap",
            justifyContent: "center",
          }}
        >
          <Chip
            icon={<Description />}
            label={file.name}
            onDelete={clearFile}
            deleteIcon={<DeleteIcon />}
          />
        </Stack>
      )}
    </Box>
  );
}

export default FileUploadField;
