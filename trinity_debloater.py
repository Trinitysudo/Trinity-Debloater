import sys
import ctypes
import json
import subprocess
import os
import logging
import tkinter as tk
from tkinter import messagebox
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget,
                             QVBoxLayout, QLabel, QCheckBox,
                             QPushButton, QScrollArea, QHBoxLayout, QSizePolicy, QSpacerItem,
                             QGridLayout, QComboBox)
from PyQt6.QtGui import QPalette, QColor, QFont, QPixmap, QIcon, QLinearGradient, QBrush, QPainter
from PyQt6.QtCore import Qt, QPoint, QRect
import threading

# --- Logging Configuration ---
logging.basicConfig(filename='trinity_debloater.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logging.info("Trinity Debloater started.")

def is_admin():
    """Check if the script is running with administrative privileges"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

class TrinityDebloaterGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon(self.get_resource_path("assets/trinity_icon.ico")))
        self.setWindowTitle("Trinity Debloater")
        self.setGeometry(100, 100, 900, 700)

        # --- Dark Modern Color Scheme ---
        self.base_bg_color = "#121212"
        self.card_bg_color = "#1E1E1E"
        self.overlay_color = "#2D2D2D"
        self.base_text_color = "#FFFFFF"
        self.secondary_text_color = "#B3B3B3"
        self.accent_color = "#507EFE"
        self.accent_secondary = "#7C9FFF"
        self.item_bg_color = "rgba(255, 255, 255, 0.1)"

        # --- Set Application Stylesheet ---
        self.setStyleSheet(f""" /* Stylesheet - No Changes Needed Here */
            QMainWindow {{
                background-color: {self.base_bg_color};
            }}
             QTabWidget::pane {{ /* The tab widget frame */
                border: none;
                background-color: {self.base_bg_color};
            }}
            QTabWidget::tab-bar {{
                alignment: center;
            }}
            QTabBar::tab {{
                background-color: rgba(255, 255, 255, 0.05);
                color: {self.secondary_text_color};
                border: none;
                padding: 10px 30px;
                margin: 4px;
                border-radius: 8px;
                font-size: 12pt;
                font-weight: bold;
            }}
            QTabBar::tab:selected {{
                background-color: rgba(80, 126, 254, 0.2);
                color: {self.accent_color};
                border-bottom: 2px solid {self.accent_color};
            }}
            QTabBar::tab:hover {{
                background-color: rgba(255, 255, 255, 0.1);
            }}
            QLabel {{
                color: {self.base_text_color};
            }}
            QPushButton {{
                background-color: {self.accent_color};
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 11pt;
                color: white;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #3A6EEF;
            }}
            QPushButton:pressed {{
                background-color: #2A5EDF;
            }}
            QPushButton:disabled {{
                background-color: #5D5D5D;
                color: #8D8D8D;
            }}
            QCheckBox {{
                spacing: 6px;
                margin-left: 0px;
                padding-left: 0px;
                margin-right: 6px;
                font-size: 10pt;
                color: {self.base_text_color};
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 4px;
            }}
            QCheckBox::indicator:unchecked {{
                border: 1px solid rgba(255, 255, 255, 0.3);
                background-color: rgba(30, 30, 30, 0.7);
            }}
            QCheckBox::indicator:checked {{
                border: 1px solid {self.accent_color};
                background-color: {self.accent_color};
            }}
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            QScrollArea > QWidget > QWidget {{
                background-color: {self.card_bg_color};
                border-radius: 12px;
            }}
            QScrollBar:vertical {{
                background-color: rgba(255, 255, 255, 0.03);
                width: 6px;
                margin: 16px 0 16px 0;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background-color: rgba(255, 255, 255, 0.2);
                min-height: 20px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: rgba(80, 126, 254, 0.5);
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
            }}
            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {{
                width: 0px;
                height: 0px;
                background: none;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
            /* Category headers */
            QLabel[category="true"] {{
                font-size: 14pt;
                font-weight: bold;
                color: {self.base_text_color};
                padding-top: 12px;
                padding-bottom: 6px;
            }}
        """)

        # --- Tab Widget ---
        self.tabs = QTabWidget()

        # --- Apps Tab ---
        self.apps_tab = QWidget()
        self.create_apps_tab_content()
        self.tabs.addTab(self.apps_tab, "Apps")

        # --- Tweaks Tab ---
        self.tweaks_tab = QWidget()
        self.create_tweaks_tab_content()
        self.tabs.addTab(self.tweaks_tab, "Tweaks")

        self.setCentralWidget(self.tabs)

    def create_apps_tab_content(self):
        logging.info("Creating Apps tab content.")
        apps_layout = QVBoxLayout(self.apps_tab)
        self.app_checkboxes = {}
        self.app_data_categories = {}
        self.load_app_list()

        # Header section with a more prominent title
        header_layout = QHBoxLayout()
        header_label = QLabel("Select Apps to Install")
        header_label.setStyleSheet(f"""
            font-size: 18pt;
            font-weight: bold;
            margin-bottom: 16px;
            color: {self.base_text_color};
        """)
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        apps_layout.addLayout(header_layout)

        # Create a stylish scroll area for the apps
        apps_scroll_area = QScrollArea()
        apps_scroll_area.setWidgetResizable(True)
        apps_scroll_content = QWidget()
        apps_scroll_content.setContentsMargins(15, 15, 15, 15)
        main_layout = QVBoxLayout(apps_scroll_content)
        main_layout.setSpacing(12)
        apps_scroll_area.setWidget(apps_scroll_content)
        apps_layout.addWidget(apps_scroll_area)

        row = 0
        col = 0

        # Iterate through categories and apps, adding headings and checkboxes
        for category_name, apps in self.app_data_categories.items():
            # Category container with its own layout
            category_container = QWidget()
            category_container.setStyleSheet(f"""
                background-color: rgba(40, 40, 40, 0.7);
                border-radius: 12px;
                margin: 6px;
            """)
            category_layout = QVBoxLayout(category_container)
            category_layout.setContentsMargins(15, 10, 15, 15)

            # Category label with a specific property for styling
            category_label = QLabel(f"{category_name}")
            category_label.setProperty("category", "true")
            category_layout.addWidget(category_label)

            # Add a horizontal line with gradient
            line = QWidget()
            line.setFixedHeight(1)
            line.setStyleSheet(f"""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                          stop:0 {self.accent_color},
                                          stop:1 rgba(80, 126, 254, 0.1));
            """)
            category_layout.addWidget(line)

            # Grid layout for apps in this category
            apps_grid = QGridLayout()
            apps_grid.setSpacing(8)

            # Sort apps alphabetically by display name
            sorted_apps = sorted(apps, key=lambda x: x.get("display_name", "").lower())

            # Add checkboxes for apps in this category
            row, col = 0, 0
            max_cols = 4  # 4 columns looks better in dark theme

            for app_info in sorted_apps:
                app_name = app_info.get("name", "Unknown App")
                display_name = app_info.get("display_name")
                winget_id = app_info.get("winget_id")
                logo_filename = app_info.get("logo")

                if winget_id:
                    checkbox_text = display_name if display_name else app_name

                    # Create a container for each app item with a glass-like effect
                    app_item = QWidget()
                    app_item.setStyleSheet(f""" /* App item styling - No changes needed */
                        QWidget {{
                            background-color: rgba(255, 255, 255, 0.07);
                            border-radius: 8px;
                            padding: 8px;
                        }}
                        QWidget:hover {{
                            background-color: rgba(255, 255, 255, 0.12);
                            border: 1px solid rgba(80, 126, 254, 0.3);
                        }}
                    """)
                    app_layout = QHBoxLayout(app_item)
                    app_layout.setContentsMargins(8, 8, 8, 8)

                    logo_label = QLabel()
                    if logo_filename:
                        logo_path = self.get_resource_path(os.path.join("assets", logo_filename))
                        logo_pixmap = QPixmap(logo_path).scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        logo_label.setPixmap(logo_pixmap)
                    else:
                        # Default app icon placeholder
                        logo_label.setText("📱")
                        logo_label.setStyleSheet("font-size: 16pt; margin-right: 4px;")

                    checkbox = QCheckBox(checkbox_text)
                    checkbox.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

                    # Store checkbox and app info
                    self.app_checkboxes[app_name] = {
                        'checkbox': checkbox,
                        'winget_id': winget_id,
                        'logo_label': logo_label
                    }

                    app_layout.addWidget(logo_label)
                    app_layout.addWidget(checkbox)

                    apps_grid.addWidget(app_item, row, col)
                    col += 1
                    if col >= max_cols:
                        col = 0
                        row += 1

            category_layout.addLayout(apps_grid)
            main_layout.addWidget(category_container)

        # Add a bottom action section with a floating action button style
        action_container = QWidget()
        action_container.setStyleSheet(f"""
            background-color: rgba(30, 30, 30, 0.7);
            border-radius: 12px;
            margin-top: 10px;
        """)
        action_layout = QHBoxLayout(action_container)

        self.install_button = QPushButton("Install Selected Apps")
        self.install_button.setMinimumHeight(48)
        self.install_button.setMinimumWidth(200)
        self.install_button.setStyleSheet(f""" /* Install button styling - No changes needed */
            QPushButton {{
                background-color: {self.accent_color};
                border-radius: 30px;
                padding: 12px 30px;
                font-weight: bold;
                font-size: 12pt;
                color: white;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #3A6EEF;
                box-shadow: 0 4px 12px rgba(80, 126, 254, 0.4);
            }}
            QPushButton:pressed {{
                background-color: #2A5EDF;
            }}
        """)
        self.install_button.clicked.connect(self.install_selected_apps)

        action_layout.addStretch()
        action_layout.addWidget(self.install_button)
        action_layout.addStretch()

        apps_layout.addWidget(action_container)

    def create_tweaks_tab_content(self):
        logging.info("Creating Tweaks tab content with Chris Titus standard tweaks.")
        tweaks_layout = QVBoxLayout(self.tweaks_tab)
        self.tweak_checkboxes = {}  # Store tweak checkboxes

        # Load Chris Titus standard tweaks
        standard_tweaks = self.load_chris_titus_tweaks()

        # Header for Tweaks Tab
        header_layout = QHBoxLayout()
        header_label = QLabel("Chris Titus Standard Tweaks")
        header_label.setStyleSheet(f"""
            font-size: 18pt;
            font-weight: bold;
            margin-bottom: 16px;
            color: {self.base_text_color};
        """)
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        tweaks_layout.addLayout(header_layout)

        # Create a scroll area for tweaks
        tweaks_scroll_area = QScrollArea()
        tweaks_scroll_area.setWidgetResizable(True)
        tweaks_scroll_content = QWidget()
        tweaks_scroll_content.setContentsMargins(15, 15, 15, 15)

        # Main layout for the tweaks content
        main_layout = QVBoxLayout(tweaks_scroll_content)
        main_layout.setSpacing(12)
        tweaks_scroll_area.setWidget(tweaks_scroll_content)
        tweaks_layout.addWidget(tweaks_scroll_area)

        # Group tweaks by category for better organization
        tweaks_by_category = {}
        for tweak in standard_tweaks:
            category = tweak.get("Category", "Miscellaneous")
            if category not in tweaks_by_category:
                tweaks_by_category[category] = []
            tweaks_by_category[category].append(tweak)

        # Create sections for each category
        for category_name, tweaks in tweaks_by_category.items():
            # Category container
            category_container = QWidget()
            category_container.setStyleSheet(f"""
                background-color: rgba(40, 40, 40, 0.7);
                border-radius: 12px;
                margin: 6px;
            """)
            category_layout = QVBoxLayout(category_container)
            category_layout.setContentsMargins(15, 10, 15, 15)

            # Category label
            category_label = QLabel(f"{category_name}")
            category_label.setProperty("category", "true")
            category_layout.addWidget(category_label)

            # Add a horizontal line with gradient
            line = QWidget()
            line.setFixedHeight(1)
            line.setStyleSheet(f"""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                          stop:0 {self.accent_color},
                                          stop:1 rgba(80, 126, 254, 0.1));
            """)
            category_layout.addWidget(line)

            # Add tweaks for this category
            for tweak in tweaks:
                tweak_name = tweak.get("Name", "Unknown Tweak")
                tweak_description = tweak.get("Description", "No description available")

                # Tweak container
                tweak_item = QWidget()
                tweak_item.setStyleSheet(f"""
                    QWidget {{
                        background-color: rgba(255, 255, 255, 0.07);
                        border-radius: 8px;
                        padding: 8px;
                        margin-bottom: 4px;
                    }}
                    QWidget:hover {{
                        background-color: rgba(255, 255, 255, 0.12);
                        border: 1px solid rgba(80, 126, 254, 0.3);
                    }}
                """)
                tweak_layout = QVBoxLayout(tweak_item)
                tweak_layout.setContentsMargins(10, 10, 10, 10)

                # Tweak checkbox
                checkbox = QCheckBox(tweak_name)
                checkbox.setStyleSheet("font-weight: bold; font-size: 11pt;")

                # Description label
                description_label = QLabel(tweak_description)
                description_label.setStyleSheet(f"color: {self.secondary_text_color}; font-size: 9pt;")
                description_label.setWordWrap(True)

                tweak_layout.addWidget(checkbox)
                tweak_layout.addWidget(description_label)

                # Store the checkbox and tweak info
                self.tweak_checkboxes[tweak_name] = {
                    'checkbox': checkbox,
                    'tweak_info': tweak
                }

                category_layout.addWidget(tweak_item)

            # Add the category to the main layout
            main_layout.addWidget(category_container)

        # Add a button container at the bottom
        action_container = QWidget()
        action_container.setStyleSheet(f"""
            background-color: rgba(30, 30, 30, 0.7);
            border-radius: 12px;
            margin-top: 10px;
            padding: 10px;
        """)
        action_layout = QHBoxLayout(action_container)

        # Select All button
        select_all_button = QPushButton("Select All")
        select_all_button.setMinimumHeight(40)
        select_all_button.setMinimumWidth(120)
        select_all_button.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(80, 126, 254, 0.7);
                border-radius: 20px;
                padding: 8px 20px;
                font-weight: bold;
                font-size: 11pt;
                color: white;
                border: none;
            }}
            QPushButton:hover {{
                background-color: rgba(80, 126, 254, 0.9);
            }}
            QPushButton:pressed {{
                background-color: rgba(80, 126, 254, 1.0);
            }}
        """)
        select_all_button.clicked.connect(self.select_all_tweaks)

        # Deselect All button
        deselect_all_button = QPushButton("Deselect All")
        deselect_all_button.setMinimumHeight(40)
        deselect_all_button.setMinimumWidth(120)
        deselect_all_button.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(100, 100, 100, 0.7);
                border-radius: 20px;
                padding: 8px 20px;
                font-weight: bold;
                font-size: 11pt;
                color: white;
                border: none;
            }}
            QPushButton:hover {{
                background-color: rgba(100, 100, 100, 0.9);
            }}
            QPushButton:pressed {{
                background-color: rgba(100, 100, 100, 1.0);
            }}
        """)
        deselect_all_button.clicked.connect(self.deselect_all_tweaks)

        # Apply Tweaks button - FIX: Create the button variable first, then set its style
        apply_tweaks_button = QPushButton("Apply Selected Tweaks")
        apply_tweaks_button.setMinimumHeight(48)
        apply_tweaks_button.setMinimumWidth(200)
        apply_tweaks_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.accent_color};
                border-radius: 30px;
                padding: 12px 30px;
                font-weight: bold;
                font-size: 12pt;
                color: white;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #3A6EEF;
                box-shadow: 0 4px 12px rgba(80, 126, 254, 0.4);
            }}
            QPushButton:pressed {{
                background-color: #2A5EDF;
            }}
        """)
        apply_tweaks_button.clicked.connect(self.apply_selected_tweaks)

        # Add buttons to the action layout
        action_layout.addWidget(select_all_button)
        action_layout.addWidget(deselect_all_button)
        action_layout.addStretch()
        action_layout.addWidget(apply_tweaks_button)

        tweaks_layout.addWidget(action_container)

    def select_all_tweaks(self):
        """Select all tweaks in the tweaks tab"""
        for tweak_data in self.tweak_checkboxes.values():
            tweak_data['checkbox'].setChecked(True)
        logging.info("All tweaks selected")

    def deselect_all_tweaks(self):
        """Deselect all tweaks in the tweaks tab"""
        for tweak_data in self.tweak_checkboxes.values():
            tweak_data['checkbox'].setChecked(False)
        logging.info("All tweaks deselected")

    def load_app_list(self):
        """Load application list from JSON file"""
        try:
            app_list_path = self.get_resource_path("apps/app_list.json")
            logging.info(f"Loading app list from: {app_list_path}")
            print(f"Debug: Attempting to load app list from: {app_list_path}") # Debug print

            with open(app_list_path, 'r') as f:
                app_data = json.load(f)

            logging.info(f"Debug: Type of app_data after json.load: {type(app_data)}") # Log the type
            logging.info(f"Debug: Content of app_data: {app_data}") # Log the content (be mindful of large output)

            # Access the "Apps" key to get the categories dictionary
            self.app_data_categories = app_data["Apps"]  # <-- Access the inner "Apps" dictionary
            logging.info(f"Successfully loaded {len(self.app_data_categories)} app categories") # Use self.app_data_categories here
        except Exception as e:
            logging.error(f"Error loading app list: {str(e)}")
            messagebox.showerror("Error", f"Failed to load app list: {str(e)}")

    def load_chris_titus_tweaks(self):
        """Load Chris Titus standard tweaks from JSON file"""
        try:
            tweaks_path = self.get_resource_path("config/chris_titus_standard_tweaks.json")
            logging.info(f"Loading Chris Titus standard tweaks from: {tweaks_path}")
            print(f"Debug: Attempting to load tweaks from: {tweaks_path}") # Debug print

            with open(tweaks_path, 'r') as f:
                tweaks_data = json.load(f)

            logging.info(f"Debug: Type of tweaks_data after json.load: {type(tweaks_data)}") # Log type of tweaks_data
            logging.info(f"Debug: Content of tweaks_data (first 50 chars): {str(tweaks_data)[:50]}...") # Log first part of content

            # Process the tweaks data to fit our format
            processed_tweaks = []

            for tweak in tweaks_data["Tweaks"]:  # <--- CORRECTED LINE: Iterate over tweaks_data["Tweaks"] (the list)
                logging.info(f"Debug: Type of tweak in loop: {type(tweak)}") # Log type of 'tweak' in loop
                # Extract and format each tweak
                processed_tweak = {
                    "Name": tweak.get("Name", "Unnamed Tweak"), # Error likely happening in one of these .get() calls
                    "Description": tweak.get("Description", "No description available"),
                    "Category": tweak.get("Category", "General"),
                    "Command": tweak.get("Command", ""),
                    "Registry": tweak.get("Registry", None)
                }
                processed_tweaks.append(processed_tweak)

            logging.info(f"Successfully loaded {len(processed_tweaks)} Chris Titus standard tweaks")
            return processed_tweaks
        except Exception as e:
            logging.error(f"Error loading Chris Titus standard tweaks: {str(e)}")
            messagebox.showerror("Error", f"Failed to load Chris Titus standard tweaks: {str(e)}")
            return []

    def install_selected_apps(self):
        """Install selected applications using winget"""
        selected_apps = []
        for app_name, app_data in self.app_checkboxes.items():
            if app_data['checkbox'].isChecked():
                selected_apps.append({
                    'name': app_name,
                    'winget_id': app_data['winget_id']
                })

        if not selected_apps:
            messagebox.showinfo("No Selection", "No apps selected for installation.")
            return

        # Confirm installation
        apps_str = "\n".join([f"• {app['name']}" for app in selected_apps])
        confirm = messagebox.askyesno("Confirm Installation",
                                    f"Do you want to install the following apps?\n\n{apps_str}")

        if confirm:
            logging.info(f"Starting installation of {len(selected_apps)} apps")

            # Disable the install button during installation
            self.install_button.setEnabled(False)
            self.install_button.setText("Installing...")

            # Create and start installation thread
            install_thread = threading.Thread(target=self._run_installations, args=(selected_apps,))
            install_thread.daemon = True
            install_thread.start()

    def _run_installations(self, selected_apps):
        """Run installation tasks in a separate thread"""
        successful = []
        failed = []

        for app in selected_apps:
            try:
                app_name = app['name']
                winget_id = app['winget_id']
                logging.info(f"Installing {app_name} ({winget_id})")

                # Install the app using winget
                result = self.install_app_winget(winget_id)

                if result:
                    logging.info(f"Successfully installed {app_name}")
                    successful.append(app_name)
                else:
                    logging.error(f"Failed to install {app_name}")
                    failed.append(app_name)
            except Exception as e:
                logging.error(f"Error installing {app['name']}: {str(e)}")
                failed.append(app['name'])

        # Update UI on the main thread
        QApplication.instance().postEvent(self, QApplication.endEvent())

        # Show results
        if successful:
            successful_str = "\n".join([f"• {app}" for app in successful])
            messagebox.showinfo("Installation Complete",
                              f"Successfully installed {len(successful)} apps:\n\n{successful_str}")

        if failed:
            failed_str = "\n".join([f"• {app}" for app in failed])
            messagebox.showwarning("Installation Issues",
                                 f"Failed to install {len(failed)} apps:\n\n{failed_str}")

        # Re-enable the install button
        self.install_button.setEnabled(True)
        self.install_button.setText("Install Selected Apps")

    def install_app_winget(self, winget_id):
        """Install an app using winget command line"""
        try:
            # Run winget install command with accept licenses and silent flags
            command = ['winget', 'install', '-e', '--id', winget_id, '--accept-source-agreements', '--accept-package-agreements', '--silent']
            result = subprocess.run(command, capture_output=True, text=True)

            # Log the output
            logging.info(f"Winget command: {' '.join(command)}")
            logging.info(f"Winget stdout: {result.stdout}")

            if result.returncode != 0:
                logging.error(f"Winget stderr: {result.stderr}")
                return False

            return True
        except Exception as e:
            logging.error(f"Exception during app installation: {str(e)}")
            return False

    def apply_selected_tweaks(self):
        """Apply selected tweaks from the tweaks tab"""
        selected_tweaks = []
        for tweak_name, tweak_data in self.tweak_checkboxes.items():
            if tweak_data['checkbox'].isChecked():
                selected_tweaks.append({
                    'name': tweak_name,
                    'tweak_info': tweak_data['tweak_info']
                })

        if not selected_tweaks:
            messagebox.showinfo("No Selection", "No tweaks selected to apply.")
            return

        # Confirm application
        tweaks_str = "\n".join([f"• {tweak['name']}" for tweak in selected_tweaks])
        confirm = messagebox.askyesno("Confirm Apply Tweaks",
                                    f"Do you want to apply the following tweaks?\n\n{tweaks_str}\n\nThis may require administrator privileges.")

        if confirm:
            logging.info(f"Starting application of {len(selected_tweaks)} tweaks")

            # Create and start application thread
            apply_thread = threading.Thread(target=self._run_tweak_applications, args=(selected_tweaks,))
            apply_thread.daemon = True
            apply_thread.start()
    def _run_tweak_applications(self, selected_tweaks):
        """Run tweak applications in a separate thread"""
        successful = []
        failed = []

        for tweak in selected_tweaks:
            try:
                tweak_name = tweak['name']
                tweak_info = tweak['tweak_info']
                logging.info(f"Applying tweak: {tweak_name}")

                # Check if the tweak has a command to run
                if 'Command' in tweak_info and tweak_info['Command']:
                    # Execute the command
                    result = self.run_powershell_command(tweak_info['Command'])
                    if result:
                        logging.info(f"Successfully applied command tweak: {tweak_name}")
                        successful.append(tweak_name)
                    else:
                        logging.error(f"Failed to apply command tweak: {tweak_name}")
                        failed.append(tweak_name)

                # Check if the tweak has registry modifications
                if 'Registry' in tweak_info and tweak_info['Registry']:
                    # Apply registry tweaks
                    registry_success = self.apply_registry_tweaks(tweak_info['Registry'])
                    if registry_success:
                        logging.info(f"Successfully applied registry tweak: {tweak_name}")
                        if tweak_name not in successful:  # Avoid duplicates
                            successful.append(tweak_name)
                    else:
                        logging.error(f"Failed to apply registry tweak: {tweak_name}")
                        if tweak_name not in failed:  # Avoid duplicates
                            failed.append(tweak_name)

            except Exception as e:
                logging.error(f"Error applying tweak {tweak['name']}: {str(e)}")
                failed.append(tweak['name'])

        # Show results
        if successful:
            successful_str = "\n".join([f"• {tweak}" for tweak in successful])
            messagebox.showinfo("Tweaks Applied",
                              f"Successfully applied {len(successful)} tweaks:\n\n{successful_str}")

        if failed:
            failed_str = "\n".join([f"• {tweak}" for tweak in failed])
            messagebox.showwarning("Tweak Application Issues",
                                 f"Failed to apply {len(failed)} tweaks:\n\n{failed_str}")

    def run_powershell_command(self, command):
        """Run a PowerShell command"""
        try:
            # Execute PowerShell command
            result = subprocess.run(
                ["powershell", "-Command", command],
                capture_output=True,
                text=True,
                check=False  # Don't raise an exception on non-zero exit
            )

            # Log the output
            logging.info(f"PowerShell command: {command}")
            logging.info(f"PowerShell stdout: {result.stdout}")

            if result.returncode != 0:
                logging.error(f"PowerShell stderr: {result.stderr}")
                return False

            return True
        except Exception as e:
            logging.error(f"Exception running PowerShell command: {str(e)}")
            return False

    def apply_registry_tweaks(self, registry_settings):
        """Apply registry modifications"""
        try:
            success = True
            for reg_item in registry_settings:
                path = reg_item.get("Path", "")
                name = reg_item.get("Name", "")
                value = reg_item.get("Value", "")
                value_type = reg_item.get("Type", "REG_DWORD")

                logging.info(f"Applying registry tweak: {path}\\{name} = {value} ({value_type})")

                # Convert the value_type to PowerShell-compatible format
                ps_value_type = self.convert_reg_type(value_type)

                # Build the PowerShell command
                if value_type in ["REG_SZ", "REG_EXPAND_SZ"]:
                    # String values need quotes
                    command = f'New-Item -Path "Registry::{path}" -Force -ErrorAction SilentlyContinue | Out-Null; Set-ItemProperty -Path "Registry::{path}" -Name "{name}" -Value "{value}" -Type {ps_value_type}'
                else:
                    # Numeric values don't need quotes
                    command = f'New-Item -Path "Registry::{path}" -Force -ErrorAction SilentlyContinue | Out-Null; Set-ItemProperty -Path "Registry::{path}" -Name "{name}" -Value {value} -Type {ps_value_type}'

                # Execute the PowerShell command
                result = self.run_powershell_command(command)
                if not result:
                    success = False
                    logging.error(f"Failed to apply registry setting: {path}\\{name}")

            return success
        except Exception as e:
            logging.error(f"Exception applying registry tweaks: {str(e)}")
            return False

    def convert_reg_type(self, reg_type):
        """Convert registry type to PowerShell compatible format"""
        type_mapping = {
            "REG_SZ": "String",
            "REG_EXPAND_SZ": "ExpandString",
            "REG_BINARY": "Binary",
            "REG_DWORD": "DWord",
            "REG_QWORD": "QWord",
            "REG_MULTI_SZ": "MultiString"
        }
        return type_mapping.get(reg_type, "String")

    def get_resource_path(self, relative_path):
        """Get the absolute path to a resource file, works for development and for PyInstaller"""
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
            return os.path.join(base_path, relative_path)
        except Exception as e:
            logging.error(f"Error finding resource path: {str(e)}")
            return os.path.join(os.path.abspath(os.path.dirname(__file__)), relative_path)

    def closeEvent(self, event):
        """Handle application close event"""
        logging.info("Trinity Debloater closing.")
        event.accept()


def main():
    # Check for administrative privileges
    if not is_admin():
        # Show warning about admin rights
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        messagebox.showwarning("Administrator Rights Required",
                               "Some features of Trinity Debloater require administrator rights.\n\n"
                               "It is recommended to run this application as administrator.")
        root.destroy()

    # Create and run the application
    app = QApplication(sys.argv)
    window = TrinityDebloaterGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()