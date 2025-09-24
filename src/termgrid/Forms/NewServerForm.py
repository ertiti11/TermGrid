from textual.containers import Horizontal, Container, ScrollableContainer
from textual.widgets import Input, Static, Button, Select, TextArea
from textual.app import ComposeResult
from typing import Optional
from ..db import Server  # Ajusta el import según tu estructura
from termgrid.static_names import DEFAULT_PORTS, PROTO_ICONS, OS_ICONS, proto_icon, os_icon
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
        self.in_group = Input(placeholder="Grupo", value=self.server.group or "")
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