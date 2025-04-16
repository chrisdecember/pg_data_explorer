from PySide6 import QtWidgets, QtCore, QtGui
import csv
import io


class ResultsView(QtWidgets.QWidget):
    """
    Widget for displaying SQL query results.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # Create layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create toolbar
        toolbar = QtWidgets.QToolBar()
        layout.addWidget(toolbar)

        # Export action
        export_action = QtGui.QAction("Export to CSV", self)
        export_action.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_DialogSaveButton)
        )
        export_action.triggered.connect(self.export_to_csv)
        toolbar.addAction(export_action)

        # Copy action
        copy_action = QtGui.QAction("Copy Selection", self)
        copy_action.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_DialogSaveButton)
        )
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(self.copy_selection)
        toolbar.addAction(copy_action)

        # Clear action
        clear_action = QtGui.QAction("Clear Results", self)
        clear_action.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_DialogResetButton)
        )
        clear_action.triggered.connect(self.clear_results)
        toolbar.addAction(clear_action)

        # Add table view
        self.table_view = QtWidgets.QTableView()
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSortingEnabled(True)
        self.table_view.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table_view.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.table_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self.show_context_menu)

        # Create model
        self.model = QtGui.QStandardItemModel()
        self.table_view.setModel(self.model)

        layout.addWidget(self.table_view)

        # Add status bar
        self.status_bar = QtWidgets.QStatusBar()
        self.status_bar.showMessage("No results")
        layout.addWidget(self.status_bar)

    def display_results(self, columns, data):
        """
        Display the query results.

        Args:
            columns (list): List of column names
            data (list): List of result rows (each row is a tuple of values)
        """
        # Clear previous results
        self.model.clear()

        if not columns:
            self.status_bar.showMessage("No results")
            return

        # Set column headers
        self.model.setHorizontalHeaderLabels(columns)

        # Add data rows
        for row_index, row_data in enumerate(data):
            row_items = []
            for col_index, cell_value in enumerate(row_data):
                item = QtGui.QStandardItem()

                # Handle None values
                if cell_value is None:
                    item.setText("NULL")
                    item.setData(None, QtCore.Qt.UserRole)
                    # Gray out NULL values
                    item.setForeground(QtGui.QBrush(QtGui.QColor(150, 150, 150)))
                else:
                    # Convert all values to strings for display
                    text = str(cell_value)
                    item.setText(text)
                    item.setData(cell_value, QtCore.Qt.UserRole)

                row_items.append(item)

            self.model.appendRow(row_items)

        # Resize columns to contents
        self.table_view.resizeColumnsToContents()

        # Update status bar
        row_count = len(data)
        column_count = len(columns)
        self.status_bar.showMessage(f"{row_count} rows, {column_count} columns")

    def show_context_menu(self, position):
        """Show context menu for the results table."""
        menu = QtWidgets.QMenu()

        # Add actions
        copy_action = menu.addAction("Copy Selection")
        copy_action.triggered.connect(self.copy_selection)

        export_action = menu.addAction("Export to CSV")
        export_action.triggered.connect(self.export_to_csv)

        # Show menu
        menu.exec(self.table_view.viewport().mapToGlobal(position))

    def copy_selection(self):
        """Copy selected cells to clipboard."""
        selection = self.table_view.selectionModel()
        if not selection.hasSelection():
            return

        selected_indexes = selection.selectedIndexes()
        if not selected_indexes:
            return

        # Sort indexes by row, then column
        selected_indexes.sort(key=lambda idx: (idx.row(), idx.column()))

        # Find the minimum and maximum row and column
        min_row = min(index.row() for index in selected_indexes)
        max_row = max(index.row() for index in selected_indexes)
        min_col = min(index.column() for index in selected_indexes)
        max_col = max(index.column() for index in selected_indexes)

        # Create a string to hold the copied data
        text = ""

        # Iterate through rows and columns
        for row in range(min_row, max_row + 1):
            row_text = []
            for col in range(min_col, max_col + 1):
                index = self.model.index(row, col)
                if index in selected_indexes:
                    # Use the text directly from the model
                    data = self.model.data(index)
                    row_text.append(str(data) if data is not None else "")
                else:
                    # If this cell is not selected, add an empty string
                    row_text.append("")

            # Add row to text
            text += "\t".join(row_text) + "\n"

        # Remove the trailing newline
        if text.endswith("\n"):
            text = text[:-1]

        # Copy to clipboard
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(text)

        # Update status bar
        self.status_bar.showMessage("Selection copied to clipboard")

    def export_to_csv(self):
        """Export the results to a CSV file."""
        if self.model.rowCount() == 0:
            self.status_bar.showMessage("No data to export")
            return

        # Open file dialog
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export to CSV", "", "CSV Files (*.csv);;All Files (*)"
        )

        if not file_path:
            return

        try:
            with open(file_path, "w", newline="") as file:
                writer = csv.writer(file)

                # Write header
                header = []
                for col in range(self.model.columnCount()):
                    header.append(self.model.headerData(col, QtCore.Qt.Horizontal))
                writer.writerow(header)

                # Write data
                for row in range(self.model.rowCount()):
                    row_data = []
                    for col in range(self.model.columnCount()):
                        item = self.model.index(row, col)
                        value = self.model.data(item, QtCore.Qt.DisplayRole)
                        if value == "NULL":  # Handle NULL display values
                            value = ""
                        row_data.append(value)
                    writer.writerow(row_data)

            self.status_bar.showMessage(f"Data exported to {file_path}")

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "Export Error", f"Failed to export data: {str(e)}"
            )

    def clear_results(self):
        """Clear the results table."""
        self.model.clear()
        self.status_bar.showMessage("No results")
