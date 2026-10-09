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
