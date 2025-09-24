from __future__ import annotations
import sqlite3
from dataclasses import dataclass
from typing import Optional, List
from .config import get_db_path

@dataclass
class Server:
    id: Optional[int]
    name: str
    host: str
    protocol: str
    username: str
    port: int
    os: str
    tags: str = ""
    notes: str = ""
    group: str = ""  # <-- Nuevo campo


def connect() -> sqlite3.Connection:
    db = get_db_path()
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    conn.execute("""
    CREATE TABLE IF NOT EXISTS servers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        host TEXT NOT NULL,
        protocol TEXT NOT NULL,
        username TEXT NOT NULL,
        port INTEGER NOT NULL,
        os TEXT NOT NULL,
        tags TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        "group" TEXT DEFAULT '' 
    );
    """)
    return conn

def list_servers(conn, q: str = "", order: str = "name") -> List[Server]:
    allowed = {"name","os","protocol"}
    order_by = order if order in allowed else "name"
    if q:
        like = f"%{q}%"
        rows = conn.execute(f"""
            SELECT * FROM servers
            WHERE name LIKE ? OR host LIKE ? OR tags LIKE ? OR os LIKE ? OR protocol LIKE ?
            ORDER BY {order_by} COLLATE NOCASE
        """, (like, like, like, like, like)).fetchall()
    else:
        rows = conn.execute(f"SELECT * FROM servers ORDER BY {order_by} COLLATE NOCASE").fetchall()
    return [Server(**dict(r)) for r in rows]




def add(conn, s: Server) -> int:
    cur = conn.execute("""
        INSERT INTO servers(name,host,protocol,username,port,os,tags,notes)
        VALUES(?,?,?,?,?,?,?,?)
    """, (s.name, s.host, s.protocol, s.username, s.port, s.os, s.tags, s.notes))
    conn.commit()
    return cur.lastrowid

def update(conn, s: Server) -> None:
    conn.execute("""
        UPDATE servers SET
            name=?, host=?, protocol=?, username=?, port=?, os=?, tags=?, notes=?
        WHERE id=?
    """, (s.name, s.host, s.protocol, s.username, s.port, s.os, s.tags, s.notes, s.id))
    conn.commit()

def delete(conn, sid: int) -> None:
    conn.execute("DELETE FROM servers WHERE id=?", (sid,))
    conn.commit()







