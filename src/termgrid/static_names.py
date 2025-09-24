OS_ICONS = {
    "linux": "🐧", "windows": "🪟", "mac": "🍎", "bsd": "🐡", "network": "🖧", "other": "🖥️"
}
PROTO_ICONS = {"ssh":"🔐","rdp":"🖥️","vnc":"🖱️","ftp":"📁","sftp":"🔒"}

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