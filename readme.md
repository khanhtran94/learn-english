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