import sys
from PySide6 import QtWidgets
from data_explorer.ui.main_window import MainWindow


def run():
    """
    Initializes and runs the Qt application.
    """
    # Create the Qt Application
    app = QtWidgets.QApplication(sys.argv)

    # Create and show the main window
    window = MainWindow()
    window.show()

    # Run the application's event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    # This ensures the run function is called only when the script is executed directly
    run()
