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
  SQL Editor rồi cấu hình `SUPABASE_API_URL`, `SUPABASE_SERVICE_ROLE_KEY` ở backend.
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

## Hiển thị kho từ Supabase

Cài dependency trong backend: `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`.
Điền chuỗi PostgreSQL vào `backend/.env`:

```dotenv
SUPABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT_REF.supabase.co:5432/postgres
```

Thay mật khẩu thật (URL-encode ký tự đặc biệt), không giữ dấu ngoặc vuông.
Backend đọc `.env` bằng python-dotenv và kết nối bằng psycopg2, bắt buộc SSL,
timeout kết nối/truy vấn 10 giây, truy vấn tham số hóa và đóng kết nối sau mỗi request.
Nếu mạng không hỗ trợ IPv6 cho direct connection, dùng chuỗi Session pooler lấy
trong mục Connect của Supabase; sao chép cả hostname, username và port chính xác.
Khởi động lại backend sau khi thay đổi `.env`.

Schema cần đủ các bảng đã thiết kế và khóa ngoại. Việc đọc DB không cần khóa
service_role. Chỉ phần nghe audio private Storage/cache từ điển mới cần thêm:

```dotenv
SUPABASE_API_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_SERVICE_ROLE_KEY=YOUR_SERVER_KEY
```

Không đưa mật khẩu PostgreSQL hoặc khóa server vào frontend.

- `GET /entries?page=1&page_size=20&kind=word`: danh sách theo tần suất giảm dần,
  phân trang, kèm nghĩa, phát âm và tiến độ. Bỏ `kind` để xem cả từ lẫn cụm.
- `GET /entries/pronunciations/{id}/audio`: tạo URL nghe audio đã lưu trong Storage,
  có hiệu lực 10 phút. Không tạo audio mới hoặc gọi Gemini.
- Mục **Kho từ đã lưu** nằm ở đầu trang. Bấm **Tải lại dữ liệu** sau khi thêm dữ liệu
  trong Supabase; bấm một từ để mở chi tiết. Thiếu nghĩa/audio/tiến độ sẽ hiện trạng
  thái chưa có dữ liệu, không làm mất từ khỏi danh sách.
- Các endpoint `/entries` chỉ đọc; `/analyze` lưu từ/cụm và tiến độ ban đầu như mô tả bên dưới.
- Thiếu cấu hình/lỗi PostgreSQL: 503; lỗi Storage: 502; chưa có audio: 404.
- Bản hiện tại dùng backend cá nhân/local. Trước khi đưa backend ra Internet cần
  xác thực người dùng cho các endpoint dùng quyền server.

## Các màn hình

- `/#library`: kho từ đã lưu, chi tiết và tra từ điển.
- `/#upload`: tải tài liệu/dán văn bản, phân tích và xem kết quả. Nội dung được giữ
  khi chuyển tab trong phiên hiện tại (không giữ sau khi tải lại trang).
- `/#flashcards`: luyện lật thẻ với các từ/cụm có nghĩa đã lưu, theo tần suất giảm
  dần, từng nhóm 20 mục trong kho. Có nghĩa, ví dụ, IPA và audio đã lưu nếu có.
  Đây là chế độ luyện tập; chưa ghi nhớ/quên hoặc cập nhật lịch ôn vào DB.

Điều hướng hỗ trợ URL hash và nút Back/Forward của trình duyệt.

## Lưu kết quả sau khi tải tài liệu

`POST /analyze` hiện phân tích rồi lưu `entries` và `learning_progress` trong một
transaction PostgreSQL. Từ/cụm cũ được cộng tần suất và cập nhật lần gặp gần nhất;
nghĩa, audio và tiến độ học cũ không bị ghi đè. Mục mới dùng các giá trị mặc định
của schema (`lookup_status=pending`, tiến độ `new`). Không lưu toàn bộ tài liệu.

Response có `storage`: `saved`, `word_count`, `phrase_count`, `occurrences_added`.
Các số đếm là số mục của lần nhập, bao gồm mục mới và mục đã có. Mỗi lần gửi nhập
lại đều cộng tần suất. Chưa có mã idempotency cho trường hợp gửi lại do mất phản hồi.
Không tự retry request ghi. Lỗi ghi DB trả 503; không báo thành công khi lưu lỗi.

Sau khi upload/lưu thành công, frontend xử lý lần lượt `storage.entry_ids` qua
`POST /entries/{id}/enrich`. Mỗi request xử lý đúng một từ/cụm: nghĩa và ví dụ vào
`meanings`, IPA và metadata audio vào `pronunciations`, trạng thái vào `entries`.
Không sửa tần suất hoặc lịch học khi bổ sung dữ liệu. `review_logs` chỉ dành cho
lần học thực tế. Ô tra từ điển độc lập vẫn chỉ tra cứu/cache; nút trong Kho từ và
hàng đợi sau upload dùng luồng lưu vào các bảng này.


## Tự động lưu nghĩa và audio

- Cấu hình `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_TTS_MODEL`, chuỗi PostgreSQL
  `SUPABASE_URL`, URL HTTPS `SUPABASE_API_URL` và `SUPABASE_SERVICE_ROLE_KEY`.
- Tạo private bucket `pronunciation` trong Storage. Audio WAV được upload tại
  `entries/<entry_id>/en-US/Kore.wav`; DB lưu path, MIME, kích thước và trạng thái.
  URL có thời hạn chỉ được tạo khi nghe. Upload dùng `upsert=true` tại đường dẫn
  cố định để thử lại an toàn khi upload thành công nhưng transaction DB thất bại.
- Sau phân tích, giữ trang mở để hàng đợi tiếp tục. Có thể tạm dừng/tiếp tục.
  Đóng hoặc tải lại trang sẽ dừng hàng đợi phía trình duyệt; dữ liệu đã lưu vẫn còn.
  Trong Kho từ có nút bổ sung từng mục, không cần upload lại để thử tiếp.
- Dùng chung hạn mức 15 lần gọi Gemini/60 giây cho nghĩa và TTS. Thông thường một
  mục mới cần hai lần gọi. Cache hit không tiêu lượt. Gặp 429, UI chờ Retry-After;
  lỗi khác tạm dừng và cho thử lại. Hạn mức của nhà cung cấp có thể thấp hơn.
- Có nghĩa/audio thì dùng lại; thiếu audio chỉ tạo/upload audio. Không tìm thấy
  nghĩa thì lưu `not_found` và không tạo audio. Audio lỗi vẫn commit nghĩa/IPA,
  trả `status=partial` cùng thông báo; lần sau bổ sung phần thiếu.
- Một transaction/advisory lock cho mỗi entry ngăn nhiều worker đồng thời ghi
  trùng nghĩa. Không tự retry mạng trong backend. Nếu DB commit lỗi sau upload,
  lần thử lại dùng cache Gemini và cùng đường dẫn Storage; không tạo nhiều file.
- Response enrich: `status=complete|partial|not_found`, `meanings_saved`,
  `audio_saved`, `message`, `retry_after`. Hai cờ saved chỉ phần mới lưu lần này.
- Tham khảo upload Storage: https://supabase.com/docs/reference/python/storage-from-upload
