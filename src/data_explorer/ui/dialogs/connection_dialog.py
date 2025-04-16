from PySide6 import QtWidgets, QtCore


class ConnectionDialog(QtWidgets.QDialog):
    """
    A dialog window for entering PostgreSQL connection details.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Connect to PostgreSQL Database")
        self.setMinimumWidth(350)

        # --- Widgets ---
        self.host_input = QtWidgets.QLineEdit("localhost")
        self.port_input = QtWidgets.QLineEdit("5432")
        self.db_input = QtWidgets.QLineEdit("odoo_database")  # Example default
        self.user_input = QtWidgets.QLineEdit("odoo_user")  # Example default
        self.password_input = QtWidgets.QLineEdit()
        self.password_input.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)

        # --- Layout ---
        form_layout = QtWidgets.QFormLayout()
        form_layout.addRow("Host:", self.host_input)
        form_layout.addRow("Port:", self.port_input)
        form_layout.addRow("Database:", self.db_input)
        form_layout.addRow("User:", self.user_input)
        form_layout.addRow("Password:", self.password_input)

        # --- Buttons ---
        # Standard buttons for dialogs (OK, Cancel)
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)  # Connect Ok signal to accept slot
        button_box.rejected.connect(self.reject)  # Connect Cancel signal to reject slot

        # Rename OK button to "Connect" for clarity
        button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Ok).setText(
            "Connect"
        )

        # --- Main Layout ---
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addLayout(form_layout)
        main_layout.addWidget(button_box)
        self.setLayout(main_layout)

    def get_connection_details(self):
        """
        Retrieves the connection details entered by the user.

        Returns:
            dict: A dictionary containing the connection parameters.
        """
        return {
            "host": self.host_input.text().strip(),
            "port": self.port_input.text().strip(),
            "dbname": self.db_input.text().strip(),
            "user": self.user_input.text().strip(),
            "password": self.password_input.text(),  # Don't strip password
        }

    # Override accept to add basic validation (optional but good)
    def accept(self):
        """Validates input before accepting the dialog."""
        details = self.get_connection_details()
        if not all(
            [details["host"], details["port"], details["dbname"], details["user"]]
        ):
            QtWidgets.QMessageBox.warning(
                self,
                "Missing Information",
                "Please fill in Host, Port, Database, and User fields.",
            )
            return  # Stay on the dialog

        # Basic port validation
        try:
            port_num = int(details["port"])
            if not (0 < port_num < 65536):
                raise ValueError("Port number out of range")
        except ValueError:
            QtWidgets.QMessageBox.warning(
                self, "Invalid Port", "Please enter a valid port number (1-65535)."
            )
            self.port_input.setFocus()  # Focus the port input
            self.port_input.selectAll()
            return  # Stay on the dialog

        # If validation passes, call the original accept method
        super().accept()
