"""MASTER baza: barcha botlar (Parent va Child) ro'yxati shu yerda saqlanadi."""
import time

import aiosqlite


class MasterDB:
    def __init__(self, path):
        self.path = str(path)
        self.conn: aiosqlite.Connection | None = None

    async def connect(self):
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA journal_mode=WAL")
        await self.conn.execute(
            """CREATE TABLE IF NOT EXISTS bots(
                bot_id INTEGER PRIMARY KEY,
                token TEXT UNIQUE NOT NULL,
                username TEXT,
                owner_id INTEGER,
                is_parent INTEGER DEFAULT 0,   -- 1 = asosiy bot, 0 = sub-bot (child)
                active INTEGER DEFAULT 1,
                created_at INTEGER)"""
        )
        await self.conn.commit()

    async def close(self):
        if self.conn:
            await self.conn.close()

    async def add_bot(self, bot_id, token, username, owner_id, is_parent):
        await self.conn.execute(
            "INSERT OR REPLACE INTO bots(bot_id,token,username,owner_id,is_parent,active,created_at) "
            "VALUES(?,?,?,?,?,1,?)",
            (bot_id, token, username, owner_id, is_parent, int(time.time())),
        )
        await self.conn.commit()

    async def get_bots(self):
        async with self.conn.execute("SELECT * FROM bots ORDER BY is_parent DESC, created_at") as cur:
            return [dict(r) for r in await cur.fetchall()]

    async def get_bot(self, bot_id):
        async with self.conn.execute("SELECT * FROM bots WHERE bot_id=?", (bot_id,)) as cur:
            r = await cur.fetchone()
            return dict(r) if r else None

    async def set_active(self, bot_id, active: int):
        await self.conn.execute("UPDATE bots SET active=? WHERE bot_id=?", (active, bot_id))
        await self.conn.commit()

    async def delete_bot(self, bot_id):
        await self.conn.execute("DELETE FROM bots WHERE bot_id=? AND is_parent=0", (bot_id,))
        await self.conn.commit()
