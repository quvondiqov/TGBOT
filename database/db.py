import aiosqlite
import asyncio

DB_PATH = "tgbot.db"


async def create_tables():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                gender      TEXT NOT NULL,
                name        TEXT NOT NULL,
                age         INTEGER NOT NULL,
                bio         TEXT,
                photo_id    TEXT,
                city        TEXT,
                is_active   INTEGER DEFAULT 1,
                created_at  TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS purchases (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                buyer_id    INTEGER NOT NULL,
                target_id   INTEGER NOT NULL,
                pay_id      TEXT NOT NULL,
                status      TEXT DEFAULT 'pending',
                created_at  TEXT DEFAULT (datetime('now','localtime')),
                UNIQUE(buyer_id, target_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS likes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user   INTEGER NOT NULL,
                to_user     INTEGER NOT NULL,
                created_at  TEXT DEFAULT (datetime('now','localtime')),
                UNIQUE(from_user, to_user)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS viewed (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                viewer_id   INTEGER NOT NULL,
                target_id   INTEGER NOT NULL,
                UNIQUE(viewer_id, target_id)
            )
        """)
        await db.commit()


# ──────────────────── USERS ────────────────────

async def add_user(user_id: int, gender: str, name: str, age: int,
                   bio: str = None, photo_id: str = None, city: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO users (user_id, gender, name, age, bio, photo_id, city)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, gender, name, age, bio, photo_id, city))
        await db.commit()


async def get_user(user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def update_user_field(user_id: int, field: str, value):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE users SET {field} = ? WHERE user_id = ?", (value, user_id))
        await db.commit()


async def get_next_profile(viewer_id: int, target_gender: str) -> dict | None:
    """Ko'ruvchi foydalanuvchi uchun navbatdagi ko'rilmagan profilni olish"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM users
            WHERE gender = ?
              AND user_id != ?
              AND is_active = 1
              AND user_id NOT IN (
                  SELECT target_id FROM viewed WHERE viewer_id = ?
              )
            ORDER BY RANDOM()
            LIMIT 1
        """, (target_gender, viewer_id, viewer_id)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def mark_viewed(viewer_id: int, target_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO viewed (viewer_id, target_id) VALUES (?, ?)",
            (viewer_id, target_id)
        )
        await db.commit()


async def clear_viewed(viewer_id: int):
    """Remove all viewed entries for a viewer to restart recommendation cycle."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM viewed WHERE viewer_id = ?",
            (viewer_id,)
        )
        await db.commit()


# ──────────────────── LIKES ────────────────────

async def add_like(from_user: int, to_user: int) -> bool:
    """Like qo'shish. Agar o'zaro like bo'lsa True qaytaradi."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO likes (from_user, to_user) VALUES (?, ?)",
            (from_user, to_user)
        )
        await db.commit()
        # O'zaro like tekshirish
        async with db.execute(
            "SELECT 1 FROM likes WHERE from_user = ? AND to_user = ?",
            (to_user, from_user)
        ) as cursor:
            row = await cursor.fetchone()
            return row is not None


# ──────────────────── PURCHASES ────────────────────

async def create_purchase(buyer_id: int, target_id: int, pay_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR IGNORE INTO purchases (buyer_id, target_id, pay_id, status)
            VALUES (?, ?, ?, 'pending')
        """, (buyer_id, target_id, pay_id))
        await db.commit()


async def get_purchase(buyer_id: int, target_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM purchases WHERE buyer_id = ? AND target_id = ?
        """, (buyer_id, target_id)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_purchase_by_pay_id(pay_id: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM purchases WHERE pay_id = ?
        """, (pay_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def update_purchase_status(pay_id: str, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE purchases SET status = ? WHERE pay_id = ?",
            (status, pay_id)
        )
        await db.commit()


async def is_profile_purchased(buyer_id: int, target_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT 1 FROM purchases WHERE buyer_id = ? AND target_id = ? AND status = 'paid'
        """, (buyer_id, target_id)) as cursor:
            row = await cursor.fetchone()
            return row is not None


async def get_pending_purchases() -> list[dict]:
    """Hali tekshirilmagan to'lovlar ro'yxati"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM purchases WHERE status = 'pending'"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
