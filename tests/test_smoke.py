import pytest
from termgrid.db import connect, add, update, delete, list_servers, Server
from termgrid.static_names import OS_ICONS, PROTO_ICONS, DEFAULT_PORTS, os_icon, proto_icon
from termgrid.config import get_data_dir, get_db_path
from termgrid.Forms.NewServerForm import FormModal
from termgrid.db import Server
from textual.app import App

@pytest.fixture
def conn(tmp_path, monkeypatch):
    # Usar base de datos temporal
    monkeypatch.setenv("APPDATA", str(tmp_path))
    return connect()

def test_add_and_list(conn):
    s = Server(None, "TestSrv", "127.0.0.1", "ssh", "root", 22, "linux", "tag", "note", "group1")
    sid = add(conn, s)
    servers = list_servers(conn)
    assert any(srv.id == sid for srv in servers)

def test_update(conn):
    s = Server(None, "SrvUpd", "127.0.0.2", "ssh", "user", 22, "linux", "tag", "note", "group2")
    sid = add(conn, s)
    s.id = sid
    s.name = "SrvUpd2"
    update(conn, s)
    servers = list_servers(conn)
    assert any(srv.name == "SrvUpd2" for srv in servers)

def test_delete(conn):
    s = Server(None, "SrvDel", "127.0.0.3", "ssh", "user", 22, "linux", "tag", "note", "group3")
    sid = add(conn, s)
    delete(conn, sid)
    servers = list_servers(conn)
    assert not any(srv.id == sid for srv in servers)



def test_os_icon():
    assert os_icon("linux") == OS_ICONS["linux"]
    assert os_icon("windows") == OS_ICONS["windows"]
    assert os_icon("unknown") == OS_ICONS["other"]

def test_proto_icon():
    assert proto_icon("ssh") == PROTO_ICONS["ssh"]
    assert proto_icon("ftp") == PROTO_ICONS["ftp"]
    assert proto_icon("other") == "🔌"

def test_default_ports():
    assert DEFAULT_PORTS["ssh"] == 22
    assert DEFAULT_PORTS["rdp"] == 3389

def test_get_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    d = get_data_dir()
    assert str(tmp_path) in str(d)

def test_get_db_path(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    db_path = get_db_path()
    assert db_path.name == "servers.db"


class DummyApp(App):
    def compose(self):
        yield FormModal("Test", Server(None, "Srv", "127.0.0.1", "ssh", "root", 22, "linux"))

@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_formmodal_get_data():
    app = DummyApp()
    async with app.run_test() as pilot:
        modal = app.query_one(FormModal)
        data = modal.get_data()
        assert isinstance(data, Server)
        assert data.name == "Srv"
