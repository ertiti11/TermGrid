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
from textual.widgets import Header, Footer, Input, Static, Button, DataTable, Select, Log, TextArea,  Tree
from textual.containers import Horizontal, Container, ScrollableContainer
from textual.reactive import reactive
from rich.text import Text
from .db import connect as db_connect, list_servers, add, update, delete, Server
from .config import setup_logging
from .Forms.NewServerForm import FormModal
from .static_names import DEFAULT_PORTS, PROTO_ICONS, OS_ICONS, proto_icon, os_icon


DB_PATH = os.path.join(os.path.dirname(__file__), "servers.db")

# ---------- Modelo & almacenamiento ----------



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
        self.title = "🖥️ TermGrid - Server Manager"
        self.conn = db_connect()
        self.modal: Optional[FormModal] = None
        self.table: DataTable
        self.row_keys: List[int] = []

    def refresh_table(self):
        """Recarga la tabla de servidores según el filtro y orden actuales."""
        self.table.clear()
        self.row_keys = []
        servers = list_servers(self.conn, self.filter_text, self.sort_field)
        
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
        self.set_focus(self.table)
    def refresh_tree(self):
        
        servers = list_servers(self.conn, self.filter_text, self.sort_field)
        groups = {}
        for s in servers:
            group = s.group or "Ungrouped"
            groups.setdefault(group, []).append(s)
        
            
            
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
    ServerTUI().run()