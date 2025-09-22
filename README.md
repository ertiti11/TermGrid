# 🖥️ ServerManager

**ServerManager** es una aplicación TUI (Interfaz de Usuario en Terminal) para gestionar tu inventario de servidores y conectarte a ellos con un solo clic, soportando SSH, RDP, VNC, FTP y SFTP.  
Ideal para administradores de sistemas, DevOps, estudiantes y entusiastas que quieren tener todos sus accesos centralizados y organizados.

---

## 🚀 Características principales

- **Inventario centralizado** de servidores con búsqueda y filtrado instantáneo.
- **Conexión 1-click** a servidores vía SSH, RDP, VNC, FTP y SFTP.
- **Soporte multiplataforma** (Windows, Linux, macOS).
- **Gestión de etiquetas y notas** para cada servidor.
- **Atajos de teclado** para máxima productividad.
- **Interfaz moderna** y personalizable gracias a [Textual](https://www.textualize.io/).

---

## 🛠️ Instalación

1. **Clona el repositorio:**
   ```bash
   git clone https://github.com/tuusuario/servermanager.git
   cd servermanager
   ```

2. **Instala las dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Ejecuta la aplicación:**
   ```bash
   python main.py
   ```

---

## 📦 Empaquetar como .EXE (Windows)

Puedes convertir ServerManager en un ejecutable usando [PyInstaller](https://pyinstaller.org/):

```bash
pip install pyinstaller
pyinstaller --onefile --windowed main.py
```

El ejecutable aparecerá en la carpeta `dist/`.

---

## ⌨️ Atajos útiles

- `Ctrl+N` — Nuevo servidor
- `Enter` — Conectar al servidor seleccionado
- `E` — Editar servidor
- `Del` — Borrar servidor
- `/` — Buscar
- `Ctrl+R` — Actualizar tabla

---

## 📝 Licencia

Este proyecto está licenciado bajo la **GPLv3**.  
¡Eres libre de usarlo, modificarlo y compartirlo!

---

## 🤝 Contribuciones

¡Las contribuciones son bienvenidas!  
Abre un issue o un pull request para sugerir mejoras, reportar bugs o añadir nuevas funciones.

---

## 📷 Capturas de pantalla

> _¡Agrega aquí tus capturas de pantalla para mostrar la interfaz!_

---

## 💡 Autor

Desarrollado por **aprieto**  
¡Sígueme en GitHub para más proyectos!

---