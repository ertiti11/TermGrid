# tui_servers.py
# TUI de inventario de servidores con conexión 1-click (SSH/RDP/VNC/FTP/SFTP)
# Requiere: textual, rich, sqlite3 (std), subprocess, shutil

from __future__ import annotations
import os
import sqlite3
import subprocess
import shutil
import platform
from dataclasses import dataclass
from typing import Optional, List, Tuple

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, Static, Button, DataTable, Select, Log, TextArea
from textual.containers import Horizontal, Container, ScrollableContainer
from textual.reactive import reactive
from rich.text import Text

DB_PATH = os.path.join(os.path.dirname(__file__), "servers.db")

# ---------- Modelo & almacenamiento ----------

@dataclass
class Server:
    id: Optional[int]
    name: str
    host: str
    protocol: str      # ssh | rdp | vnc | ftp | sftp
    username: str
    port: int
    os: str            # linux | windows | mac | bsd | network | other
    tags: str = ""
    notes: str = ""

def db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
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
        notes TEXT DEFAULT ''
    );
    """)
    return conn

def db_list(conn: sqlite3.Connection, q: str = "", order: str = "name") -> List[Server]:
    allowed = {"name","os","protocol"}
    order_by = order if order in allowed else "name"
    if q:
        qlike = f"%{q}%"
        rows = conn.execute(f"""
            SELECT * FROM servers
            WHERE name LIKE ? OR host LIKE ? OR tags LIKE ? OR os LIKE ? OR protocol LIKE ?
            ORDER BY {order_by} COLLATE NOCASE
        """, (qlike, qlike, qlike, qlike, qlike)).fetchall()
    else:
        rows = conn.execute(f"SELECT * FROM servers ORDER BY {order_by} COLLATE NOCASE").fetchall()
    return [Server(**dict(r)) for r in rows]

def db_add(conn: sqlite3.Connection, s: Server) -> int:
    cur = conn.execute("""
        INSERT INTO servers(name,host,protocol,username,port,os,tags,notes)
        VALUES(?,?,?,?,?,?,?,?)
    """, (s.name, s.host, s.protocol, s.username, s.port, s.os, s.tags, s.notes))
    conn.commit()
    return cur.lastrowid

def db_update(conn: sqlite3.Connection, s: Server) -> None:
    conn.execute("""
        UPDATE servers SET
            name=?, host=?, protocol=?, username=?, port=?, os=?, tags=?, notes=?
        WHERE id=?
    """, (s.name, s.host, s.protocol, s.username, s.port, s.os, s.tags, s.notes, s.id))
    conn.commit()

def db_delete(conn: sqlite3.Connection, sid: int) -> None:
    conn.execute("DELETE FROM servers WHERE id=?", (sid,))
    conn.commit()

# ---------- Lógica de conexión ----------

def which(cmd: str) -> Optional[str]:
    return shutil.which(cmd)

def connect(server: Server) -> Tuple[bool, str, Optional[List[str]]]:
    """Prepara y lanza el cliente. Devuelve (ok, msg, cmd_lanzado)."""
    sysname = platform.system().lower()

    def found(cmd): return shutil.which(cmd)

    if server.protocol == "ssh":
        ssh = found("ssh")
        if not ssh:
            return False, "No se encontró 'ssh'. Instala OpenSSH Client.", None
        if not server.username:
            return False, "Usuario vacío para SSH.", None
        base = [ssh, f"{server.username}@{server.host}", "-p", str(server.port or 22)]

    elif server.protocol == "sftp":
        sftp = found("sftp")
        if not sftp:
            return False, "No se encontró 'sftp'. Instala OpenSSH Client.", None
        if not server.username:
            return False, "Usuario vacío para SFTP.", None
        base = [sftp, "-P", str(server.port or 22), f"{server.username}@{server.host}"]

    elif server.protocol == "ftp":
        ftp = found("ftp") or found("lftp") or found("ncftp")
        if not ftp:
            return False, "No se encontró cliente FTP. Instala 'ftp', 'lftp' o 'ncftp'.", None
        if "lftp" in ftp:
            if server.username:
                base = [ftp, f"ftp://{server.username}@{server.host}:{server.port or 21}"]
            else:
                base = [ftp, f"ftp://{server.host}:{server.port or 21}"]
        else:
            base = [ftp, server.host, str(server.port or 21)]

    elif server.protocol == "rdp":
        if sysname == "windows":
            mstsc = found("mstsc") or found("mstsc.exe")
            if not mstsc:
                return False, "No se encontró 'mstsc' (Cliente de Escritorio remoto).", None
            base = [mstsc, f"/v:{server.host}:{server.port or 3389}", "/prompt"]
        else:
            rdesktop = found("rdesktop") or found("xfreerdp") or found("remmina")
            if not rdesktop:
                return False, "Instala 'rdesktop', 'xfreerdp' o 'remmina' para RDP.", None
            if "xfreerdp" in rdesktop:
                base = [rdesktop, f"/v:{server.host}:{server.port or 3389}"]
                if server.username:
                    base.extend([f"/u:{server.username}"])
            else:
                base = [rdesktop, f"{server.host}:{server.port or 3389}"]

    elif server.protocol == "vnc":
        vnc = (found("vncviewer") or found("realvnc") or
               found("tigervncviewer") or found("xtightvncviewer"))
        if not vnc:
            return False, "Instala un viewer VNC (p. ej., TigerVNC: vncviewer).", None
        base = [vnc, f"{server.host}:{server.port or 5900}"]

    else:
        return False, f"Protocolo no soportado: {server.protocol}", None

    try:
        if sysname == "windows":
            if server.protocol in ["ssh", "sftp", "ftp"]:
                cmd = ["cmd", "/c", "start", "", "cmd", "/k"] + base
            else:
                cmd = ["cmd", "/c", "start", "", *base]
        else:
            term = found("gnome-terminal") or found("konsole") or found("xterm")
            if term and server.protocol in ["ssh", "sftp", "ftp"]:
                if "gnome-terminal" in term:
                    cmd = [term, "--", *base]
                elif "konsole" in term:
                    cmd = [term, "-e", *base]
                else:
                    cmd = [term, "-e", *base]
            else:
                cmd = base

        subprocess.Popen(cmd)
        return True, f"Conectando con {server.name} ({server.protocol.upper()})…", cmd
    except Exception as e:
        return False, f"Error al lanzar cliente: {e}", None

# ---------- TUI con Textual ----------

OS_ICONS = {
    "linux": "🐧", "windows": "🪟", "mac": "🍎", "bsd": "🐡", "network": "🖧", "other": "🖥️"
}
PROTO_ICONS = {"ssh":"🔐","rdp":"🖥️","vnc":"🖱️","ftp":"📁","sftp":"🔒"}

# Puertos por defecto para cada protocolo
DEFAULT_PORTS = {
    "ssh": 22,
    "sftp": 22,
    "ftp": 21,
    "rdp": 3389,
    "vnc": 5900
}

def os_icon(osname:str) -> str:
    return OS_ICONS.get(osname.lower(), OS_ICONS["other"])

def proto_icon(p:str) -> str:
    return PROTO_ICONS.get(p.lower(), "🔌")

class FormModal(Container):
    """Modal mejorado para añadir/editar servidores."""
    DEFAULT_CSS = """
    FormModal {
        width: 90%;
        height: 85%;
        padding: 2;
        border: thick $accent;
        background: $surface;
        layer: overlay;
        offset-x: 5%;
        offset-y: 7%;
        border-title-color: $accent;
        border-title-style: bold;
    }
    
    FormModal .form-row {
        height: auto;
        margin-bottom: 1;
    }
    
    FormModal .form-label {
        width: 15;
        text-align: right;
        padding-right: 1;
        color: $text-muted;
        text-style: bold;
    }
    
    FormModal .form-input {
        width: 1fr;
    }
    
    FormModal .button-row {
        height: 3;
        margin-top: 1;
        align: center middle;
    }
    
    FormModal Button {
        margin: 0 1;
        min-width: 12;
    }
    
    FormModal TextArea {
        height: 4;
    }
    """

    def __init__(self, title: str, server: Optional[Server] = None) -> None:
        super().__init__()
        self.border_title = title
        self.server = server or Server(None,"","","ssh","",22,"linux","","")
        
        # Widgets del formulario
        self.in_name = Input(placeholder="Ej: Servidor Web Principal", value=self.server.name, id="name")
        self.in_host = Input(placeholder="192.168.1.100 o servidor.ejemplo.com", value=self.server.host)
        self.in_user = Input(placeholder="root, admin, usuario...", value=self.server.username)
        self.in_port = Input(placeholder="Puerto", value=str(self.server.port or DEFAULT_PORTS.get(self.server.protocol, 22)))
        
        self.sel_proto = Select(
            ((f"{PROTO_ICONS['ssh']} SSH - Secure Shell","ssh"),
             (f"{PROTO_ICONS['sftp']} SFTP - Secure File Transfer","sftp"),
             (f"{PROTO_ICONS['ftp']} FTP - File Transfer Protocol","ftp"),
             (f"{PROTO_ICONS['rdp']} RDP - Remote Desktop","rdp"),
             (f"{PROTO_ICONS['vnc']} VNC - Virtual Network Computing","vnc")),
            value=self.server.protocol, 
            id="proto"
        )
        
        self.sel_os = Select(
            ((f"{OS_ICONS['linux']} Linux","linux"),
             (f"{OS_ICONS['windows']} Windows","windows"),
             (f"{OS_ICONS['mac']} macOS","mac"),
             (f"{OS_ICONS['bsd']} BSD","bsd"),
             (f"{OS_ICONS['network']} Network Device","network"),
             (f"{OS_ICONS['other']} Other","other")),
            value=self.server.os, 
            id="os"
        )
        
        self.in_tags = Input(placeholder="web, database, production, backup...", value=self.server.tags)
        self.ta_notes = TextArea(text=self.server.notes, soft_wrap=True)

    def compose(self) -> ComposeResult:
        with ScrollableContainer():
            with Horizontal(classes="form-row"):
                yield Static("Nombre:", classes="form-label")
                yield self.in_name
            
            with Horizontal(classes="form-row"):
                yield Static("Host/IP:", classes="form-label")
                yield self.in_host
            
            with Horizontal(classes="form-row"):
                yield Static("Protocolo:", classes="form-label")
                yield self.sel_proto
            
            with Horizontal(classes="form-row"):
                yield Static("Usuario:", classes="form-label")
                yield self.in_user
            
            with Horizontal(classes="form-row"):
                yield Static("Puerto:", classes="form-label")
                yield self.in_port
            
            with Horizontal(classes="form-row"):
                yield Static("Sistema:", classes="form-label")
                yield self.sel_os
            
            with Horizontal(classes="form-row"):
                yield Static("Tags:", classes="form-label")
                yield self.in_tags
            
            with Horizontal(classes="form-row"):
                yield Static("Notas:", classes="form-label")
                yield self.ta_notes
            
            with Horizontal(classes="button-row"):
                yield Button("💾 Guardar", id="save", variant="success")
                yield Button("❌ Cancelar", id="cancel", variant="error")

    def on_select_changed(self, event: Select.Changed):
        if event.select is self.sel_proto:
            # Auto-ajustar puerto cuando se cambia protocolo
            new_port = DEFAULT_PORTS.get(self.sel_proto.value, 22)
            current = (self.in_port.value or "").strip()
            # Solo cambiar si el puerto actual es vacío o es uno de los puertos por defecto
            if current in ("", "22", "21", "3389", "5900") or current == str(new_port):
                self.in_port.value = str(new_port)

    def on_mount(self) -> None:
        # Enfocar el primer campo
        self.set_timer(0.1, lambda: self.in_name.focus())

    def get_data(self) -> Optional[Server]:
        try:
            port = int((self.in_port.value or "").strip() or "0")
        except Exception:
            port = 0
        
        name = self.in_name.value.strip()
        host = self.in_host.value.strip()
        username = self.in_user.value.strip()
        
        # Validaciones
        if not name:
            return None
        if not host:
            return None
        if self.sel_proto.value in ["ssh", "sftp"] and not username:
            return None
        if port <= 0:
            return None
            
        return Server(
            id=self.server.id,
            name=name,
            host=host,
            protocol=self.sel_proto.value,
            username=username,
            port=port,
            os=self.sel_os.value,
            tags=self.in_tags.value.strip(),
            notes=self.ta_notes.text.strip()
        )

class ServerTUI(App):
    CSS = """
    Screen { 
        layout: vertical; 
        background: $surface;
    }
    
    #toolbar { 
        height: 5; 
        padding: 1; 
        background: $panel;
        border: solid $primary;
        margin-bottom: 1;
    }
    
    #toolbar .toolbar-row {
        height: auto;
        margin-bottom: 1;
    }
    
    #toolbar Static {
        color: $accent;
        text-style: bold;
        width: auto;
        margin-right: 2;
    }
    
    #search {
        width: 1fr;
        margin-right: 1;
    }
    
    #sortsel {
        width: 20;
    }
    
    #table { 
        height: 1fr; 
        margin-bottom: 1;
        border: solid $primary;
    }
    
    #status { 
        height: 6; 
        background: $panel;
        border: solid $primary;
        padding: 1;
    }
    
    DataTable {
        background: $surface;
    }
    
    DataTable > .datatable--header {
        background: $primary;
        color: $text;
        text-style: bold;
    }
    
    DataTable > .datatable--cursor {
        background: $accent 50%;
    }
    
    .status-title {
        color: $accent;
        text-style: bold;
    }
    """

    BINDINGS = [
        ("q", "quit", "Salir"),
        ("ctrl+n,a", "add_server", "Nuevo"),
        ("ctrl+e,e", "edit_server", "Editar"),
        ("delete,ctrl+d", "delete_server", "Borrar"),
        ("enter,space", "connect_server", "Conectar"),
        ("ctrl+f,/", "focus_search", "Buscar"),
        ("ctrl+s,s", "cycle_sort", "Ordenar"),
        ("ctrl+r,r", "refresh_table", "Actualizar"),
    ]

    filter_text = reactive("")
    sort_field = reactive("name")

    def __init__(self) -> None:
        super().__init__()
        self.title = "🖥️ Server Manager - Gestión de Servidores"
        self.conn = db_connect()
        self.modal: Optional[FormModal] = None
        self.table: DataTable
        self.row_keys: List[int] = []

    def refresh_table(self):
        """Recarga la tabla de servidores según el filtro y orden actuales."""
        self.table.clear()
        self.row_keys = []
        servers = db_list(self.conn, self.filter_text, self.sort_field)
        
        for s in servers:
            # Crear texto rico para las celdas
            proto_text = Text()
            proto_text.append(proto_icon(s.protocol), style="bold")
            proto_text.append(f" {s.protocol.upper()}")
            
            os_text = Text()
            os_text.append(os_icon(s.os), style="bold") 
            os_text.append(f" {s.os.title()}")
            
            # Truncar notas si son muy largas
            notes_display = s.notes[:30] + "..." if len(s.notes) > 30 else s.notes
            
            # Formatear tags
            tags_display = s.tags.replace(",", " • ") if s.tags else ""
            
            self.table.add_row(
                str(s.id),
                s.name,
                s.host,
                proto_text,
                s.username or "—",
                str(s.port),
                os_text,
                tags_display,
                notes_display
            )
            self.row_keys.append(s.id)
        
        # Mostrar estadísticas
        total = len(servers)
        by_proto = {}
        by_os = {}
        for s in servers:
            by_proto[s.protocol] = by_proto.get(s.protocol, 0) + 1
            by_os[s.os] = by_os.get(s.os, 0) + 1
        
        stats = f"Total: [bold]{total}[/] servidores"
        if by_proto:
            proto_stats = " • ".join([f"{proto_icon(k)} {k.upper()}: {v}" for k, v in by_proto.items()])
            stats += f" | {proto_stats}"
        
        self.status_log.write(f"[green]{stats}[/]")
        
        # Mover cursor a la primera fila
        if servers and hasattr(self.table, 'move_cursor'):
            self.table.move_cursor(row=0, column=0)

    def action_refresh_table(self):
        """Acción para refrescar la tabla manualmente."""
        self.refresh_table()
        self.status_log.write("[green]📊 Tabla actualizada[/]")
   
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Container(id="toolbar"):
            with Horizontal(classes="toolbar-row"):
                yield Static("🔍 Buscar:")
                self.search = Input(placeholder="Nombre, host, tags, SO...", id="search")
                yield self.search
                yield Static("📋 Ordenar:")
                self.sort_select = Select(
                    (("📝 Nombre","name"),("🖥️ Sistema","os"),("🔌 Protocolo","protocol")), 
                    value="name", 
                    id="sortsel"
                )
                yield self.sort_select
            
            with Horizontal(classes="toolbar-row"):
                yield Button("➕ Nuevo", id="btn-add", variant="success")
                yield Button("✏️ Editar", id="btn-edit", variant="primary")
                yield Button("🗑️ Borrar", id="btn-delete", variant="error")
                yield Button("🔄 Actualizar", id="btn-refresh")

        # Tabla principal
        self.table = DataTable(id="table", zebra_stripes=True)
        try:
            self.table.cursor_type = "row"
        except Exception:
            pass
        yield self.table
        
        # Panel de estado
        with Container(id="status"):
            yield Static("📊 Estado:", classes="status-title")
            self.status_log = Log(highlight=True)
            yield self.status_log

        yield Footer()

    def on_mount(self) -> None:
        # Configurar columnas de la tabla con anchos apropiados
        columns = [
            ("ID", 6),
            ("Nombre", 20), 
            ("Host", 18),
            ("Protocolo", 12),
            ("Usuario", 12),
            ("Puerto", 8),
            ("Sistema", 12),
            ("Tags", 15),
            ("Notas", 25)
        ]
        for col, width in columns:
            self.table.add_column(col, width=width)
        
        self.refresh_table()
        self.status_log.write("[bold cyan]🚀 Server Manager iniciado[/]")
        self.status_log.write("[dim]💡 Atajos: Ctrl+N=Nuevo • Enter=Conectar • E=Editar • Del=Borrar • /=Buscar[/]")

    def get_selected_server(self) -> Optional[Server]:
        """Get the currently selected server from the table."""
        if not self.table.row_count or not self.row_keys:
            return None
        
        cursor_row = getattr(self.table, "cursor_row", None)
        if cursor_row is None or cursor_row < 0 or cursor_row >= len(self.row_keys):
            return None
        
        server_id = self.row_keys[cursor_row]
        row = self.conn.execute("SELECT * FROM servers WHERE id=?", (server_id,)).fetchone()
        return Server(**dict(row)) if row else None

    def action_focus_search(self):
        self.set_focus(self.search)

    def on_input_changed(self, event: Input.Changed):
        if event.input.id == "search":
            self.filter_text = event.value
            self.refresh_table()

    def on_select_changed(self, event: Select.Changed):
        if event.select.id == "sortsel":
            self.sort_field = event.value
            self.refresh_table()

    def action_cycle_sort(self):
        order = ["name","os","protocol"]
        idx = (order.index(self.sort_field)+1) % len(order)
        self.sort_field = order[idx]
        self.sort_select.value = self.sort_field
        self.refresh_table()

    def action_add_server(self):
        self.modal = FormModal("➕ Añadir Nuevo Servidor", None)
        self.mount(self.modal)

    def action_edit_server(self):
        s = self.get_selected_server()
        if not s:
            self.status_log.write("[yellow]⚠️ No hay servidor seleccionado[/]")
            return
        self.modal = FormModal(f"✏️ Editar Servidor: {s.name}", s)
        self.mount(self.modal)

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-add":
            self.action_add_server()
        elif event.button.id == "btn-edit":
            self.action_edit_server()
        elif event.button.id == "btn-delete":
            self.action_delete_server()
        elif event.button.id == "btn-refresh":
            self.action_refresh_table()
        elif self.modal:
            if event.button.id == "cancel":
                self.modal.remove()
                self.modal = None
                self.status_log.write("[dim]❌ Operación cancelada[/]")
            elif event.button.id == "save":
                data = self.modal.get_data()
                if not data:
                    self.status_log.write("[red]❌ Campos inválidos o incompletos[/]")
                    return
                    
                try:
                    if data.id is None:
                        new_id = db_add(self.conn, data)
                        self.status_log.write(f"[green]✅ Servidor '{data.name}' añadido (ID: {new_id})[/]")
                    else:
                        db_update(self.conn, data)
                        self.status_log.write(f"[green]✅ Servidor '{data.name}' actualizado[/]")
                    
                    self.modal.remove()
                    self.modal = None
                    self.refresh_table()
                except Exception as e:
                    self.status_log.write(f"[red]❌ Error al guardar: {e}[/]")

    def action_delete_server(self):
        s = self.get_selected_server()
        if not s:
            self.status_log.write("[yellow]⚠️ No hay servidor seleccionado[/]")
            return
        
        try:
            db_delete(self.conn, s.id)
            self.status_log.write(f"[red]🗑️ Servidor '{s.name}' eliminado[/]")
            self.refresh_table()
        except Exception as e:
            self.status_log.write(f"[red]❌ Error al eliminar: {e}[/]")

    def action_connect_server(self):
        s = self.get_selected_server()
        
        if not s:
            self.status_log.write("[yellow]⚠️ No hay servidor seleccionado[/]")
            return

        self.status_log.write(f"[cyan]🔄 Conectando a {s.name} ({s.host})...[/]")
        
        try:
            ok, msg, cmd = connect(s)
            
            if ok:
                self.status_log.write(f"[green]✅ {msg}[/]")
                if cmd:
                    import shlex
                    cmd_str = ' '.join(shlex.quote(c) for c in cmd)
                    self.status_log.write(f"[dim]🔧 Comando: {cmd_str}[/]")
            else:
                self.status_log.write(f"[red]❌ {msg}[/]")
                
        except Exception as e:
            self.status_log.write(f"[red]💥 Error inesperado: {e}[/]")

if __name__ == "__main__":
    # Datos de ejemplo mejorados
    conn = db_connect()
    if conn.execute("SELECT COUNT(*) FROM servers").fetchone()[0] == 0:
        sample_servers = [
            Server(None,"Proxmox-Node1","192.168.1.10","ssh","root",22,"linux","proxmox,hypervisor,cluster","Nodo principal Proxmox VE"),
            Server(None,"DC-Windows","192.168.4.5","rdp","administrator",3389,"windows","AD,DC,windows-server","Domain Controller Principal"),
            Server(None,"GLPI-Server","192.168.4.87","ssh","ubuntu",22,"linux","glpi,web,ticketing","Servidor de tickets GLPI"),
            Server(None,"NAS-Synology","192.168.1.100","ssh","admin",22,"linux","nas,storage,backup","NAS principal para backups"),
            Server(None,"FTP-Files","192.168.1.50","ftp","ftpuser",21,"linux","ftp,files,transfer","Servidor FTP para transferencias"),
            Server(None,"SFTP-Secure","192.168.1.51","sftp","secure",22,"linux","sftp,secure,files","Servidor SFTP seguro"),
            Server(None,"Router-Main","192.168.1.1","ssh","admin",22,"network","router,network,main","Router principal de la red"),
            Server(None,"Mac-Studio","192.168.1.200","vnc","",5900,"mac","vnc,desktop,design","Mac Studio para diseño"),
        ]
        
        for server in sample_servers:
            db_add(conn, server)
        
        print("✅ Base de datos inicializada con servidores de ejemplo")
    
    conn.close()
    ServerTUI().run()