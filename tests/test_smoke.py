from termgrid.db import connect, add, list_servers, Server

def test_db_crud(tmp_path, monkeypatch):
    # Forzar DB a temporal para test
    monkeypatch.setenv("APPDATA", str(tmp_path))  # en Windows
    conn = connect()
    assert conn is not None
    sid = add(conn, Server(None,"Test","127.0.0.1","ssh","root",22,"linux"))
    rows = list_servers(conn)
    assert any(s.id == sid for s in rows)