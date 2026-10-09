"""PostgreSQL connections for the personal vocabulary library."""
import os
from contextlib import contextmanager
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from fastapi import HTTPException
from psycopg2.extras import RealDictCursor

ENV_PATH = Path(__file__).resolve().parents[1] / '.env'


@contextmanager
def database_cursor():
    load_dotenv(ENV_PATH, encoding='utf-8-sig')
    url = os.getenv('SUPABASE_URL', '').strip()
    if not url.startswith(('postgresql://', 'postgres://')):
        raise HTTPException(503, 'SUPABASE_URL cần là chuỗi kết nối PostgreSQL trong backend/.env.')
    connection = None
    try:
        connection = psycopg2.connect(url, sslmode='require', connect_timeout=10)
        connection.set_session(readonly=True, isolation_level='REPEATABLE READ')
        with connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SET LOCAL statement_timeout = '10s'")
                yield cursor
    except psycopg2.Error as exc:
        # PostgreSQL errors may contain connection details; never return them.
        raise HTTPException(503, 'Không đọc được PostgreSQL. Kiểm tra URL, mật khẩu, kết nối mạng và các bảng đã tạo.') from exc
    finally:
        if connection is not None:
            connection.close()
