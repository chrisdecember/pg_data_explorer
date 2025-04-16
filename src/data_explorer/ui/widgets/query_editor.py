from PySide6 import QtWidgets, QtCore, QtGui


class QueryEditor(QtWidgets.QWidget):
    """
    Widget for editing and executing SQL queries.
    """

    # Signal emitted when a query is executed
    queryExecuted = QtCore.Signal(list, list)  # columns, data

    def __init__(self, parent=None):
        super().__init__(parent)

        # Store database connection
        self.connection = None

        # Create layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create toolbar
        toolbar = QtWidgets.QToolBar()
        layout.addWidget(toolbar)

        # Execute action
        self.execute_action = QtGui.QAction("Execute", self)
        self.execute_action.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay)
        )
        self.execute_action.setShortcut("F5")
        self.execute_action.setToolTip("Execute query (F5)")
        self.execute_action.triggered.connect(self.execute_query)
        toolbar.addAction(self.execute_action)

        # Clear action
        clear_action = QtGui.QAction("Clear", self)
        clear_action.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_DialogResetButton)
        )
        clear_action.triggered.connect(self.clear_query)
        toolbar.addAction(clear_action)

        toolbar.addSeparator()

        # History actions (placeholder)
        back_action = QtGui.QAction("Previous", self)
        back_action.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_ArrowLeft))
        back_action.setEnabled(False)  # Disabled until history is implemented
        toolbar.addAction(back_action)

        forward_action = QtGui.QAction("Next", self)
        forward_action.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.SP_ArrowRight)
        )
        forward_action.setEnabled(False)  # Disabled until history is implemented
        toolbar.addAction(forward_action)

        # Add query editor
        self.editor = QtWidgets.QPlainTextEdit()
        self.editor.setPlaceholderText("Enter your SQL query here...")

        # Use a monospaced font
        font = QtGui.QFont("Courier New", 10)
        self.editor.setFont(font)

        # Add line numbers (optional enhancement)
        self.line_numbers = LineNumberArea(self.editor)
        self.editor.blockCountChanged.connect(self.update_line_number_area_width)
        self.editor.updateRequest.connect(self.update_line_number_area)
        self.update_line_number_area_width(0)

        layout.addWidget(self.editor)

        # Enable syntax highlighting (for a future enhancement)
        # self.highlighter = SQLHighlighter(self.editor.document())

        # Add status bar
        self.status_bar = QtWidgets.QStatusBar()
        self.status_bar.showMessage("Ready")
        layout.addWidget(self.status_bar)

        # Query history
        self.query_history = []
        self.history_position = -1

    def set_connection(self, connection):
        """Set the database connection."""
        self.connection = connection
        # Enable or disable execute button based on connection status
        self.execute_action.setEnabled(connection is not None)

    def execute_query(self):
        """Execute the current SQL query."""
        if not self.connection:
            self.status_bar.showMessage("Not connected to a database.")
            return

        # Get the query text
        query = self.editor.toPlainText().strip()
        if not query:
            self.status_bar.showMessage("No query to execute.")
            return

        # Add to history
        if not self.query_history or self.query_history[-1] != query:
            self.query_history.append(query)
            self.history_position = len(self.query_history) - 1

        # Update status
        self.status_bar.showMessage("Executing query...")

        try:
            cursor = self.connection.cursor()
            cursor.execute(query)

            # Check if the query returns results
            if cursor.description:
                # Get column names
                columns = [desc[0] for desc in cursor.description]

                # Fetch all data
                # Note: For large results, might want to limit rows or implement pagination
                data = cursor.fetchall()

                # Update status
                self.status_bar.showMessage(
                    f"Query executed successfully. Returned {len(data)} rows."
                )

                # Emit signal with results
                self.queryExecuted.emit(columns, data)
            else:
                # For queries that don't return data (INSERT, UPDATE, DELETE)
                affected = cursor.rowcount
                self.status_bar.showMessage(
                    f"Query executed successfully. Affected {affected} rows."
                )

                # Emit signal with empty results to clear the results view
                self.queryExecuted.emit([], [])

            cursor.close()

        except Exception as e:
            self.status_bar.showMessage(f"Error: {str(e)}")
            # Display error in a message box for better visibility
            QtWidgets.QMessageBox.critical(self, "Query Error", str(e))

    def clear_query(self):
        """Clear the query editor."""
        self.editor.clear()
        self.status_bar.showMessage("Ready")

    def insert_text(self, text):
        """Insert text at the current cursor position."""
        self.editor.insertPlainText(text)

    def update_line_number_area_width(self, count):
        """Update the width of the line number area."""
        width = self.line_numbers.calculate_width(self.editor.blockCount())
        self.editor.setViewportMargins(width, 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        """Update the line number area."""
        if dy:
            self.line_numbers.scroll(0, dy)
        else:
            self.line_numbers.update(
                0, rect.y(), self.line_numbers.width(), rect.height()
            )

        if rect.contains(self.editor.viewport().rect()):
            self.update_line_number_area_width(0)


class LineNumberArea(QtWidgets.QWidget):
    """Widget for displaying line numbers in the query editor."""

    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
        self.editor.installEventFilter(self)

    def calculate_width(self, count):
        """Calculate the width needed to display line numbers."""
        digits = len(str(max(1, count)))
        return 10 + self.editor.fontMetrics().horizontalAdvance("9") * digits

    def eventFilter(self, obj, event):
        """Handle resize events to update the line number area."""
        if obj is self.editor and event.type() == QtCore.QEvent.Resize:
            rect = self.editor.contentsRect()
            self.setGeometry(
                QtCore.QRect(
                    rect.left(),
                    rect.top(),
                    self.calculate_width(self.editor.blockCount()),
                    rect.height(),
                )
            )
        return super().eventFilter(obj, event)

    def paintEvent(self, event):
        """Paint the line numbers."""
        painter = QtGui.QPainter(self)
        painter.fillRect(event.rect(), QtGui.QColor(240, 240, 240))

        block = self.editor.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(
            self.editor.blockBoundingGeometry(block)
            .translated(self.editor.contentOffset())
            .top()
        )
        bottom = top + int(self.editor.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QtGui.QColor(100, 100, 100))
                painter.drawText(
                    0,
                    top,
                    self.width() - 5,
                    self.editor.fontMetrics().height(),
                    QtCore.Qt.AlignRight,
                    number,
                )

            block = block.next()
            top = bottom
            bottom = top + int(self.editor.blockBoundingRect(block).height())
            block_number += 1
