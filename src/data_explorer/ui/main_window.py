from PySide6 import QtWidgets, QtGui, QtCore
from data_explorer.ui.dialogs.connection_dialog import ConnectionDialog
from data_explorer.database.connection import connect_to_db, ConnectionError
from data_explorer.ui.widgets.schema_browser import SchemaBrowser
from data_explorer.ui.widgets.query_editor import QueryEditor
from data_explorer.ui.widgets.results_view import ResultsView
from data_explorer.ui.widgets.visualization_view import VisualizationView
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

        # --- Toolbar ---
        self.main_toolbar = QtWidgets.QToolBar("Main Toolbar")
        self.addToolBar(self.main_toolbar)

        # Add connect button for more visibility
        connect_button = QtGui.QAction(
            self.style().standardIcon(QtWidgets.QStyle.SP_ComputerIcon),
            "Connect to Database",
            self,
        )
        connect_button.triggered.connect(self.open_connection_dialog)
        self.main_toolbar.addAction(connect_button)

        # Add execute query button
        execute_button = QtGui.QAction(
            self.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay),
            "Execute Query",
            self,
        )
        execute_button.triggered.connect(self.execute_query)
        self.main_toolbar.addAction(execute_button)

        # Add disconnect button
        disconnect_button = QtGui.QAction(
            self.style().standardIcon(QtWidgets.QStyle.SP_BrowserStop),
            "Disconnect",
            self,
        )
        disconnect_button.triggered.connect(self.disconnect_database)
        disconnect_button.setEnabled(False)
        self.main_toolbar.addAction(disconnect_button)
        self.disconnect_button = disconnect_button

        # --- Split Views ---
        # Create main horizontal splitter (schema browser | query+results)
        self.h_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        # Create schema browser
        self.schema_browser = SchemaBrowser()
        self.h_splitter.addWidget(self.schema_browser)

        # Create right side panel (with tabs)
        self.right_panel = QtWidgets.QTabWidget()

        # Create query/results tab
        query_results_tab = QtWidgets.QWidget()
        query_results_layout = QtWidgets.QVBoxLayout(query_results_tab)

        # Create vertical splitter for query editor and results
        self.v_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)

        # Create query editor
        self.query_editor = QueryEditor()
        self.v_splitter.addWidget(self.query_editor)

        # Create results view
        self.results_view = ResultsView()
        self.v_splitter.addWidget(self.results_view)

        # Set initial sizes for vertical splitter
        v_splitter_sizes = self.config.get("splitters").get("v_splitter")
        self.v_splitter.setSizes(v_splitter_sizes)

        query_results_layout.addWidget(self.v_splitter)
        self.right_panel.addTab(query_results_tab, "Query & Results")

        # Create visualization tab
        self.visualization_view = VisualizationView()
        self.right_panel.addTab(self.visualization_view, "Visualization")

        # Add right panel to horizontal splitter
        self.h_splitter.addWidget(self.right_panel)

        # Set initial sizes for horizontal splitter
        h_splitter_sizes = self.config.get("splitters").get("h_splitter")
        self.h_splitter.setSizes(h_splitter_sizes)

        # Add splitter to main layout
        main_layout.addWidget(self.h_splitter)

        # --- Status Bar ---
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")

        # --- Connection Indicator ---
        self.connection_indicator = QtWidgets.QLabel("Not Connected")
        self.connection_indicator.setStyleSheet("color: red;")
        self.connection_indicator.setAlignment(QtCore.Qt.AlignCenter)
        self.connection_indicator.setMinimumWidth(150)
        self.status_bar.addPermanentWidget(self.connection_indicator)

        # --- Database Connection State ---
        self.db_connection = None  # Store the active connection object

        # --- Menu Bar ---
        self.setup_menu()

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
        connect_action.setShortcut("Ctrl+N")
        connect_action.triggered.connect(self.open_connection_dialog)
        file_menu.addAction(connect_action)

        # Recent connections submenu
        self.recent_menu = QtWidgets.QMenu("Recent Connections", self)
        self.update_recent_connections_menu()
        file_menu.addMenu(self.recent_menu)

        disconnect_action = QtGui.QAction("&Disconnect", self)
        disconnect_action.setStatusTip("Disconnect from the current database")
        disconnect_action.setShortcut("Ctrl+D")
        disconnect_action.triggered.connect(self.disconnect_database)
        disconnect_action.setEnabled(False)  # Disabled initially
        file_menu.addAction(disconnect_action)
        self.disconnect_action = disconnect_action  # Store reference to enable/disable

        file_menu.addSeparator()

        export_menu = QtWidgets.QMenu("Export", self)

        export_results_action = QtGui.QAction("Export Results to CSV...", self)
        export_results_action.triggered.connect(self.export_results_to_csv)
        export_menu.addAction(export_results_action)

        export_chart_action = QtGui.QAction("Export Chart...", self)
        export_chart_action.triggered.connect(self.export_visualization)
        export_menu.addAction(export_chart_action)

        file_menu.addMenu(export_menu)

        file_menu.addSeparator()

        exit_action = QtGui.QAction("E&xit", self)
        exit_action.setStatusTip("Exit the application")
        exit_action.setShortcut("Ctrl+Q")
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

        query_menu.addSeparator()

        query_history_menu = QtWidgets.QMenu("Recent Queries", self)
        self.query_history_menu = query_history_menu
        query_menu.addMenu(query_history_menu)
        self.update_query_history_menu()

        # View Menu
        view_menu = menu_bar.addMenu("&View")

        view_query_results_action = QtGui.QAction("Query && Results", self)
        view_query_results_action.triggered.connect(
            lambda: self.right_panel.setCurrentIndex(0)
        )
        view_menu.addAction(view_query_results_action)

        view_visualizations_action = QtGui.QAction("Visualizations", self)
        view_visualizations_action.triggered.connect(
            lambda: self.right_panel.setCurrentIndex(1)
        )
        view_menu.addAction(view_visualizations_action)

        view_menu.addSeparator()

        toggle_sidebar_action = QtGui.QAction("Toggle Schema Browser", self)
        toggle_sidebar_action.setShortcut("Ctrl+S")
        toggle_sidebar_action.triggered.connect(self.toggle_schema_browser)
        view_menu.addAction(toggle_sidebar_action)

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
        self.query_editor.queryExecuted.connect(self.on_query_executed)

        # Connect right panel tab change
        self.right_panel.currentChanged.connect(self.on_tab_changed)

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

    def update_query_history_menu(self):
        """Update the query history menu."""
        self.query_history_menu.clear()

        query_history = self.config.get_query_history()

        if not query_history:
            no_history_action = QtGui.QAction("No Recent Queries", self)
            no_history_action.setEnabled(False)
            self.query_history_menu.addAction(no_history_action)
            return

        # Add most recent queries (limit to 10 for menu usability)
        for i, query in enumerate(query_history[:10]):
            # Truncate long queries for menu display
            display_query = query[:50] + "..." if len(query) > 50 else query
            # Replace newlines with spaces for menu display
            display_query = display_query.replace("\n", " ")

            action = QtGui.QAction(display_query, self)
            action.setData(query)  # Store the full query
            action.triggered.connect(self.load_query_from_history)
            self.query_history_menu.addAction(action)

        # Add a separator and clear action if there are queries
        if query_history:
            self.query_history_menu.addSeparator()
            clear_action = QtGui.QAction("Clear Query History", self)
            clear_action.triggered.connect(self.clear_query_history)
            self.query_history_menu.addAction(clear_action)

    def load_query_from_history(self):
        """Load a query from history into the editor."""
        action = self.sender()
        if not action:
            return

        query = action.data()
        if not query:
            return

        # Set query in editor
        self.query_editor.editor.setPlainText(query)

        # Focus the editor
        self.query_editor.editor.setFocus()

        # Switch to query tab if on visualization
        if self.right_panel.currentIndex() == 1:
            self.right_panel.setCurrentIndex(0)

    def clear_query_history(self):
        """Clear the query history."""
        reply = QtWidgets.QMessageBox.question(
            self,
            "Clear Query History",
            "Are you sure you want to clear the query history?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )

        if reply == QtWidgets.QMessageBox.Yes:
            self.config.set("query_history", [])
            self.update_query_history_menu()

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
                self.disconnect_button.setEnabled(True)

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
                    self.disconnect_button.setEnabled(True)

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

        # Update connection indicator
        self.connection_indicator.setText(f"Connected: {db_name}@{host}")
        self.connection_indicator.setStyleSheet("color: green; font-weight: bold;")

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
                self.disconnect_button.setEnabled(False)

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

        # Update connection indicator
        self.connection_indicator.setText("Not Connected")
        self.connection_indicator.setStyleSheet("color: red;")

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

        # Focus the query editor
        self.query_editor.editor.setFocus()

        # Switch to query tab if on visualization
        if self.right_panel.currentIndex() == 1:
            self.right_panel.setCurrentIndex(0)

    def on_query_generated(self, query):
        """Handle a query being generated from the schema browser."""
        # Insert the query into the editor
        self.query_editor.editor.setPlainText(query)

        # Focus the query editor
        self.query_editor.editor.setFocus()

        # Switch to query tab if on visualization
        if self.right_panel.currentIndex() == 1:
            self.right_panel.setCurrentIndex(0)

    def on_query_executed(self, columns, data):
        """Handle query execution results."""
        # Display results in results view
        self.results_view.display_results(columns, data)

        # If there's data, also update visualization view
        if columns and data:
            self.visualization_view.set_data(columns, data)

            # Update status bar with suggestion to view visualizations
            if self.right_panel.currentIndex() == 0:  # If on query tab
                self.status_bar.showMessage(
                    f"Query returned {len(data)} rows. Switch to Visualization tab to explore data visually."
                )

    def on_tab_changed(self, index):
        """Handle tab changes."""
        if index == 1:  # Visualization tab
            # Make sure visualization has current data
            if (
                hasattr(self.results_view, "model")
                and self.results_view.model.rowCount() > 0
            ):
                # Get data from results view
                columns = []
                for i in range(self.results_view.model.columnCount()):
                    columns.append(
                        self.results_view.model.headerData(i, QtCore.Qt.Horizontal)
                    )

                data = []
                for i in range(self.results_view.model.rowCount()):
                    row = []
                    for j in range(self.results_view.model.columnCount()):
                        value = self.results_view.model.index(i, j).data(
                            QtCore.Qt.UserRole
                        )
                        row.append(value)
                    data.append(row)

                self.visualization_view.set_data(columns, data)

    def execute_query(self):
        """Execute the current query in the editor."""
        query = self.query_editor.editor.toPlainText().strip()
        if query:
            # Add to query history in config
            self.config.add_query_history(query)
            # Update the query history menu
            self.update_query_history_menu()

        # Execute the query
        self.query_editor.execute_query()

        # Switch to query results tab if on visualization
        if self.right_panel.currentIndex() == 1:
            self.right_panel.setCurrentIndex(0)

    def clear_query(self):
        """Clear the query editor."""
        self.query_editor.clear_query()

    def export_results_to_csv(self):
        """Export results to CSV."""
        if (
            not hasattr(self.results_view, "model")
            or self.results_view.model.rowCount() == 0
        ):
            self.status_bar.showMessage("No results to export")
            return

        self.results_view.export_to_csv()

    def export_visualization(self):
        """Export the current visualization."""
        if self.right_panel.currentIndex() != 1:
            self.right_panel.setCurrentIndex(1)

        self.visualization_view.export_chart()

    def toggle_schema_browser(self):
        """Toggle the visibility of the schema browser."""
        if self.schema_browser.isVisible():
            # Save current size
            self.schema_browser_size = self.h_splitter.sizes()[0]
            # Hide schema browser
            self.h_splitter.setSizes(
                [0, self.h_splitter.sizes()[1] + self.schema_browser_size]
            )
        else:
            # Restore schema browser
            if hasattr(self, "schema_browser_size"):
                self.h_splitter.setSizes(
                    [
                        self.schema_browser_size,
                        self.h_splitter.sizes()[1] - self.schema_browser_size,
                    ]
                )
            else:
                # Default size if no saved size
                self.h_splitter.setSizes([250, self.h_splitter.sizes()[1] - 250])

    def show_preferences_dialog(self):
        """Show the preferences dialog."""
        # Create preferences dialog
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Preferences")
        dialog.setMinimumWidth(400)

        # Main layout
        layout = QtWidgets.QVBoxLayout(dialog)

        # Tab widget for different preference categories
        tab_widget = QtWidgets.QTabWidget()

        # General preferences tab
        general_tab = QtWidgets.QWidget()
        general_layout = QtWidgets.QFormLayout(general_tab)

        # Query limit setting
        query_limit_spinner = QtWidgets.QSpinBox()
        query_limit_spinner.setRange(1, 10000)
        query_limit_spinner.setValue(self.config.get("query_limit", 100))
        query_limit_spinner.setSingleStep(100)
        general_layout.addRow("Default query limit:", query_limit_spinner)

        # Theme setting
        theme_combo = QtWidgets.QComboBox()
        theme_combo.addItems(["Light", "Dark", "System"])
        theme_combo.setCurrentText(self.config.get("theme", "System"))
        general_layout.addRow("Theme:", theme_combo)

        # Add to tab widget
        tab_widget.addTab(general_tab, "General")

        # Connection preferences tab
        connection_tab = QtWidgets.QWidget()
        connection_layout = QtWidgets.QFormLayout(connection_tab)

        # Default connection settings
        default_host = QtWidgets.QLineEdit(self.config.get("default_host", "localhost"))
        default_port = QtWidgets.QLineEdit(self.config.get("default_port", "5432"))
        default_user = QtWidgets.QLineEdit(self.config.get("default_user", ""))

        connection_layout.addRow("Default host:", default_host)
        connection_layout.addRow("Default port:", default_port)
        connection_layout.addRow("Default user:", default_user)

        # Add to tab widget
        tab_widget.addTab(connection_tab, "Connection")

        # Add tab widget to layout
        layout.addWidget(tab_widget)

        # Add buttons
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        # Show dialog
        if dialog.exec():
            # Save preferences if accepted
            self.config.set("query_limit", query_limit_spinner.value())
            self.config.set("theme", theme_combo.currentText())
            self.config.set("default_host", default_host.text())
            self.config.set("default_port", default_port.text())
            self.config.set("default_user", default_user.text())

            # Apply theme if changed
            self.apply_theme(theme_combo.currentText())

    def apply_theme(self, theme_name):
        """Apply the selected theme."""
        if theme_name == "System":
            # Use system theme
            QtWidgets.QApplication.setStyle(QtWidgets.QStyleFactory.create("Fusion"))
            return

        # Create palette for the theme
        palette = QtGui.QPalette()

        if theme_name == "Dark":
            # Set dark theme colors
            palette.setColor(QtGui.QPalette.Window, QtGui.QColor(53, 53, 53))
            palette.setColor(QtGui.QPalette.WindowText, QtCore.Qt.white)
            palette.setColor(QtGui.QPalette.Base, QtGui.QColor(25, 25, 25))
            palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(53, 53, 53))
            palette.setColor(QtGui.QPalette.ToolTipBase, QtCore.Qt.white)
            palette.setColor(QtGui.QPalette.ToolTipText, QtCore.Qt.white)
            palette.setColor(QtGui.QPalette.Text, QtCore.Qt.white)
            palette.setColor(QtGui.QPalette.Button, QtGui.QColor(53, 53, 53))
            palette.setColor(QtGui.QPalette.ButtonText, QtCore.Qt.white)
            palette.setColor(QtGui.QPalette.BrightText, QtCore.Qt.red)
            palette.setColor(QtGui.QPalette.Link, QtGui.QColor(42, 130, 218))
            palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(42, 130, 218))
            palette.setColor(QtGui.QPalette.HighlightedText, QtCore.Qt.black)
        else:  # Light theme
            # Use default palette
            palette = QtGui.QPalette()

        # Apply the palette
        QtWidgets.QApplication.setPalette(palette)

        # Set style to Fusion for consistent look
        QtWidgets.QApplication.setStyle(QtWidgets.QStyleFactory.create("Fusion"))

    def show_about_dialog(self):
        """Show the about dialog."""
        QtWidgets.QMessageBox.about(
            self,
            "About PG Data Explorer",
            """<h3>PG Data Explorer</h3>
            <p style="font-size: 12px;">A cross-platform PostgreSQL database explorer with advanced visualization capabilities and Odoo compatibility.</p>
            <p style="font-size: 12px;">Features:</p>
            <ul style="font-size: 12px;">
                <li>Connect to any PostgreSQL database</li>
                <li>Browse database schemas, tables, and columns</li>
                <li>Execute SQL queries with syntax highlighting</li>
                <li>Visualize query results with interactive charts</li>
                <li>Export data and visualizations</li>
                <li>Special support for Odoo database schema</li>
            </ul>
            <p style="font-size: 12px;">Created as a portfolio project showcasing database integration, data visualization, and UI design skills.</p>
            <p style="font-size: 12px;"><b>Version 1.0.0</b></p>""",
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
