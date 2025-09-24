# 📚 TermGrid Deep Dive Documentation

## Architecture Overview

TermGrid is a modular Python application designed for terminal-based server management. It leverages [Textual](https://www.textualize.io/) for the UI and SQLite for persistent storage. The codebase is organized for clarity, extensibility, and testability.

---

## Main Components

### 1. `src/termgrid/app.py` — Main Application (TUI)

- **Purpose:**  
  Orchestrates the Textual UI, event handling, and user interactions.
- **Key Classes:**
  - `ServerTUI(App)`: The main Textual app. Handles layout, widget composition, keyboard shortcuts, and core logic.
  - **Widgets:**  
    - `Header`, `Footer`: Standard UI elements.
    - `Input`, `Select`, `Button`: For searching, sorting, and actions.
    - `DataTable`: Displays server inventory.
    - `Tree`: (Optional) For visual grouping by folders.
    - `Log`: Status and feedback panel.
    - `FormModal`: Modal dialog for adding/editing servers.
- **Event Handling:**  
  - Uses Textual's event system (`on_button_pressed`, `on_input_changed`, etc.) to react to user actions.
  - Keyboard shortcuts are defined in the `BINDINGS` list and mapped to action methods.
- **Data Flow:**  
  - Loads server data from the database via functions in `db.py`.
  - Updates UI widgets based on user actions and database changes.

### 2. `src/termgrid/db.py` — Database Layer

- **Purpose:**  
  Encapsulates all database operations and the server data model.
- **Key Elements:**
  - `Server` dataclass: Represents a server entry, including fields like `name`, `host`, `protocol`, `username`, `port`, `os`, `tags`, `notes`, and `group`.
  - Functions:
    - `connect()`: Opens a SQLite connection and ensures the table schema.
    - `add()`, `update()`, `delete()`: CRUD operations for servers.
    - `list_servers()`: Query servers, with optional filtering and sorting.
- **Extensibility:**  
  - To add new fields, update the `Server` dataclass and the SQL schema in `connect()`.

### 3. `src/termgrid/Forms/NewServerForm.py` — Modal Form

- **Purpose:**  
  Provides a modal dialog for adding or editing server entries.
- **Key Class:**
  - `FormModal(Container)`: Composes input widgets for each server field, validates input, and returns a `Server` instance.
- **Validation:**  
  - Ensures required fields are filled and ports are valid.
- **Customization:**  
  - Add new input widgets for additional fields as needed.

### 4. `src/termgrid/static_names.py` — Constants & Helpers

- **Purpose:**  
  Centralizes protocol and OS icons, default ports, and helper functions.
- **Key Elements:**
  - `OS_ICONS`, `PROTO_ICONS`, `DEFAULT_PORTS`: Dictionaries for UI display.
  - `os_icon()`, `proto_icon()`: Functions to get icons for display.

### 5. `src/termgrid/config.py` — Configuration

- **Purpose:**  
  Handles paths for data storage and logging setup.
- **Key Functions:**
  - `get_data_dir()`: Returns the directory for app data.
  - `get_db_path()`: Returns the path to the SQLite database.
  - `setup_logging()`: Configures logging (optional).

---

## Data Flow Example

1. **Startup:**  
   - `ServerTUI` initializes, connects to the database, and loads servers.
2. **User Action:**  
   - User clicks "Nuevo" or presses `Ctrl+N`.
   - `FormModal` is mounted; user fills in server details.
   - On "Guardar", data is validated and passed to `add()` in `db.py`.
   - Table is refreshed to show the new server.
3. **Connection:**  
   - User selects a server and presses `Enter`.
   - `connect()` builds the appropriate command based on protocol and OS, then launches the external client (e.g., SSH, RDP).
4. **Grouping:**  
   - Servers can be assigned to groups/folders via the `group` field.
   - UI can display servers grouped visually using a `Tree` widget.

---

## Extending the Application

### Adding a New Field (e.g., "Location")

1. **Model:**  
   - Add `location: str = ""` to the `Server` dataclass in `db.py`.
   - Add `location TEXT DEFAULT ''` to the SQL schema in `connect()`.
2. **Form:**  
   - Add an `Input` widget for "Location" in `FormModal`.
   - Update `get_data()` to include the new field.
3. **Table:**  
   - Add a new column in the DataTable in `app.py`.
   - Update row rendering to include the location.

### Adding a New Protocol (e.g., "Telnet")

1. **Constants:**  
   - Add `"telnet": "🔓"` to `PROTO_ICONS` and `DEFAULT_PORTS["telnet"] = 23` in `static_names.py`.
2. **Form:**  
   - Add Telnet to the protocol dropdown in `FormModal`.
3. **Connection Logic:**  
   - Add a new branch in `connect()` to handle Telnet.

### Visual Grouping

- Use the `group` field to assign servers to folders.
- In `app.py`, use a `Tree` widget to display servers grouped by folder.
- On selection, show only servers in the selected group.

---

## Testing

- Tests are written with `pytest` and cover database operations, config, and static helpers.
- For UI components, use `pytest-asyncio` and Textual's test utilities to simulate app context.
- Example:
  ```python
  import pytest
  from textual.app import App
  from termgrid.Forms.NewServerForm import FormModal
  from termgrid.db import Server

  class DummyApp(App):
      def compose(self):
          yield FormModal("Test", Server(None, "Srv", "127.0.0.1", "ssh", "root", 22, "linux"))

  @pytest.mark.asyncio
  async def test_formmodal_get_data():
      app = DummyApp()
      async with app.run_test() as pilot:
          modal = app.query_one(FormModal)
          data = modal.get_data()
          assert isinstance(data, Server)
  ```

---

## Adding More Functionality

- **New UI Panels:**  
  - Create new classes inheriting from Textual containers or widgets.
  - Add them in the `compose()` method of your app.
- **New Actions/Shortcuts:**  
  - Add to the `BINDINGS` list and implement corresponding methods.
- **Integrations:**  
  - Add new modules for API calls, notifications, etc.
- **Settings Panel:**  
  - Create a modal or sidebar for user preferences.

---

## Best Practices

- Keep logic and UI separate for testability.
- Use constants and helpers for icons and protocol details.
- Modularize new features into separate files/folders.
- Write tests for new features and edge cases.

---

## Resources

- [Textual Documentation](https://textual.textualize.io/)
- [Rich Documentation](https://rich.readthedocs.io/)
- [PyInstaller](https://pyinstaller.org/) (for .exe packaging)
- [pytest](https://docs.pytest.org/en/stable/)

---

## Troubleshooting

- **Import Errors:**  
  - Check folder names and `__init__.py` files.
  - Use relative imports within the package.
- **Widget Errors in Tests:**  
  - Use Textual's test utilities and run tests in an app context.
- **Database Issues:**  
  - Ensure schema matches the dataclass.
  - Use migrations for schema changes if needed.

---

## Contact

For questions or suggestions, open an issue on GitHub or contact the author.

---