1. front end
- buil ban lenh 

npm create vite@latest frontend -- --template react-ts

- muốn chạy thì cd vao frontend 

```cmd
cd frontend
npm install
npm run dev
```

2. backend
- build bang lenh 

```cmd
mkdir backend
cd backend

python -m venv .venv
```

- sau khi build vao thu muc backend, o power shell  run

```cmd
.\.venv\Scripts\Activate.ps1
```

- cai fast api

```cmd
pip install fastapi "uvicorn[standard]"
pip freeze > requirements.txt

```

Chạy tại thư mục backend:
```cmd
uvicorn app.main:app --reload
```

- khi chay project backend, cần chạy câu lệnh 
```cmd
.\.venv\Scripts\Activate.ps1
```
trong thư mục backend
## Ngày 4: Phân tích cụm từ

`POST /analyze` giữ `analysis.words` và bổ sung `analysis.phrases`,
`analysis.total_phrases` (tổng lượt xuất hiện), `analysis.unique_phrases`.
Mỗi cụm gồm `phrase`, `frequency`, `forms`, `types`, `example`.

- Noun chunks lấy từ spaCy, bỏ stop words ở hai đầu và chỉ giữ cụm ít nhất 2 từ.
- Cụm ứng viên gồm 2–4 từ liên tiếp thuộc ADJ/NOUN/PROPN, kết thúc bằng NOUN/PROPN;
  không chứa stop words, số, dấu câu và không vượt ranh giới câu.
- Chuẩn hóa bằng lemma viết thường; giữ các dạng gốc trong `forms` và câu ví dụ đầu tiên.
- Một span được cả hai bộ trích xuất nhận diện chỉ tính một lần. Các span chồng lấp
  khác nhau vẫn là các cụm riêng. Sắp xếp theo tần suất giảm dần, rồi theo tên cụm.
- Đây là cụm ứng viên theo quy tắc, chưa phải nhận diện thành ngữ/collocation.
  Lemma và noun chunks phụ thuộc model spaCy (ví dụ `data` có thể thành `datum`).
- Frontend hiển thị bảng Words và Phrases riêng biệt.

Chạy kiểm thử trong thư mục backend:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Tra từ Anh–Việt bằng Gemini

1. Trong `backend`, chạy `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`.
2. Sao chép `.env.example` thành `.env`, điền `GEMINI_API_KEY` và model có quyền
   truy cập trong Google AI Studio (`GEMINI_MODEL`, `GEMINI_TTS_MODEL`). Không đưa
   khóa Gemini hoặc Supabase vào frontend hay commit `.env`.
3. Khởi động backend và frontend như trên. Dùng ô **Từ điển Anh–Việt** hoặc bấm
   một từ/cụm trong bảng kết quả. Mỗi yêu cầu chỉ nhận một từ/cụm (tối đa 12 từ,
   120 ký tự), không nhận mảng hoặc danh sách phân tách bằng dấu phẩy.

API:
- `POST /dictionary/lookup` với `{"term":"bank"}` trả `term`, `found`, `ipa`,
  `meanings[]` (loại từ, nghĩa tiếng Việt, ví dụ Anh–Việt), `cached`, `source`.
- `POST /dictionary/audio` với cùng body trả WAV từ Gemini TTS. Audio chỉ được
  tạo khi bấm **Nghe phát âm**, không tự gọi thêm khi tra nghĩa.
- Không tìm thấy nghĩa: HTTP 200, `found=false`, `meanings=[]`; thiếu IPA: null.
  Audio rỗng: 404. Dữ liệu sai/lỗi provider: 502; timeout: 504; thiếu API key: 503.
- Giới hạn **15 lần gọi Gemini trong cửa sổ trượt 60 giây**, dùng chung tra nghĩa
  và TTS, kể cả lần gọi lỗi. Không retry SDK tự động. HTTP 429 có `Retry-After`;
  UI đếm ngược và cho thử lại. Hạn mức thực tế của Google có thể thấp hơn hoặc
  có thêm giới hạn token/ngày; lỗi 429 từ Google cũng được hiển thị.
- SQLite trong `backend/data/dictionary.sqlite3` lưu cache và bộ đếm, dùng chung
  cho các worker trên cùng máy dùng cùng file. Cache nghĩa/audio 30 ngày, kết quả
  không có nghĩa 1 giờ; cache hit không tiêu tốn lượt Gemini. Giới hạn này chưa
  phân tán giữa nhiều máy/container; triển khai nhiều máy cần bộ đếm chung.
- Supabase là cache nghĩa tùy chọn: chạy `backend/sql/dictionary_cache.sql` trong
  SQL Editor rồi cấu hình `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` ở backend.
  RLS không cho anon/authenticated đọc hoặc ghi bảng. Nếu Supabase lỗi, dùng cache
  SQLite. Audio lưu local. Chưa cần Supabase để chạy bản local.
- Nghĩa/IPA là dữ liệu do Gemini tạo; chất lượng phụ thuộc model. Cụm được tra bằng
  dạng xuất hiện trong văn bản để tránh lemma bất thường như `datum science`.

Kiểm thử offline (không dùng quota Gemini), từ thư mục backend:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

Tài liệu: https://ai.google.dev/gemini-api/docs/structured-output,
https://ai.google.dev/gemini-api/docs/speech-generation,
https://ai.google.dev/gemini-api/docs/rate-limits.
