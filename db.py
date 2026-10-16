import aiosqlite
import os
from datetime import datetime, timezone

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "complaints.db"))


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                complaint_number TEXT UNIQUE,
                caller_name TEXT,
                mobile TEXT,
                city TEXT,
                area TEXT,
                category TEXT,
                description TEXT,
                status TEXT DEFAULT 'Pending',
                timestamp TEXT,
                cluster_alert INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS transcripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                complaint_number TEXT,
                role TEXT,
                content TEXT,
                turn_index INTEGER,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (complaint_number) REFERENCES complaints(complaint_number)
            )
        """)
        await db.commit()


async def save_complaint(data: dict) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR IGNORE INTO complaints
                (complaint_number, caller_name, mobile, city, area, category, description, timestamp)
            VALUES
                (:complaint_number, :caller_name, :mobile, :city, :area, :category, :description, :timestamp)
        """, data)
        await db.commit()


async def get_caller_history(mobile: str) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT complaint_number, category, description, status, timestamp
            FROM complaints WHERE mobile = ?
            ORDER BY created_at DESC LIMIT 5
        """, (mobile,)) as cursor:
            rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def check_duplicate(mobile: str, category: str, within_days: int = 7) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT complaint_number, status, timestamp FROM complaints
            WHERE mobile = ? AND category = ?
              AND created_at >= datetime('now', ? || ' days')
            ORDER BY created_at DESC LIMIT 1
        """, (mobile, category, f"-{within_days}")) as cursor:
            row = await cursor.fetchone()
    return dict(row) if row else None


async def get_complaint_status(complaint_number: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT complaint_number, category, status, city, area, timestamp
            FROM complaints WHERE UPPER(complaint_number) = UPPER(?)
        """, (complaint_number,)) as cursor:
            row = await cursor.fetchone()
    return dict(row) if row else None


async def save_transcript(complaint_number: str, turns: list[dict]) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executemany("""
            INSERT INTO transcripts (complaint_number, role, content, turn_index)
            VALUES (:complaint_number, :role, :content, :index)
        """, [{"complaint_number": complaint_number, **t} for t in turns])
        await db.commit()


async def check_and_flag_cluster(area: str, category: str, within_days: int = 7) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT COUNT(*) FROM complaints
            WHERE area = ? AND category = ?
              AND created_at >= datetime('now', ? || ' days')
        """, (area, category, f"-{within_days}")) as cursor:
            row = await cursor.fetchone()
        count = row[0] if row else 0
        if count >= 3:
            await db.execute("""
                UPDATE complaints SET cluster_alert = 1
                WHERE area = ? AND category = ?
                  AND created_at >= datetime('now', ? || ' days')
            """, (area, category, f"-{within_days}"))
            await db.commit()
    return count


async def get_complaint_full(complaint_number: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM complaints WHERE UPPER(complaint_number) = UPPER(?)",
            (complaint_number,)
        ) as cursor:
            row = await cursor.fetchone()
    return dict(row) if row else None


async def get_all_complaints(category=None, status=None, area=None, search=None) -> list[dict]:
    clauses, params = [], []
    if category:
        clauses.append("category = ?"); params.append(category)
    if status:
        clauses.append("status = ?"); params.append(status)
    if area:
        clauses.append("area LIKE ?"); params.append(f"%{area}%")
    if search:
        clauses.append("(caller_name LIKE ? OR mobile LIKE ? OR complaint_number LIKE ?)")
        params += [f"%{search}%", f"%{search}%", f"%{search}%"]
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            f"SELECT * FROM complaints {where} ORDER BY created_at DESC", params
        ) as cursor:
            rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def update_complaint_status(complaint_number: str, status: str) -> bool:
    if status not in ("Pending", "In Progress", "Resolved"):
        return False
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE complaints SET status = ? WHERE complaint_number = ?",
            (status, complaint_number)
        )
        await db.commit()
    return True


async def get_transcript(complaint_number: str) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT role, content, turn_index FROM transcripts
            WHERE complaint_number = ? ORDER BY turn_index
        """, (complaint_number,)) as cursor:
            rows = await cursor.fetchall()
    return [dict(r) for r in rows]
