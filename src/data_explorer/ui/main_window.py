from PySide6 import QtWidgets, QtGui, QtCore
from data_explorer.ui.dialogs.connection_dialog import ConnectionDialog
from data_explorer.database.connection import connect_to_db, ConnectionError
from data_explorer.ui.widgets.schema_browser import SchemaBrowser
from data_explorer.ui.widgets.query_editor import QueryEditor
from data_explorer.ui.widgets.results_view import ResultsView
from data_explorer.config import Config  # Import the Config class


class MainWindow(QtWidgets.QMainWindow):
    """
    The main application window.
    """

    def __init__(self):
        super().__init__()

        # --- Config Handling ---
        self.config = Config()
        self.recent_connections = self.config.get_recent_connections()

        # --- Window Setup ---
        window_size = self.config.get("window").get("size")
        window_pos = self.config.get("window").get("position")
        window_maximized = self.config.get("window").get("maximized")

        self.setWindowTitle("PG Data Explorer")
        self.setGeometry(window_pos[0], window_pos[1], window_size[0], window_size[1])

        if window_maximized:
            self.setWindowState(QtCore.Qt.WindowMaximized)

        # --- Central Widget ---
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)

        # --- Layout ---
        main_layout = QtWidgets.QVBoxLayout(central_widget)

        # --- Split Views ---
        # Create main horizontal splitter (schema browser | query+results)
        self.h_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        # Create schema browser
        self.schema_browser = SchemaBrowser()
        self.h_splitter.addWidget(self.schema_browser)

        # Create vertical splitter for query editor and results
        self.v_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)

        # Create query editor
        self.query_editor = QueryEditor()
        self.v_splitter.addWidget(self.query_editor)

        # Create results view
        self.results_view = ResultsView()
        self.v_splitter.addWidget(self.results_view)

        # Set initial sizes for splitters from config
        h_splitter_sizes = self.config.get("splitters").get("h_splitter")
        v_splitter_sizes = self.config.get("splitters").get("v_splitter")

        self.h_splitter.setSizes(h_splitter_sizes)
        self.v_splitter.setSizes(v_splitter_sizes)

        # Add vertical splitter to horizontal splitter
        self.h_splitter.addWidget(self.v_splitter)

        # Add splitter to main layout
        main_layout.addWidget(self.h_splitter)

        # --- Menu Bar ---
        self.setup_menu()

        # --- Status Bar ---
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")

        # --- Database Connection State ---
        self.db_connection = None  # Store the active connection object

        # --- Connect Signals ---
        self.connect_signals()

        # --- Connect Splitter Moved Signals to Save Config ---
        self.h_splitter.splitterMoved.connect(self.save_splitter_sizes)
        self.v_splitter.splitterMoved.connect(self.save_splitter_sizes)

    def setup_menu(self):
        """Creates the main menu bar."""
        menu_bar = self.menuBar()

        # File Menu
        file_menu = menu_bar.addMenu("&File")

        connect_action = QtGui.QAction("&Connect to Database...", self)
        connect_action.setStatusTip("Open dialog to connect to a PostgreSQL database")
        connect_action.triggered.connect(self.open_connection_dialog)
        file_menu.addAction(connect_action)

        # Recent connections submenu
        self.recent_menu = QtWidgets.QMenu("Recent Connections", self)
        self.update_recent_connections_menu()
        file_menu.addMenu(self.recent_menu)

        disconnect_action = QtGui.QAction("&Disconnect", self)
        disconnect_action.setStatusTip("Disconnect from the current database")
        disconnect_action.triggered.connect(self.disconnect_database)
        disconnect_action.setEnabled(False)  # Disabled initially
        file_menu.addAction(disconnect_action)
        self.disconnect_action = disconnect_action  # Store reference to enable/disable

        file_menu.addSeparator()

        exit_action = QtGui.QAction("&Exit", self)
        exit_action.setStatusTip("Exit the application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Query Menu
        query_menu = menu_bar.addMenu("&Query")

        execute_action = QtGui.QAction("&Execute", self)
        execute_action.setShortcut("F5")
        execute_action.setStatusTip("Execute the current query")
        execute_action.triggered.connect(self.execute_query)
        query_menu.addAction(execute_action)

        clear_action = QtGui.QAction("&Clear Editor", self)
        clear_action.setStatusTip("Clear the query editor")
        clear_action.triggered.connect(self.clear_query)
        query_menu.addAction(clear_action)

        # Settings Menu
        settings_menu = menu_bar.addMenu("&Settings")

        preferences_action = QtGui.QAction("&Preferences", self)
        preferences_action.setStatusTip("Configure application settings")
        preferences_action.triggered.connect(self.show_preferences_dialog)
        settings_menu.addAction(preferences_action)

        # Help Menu
        help_menu = menu_bar.addMenu("&Help")

        about_action = QtGui.QAction("&About", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def connect_signals(self):
        """Connect signals between components."""
        # Connect schema browser table selection to query editor
        self.schema_browser.tableSelected.connect(self.on_table_selected)

        # Connect schema browser query generation to query editor
        self.schema_browser.queryGenerated.connect(self.on_query_generated)

        # Connect query editor execution to results view
        self.query_editor.queryExecuted.connect(self.results_view.display_results)

    def save_splitter_sizes(self):
        """Save splitter sizes to config when they change."""
        splitters = self.config.get("splitters")
        splitters["h_splitter"] = self.h_splitter.sizes()
        splitters["v_splitter"] = self.v_splitter.sizes()
        self.config.set("splitters", splitters)

    def save_window_state(self):
        """Save window size, position, and state to config."""
        window = self.config.get("window")

        # Only save size and position if not maximized
        if not self.isMaximized():
            window["size"] = [self.width(), self.height()]
            window["position"] = [self.x(), self.y()]

        window["maximized"] = self.isMaximized()
        self.config.set("window", window)

    def update_recent_connections_menu(self):
        """Update the recent connections menu with saved connections."""
        self.recent_menu.clear()

        if not self.recent_connections:
            no_recent_action = QtGui.QAction("No Recent Connections", self)
            no_recent_action.setEnabled(False)
            self.recent_menu.addAction(no_recent_action)
            return

        for conn in self.recent_connections:
            # Create a menu item with the connection details
            conn_name = f"{conn.get('dbname', '')}@{conn.get('host', '')}:{conn.get('port', '')}"
            action = QtGui.QAction(conn_name, self)
            action.setData(conn)  # Store the connection details
            action.triggered.connect(self.connect_to_recent)
            self.recent_menu.addAction(action)

        # Add a separator and clear action
        self.recent_menu.addSeparator()
        clear_action = QtGui.QAction("Clear Recent Connections", self)
        clear_action.triggered.connect(self.clear_recent_connections)
        self.recent_menu.addAction(clear_action)

    def add_to_recent_connections(self, conn_details):
        """Add connection details to recent connections list."""
        # Use the Config class to add the connection
        self.config.add_recent_connection(conn_details)
        # Update our local copy
        self.recent_connections = self.config.get_recent_connections()
        # Update the menu
        self.update_recent_connections_menu()

    def clear_recent_connections(self):
        """Clear the recent connections list."""
        reply = QtWidgets.QMessageBox.question(
            self,
            "Clear Recent Connections",
            "Are you sure you want to clear the recent connections list?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )

        if reply == QtWidgets.QMessageBox.Yes:
            # Use the Config class to clear connections
            self.config.set("recent_connections", [])
            # Update our local copy
            self.recent_connections = []
            # Update the menu
            self.update_recent_connections_menu()

    def connect_to_recent(self):
        """Connect to a database from the recent connections menu."""
        action = self.sender()
        if not action:
            return

        # Get connection details
        conn_details = action.data()
        if not conn_details:
            return

        # Need to ask for password since we don't store it
        password, ok = QtWidgets.QInputDialog.getText(
            self,
            "Password Required",
            f"Enter password for {conn_details.get('user', '')}@{conn_details.get('dbname', '')}:",
            QtWidgets.QLineEdit.Password,
        )

        if not ok:
            return

        # Add password to connection details
        conn_details["password"] = password

        # Connect
        self.status_bar.showMessage("Connecting...")
        try:
            self.db_connection = connect_to_db(**conn_details)
            if self.db_connection:
                db_name = conn_details.get("dbname", "Unknown DB")
                host = conn_details.get("host", "Unknown Host")
                user = conn_details.get("user", "Unknown User")
                self.status_bar.showMessage(
                    f"Connected to '{db_name}' on '{host}' as '{user}'"
                )
                self.disconnect_action.setEnabled(True)

                # Set up UI for connected state
                self.setup_connected_state(db_name, host)

                # Add to recent connections
                self.add_to_recent_connections(conn_details)
            else:
                self.status_bar.showMessage("Connection failed.")
        except ConnectionError as e:
            self.status_bar.showMessage(f"Connection Error: {e}")
            QtWidgets.QMessageBox.critical(
                self, "Connection Error", f"Failed to connect:\n{e}"
            )
        except Exception as e:
            self.status_bar.showMessage(f"An unexpected error occurred: {e}")
            QtWidgets.QMessageBox.critical(
                self, "Error", f"An unexpected error occurred:\n{e}"
            )

    def open_connection_dialog(self):
        """Opens the database connection dialog."""
        if self.db_connection:
            # Prevent opening if already connected - could ask to disconnect first
            QtWidgets.QMessageBox.warning(
                self,
                "Already Connected",
                "Please disconnect before connecting to a new database.",
            )
            return

        dialog = ConnectionDialog(self)
        if dialog.exec():
            conn_details = dialog.get_connection_details()
            self.status_bar.showMessage("Connecting...")
            try:
                self.db_connection = connect_to_db(**conn_details)
                if self.db_connection:
                    db_name = conn_details.get("dbname", "Unknown DB")
                    host = conn_details.get("host", "Unknown Host")
                    user = conn_details.get("user", "Unknown User")
                    self.status_bar.showMessage(
                        f"Connected to '{db_name}' on '{host}' as '{user}'"
                    )
                    self.disconnect_action.setEnabled(True)

                    # Set up UI for connected state
                    self.setup_connected_state(db_name, host)

                    # Add to recent connections
                    self.add_to_recent_connections(conn_details)
                else:
                    self.status_bar.showMessage("Connection failed.")
            except ConnectionError as e:
                self.status_bar.showMessage(f"Connection Error: {e}")
                QtWidgets.QMessageBox.critical(
                    self, "Connection Error", f"Failed to connect:\n{e}"
                )
            except Exception as e:
                self.status_bar.showMessage(f"An unexpected error occurred: {e}")
                QtWidgets.QMessageBox.critical(
                    self, "Error", f"An unexpected error occurred:\n{e}"
                )

    def setup_connected_state(self, db_name, host):
        """Set up the UI for a connected database state."""
        # Update window title to show connection info
        self.setWindowTitle(f"PG Data Explorer - {db_name}@{host}")

        # Update components with the connection
        self.schema_browser.populate_schema(self.db_connection)
        self.query_editor.set_connection(self.db_connection)

        # Clear any previous results
        self.results_view.clear_results()

    def disconnect_database(self):
        """Closes the current database connection."""
        if self.db_connection:
            try:
                self.db_connection.close()
                self.db_connection = None
                self.status_bar.showMessage("Disconnected.")
                self.disconnect_action.setEnabled(False)

                # Reset UI state
                self.reset_ui_state()
            except Exception as e:
                self.status_bar.showMessage(f"Error during disconnection: {e}")
                QtWidgets.QMessageBox.warning(
                    self,
                    "Disconnection Error",
                    f"An error occurred while disconnecting:\n{e}",
                )
        else:
            self.status_bar.showMessage("Not currently connected.")

    def reset_ui_state(self):
        """Reset the UI to the disconnected state."""
        # Reset window title
        self.setWindowTitle("PG Data Explorer")

        # Clear schema browser
        self.schema_browser.clear()

        # Reset query editor
        self.query_editor.set_connection(None)

        # Clear results
        self.results_view.clear_results()

    def on_table_selected(self, schema_name, table_name):
        """Handle a table being selected in the schema browser."""
        # Get default query limit from config
        limit = self.config.get("query_limit", 100)

        # Generate a SELECT query for the table
        query = f"SELECT * FROM {schema_name}.{table_name} LIMIT {limit};"

        # Insert the query into the editor
        self.query_editor.editor.setPlainText(query)

        # Optionally, execute the query automatically
        # self.execute_query()

    def on_query_generated(self, query):
        """Handle a query being generated from the schema browser."""
        # Insert the query into the editor
        self.query_editor.editor.setPlainText(query)

        # Focus the query editor
        self.query_editor.editor.setFocus()

    def execute_query(self):
        """Execute the current query in the editor."""
        query = self.query_editor.editor.toPlainText().strip()
        if query:
            # Add to query history in config
            self.config.add_query_history(query)

        # Execute the query
        self.query_editor.execute_query()

    def clear_query(self):
        """Clear the query editor."""
        self.query_editor.clear_query()

    def show_preferences_dialog(self):
        """Show the preferences dialog."""
        # This is a placeholder for implementing a preferences dialog
        # Will implement this later
        QtWidgets.QMessageBox.information(
            self,
            "Preferences",
            "Preferences dialog will be implemented in a future version.",
        )

    def show_about_dialog(self):
        """Show the about dialog."""
        QtWidgets.QMessageBox.about(
            self,
            "About PG Data Explorer",
            """<h3>PG Data Explorer</h3>
            <p>A cross-platform PostgreSQL database explorer with Odoo compatibility.</p>
            <p>Created by You as a portfolio project.</p>
            <p>Version 0.1.0</p>""",
        )

    def closeEvent(self, event: QtGui.QCloseEvent):
        """Handle window close event to save state and disconnect."""
        # Save window state
        self.save_window_state()

        # Save splitter sizes
        self.save_splitter_sizes()

        # Disconnect from database
        self.disconnect_database()

        # Accept the close event
        event.accept()
