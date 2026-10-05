"""Har bir bot uchun alohida SQLite baza (aiosqlite).

Parent va har bir Child bot o'z bazasiga ega: kontent, foydalanuvchilar,
kanallar va sozlamalar bir-biridan to'liq ajratilgan.
"""
import time
from collections import Counter

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY, full_name TEXT, username TEXT,
    joined_at INTEGER, last_active INTEGER, blocked INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS admins(user_id INTEGER PRIMARY KEY);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS force_channels(
    id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER UNIQUE, title TEXT, link TEXT, active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS post_channels(
    id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER UNIQUE, title TEXT, link TEXT, active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS contents(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    code INTEGER UNIQUE NOT NULL,
    title TEXT NOT NULL, genre TEXT, language TEXT, quality TEXT, year INTEGER, description TEXT,
    poster TEXT, file_id TEXT, file_type TEXT,
    views INTEGER DEFAULT 0, created_at INTEGER);
CREATE TABLE IF NOT EXISTS episodes(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    series_id INTEGER NOT NULL REFERENCES contents(id) ON DELETE CASCADE,
    season INTEGER NOT NULL, number INTEGER NOT NULL,
    code INTEGER UNIQUE NOT NULL, file_id TEXT, file_type TEXT, created_at INTEGER);
CREATE TABLE IF NOT EXISTS favorites(
    user_id INTEGER, content_id INTEGER REFERENCES contents(id) ON DELETE CASCADE,
    PRIMARY KEY(user_id, content_id));
CREATE TABLE IF NOT EXISTS ratings(
    user_id INTEGER, content_id INTEGER REFERENCES contents(id) ON DELETE CASCADE,
    score INTEGER, PRIMARY KEY(user_id, content_id));
CREATE INDEX IF NOT EXISTS idx_ep_series ON episodes(series_id, season, number);
CREATE INDEX IF NOT EXISTS idx_content_type ON contents(type);
"""

CHANNEL_TABLES = {"force": "force_channels", "post": "post_channels"}
CONTENT_FIELDS = {"title", "code", "genre", "language", "quality", "year",
                  "description", "poster", "file_id", "file_type"}


class Database:
    def __init__(self, path):
        self.path = str(path)
        self.conn: aiosqlite.Connection | None = None

    # ------------------------------------------------------------ ulanish
    async def connect(self):
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA journal_mode=WAL")
        await self.conn.execute("PRAGMA foreign_keys=ON")
        # Kirill/lotin harflarida ham katta-kichik harfga bog'liq bo'lmagan qidiruv uchun
        await self.conn.create_function("py_lower", 1, lambda s: s.lower() if isinstance(s, str) else s)
        await self.conn.executescript(SCHEMA)
        await self.conn.commit()

    async def close(self):
        if self.conn:
            await self.conn.close()

    # ------------------------------------------------------------ yordamchi
    async def _exec(self, sql, params=()):
        cur = await self.conn.execute(sql, params)
        await self.conn.commit()
        last = cur.lastrowid
        await cur.close()
        return last

    async def _one(self, sql, params=()):
        async with self.conn.execute(sql, params) as cur:
            r = await cur.fetchone()
            return dict(r) if r else None

    async def _all(self, sql, params=()):
        async with self.conn.execute(sql, params) as cur:
            return [dict(r) for r in await cur.fetchall()]

    async def _val(self, sql, params=(), default=0):
        async with self.conn.execute(sql, params) as cur:
            r = await cur.fetchone()
            return r[0] if r and r[0] is not None else default

    # ------------------------------------------------------------ sozlamalar
    async def get_setting(self, key, default=None):
        v = await self._val("SELECT value FROM settings WHERE key=?", (key,), None)
        return default if v is None else v

    async def set_setting(self, key, value):
        await self._exec("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, str(value)))

    # ------------------------------------------------------------ adminlar
    async def is_admin(self, user_id):
        return bool(await self._val("SELECT 1 FROM admins WHERE user_id=?", (user_id,)))

    async def add_admin(self, user_id):
        await self._exec("INSERT OR IGNORE INTO admins(user_id) VALUES(?)", (user_id,))

    async def del_admin(self, user_id):
        await self._exec("DELETE FROM admins WHERE user_id=?", (user_id,))

    async def list_admins(self):
        return [r["user_id"] for r in await self._all("SELECT user_id FROM admins")]

    # ------------------------------------------------------------ foydalanuvchilar
    async def touch_user(self, user_id, full_name, username):
        now = int(time.time())
        await self._exec(
            "INSERT INTO users(user_id,full_name,username,joined_at,last_active) VALUES(?,?,?,?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET full_name=excluded.full_name, "
            "username=excluded.username, last_active=excluded.last_active, blocked=0",
            (user_id, full_name, username, now, now),
        )

    async def user_ids(self):
        return [r["user_id"] for r in await self._all("SELECT user_id FROM users WHERE blocked=0")]

    async def set_blocked(self, user_id, flag=True):
        await self._exec("UPDATE users SET blocked=? WHERE user_id=?", (int(flag), user_id))

    async def stats(self):
        day = int(time.time()) - 86400
        return {
            "users": await self._val("SELECT COUNT(*) FROM users"),
            "new_today": await self._val("SELECT COUNT(*) FROM users WHERE joined_at>=?", (day,)),
            "active": await self._val("SELECT COUNT(*) FROM users WHERE last_active>=?", (day,)),
            "blocked": await self._val("SELECT COUNT(*) FROM users WHERE blocked=1"),
            "movies": await self._val("SELECT COUNT(*) FROM contents WHERE type='movie'"),
            "series": await self._val("SELECT COUNT(*) FROM contents WHERE type='series'"),
            "episodes": await self._val("SELECT COUNT(*) FROM episodes"),
            "views": await self._val("SELECT COALESCE(SUM(views),0) FROM contents"),
            "favs": await self._val("SELECT COUNT(*) FROM favorites"),
            "force": await self._val("SELECT COUNT(*) FROM force_channels"),
            "post": await self._val("SELECT COUNT(*) FROM post_channels"),
        }

    # ------------------------------------------------------------ kanallar (force / post)
    async def add_channel(self, kind, chat_id, title, link):
        t = CHANNEL_TABLES[kind]
        await self._exec(
            f"INSERT OR REPLACE INTO {t}(chat_id,title,link,active) VALUES(?,?,?,1)", (chat_id, title, link))

    async def list_channels(self, kind, only_active=False):
        t = CHANNEL_TABLES[kind]
        sql = f"SELECT * FROM {t}" + (" WHERE active=1" if only_active else "") + " ORDER BY id"
        return await self._all(sql)

    async def del_channel(self, kind, ch_id):
        await self._exec(f"DELETE FROM {CHANNEL_TABLES[kind]} WHERE id=?", (ch_id,))

    async def toggle_channel(self, kind, ch_id):
        await self._exec(f"UPDATE {CHANNEL_TABLES[kind]} SET active=1-active WHERE id=?", (ch_id,))

    # ------------------------------------------------------------ kodlar
    async def code_exists(self, code):
        return bool(await self._val(
            "SELECT 1 FROM contents WHERE code=? UNION SELECT 1 FROM episodes WHERE code=?", (code, code)))

    async def next_code(self):
        a = await self._val("SELECT MAX(code) FROM contents")
        b = await self._val("SELECT MAX(code) FROM episodes")
        return max(a, b) + 1

    async def find_by_code(self, code):
        """Kod bo'yicha kino/serial yoki alohida seriyani topadi."""
        c = await self._one("SELECT * FROM contents WHERE code=?", (code,))
        if c:
            return "content", c
        e = await self._one("SELECT * FROM episodes WHERE code=?", (code,))
        return ("episode", e) if e else None

    # ------------------------------------------------------------ kontent
    async def add_content(self, type_, f: dict):
        return await self._exec(
            "INSERT INTO contents(type,code,title,genre,language,quality,year,description,"
            "poster,file_id,file_type,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (type_, f["code"], f["title"], f.get("genre"), f.get("language"), f.get("quality"),
             f.get("year"), f.get("description"), f.get("poster"), f.get("file_id"),
             f.get("file_type"), int(time.time())))

    async def update_content(self, cid, **fields):
        fields = {k: v for k, v in fields.items() if k in CONTENT_FIELDS}
        if not fields:
            return
        sets = ",".join(f"{k}=?" for k in fields)
        await self._exec(f"UPDATE contents SET {sets} WHERE id=?", (*fields.values(), cid))

    async def get_content(self, cid):
        return await self._one("SELECT * FROM contents WHERE id=?", (cid,))

    async def delete_content(self, cid):
        await self._exec("DELETE FROM contents WHERE id=?", (cid,))

    async def inc_views(self, cid):
        await self._exec("UPDATE contents SET views=views+1 WHERE id=?", (cid,))

    async def random_content(self):
        return await self._one("SELECT * FROM contents ORDER BY RANDOM() LIMIT 1")

    @staticmethod
    def _where(kind, value, user_id):
        """Ro'yxat turlari: q=qidiruv, g=janr, y=yil, top, new, fav, m=kinolar, s=seriallar."""
        if kind == "q":
            v = f"%{str(value).lower()}%"
            return "(py_lower(title) LIKE ? OR py_lower(genre) LIKE ?)", [v, v], "views DESC, id DESC"
        if kind == "g":
            return "py_lower(genre) LIKE ?", [f"%{str(value).lower()}%"], "id DESC"
        if kind == "y":
            return "year=?", [int(value)], "views DESC, id DESC"
        if kind == "top":
            return "1=1", [], "views DESC, id DESC"
        if kind == "new":
            return "1=1", [], "id DESC"
        if kind == "fav":
            return "id IN (SELECT content_id FROM favorites WHERE user_id=?)", [user_id], "id DESC"
        if kind == "m":
            return "type='movie'", [], "id DESC"
        if kind == "s":
            return "type='series'", [], "id DESC"
        raise ValueError(kind)

    async def list_by(self, kind, value=None, user_id=0, offset=0, limit=8):
        where, params, order = self._where(kind, value, user_id)
        total = await self._val(f"SELECT COUNT(*) FROM contents WHERE {where}", params)
        rows = await self._all(
            f"SELECT * FROM contents WHERE {where} ORDER BY {order} LIMIT ? OFFSET ?",
            [*params, limit, offset])
        return rows, total

    async def genres(self, limit=30):
        rows = await self._all("SELECT genre FROM contents WHERE genre IS NOT NULL AND genre!=''")
        cnt = Counter()
        for r in rows:
            for g in r["genre"].split(","):
                g = g.strip()
                if g:
                    cnt[g.capitalize()] += 1
        return cnt.most_common(limit)

    async def years(self, limit=40):
        rows = await self._all(
            "SELECT DISTINCT year FROM contents WHERE year IS NOT NULL ORDER BY year DESC LIMIT ?", (limit,))
        return [r["year"] for r in rows]

    # ------------------------------------------------------------ seriyalar
    async def add_episode(self, series_id, season, number, code, file_id, file_type):
        return await self._exec(
            "INSERT INTO episodes(series_id,season,number,code,file_id,file_type,created_at) "
            "VALUES(?,?,?,?,?,?,?)", (series_id, season, number, code, file_id, file_type, int(time.time())))

    async def get_episode(self, eid):
        return await self._one("SELECT * FROM episodes WHERE id=?", (eid,))

    async def seasons(self, series_id):
        return await self._all(
            "SELECT season, COUNT(*) AS cnt FROM episodes WHERE series_id=? GROUP BY season ORDER BY season",
            (series_id,))

    async def episodes_of(self, series_id, season):
        return await self._all(
            "SELECT * FROM episodes WHERE series_id=? AND season=? ORDER BY number", (series_id, season))

    async def next_episode_number(self, series_id, season):
        m = await self._val(
            "SELECT MAX(number) FROM episodes WHERE series_id=? AND season=?", (series_id, season))
        return m + 1

    async def next_episode(self, ep):
        return await self._one(
            "SELECT * FROM episodes WHERE series_id=? AND ((season=? AND number>?) OR season>?) "
            "ORDER BY season, number LIMIT 1", (ep["series_id"], ep["season"], ep["number"], ep["season"]))

    async def delete_episode(self, eid):
        await self._exec("DELETE FROM episodes WHERE id=?", (eid,))

    async def count_episodes(self, series_id):
        return await self._val("SELECT COUNT(*) FROM episodes WHERE series_id=?", (series_id,))

    # ------------------------------------------------------------ saqlanganlar / baholash
    async def is_fav(self, user_id, cid):
        return bool(await self._val("SELECT 1 FROM favorites WHERE user_id=? AND content_id=?", (user_id, cid)))

    async def toggle_fav(self, user_id, cid):
        """True qaytarsa — saqlandi, False — olib tashlandi."""
        if await self.is_fav(user_id, cid):
            await self._exec("DELETE FROM favorites WHERE user_id=? AND content_id=?", (user_id, cid))
            return False
        await self._exec("INSERT OR IGNORE INTO favorites(user_id,content_id) VALUES(?,?)", (user_id, cid))
        return True

    async def set_rating(self, user_id, cid, score):
        await self._exec("INSERT OR REPLACE INTO ratings(user_id,content_id,score) VALUES(?,?,?)",
                         (user_id, cid, score))

    async def user_rating(self, user_id, cid):
        return await self._val("SELECT score FROM ratings WHERE user_id=? AND content_id=?", (user_id, cid), None)

    async def get_rating(self, cid):
        r = await self._one("SELECT AVG(score) AS a, COUNT(*) AS c FROM ratings WHERE content_id=?", (cid,))
        return (r["a"] or 0.0, r["c"]) if r else (0.0, 0)
  
