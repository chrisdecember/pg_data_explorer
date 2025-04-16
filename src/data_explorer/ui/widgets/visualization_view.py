from PySide6 import QtWidgets, QtCore, QtGui
import matplotlib

matplotlib.use("Qt5Agg")
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
import numpy as np
import pandas as pd
from datetime import datetime
import re
import seaborn as sns
import io
from pathlib import Path


class VisualizationView(QtWidgets.QWidget):
    """Widget for visualizing query results."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_df = None
        self.column_types = {}
        self.setup_ui()

    def setup_ui(self):
        """Set up the UI components."""
        main_layout = QtWidgets.QVBoxLayout(self)

        self.status_bar = QtWidgets.QStatusBar()

        # Title
        title_label = QtWidgets.QLabel("Data Visualization")
        title_font = title_label.font()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        main_layout.addWidget(title_label)

        # Split view for options and chart
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        main_layout.addWidget(splitter)

        # Options panel (left side)
        options_widget = QtWidgets.QWidget()
        options_layout = QtWidgets.QVBoxLayout(options_widget)

        # Chart type selection
        chart_type_group = QtWidgets.QGroupBox("Chart Type")
        chart_type_layout = QtWidgets.QVBoxLayout()
        self.chart_type_combo = QtWidgets.QComboBox()
        self.chart_type_combo.addItems(
            [
                "Bar Chart",
                "Line Chart",
                "Scatter Plot",
                "Pie Chart",
                "Histogram",
                "Box Plot",
                "Heatmap",
                "Area Chart",
                "Violin Plot",
            ]
        )
        self.chart_type_combo.currentIndexChanged.connect(self.on_chart_type_changed)
        chart_type_layout.addWidget(self.chart_type_combo)
        chart_type_group.setLayout(chart_type_layout)
        options_layout.addWidget(chart_type_group)

        # Data columns selection
        data_columns_group = QtWidgets.QGroupBox("Data Columns")
        data_columns_layout = QtWidgets.QFormLayout()

        self.x_axis_combo = QtWidgets.QComboBox()
        self.x_axis_combo.currentIndexChanged.connect(self.update_chart)

        self.y_axis_combo = QtWidgets.QComboBox()
        self.y_axis_combo.currentIndexChanged.connect(self.update_chart)

        self.group_by_combo = QtWidgets.QComboBox()
        self.group_by_combo.addItem("None")
        self.group_by_combo.currentIndexChanged.connect(self.update_chart)

        data_columns_layout.addRow("X-Axis:", self.x_axis_combo)
        data_columns_layout.addRow("Y-Axis:", self.y_axis_combo)
        data_columns_layout.addRow("Group By:", self.group_by_combo)

        data_columns_group.setLayout(data_columns_layout)
        options_layout.addWidget(data_columns_group)

        # Chart options group
        chart_options_group = QtWidgets.QGroupBox("Chart Options")
        chart_options_layout = QtWidgets.QFormLayout()

        self.chart_title_input = QtWidgets.QLineEdit()
        self.chart_title_input.setPlaceholderText("Enter chart title")
        self.chart_title_input.textChanged.connect(self.update_chart)

        self.x_label_input = QtWidgets.QLineEdit()
        self.x_label_input.setPlaceholderText("X-Axis Label")
        self.x_label_input.textChanged.connect(self.update_chart)

        self.y_label_input = QtWidgets.QLineEdit()
        self.y_label_input.setPlaceholderText("Y-Axis Label")
        self.y_label_input.textChanged.connect(self.update_chart)

        # Color scheme dropdown
        self.color_scheme_combo = QtWidgets.QComboBox()
        self.color_scheme_combo.addItems(
            [
                "Default",
                "Viridis",
                "Plasma",
                "Inferno",
                "Magma",
                "Cividis",
                "Blues",
                "Greens",
                "Reds",
                "Purples",
                "Oranges",
            ]
        )
        self.color_scheme_combo.currentIndexChanged.connect(self.update_chart)

        chart_options_layout.addRow("Title:", self.chart_title_input)
        chart_options_layout.addRow("X Label:", self.x_label_input)
        chart_options_layout.addRow("Y Label:", self.y_label_input)
        chart_options_layout.addRow("Color Scheme:", self.color_scheme_combo)

        chart_options_group.setLayout(chart_options_layout)
        options_layout.addWidget(chart_options_group)

        # Chart-specific options (these will be shown/hidden based on chart type)
        self.chart_specific_options = QtWidgets.QStackedWidget()

        # Bar chart options
        bar_options = QtWidgets.QWidget()
        bar_layout = QtWidgets.QFormLayout(bar_options)

        self.bar_orientation_combo = QtWidgets.QComboBox()
        self.bar_orientation_combo.addItems(["Vertical", "Horizontal"])
        self.bar_orientation_combo.currentIndexChanged.connect(self.update_chart)

        self.bar_width_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.bar_width_slider.setRange(1, 100)
        self.bar_width_slider.setValue(80)
        self.bar_width_slider.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.bar_width_slider.valueChanged.connect(self.update_chart)

        bar_layout.addRow("Orientation:", self.bar_orientation_combo)
        bar_layout.addRow("Bar Width:", self.bar_width_slider)

        self.chart_specific_options.addWidget(bar_options)

        # Line chart options
        line_options = QtWidgets.QWidget()
        line_layout = QtWidgets.QFormLayout(line_options)

        self.line_style_combo = QtWidgets.QComboBox()
        self.line_style_combo.addItems(["Solid", "Dashed", "Dotted", "Dash-Dot"])
        self.line_style_combo.currentIndexChanged.connect(self.update_chart)

        self.line_marker_combo = QtWidgets.QComboBox()
        self.line_marker_combo.addItems(
            ["None", "Circle", "Square", "Triangle", "Star", "Plus", "X"]
        )
        self.line_marker_combo.currentIndexChanged.connect(self.update_chart)

        self.line_width_spinner = QtWidgets.QSpinBox()
        self.line_width_spinner.setRange(1, 10)
        self.line_width_spinner.setValue(2)
        self.line_width_spinner.valueChanged.connect(self.update_chart)

        line_layout.addRow("Line Style:", self.line_style_combo)
        line_layout.addRow("Markers:", self.line_marker_combo)
        line_layout.addRow("Line Width:", self.line_width_spinner)

        self.chart_specific_options.addWidget(line_options)

        # Scatter plot options
        scatter_options = QtWidgets.QWidget()
        scatter_layout = QtWidgets.QFormLayout(scatter_options)

        self.scatter_size_spinner = QtWidgets.QSpinBox()
        self.scatter_size_spinner.setRange(5, 500)
        self.scatter_size_spinner.setValue(50)
        self.scatter_size_spinner.valueChanged.connect(self.update_chart)

        self.scatter_alpha_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.scatter_alpha_slider.setRange(0, 100)
        self.scatter_alpha_slider.setValue(70)
        self.scatter_alpha_slider.valueChanged.connect(self.update_chart)

        scatter_layout.addRow("Point Size:", self.scatter_size_spinner)
        scatter_layout.addRow("Transparency:", self.scatter_alpha_slider)

        self.chart_specific_options.addWidget(scatter_options)

        # Pie chart options
        pie_options = QtWidgets.QWidget()
        pie_layout = QtWidgets.QFormLayout(pie_options)

        self.pie_autopct_combo = QtWidgets.QComboBox()
        self.pie_autopct_combo.addItems(["None", "Percentage", "Value", "Both"])
        self.pie_autopct_combo.currentIndexChanged.connect(self.update_chart)

        self.pie_explode_check = QtWidgets.QCheckBox("Explode Largest Slice")
        self.pie_explode_check.stateChanged.connect(self.update_chart)

        self.pie_start_angle_spinner = QtWidgets.QSpinBox()
        self.pie_start_angle_spinner.setRange(0, 359)
        self.pie_start_angle_spinner.setValue(0)
        self.pie_start_angle_spinner.valueChanged.connect(self.update_chart)

        pie_layout.addRow("Labels:", self.pie_autopct_combo)
        pie_layout.addRow("", self.pie_explode_check)
        pie_layout.addRow("Start Angle:", self.pie_start_angle_spinner)

        self.chart_specific_options.addWidget(pie_options)

        # Histogram options
        histogram_options = QtWidgets.QWidget()
        histogram_layout = QtWidgets.QFormLayout(histogram_options)

        self.histogram_bins_spinner = QtWidgets.QSpinBox()
        self.histogram_bins_spinner.setRange(2, 100)
        self.histogram_bins_spinner.setValue(10)
        self.histogram_bins_spinner.valueChanged.connect(self.update_chart)

        self.histogram_kde_check = QtWidgets.QCheckBox("Show Density Curve")
        self.histogram_kde_check.stateChanged.connect(self.update_chart)

        histogram_layout.addRow("Bins:", self.histogram_bins_spinner)
        histogram_layout.addRow("", self.histogram_kde_check)

        self.chart_specific_options.addWidget(histogram_options)

        # Box plot options
        boxplot_options = QtWidgets.QWidget()
        boxplot_layout = QtWidgets.QFormLayout(boxplot_options)

        self.boxplot_notch_check = QtWidgets.QCheckBox("Show Notches")
        self.boxplot_notch_check.stateChanged.connect(self.update_chart)

        self.boxplot_orientation_combo = QtWidgets.QComboBox()
        self.boxplot_orientation_combo.addItems(["Vertical", "Horizontal"])
        self.boxplot_orientation_combo.currentIndexChanged.connect(self.update_chart)

        boxplot_layout.addRow("", self.boxplot_notch_check)
        boxplot_layout.addRow("Orientation:", self.boxplot_orientation_combo)

        self.chart_specific_options.addWidget(boxplot_options)

        # Heatmap options
        heatmap_options = QtWidgets.QWidget()
        heatmap_layout = QtWidgets.QFormLayout(heatmap_options)

        self.heatmap_annot_check = QtWidgets.QCheckBox("Show Values")
        self.heatmap_annot_check.setChecked(True)
        self.heatmap_annot_check.stateChanged.connect(self.update_chart)

        self.heatmap_cmap_combo = QtWidgets.QComboBox()
        self.heatmap_cmap_combo.addItems(
            [
                "Viridis",
                "Plasma",
                "Inferno",
                "Magma",
                "Cividis",
                "Blues",
                "Greens",
                "Reds",
                "Purples",
                "Oranges",
                "YlOrRd",
                "YlGnBu",
            ]
        )
        self.heatmap_cmap_combo.currentIndexChanged.connect(self.update_chart)

        heatmap_layout.addRow("", self.heatmap_annot_check)
        heatmap_layout.addRow("Color Map:", self.heatmap_cmap_combo)

        self.chart_specific_options.addWidget(heatmap_options)

        # Area chart options
        area_options = QtWidgets.QWidget()
        area_layout = QtWidgets.QFormLayout(area_options)

        self.area_alpha_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.area_alpha_slider.setRange(0, 100)
        self.area_alpha_slider.setValue(60)
        self.area_alpha_slider.valueChanged.connect(self.update_chart)

        self.area_stacked_check = QtWidgets.QCheckBox("Stacked Areas")
        self.area_stacked_check.stateChanged.connect(self.update_chart)

        area_layout.addRow("Transparency:", self.area_alpha_slider)
        area_layout.addRow("", self.area_stacked_check)

        self.chart_specific_options.addWidget(area_options)

        # Violin plot options
        violin_options = QtWidgets.QWidget()
        violin_layout = QtWidgets.QFormLayout(violin_options)

        self.violin_inner_combo = QtWidgets.QComboBox()
        self.violin_inner_combo.addItems(["Box", "Quartile", "Point", "Stick", "None"])
        self.violin_inner_combo.currentIndexChanged.connect(self.update_chart)

        self.violin_orientation_combo = QtWidgets.QComboBox()
        self.violin_orientation_combo.addItems(["Vertical", "Horizontal"])
        self.violin_orientation_combo.currentIndexChanged.connect(self.update_chart)

        violin_layout.addRow("Inner:", self.violin_inner_combo)
        violin_layout.addRow("Orientation:", self.violin_orientation_combo)

        self.chart_specific_options.addWidget(violin_options)

        options_layout.addWidget(self.chart_specific_options)

        # Export options
        export_group = QtWidgets.QGroupBox("Export")
        export_layout = QtWidgets.QVBoxLayout()

        self.export_button = QtWidgets.QPushButton("Export Chart")
        self.export_button.clicked.connect(self.export_chart)
        export_layout.addWidget(self.export_button)

        export_group.setLayout(export_layout)
        options_layout.addWidget(export_group)

        # Add stretch to push everything to the top
        options_layout.addStretch()

        # Chart view (right side)
        self.chart_widget = QtWidgets.QWidget()
        self.chart_layout = QtWidgets.QVBoxLayout(self.chart_widget)

        # Add placeholder for when no data is available
        self.placeholder_label = QtWidgets.QLabel(
            "No data to visualize. Run a query first."
        )
        self.placeholder_label.setAlignment(QtCore.Qt.AlignCenter)
        placeholder_font = self.placeholder_label.font()
        placeholder_font.setPointSize(14)
        self.placeholder_label.setFont(placeholder_font)
        self.chart_layout.addWidget(self.placeholder_label)

        # Add widgets to splitter
        splitter.addWidget(options_widget)
        splitter.addWidget(self.chart_widget)

        # Set initial splitter sizes (30% options, 70% chart)
        splitter.setSizes([300, 700])

        # Set the initial chart type
        self.on_chart_type_changed(0)

        main_layout.addWidget(self.status_bar)

    def on_chart_type_changed(self, index):
        """Show the appropriate options for the selected chart type."""
        self.chart_specific_options.setCurrentIndex(index)
        self.update_chart()

    def set_data(self, columns, data):
        """Set the data to visualize."""
        if not columns or not data:
            # Clear the current visualization if there's no data
            self.data_df = None
            self.clear_chart()
            self.placeholder_label.setVisible(True)
            return

        # Convert to pandas DataFrame for easier manipulation
        self.data_df = pd.DataFrame(data, columns=columns)

        # Remove the placeholder
        self.placeholder_label.setVisible(False)

        # Determine column types (numeric, date, categorical, etc.)
        self.infer_column_types()

        # Update column selectors
        self.update_column_selectors()

        # Update the chart
        self.update_chart()

    def infer_column_types(self):
        """Infer data types for each column."""
        self.column_types = {}
        if self.data_df is None:
            return

        for column in self.data_df.columns:
            # Check if column is numeric
            if pd.api.types.is_numeric_dtype(self.data_df[column]):
                self.column_types[column] = "numeric"
            else:
                # Check if column contains dates
                try:
                    # Try to convert a sample to datetime
                    sample = (
                        self.data_df[column].dropna().iloc[0]
                        if not self.data_df[column].dropna().empty
                        else None
                    )
                    if sample and isinstance(sample, str):
                        datetime.strptime(sample, "%Y-%m-%d")
                        self.column_types[column] = "date"
                    else:
                        self.column_types[column] = "categorical"
                except (ValueError, TypeError):
                    # If conversion fails, consider it categorical
                    self.column_types[column] = "categorical"

    def update_column_selectors(self):
        """Update column selector dropdown options based on available data."""
        if self.data_df is None:
            return

        # Store current selections
        x_current = (
            self.x_axis_combo.currentText() if self.x_axis_combo.count() > 0 else ""
        )
        y_current = (
            self.y_axis_combo.currentText() if self.y_axis_combo.count() > 0 else ""
        )
        group_current = (
            self.group_by_combo.currentText() if self.group_by_combo.count() > 0 else ""
        )

        # Temporarily block signals to prevent chart updates during changes
        self.x_axis_combo.blockSignals(True)
        self.y_axis_combo.blockSignals(True)
        self.group_by_combo.blockSignals(True)

        # Clear current options
        self.x_axis_combo.clear()
        self.y_axis_combo.clear()
        self.group_by_combo.clear()
        self.group_by_combo.addItem("None")

        # Populate with current columns
        for column in self.data_df.columns:
            self.x_axis_combo.addItem(column)
            self.y_axis_combo.addItem(column)
            self.group_by_combo.addItem(column)

        # Restore previous selections if they still exist
        if x_current and self.x_axis_combo.findText(x_current) >= 0:
            self.x_axis_combo.setCurrentText(x_current)
        elif self.x_axis_combo.count() > 0:
            # Set default X axis based on column types - prefer categorical or date for x-axis
            for col, col_type in self.column_types.items():
                if col_type in ("categorical", "date"):
                    self.x_axis_combo.setCurrentText(col)
                    break

        if y_current and self.y_axis_combo.findText(y_current) >= 0:
            self.y_axis_combo.setCurrentText(y_current)
        elif self.y_axis_combo.count() > 0:
            # Set default Y axis - prefer numeric
            for col, col_type in self.column_types.items():
                if col_type == "numeric":
                    self.y_axis_combo.setCurrentText(col)
                    break

        if group_current and self.group_by_combo.findText(group_current) >= 0:
            self.group_by_combo.setCurrentText(group_current)

        # Unblock signals
        self.x_axis_combo.blockSignals(False)
        self.y_axis_combo.blockSignals(False)
        self.group_by_combo.blockSignals(False)

        # Set default chart title and axis labels
        if self.x_axis_combo.count() > 0 and self.y_axis_combo.count() > 0:
            x_col = self.x_axis_combo.currentText()
            y_col = self.y_axis_combo.currentText()

            self.chart_title_input.setText(f"{y_col} by {x_col}")
            self.x_label_input.setText(x_col)
            self.y_label_input.setText(y_col)

    def clear_chart(self):
        # Loop backwards over layout items to safely remove widgets
        for i in reversed(range(self.chart_layout.count())):
            item = self.chart_layout.itemAt(i)
            widget = item.widget()
            # Check if the widget is not the placeholder label
            if widget is not self.placeholder_label:
                self.chart_layout.removeWidget(widget)
                widget.deleteLater()

    def update_chart(self):
        """Update the chart based on current settings."""
        if self.data_df is None or self.data_df.empty:
            self.status_bar.showMessage("No data available")
            return

        # Clear previous chart
        self.clear_chart()

        try:
            # Get chart settings
            chart_type = self.chart_type_combo.currentText()

            if self.x_axis_combo.count() == 0 or self.y_axis_combo.count() == 0:
                self.status_bar.showMessage(
                    "Not enough columns available for visualization"
                )
                return

            x_col = self.x_axis_combo.currentText()
            y_col = self.y_axis_combo.currentText()

            group_col = self.group_by_combo.currentText()
            if group_col == "None":
                group_col = None

            # Create matplotlib figure
            fig = Figure(figsize=(8, 6), dpi=100, tight_layout=True)
            canvas = FigureCanvasQTAgg(fig)
            ax = fig.add_subplot(111)

            # Apply seaborn styling
            sns.set_style("whitegrid")

            # Get color palette
            color_scheme = self.color_scheme_combo.currentText()
            if color_scheme != "Default":
                palette = color_scheme.lower()
            else:
                palette = None

            # Create the appropriate chart type
            if chart_type == "Bar Chart":
                self.create_bar_chart(fig, ax, x_col, y_col, group_col, palette)
            elif chart_type == "Line Chart":
                self.create_line_chart(fig, ax, x_col, y_col, group_col, palette)
            elif chart_type == "Scatter Plot":
                self.create_scatter_plot(fig, ax, x_col, y_col, group_col, palette)
            elif chart_type == "Pie Chart":
                self.create_pie_chart(fig, ax, x_col, y_col, palette)
            elif chart_type == "Histogram":
                self.create_histogram(fig, ax, x_col, y_col, group_col, palette)
            elif chart_type == "Box Plot":
                self.create_box_plot(fig, ax, x_col, y_col, group_col, palette)
            elif chart_type == "Heatmap":
                self.create_heatmap(fig, ax, palette)
            elif chart_type == "Area Chart":
                self.create_area_chart(fig, ax, x_col, y_col, group_col, palette)
            elif chart_type == "Violin Plot":
                self.create_violin_plot(fig, ax, x_col, y_col, group_col, palette)

            # Apply titles and labels
            title = self.chart_title_input.text()
            if title:
                ax.set_title(title, fontsize=14)

            x_label = self.x_label_input.text()
            if x_label and chart_type != "Pie Chart":
                ax.set_xlabel(x_label, fontsize=12)

            y_label = self.y_label_input.text()
            if y_label and chart_type != "Pie Chart":
                ax.set_ylabel(y_label, fontsize=12)

            # Add the toolbar for zooming, panning, saving, etc.
            toolbar = NavigationToolbar2QT(canvas, self)

            # Add the canvas and toolbar to the layout
            self.chart_layout.addWidget(toolbar)
            self.chart_layout.addWidget(canvas)

            self.status_bar.showMessage("Chart updated successfully")

        except Exception as e:
            self.status_bar.showMessage(f"Error creating chart: {str(e)}")
            # Add a label with the error message to the chart area
            error_label = QtWidgets.QLabel(f"Error creating chart:\n{str(e)}")
            error_label.setAlignment(QtCore.Qt.AlignCenter)
            error_label.setStyleSheet("color: red;")
            self.chart_layout.addWidget(error_label)

    def create_bar_chart(self, fig, ax, x_col, y_col, group_col, palette):
        """Create a bar chart."""
        # Get bar chart options
        orientation = self.bar_orientation_combo.currentText()
        bar_width = (
            self.bar_width_slider.value() / 100.0
        )  # Convert slider value to proportion

        df = self.data_df.copy()

        # Group by x-axis if needed
        if df[x_col].nunique() > 100:  # If too many categories
            self.status_bar.showMessage("Warning: Too many categories. Showing top 20.")
            # Get counts and take top categories
            value_counts = df[x_col].value_counts().nlargest(20)
            # Filter to keep only these categories
            df = df[df[x_col].isin(value_counts.index)]

        if group_col:
            # Group data for a grouped bar chart
            grouped = df.groupby([x_col, group_col])[y_col].mean().unstack()
            if orientation == "Horizontal":
                grouped.plot(kind="barh", ax=ax, width=bar_width, colormap=palette)
            else:
                grouped.plot(kind="bar", ax=ax, width=bar_width, colormap=palette)
        else:
            # Simple bar chart
            grouped = df.groupby(x_col)[y_col].mean()
            if orientation == "Horizontal":
                grouped.plot(
                    kind="barh",
                    ax=ax,
                    width=bar_width,
                    color=sns.color_palette(palette, 1)[0],
                )
            else:
                grouped.plot(
                    kind="bar",
                    ax=ax,
                    width=bar_width,
                    color=sns.color_palette(palette, 1)[0],
                )

        # Rotate x-axis labels if vertical bars
        if orientation == "Vertical" and len(grouped) > 5:
            plt = fig.canvas.manager.canvas.figure.gca()
            plt.tick_params(axis="x", rotation=45)

        if group_col:
            ax.legend(title=group_col)

        # Adjustments for better appearance
        ax.set_axisbelow(True)  # Put grid behind bars

    def create_line_chart(self, fig, ax, x_col, y_col, group_col, palette):
        """Create a line chart."""
        # Get line chart options
        line_style = self.line_style_combo.currentText().lower()
        marker = self.line_marker_combo.currentText()
        line_width = self.line_width_spinner.value()

        # Map line styles
        line_styles = {"solid": "-", "dashed": "--", "dotted": ":", "dash-dot": "-."}

        # Map markers
        markers = {
            "none": "",
            "circle": "o",
            "square": "s",
            "triangle": "^",
            "star": "*",
            "plus": "+",
            "x": "x",
        }

        df = self.data_df.copy()

        # Check if x column could be a date
        if self.column_types.get(x_col) == "date":
            try:
                df[x_col] = pd.to_datetime(df[x_col])
                df = df.sort_values(by=x_col)
            except:
                pass

        # Sort by x-axis values if numeric
        elif self.column_types.get(x_col) == "numeric":
            df = df.sort_values(by=x_col)

        if group_col:
            # Create a line for each group
            for name, group in df.groupby(group_col):
                ax.plot(
                    group[x_col],
                    group[y_col],
                    label=name,
                    linestyle=line_styles.get(line_style, "-"),
                    marker=markers.get(marker, ""),
                    linewidth=line_width,
                )
            ax.legend(title=group_col)
        else:
            # Simple line chart
            ax.plot(
                df[x_col],
                df[y_col],
                linestyle=line_styles.get(line_style, "-"),
                marker=markers.get(marker, ""),
                linewidth=line_width,
                color=sns.color_palette(palette, 1)[0],
            )

        # Rotate x-axis labels if many categories
        if df[x_col].nunique() > 5:
            plt = fig.canvas.manager.canvas.figure.gca()
            plt.tick_params(axis="x", rotation=45)

    def create_scatter_plot(self, fig, ax, x_col, y_col, group_col, palette):
        """Create a scatter plot."""
        # Get scatter plot options
        point_size = self.scatter_size_spinner.value()
        alpha = self.scatter_alpha_slider.value() / 100.0  # Convert to proportion

        df = self.data_df.copy()

        # Ensure x and y are numeric
        if not pd.api.types.is_numeric_dtype(
            df[x_col]
        ) or not pd.api.types.is_numeric_dtype(df[y_col]):
            self.status_bar.showMessage(
                "Warning: Non-numeric columns converted for scatter plot"
            )
            # Convert non-numeric columns
            for col in [x_col, y_col]:
                if not pd.api.types.is_numeric_dtype(df[col]):
                    if len(df[col].unique()) <= 20:  # If not too many categories
                        # Map categories to numbers
                        categories = df[col].unique()
                        mapping = {cat: i for i, cat in enumerate(categories)}
                        df[col] = df[col].map(mapping)
                    else:
                        # Too many categories, use rank
                        df[col] = df[col].rank()

        if group_col:
            # Create a scatter for each group with different colors
            for name, group in df.groupby(group_col):
                ax.scatter(
                    group[x_col], group[y_col], s=point_size, alpha=alpha, label=name
                )
            ax.legend(title=group_col)
        else:
            # Simple scatter plot
            scatter = ax.scatter(
                df[x_col],
                df[y_col],
                s=point_size,
                alpha=alpha,
                color=sns.color_palette(palette, 1)[0],
            )

    def create_pie_chart(self, fig, ax, x_col, y_col, palette):
        """Create a pie chart."""
        # Get pie chart options
        autopct = self.pie_autopct_combo.currentText()
        explode_largest = self.pie_explode_check.isChecked()
        start_angle = self.pie_start_angle_spinner.value()

        # Map autopct options
        if autopct == "None":
            autopct_fmt = None
        elif autopct == "Percentage":
            autopct_fmt = "%1.1f%%"
        elif autopct == "Value":
            autopct_fmt = lambda p: "{:.0f}".format(p * sum(sizes) / 100)
        else:  # Both
            autopct_fmt = lambda p: "{:.0f} ({:.1f}%)".format(p * sum(sizes) / 100, p)

        df = self.data_df.copy()

        # Group by x-axis and aggregate y-axis
        grouped = df.groupby(x_col)[y_col].sum()

        # Limit to top 10 categories if too many
        if len(grouped) > 10:
            self.status_bar.showMessage("Warning: Too many categories. Showing top 10.")
            grouped = grouped.nlargest(10)

        # Get labels and sizes
        labels = grouped.index.tolist()
        sizes = grouped.values.tolist()

        # Create explode values if needed
        explode = None
        if explode_largest:
            explode = [0] * len(sizes)
            largest_idx = sizes.index(max(sizes))
            explode[largest_idx] = 0.1

        # Create pie chart
        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=labels,
            autopct=autopct_fmt,
            explode=explode,
            startangle=start_angle,
            shadow=True,
            colors=sns.color_palette(palette, len(sizes)),
        )

        # Equal aspect ratio ensures pie is drawn as a circle
        ax.axis("equal")

        # Format text labels if they exist
        if autopct_fmt:
            for autotext in autotexts:
                autotext.set_fontsize(9)

        # Shrink text if many categories
        if len(labels) > 5:
            for text in texts:
                text.set_fontsize(8)

    def create_histogram(self, fig, ax, x_col, y_col, group_col, palette):
        """Create a histogram."""
        # Get histogram options
        bins = self.histogram_bins_spinner.value()
        kde = self.histogram_kde_check.isChecked()

        df = self.data_df.copy()

        # For histogram, we primarily care about the x-axis
        # y-axis is ignored for simple histograms

        if group_col:
            # Create histogram for each group
            for name, group in df.groupby(group_col):
                sns.histplot(
                    data=group,
                    x=x_col,
                    bins=bins,
                    kde=kde,
                    ax=ax,
                    label=name,
                    alpha=0.6,
                )
            ax.legend(title=group_col)
        else:
            # Simple histogram
            sns.histplot(
                data=df,
                x=x_col,
                bins=bins,
                kde=kde,
                ax=ax,
                color=sns.color_palette(palette, 1)[0],
            )

    def create_box_plot(self, fig, ax, x_col, y_col, group_col, palette):
        """Create a box plot."""
        # Get box plot options
        notch = self.boxplot_notch_check.isChecked()
        orientation = self.boxplot_orientation_combo.currentText().lower()

        df = self.data_df.copy()

        # Determine x and y based on orientation
        if orientation == "horizontal":
            plot_x = y_col
            plot_y = x_col
        else:
            plot_x = x_col
            plot_y = y_col

        # Create box plot
        if group_col:
            sns.boxplot(
                data=df,
                x=plot_x,
                y=plot_y,
                hue=group_col,
                notch=notch,
                palette=palette,
                ax=ax,
            )
            # Move legend outside if many groups
            if df[group_col].nunique() > 4:
                ax.legend(title=group_col, bbox_to_anchor=(1.05, 1), loc="upper left")
        else:
            sns.boxplot(
                data=df, x=plot_x, y=plot_y, notch=notch, palette=palette, ax=ax
            )

        # Add grid lines for better readability
        ax.grid(True, linestyle="--", alpha=0.7)

    def create_heatmap(self, fig, ax, palette):
        """Create a correlation heatmap."""
        # Get heatmap options
        show_values = self.heatmap_annot_check.isChecked()
        cmap = self.heatmap_cmap_combo.currentText().lower()

        df = self.data_df.copy()

        # Select only numeric columns for correlation
        numeric_df = df.select_dtypes(include=["number"])

        if numeric_df.shape[1] < 2:
            self.status_bar.showMessage("Error: Not enough numeric columns for heatmap")
            ax.text(
                0.5,
                0.5,
                "Not enough numeric columns for correlation analysis",
                horizontalalignment="center",
                verticalalignment="center",
                transform=ax.transAxes,
                fontsize=12,
            )
            return

        # Calculate correlation matrix
        corr_matrix = numeric_df.corr()

        # Create heatmap
        sns.heatmap(
            corr_matrix,
            annot=show_values,
            fmt=".2f",
            cmap=cmap,
            ax=ax,
            vmin=-1,
            vmax=1,
            center=0,
            square=True,
            linewidths=0.5,
        )

        # Rotate axis labels if many columns
        if numeric_df.shape[1] > 5:
            ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right")
            ax.set_yticklabels(ax.get_yticklabels(), rotation=0)

        # Set title
        ax.set_title("Correlation Matrix", fontsize=14)

    def create_area_chart(self, fig, ax, x_col, y_col, group_col, palette):
        """Create an area chart."""
        # Get area chart options
        alpha = self.area_alpha_slider.value() / 100.0  # Convert to proportion
        stacked = self.area_stacked_check.isChecked()

        df = self.data_df.copy()

        # Check if x column could be a date
        if self.column_types.get(x_col) == "date":
            try:
                df[x_col] = pd.to_datetime(df[x_col])
                df = df.sort_values(by=x_col)
            except:
                pass
        # Sort by x-axis values if numeric
        elif self.column_types.get(x_col) == "numeric":
            df = df.sort_values(by=x_col)

        if group_col:
            # Pivot data for area chart
            pivot_df = df.pivot_table(
                index=x_col, columns=group_col, values=y_col, aggfunc="mean"
            )

            # Fill NAs with zeros
            pivot_df = pivot_df.fillna(0)

            # Plot area chart
            pivot_df.plot(
                kind="area", stacked=stacked, alpha=alpha, ax=ax, colormap=palette
            )

            # Add legend
            ax.legend(title=group_col)
        else:
            # For non-grouped area chart, we need to aggregate if there are duplicate x values
            grouped = df.groupby(x_col)[y_col].mean()
            grouped.plot(
                kind="area", alpha=alpha, ax=ax, color=sns.color_palette(palette, 1)[0]
            )

        # Rotate x-axis labels if many
        if df[x_col].nunique() > 5:
            ax.tick_params(axis="x", rotation=45)

    def create_violin_plot(self, fig, ax, x_col, y_col, group_col, palette):
        """Create a violin plot."""
        # Get violin plot options
        inner = self.violin_inner_combo.currentText().lower()
        orientation = self.violin_orientation_combo.currentText().lower()

        df = self.data_df.copy()

        # Determine x and y based on orientation
        if orientation == "horizontal":
            plot_x = y_col
            plot_y = x_col
        else:
            plot_x = x_col
            plot_y = y_col

        # Create violin plot
        if group_col:
            sns.violinplot(
                data=df,
                x=plot_x,
                y=plot_y,
                hue=group_col,
                inner=inner,
                palette=palette,
                ax=ax,
            )
            # Move legend outside if many groups
            if df[group_col].nunique() > 4:
                ax.legend(title=group_col, bbox_to_anchor=(1.05, 1), loc="upper left")
        else:
            sns.violinplot(
                data=df, x=plot_x, y=plot_y, inner=inner, palette=palette, ax=ax
            )

        # Add grid lines for better readability
        ax.grid(True, linestyle="--", alpha=0.7)

    def export_chart(self):
        """Export the current chart to a file."""
        if not hasattr(self, "data_df") or self.data_df is None:
            self.status_bar.showMessage("No chart to export")
            return

        # Open file dialog
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export Chart",
            str(Path.home()),
            "PNG (*.png);;JPEG (*.jpg *.jpeg);;PDF (*.pdf);;SVG (*.svg);;All Files (*)",
        )

        if not file_path:
            return

        try:
            # Get the current figure from the canvas
            canvas_items = [
                item.widget()
                for item in self.chart_layout.children()
                if isinstance(item.widget(), FigureCanvasQTAgg)
            ]

            if not canvas_items:
                self.status_bar.showMessage("No chart to export")
                return

            # Get the first canvas
            canvas = canvas_items[0]
            fig = canvas.figure

            # Save the figure
            fig.savefig(file_path, dpi=300, bbox_inches="tight")

            self.status_bar.showMessage(f"Chart exported to {file_path}")

        except Exception as e:
            self.status_bar.showMessage(f"Error exporting chart: {str(e)}")
            QtWidgets.QMessageBox.critical(
                self, "Export Error", f"Failed to export chart:\n{str(e)}"
            )
