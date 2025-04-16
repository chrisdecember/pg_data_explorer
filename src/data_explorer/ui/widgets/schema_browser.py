from PySide6 import QtWidgets, QtCore, QtGui


class SchemaBrowser(QtWidgets.QTreeWidget):
    """
    Tree widget for browsing database schemas, tables, and columns.
    """

    # Signal emitted when a table is double-clicked
    tableSelected = QtCore.Signal(str, str)  # schema_name, table_name
    queryGenerated = QtCore.Signal(str)  # Signal to emit generated queries

    def __init__(self, parent=None):
        super().__init__(parent)

        # Set properties
        self.setHeaderLabels(["Database Objects"])
        self.setAlternatingRowColors(True)
        self.setAnimated(True)

        # Connect signals
        self.itemExpanded.connect(self.on_item_expanded)
        self.itemDoubleClicked.connect(self.on_item_double_clicked)

        # Context menu
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def populate_schema(self, connection):
        """
        Populate the tree with schema information from the database.

        Args:
            connection: psycopg2 connection object
        """
        self.clear()
        self.connection = connection

        try:
            cursor = connection.cursor()

            # Get schemas
            cursor.execute("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name NOT LIKE 'pg_%' 
                AND schema_name != 'information_schema'
                ORDER BY schema_name
            """)

            schemas = cursor.fetchall()

            # For each schema
            for schema in schemas:
                schema_name = schema[0]
                schema_item = QtWidgets.QTreeWidgetItem(self, [schema_name])
                schema_item.setData(
                    0, QtCore.Qt.UserRole, {"type": "schema", "name": schema_name}
                )

                # Add a placeholder for tables
                placeholder = QtWidgets.QTreeWidgetItem(
                    schema_item, ["Loading tables..."]
                )
                schema_item.addChild(placeholder)

            cursor.close()

        except Exception as e:
            QtWidgets.QMessageBox.warning(
                self,
                "Error Loading Schema",
                f"Failed to load database schema:\n{str(e)}",
            )

    def on_item_expanded(self, item):
        """Load child items when a parent item is expanded."""
        item_data = item.data(0, QtCore.Qt.UserRole)
        if not item_data:
            return

        item_type = item_data.get("type")

        # If a schema is expanded, load its tables
        if (
            item_type == "schema"
            and item.childCount() == 1
            and item.child(0).text(0) == "Loading tables..."
        ):
            schema_name = item_data.get("name")
            self.load_tables(item, schema_name)

        # If a table is expanded, load its columns
        elif (
            item_type == "table"
            and item.childCount() == 1
            and item.child(0).text(0) == "Loading columns..."
        ):
            schema_name = item_data.get("schema")
            table_name = item_data.get("name")
            self.load_columns(item, schema_name, table_name)

    def load_tables(self, schema_item, schema_name):
        """Load tables for a schema."""
        try:
            # Remove placeholder
            schema_item.removeChild(schema_item.child(0))

            cursor = self.connection.cursor()
            cursor.execute(
                """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = %s 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """,
                (schema_name,),
            )

            tables = cursor.fetchall()

            if not tables:
                no_tables = QtWidgets.QTreeWidgetItem(schema_item, ["No tables"])
                schema_item.addChild(no_tables)
                return

            # Add tables
            for table in tables:
                table_name = table[0]
                table_item = QtWidgets.QTreeWidgetItem(schema_item, [table_name])
                table_item.setData(
                    0,
                    QtCore.Qt.UserRole,
                    {"type": "table", "name": table_name, "schema": schema_name},
                )

                # Add placeholder for columns
                placeholder = QtWidgets.QTreeWidgetItem(
                    table_item, ["Loading columns..."]
                )
                table_item.addChild(placeholder)

            cursor.close()

        except Exception as e:
            QtWidgets.QMessageBox.warning(
                self,
                "Error Loading Tables",
                f"Failed to load tables for schema '{schema_name}':\n{str(e)}",
            )

    def load_columns(self, table_item, schema_name, table_name):
        """Load columns for a table."""
        try:
            # Remove placeholder
            table_item.removeChild(table_item.child(0))

            cursor = self.connection.cursor()
            cursor.execute(
                """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
            """,
                (schema_name, table_name),
            )

            columns = cursor.fetchall()

            if not columns:
                no_columns = QtWidgets.QTreeWidgetItem(table_item, ["No columns"])
                table_item.addChild(no_columns)
                return

            # Add columns
            for column in columns:
                column_name = column[0]
                data_type = column[1]
                is_nullable = "YES" if column[2] == "YES" else "NO"

                # Include data type and nullability in the display
                display_text = f"{column_name} ({data_type}, Nullable: {is_nullable})"

                column_item = QtWidgets.QTreeWidgetItem(table_item, [display_text])
                column_item.setData(
                    0,
                    QtCore.Qt.UserRole,
                    {
                        "type": "column",
                        "name": column_name,
                        "data_type": data_type,
                        "is_nullable": is_nullable,
                        "table": table_name,
                        "schema": schema_name,
                    },
                )

            cursor.close()

        except Exception as e:
            QtWidgets.QMessageBox.warning(
                self,
                "Error Loading Columns",
                f"Failed to load columns for table '{schema_name}.{table_name}':\n{str(e)}",
            )

    def on_item_double_clicked(self, item, column):
        """Handle double-click on an item."""
        item_data = item.data(0, QtCore.Qt.UserRole)
        if not item_data:
            return

        item_type = item_data.get("type")

        if item_type == "table":
            schema_name = item_data.get("schema")
            table_name = item_data.get("name")
            # Emit signal with schema and table name
            self.tableSelected.emit(schema_name, table_name)

    def show_context_menu(self, position):
        """Show context menu for tree items."""
        item = self.itemAt(position)
        if not item:
            return

        item_data = item.data(0, QtCore.Qt.UserRole)
        if not item_data:
            return

        item_type = item_data.get("type")

        menu = QtWidgets.QMenu()

        if item_type == "schema":
            schema_name = item_data.get("name")
            refresh_action = menu.addAction("Refresh Schema")
            refresh_action.triggered.connect(
                lambda: self.refresh_schema_item(item, schema_name)
            )

        elif item_type == "table":
            schema_name = item_data.get("schema")
            table_name = item_data.get("name")

            view_action = menu.addAction("Browse Data")
            view_action.triggered.connect(
                lambda: self.tableSelected.emit(schema_name, table_name)
            )

            refresh_action = menu.addAction("Refresh Table")
            refresh_action.triggered.connect(
                lambda: self.refresh_table_item(item, schema_name, table_name)
            )

            # Structure submenu
            structure_menu = menu.addMenu("Structure")

            # Add actions to structure menu
            columns_action = structure_menu.addAction("Show Columns")
            columns_action.triggered.connect(
                lambda: self.show_table_columns(schema_name, table_name)
            )

            indexes_action = structure_menu.addAction("Show Indexes")
            indexes_action.triggered.connect(
                lambda: self.show_table_indexes(schema_name, table_name)
            )

            # Sample query submenu
            query_menu = menu.addMenu("Sample Queries")

            # Add sample query actions
            select_action = query_menu.addAction("SELECT *")
            select_action.triggered.connect(
                lambda: self.generate_query(
                    f"SELECT * FROM {schema_name}.{table_name} LIMIT 100;"
                )
            )

            count_action = query_menu.addAction("COUNT(*)")
            count_action.triggered.connect(
                lambda: self.generate_query(
                    f"SELECT COUNT(*) FROM {schema_name}.{table_name};"
                )
            )

        elif item_type == "column":
            schema_name = item_data.get("schema")
            table_name = item_data.get("table")
            column_name = item_data.get("name")

            # Query submenu for column
            query_menu = menu.addMenu("Sample Queries")

            # Add sample query actions for column
            select_action = query_menu.addAction(f"SELECT {column_name}")
            select_action.triggered.connect(
                lambda: self.generate_query(
                    f"SELECT {column_name} FROM {schema_name}.{table_name} LIMIT 100;"
                )
            )

            distinct_action = query_menu.addAction(f"SELECT DISTINCT {column_name}")
            distinct_action.triggered.connect(
                lambda: self.generate_query(
                    f"SELECT DISTINCT {column_name} FROM {schema_name}.{table_name} LIMIT 100;"
                )
            )

            count_action = query_menu.addAction(f"COUNT DISTINCT {column_name}")
            count_action.triggered.connect(
                lambda: self.generate_query(
                    f"SELECT COUNT(DISTINCT {column_name}) FROM {schema_name}.{table_name};"
                )
            )

        # Only show menu if it has actions
        if not menu.isEmpty():
            menu.exec(self.viewport().mapToGlobal(position))

    def refresh_schema_item(self, item, schema_name):
        """Refresh a schema item."""
        # Remove all children
        item.takeChildren()

        # Add placeholder
        placeholder = QtWidgets.QTreeWidgetItem(item, ["Loading tables..."])
        item.addChild(placeholder)

        # Load tables
        self.load_tables(item, schema_name)

    def refresh_table_item(self, item, schema_name, table_name):
        """Refresh a table item."""
        # Remove all children
        item.takeChildren()

        # Add placeholder
        placeholder = QtWidgets.QTreeWidgetItem(item, ["Loading columns..."])
        item.addChild(placeholder)

        # Load columns
        self.load_columns(item, schema_name, table_name)

    def show_table_columns(self, schema_name, table_name):
        """Show table columns in a popup."""
        # This would be implemented to show detailed column info
        # For now, we'll just expand the table node
        for i in range(self.topLevelItemCount()):
            schema_item = self.topLevelItem(i)
            schema_data = schema_item.data(0, QtCore.Qt.UserRole)

            if (
                schema_data
                and schema_data.get("type") == "schema"
                and schema_data.get("name") == schema_name
            ):
                schema_item.setExpanded(True)

                for j in range(schema_item.childCount()):
                    table_item = schema_item.child(j)
                    table_data = table_item.data(0, QtCore.Qt.UserRole)

                    if (
                        table_data
                        and table_data.get("type") == "table"
                        and table_data.get("name") == table_name
                    ):
                        table_item.setExpanded(True)
                        break

                break

    def show_table_indexes(self, schema_name, table_name):
        """Show table indexes in a popup."""
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                """
                SELECT
                    i.relname AS index_name,
                    a.attname AS column_name,
                    am.amname AS index_type
                FROM
                    pg_class t,
                    pg_class i,
                    pg_index ix,
                    pg_attribute a,
                    pg_am am,
                    pg_namespace n
                WHERE
                    t.oid = ix.indrelid
                    AND i.oid = ix.indexrelid
                    AND a.attrelid = t.oid
                    AND a.attnum = ANY(ix.indkey)
                    AND t.relkind = 'r'
                    AND i.relam = am.oid
                    AND t.relnamespace = n.oid
                    AND n.nspname = %s
                    AND t.relname = %s
                ORDER BY
                    i.relname, array_position(ix.indkey, a.attnum)
            """,
                (schema_name, table_name),
            )

            indexes = cursor.fetchall()
            cursor.close()

            if not indexes:
                QtWidgets.QMessageBox.information(
                    self,
                    "Indexes",
                    f"No indexes found for table '{schema_name}.{table_name}'",
                )
                return

            # Create a simple dialog to display indexes
            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle(f"Indexes for {schema_name}.{table_name}")
            dialog.resize(400, 300)

            layout = QtWidgets.QVBoxLayout(dialog)

            # Create a table widget to display indexes
            table = QtWidgets.QTableWidget()
            table.setColumnCount(3)
            table.setHorizontalHeaderLabels(["Index Name", "Column", "Type"])
            table.setRowCount(len(indexes))

            for i, index in enumerate(indexes):
                table.setItem(i, 0, QtWidgets.QTableWidgetItem(index[0]))
                table.setItem(i, 1, QtWidgets.QTableWidgetItem(index[1]))
                table.setItem(i, 2, QtWidgets.QTableWidgetItem(index[2]))

            table.resizeColumnsToContents()
            layout.addWidget(table)

            # Add a close button
            button = QtWidgets.QPushButton("Close")
            button.clicked.connect(dialog.accept)
            layout.addWidget(button)

            dialog.setLayout(layout)
            dialog.exec()

        except Exception as e:
            QtWidgets.QMessageBox.warning(
                self,
                "Error Loading Indexes",
                f"Failed to load indexes for table '{schema_name}.{table_name}':\n{str(e)}",
            )

    def generate_query(self, query):
        """Generate a SQL query and emit a signal with it."""
        # Emit the signal with the generated query
        self.queryGenerated.emit(query)

