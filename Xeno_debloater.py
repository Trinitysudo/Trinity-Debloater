import sys
import tkinter as tk
import ctypes
import json
import subprocess
import os
import logging
from tkinter import messagebox
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget,
                             QVBoxLayout, QLabel, QCheckBox,
                             QPushButton, QScrollArea, QHBoxLayout, QSizePolicy, QSpacerItem,
                             QGridLayout, QComboBox)
from PyQt6.QtGui import QPalette, QColor, QFont, QPixmap, QIcon, QLinearGradient, QBrush, QPainter, QDesktopServices
from PyQt6.QtCore import Qt, QPoint, QRect, QEvent, QObject, QUrl
import threading
import shutil
from ctypes.wintypes import HWND, HINSTANCE, LPCWSTR, INT, UINT, DWORD, WORD, MAX_PATH, ULONG, LPVOID, HKEY, HANDLE

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

# --- ctypes definitions for ShellExecuteEx (if still needed later) ---
from ctypes import windll, Structure, POINTER, WINFUNCTYPE, c_wchar_p, c_int, c_uint, sizeof, byref
# ... (SHELLEXECUTEINFO, ULONG, LPVOID, HKEY, HANDLE, SEE_MASK_NOCLOSEPROCESS, SW_SHOWNORMAL, ERROR_CANCELLED remain as before)
class SHELLEXECUTEINFO(Structure):
    _fields_ = [
        ('cbSize', DWORD),
        ('fMask', ULONG),
        ('hwnd', HWND),
        ('lpVerb', LPCWSTR),
        ('lpFile', LPCWSTR),
        ('lpParameters', LPCWSTR),
        ('lpDirectory', LPCWSTR),
        ('nShow', INT),
        ('hInstApp', HINSTANCE),
        ('lpIDList', LPVOID),
        ('lpClass', LPCWSTR),
        ('hkeyClass', HKEY),
        ('dwHotKey', DWORD),
        ('hIcon', HANDLE),
        ('hProcess', HANDLE),
    ]
    def __init__(self, **kwargs):
        super().__init__()
        self.cbSize = sizeof(self)
        for key, value in kwargs.items():
            setattr(self, key, value)

ULONG = DWORD
LPVOID = POINTER(None)
HKEY = LPVOID
HANDLE = LPVOID

SEE_MASK_NOCLOSEPROCESS = 0x00000040
SW_SHOWNORMAL = 1
ERROR_CANCELLED = 1223  # Operation was canceled by user


# Custom event types for UI updates (threads)
class InstallCompleteEvent(QEvent):
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())
    def __init__(self, successful, failed):
        super().__init__(InstallCompleteEvent.EVENT_TYPE)
        self.successful = successful
        self.failed = failed

class TweakCompleteEvent(QEvent):
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())
    def __init__(self, successful, failed):
        super().__init__(TweakCompleteEvent.EVENT_TYPE)
        self.successful = successful
        self.failed = failed

class TrinityDebloaterGUI(QMainWindow):
    def get_resource_path(self, relative_path):
      """Get absolute path to resource, works for dev and for PyInstaller"""
      try:
          base_path = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
          return os.path.join(base_path, relative_path)
      except Exception as e:
          logging.error(f"Error finding resource path: {str(e)}")
          return os.path.join(os.path.abspath(os.path.dirname(__file__)), relative_path)

    def install_selected_apps(self):
        """Install selected applications using winget."""
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
            # Run installation in a separate thread
            install_thread = threading.Thread(target=self._run_installations, args=(selected_apps,))
            install_thread.daemon = True
            install_thread.start()

    def _run_installations(self, selected_apps):
        """Run installation tasks in a separate thread."""
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

        # Update UI on the main thread *after* all installations are done
        QApplication.instance().postEvent(self, InstallCompleteEvent(successful, failed))


    def install_app_winget(self, winget_id):
        """Install an app using winget command line"""
        try:
            # Run winget install command with accept licenses and silent flags
            command = ['winget', 'install', '-e', '--id', winget_id,  '--accept-source-agreements', '--accept-package-agreements', '--silent']
            result = subprocess.run(command, capture_output=True, text=True, check=False) # Added check=False

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

    def apply_sleek_minimal(self): # corrected indentation
        logging.info("Applying Sleek Minimal appearance theme.")
        successful_tweaks = [] # Initialize lists to track tweak status
        failed_tweaks = []

        try:
            # 1. TranslucentTB Handling
            if not self.start_translucent_tb(): # Try to start, if fails, try fallback
                logging.warning("Failed to start TranslucentTB from default paths. Attempting fallback: Uninstall and reinstall via winget.")
                failed_tweaks.append("TranslucentTB Start Failed (Initial)")

                # --- Fallback: Uninstall and Reinstall TranslucentTB ---
                uninstall_success = self.uninstall_translucent_tb_winget() # Attempt uninstall via winget first
                if uninstall_success:
                    logging.info("TranslucentTB uninstalled successfully (fallback).")
                    install_success = self.install_translucent_tb() # Reinstall via winget
                    if install_success:
                        logging.info("TranslucentTB reinstalled successfully via winget (fallback).")
                        if self.start_translucent_tb(): # Try to start again after reinstall
                            successful_tweaks.append("TranslucentTB Started (Fallback)")
                        else:
                            failed_tweaks.append("TranslucentTB Start Failed (Fallback Reinstall)")
                            messagebox.showerror("TranslucentTB Start Failed",
                                                 "Failed to start TranslucentTB even after reinstalling. \n"
                                                 "Please check the logs and ensure TranslucentTB is working correctly.")
                    else:
                        failed_tweaks.append("TranslucentTB Reinstall Failed (Fallback)")
                        messagebox.showerror("TranslucentTB Reinstall Failed",
                                             "Failed to reinstall TranslucentTB via winget. \n"
                                             "Please check your internet connection and winget installation.")
                else:
                    failed_tweaks.append("TranslucentTB Uninstall Failed (Fallback)")
                    messagebox.showerror("TranslucentTB Uninstall Failed",
                                         "Failed to uninstall TranslucentTB. This is needed for reinstall fallback. \n"
                                         "Please try uninstalling TranslucentTB manually and try again.")

            else:
                successful_tweaks.append("TranslucentTB Started")

            # 2. Unpin Start Menu Tiles - Using Provided Command
            ps_command_unpin_start = """
            Get-StartApps | ForEach-Object { Start-Process "shell:AppsFolder\\$_.AppID" -ArgumentList "/unpinfromstart" -NoNewWindow -PassThru }
            """
            if self.run_powershell_command(ps_command_unpin_start):
                successful_tweaks.append("Start Menu Tiles Unpinned")
            else:
                failed_tweaks.append("Start Menu Tiles Unpin Failed")

            # 3. Set Background (already working)
            background_path = self.get_resource_path("assets/Xeno_Debloater.png")
            ps_command_background = f"""
            $Path = '{background_path}';
            $WallpaperStyle = 'Fill';
            Set-ItemProperty -Path 'HKCU:\\Control Panel\\Desktop' -Name Wallpaper -Value $Path;
            Set-ItemProperty -Path 'HKCU:\\Control Panel\\Desktop' -Name WallpaperStyle -Value 2;
            Set-ItemProperty -Path 'HKCU:\\Control Panel\\Desktop' -Name TileWallpaper -Value 0;
            [System.Runtime.InteropServices.DllImport("user32.dll", SetLastError = True, CharSet = System.Runtime.InteropServices.CharSet.Auto)]
            [int]$SPI_SETDESKWALLPAPER = 20;
            [int]$SPIF_UPDATEINIFILE = 0x01;
            [int]$SPIF_SENDWININICHANGE = 0x02;
            public static extern bool SystemParametersInfo(int uAction, int uParam, string lpvParam, int fuWinIni);
            [TrinityDebloaterGUI]::SystemParametersInfo($SPI_SETDESKWALLPAPER, 0, $Path, $SPIF_UPDATEINIFILE -bor $SPIF_SENDWININICHANGE);
            """
            if self.run_powershell_command(ps_command_background):
                successful_tweaks.append("Background Set")
            else:
                failed_tweaks.append("Background Set Failed")

            # 4. Hide Desktop Icons (already working)
            ps_command_hide_icons = "Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced' -Name HideIcons -Value 1"
            if self.run_powershell_command(ps_command_hide_icons):
                successful_tweaks.append("Hide Desktop Icons")
            else:
                failed_tweaks.append("Hide Desktop Icons Failed")

            # 5. Restart Explorer to Apply Icon Changes Immediately
            ps_command_restart_explorer = "Stop-Process -Name explorer -Force ; Start-Process explorer"
            if self.run_powershell_command(ps_command_restart_explorer):
                successful_tweaks.append("Explorer Restarted")
            else:
                failed_tweaks.append("Explorer Restart Failed")

            # 6. Set Dark Mode - Using Settings App
            messagebox.showinfo("Dark Mode", "Please manually switch to 'Dark' mode in the Settings app that will now open. After setting dark mode, close the Settings app.")
            QDesktopServices.openUrl(QUrl("ms-settings:colors")) # Open Colors Settings Page
            successful_tweaks.append("Dark Mode Setting Opened (Manual)") # Track as successful - manual step
            # No automated dark mode setting anymore

            # 7. Remove Taskbar Items (Widgets, Task View, Search) (already working)
            ps_command_taskbar = """
            Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced' -Name ShowTaskViewButton -Value 0;
            Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Search' -Name SearchboxTaskbarMode -Value 0; # Icon Only
            """
            if self.run_powershell_command(ps_command_taskbar):
                successful_tweaks.append("Taskbar Items Removed")
            else:
                failed_tweaks.append("Taskbar Items Remove Failed")

            # 8. Remove OneDrive Icon (Requires knowing the exact registry key name, may vary) (already working)
            ps_command_onedrive = """
            if (Test-Path -Path 'HKCU:\\Software\\Classes\\CLSID\\{018D5C66-4533-4307-9E7D-EEA822470300}') {
                Remove-Item -Path 'HKCU:\\Software\\Classes\\CLSID\\{018D5C66-4533-4307-9E7D-EEA822470300}' -Force -Recurse
            } else {
                Write-Host "OneDrive registry key not found. Skipping removal."
            }
            """
            if self.run_powershell_command(ps_command_onedrive):
                successful_tweaks.append("OneDrive Icon Removed")
            else:
                failed_tweaks.append("OneDrive Icon Remove Failed")

            # 9. Set Theme Color to Blue (Standard Blue: #0078D4 - ARGB format) - ENSURE BLUE EVERY TIME
            standard_blue_argb = 0xFF0078D4 # Standard Blue - ENSURE THIS VALUE IS CORRECT
            ps_command_theme_color = f"""
            $DwmKey = 'HKCU:\\Software\\Microsoft\\Windows\\DWM'
            New-Item -Path "Registry::$DwmKey" -ItemType Directory -Force -ErrorAction SilentlyContinue | Out-Null # Ensure key exists
            Set-ItemProperty -Path "Registry::$DwmKey" -Name "ColorizationColor" -Value {standard_blue_argb} -Type DWord
            Set-ItemProperty -Path "Registry::$DwmKey" -Name "AccentColor" -Value {standard_blue_argb} -Type DWord
            Set-ItemProperty -Path "Registry::$DwmKey" -Name "AccentColorInactive" -Value {standard_blue_argb} -Type DWord
            """
            if self.run_powershell_command(ps_command_theme_color):
                successful_tweaks.append("Theme Color Set to Blue")
            else:
                failed_tweaks.append("Theme Color Set to Blue Failed")

            # 10. No more System Dark Mode Setting via Registry - User will set in Settings App


            messagebox.showinfo("Appearance Applied", "Sleek Minimal theme applied successfully (Dark Mode requires manual setting in opened Settings app)!")

        except Exception as e:
            logging.error(f"Error applying Sleek Minimal theme: {str(e)}")
            messagebox.showerror("Error", f"Failed to apply Sleek Minimal theme: {str(e)}")
        finally: # Ensure event is posted even if errors occur
            QApplication.instance().postEvent(self, TweakCompleteEvent(successful_tweaks, failed_tweaks))


    def apply_selected_tweaks(self):
        """Apply selected tweaks from the tweaks tab."""
        selected_tweaks = []
        for tweak_name, tweak_data in self.tweak_checkboxes.items():
            if tweak_data['checkbox'].isChecked():
                selected_tweaks.append(tweak_data['tweak_info'])

        if not selected_tweaks:
            messagebox.showinfo("No Selection", "No tweaks selected to apply.")
            return

        # Confirm tweak application
        tweaks_str = "\n".join([f"• {tweak['Name']}" for tweak in selected_tweaks])
        confirm = messagebox.askyesno("Confirm Tweaks",
                                        f"Do you want to apply the following tweaks?\n\n{tweaks_str}")

        if confirm:
            logging.info(f"Starting application of {len(selected_tweaks)} tweaks")
            # Disable the apply tweaks button during application
            self.apply_tweaks_button.setEnabled(False)
            self.apply_tweaks_button.setText("Applying Tweaks...")
            # Run tweak application in a separate thread
            tweaks_thread = threading.Thread(target=self._run_tweaks, args=(selected_tweaks,))
            tweaks_thread.daemon = True
            tweaks_thread.start()


    def _run_tweaks(self, selected_tweaks):
        """Run tweak application tasks in a separate thread."""
        successful_tweaks = []
        failed_tweaks = []

        for tweak in selected_tweaks:
            tweak_name = tweak['Name']
            try:
                logging.info(f"Applying tweak: {tweak_name}")
                success = False # Assume failure initially

                if "Command" in tweak and tweak["Command"]: # Apply command tweak
                    if self.run_powershell_command(tweak["Command"]):
                        success = True
                    else:
                        logging.error(f"Failed to apply command tweak: {tweak_name}")

                elif "Registry" in tweak and tweak["Registry"]: # Apply registry tweak
                    if self.apply_registry_tweaks([tweak["Registry"]]): # Needs to be a list
                        success = True
                    else:
                        logging.error(f"Failed to apply registry tweak: {tweak_name}")

                elif "Service" in tweak and tweak["Service"]: # Apply service tweak
                    if self.apply_service_tweaks([tweak["Service"]]): # Needs to be a list
                        success = True
                    else:
                        logging.error(f"Failed to apply service tweak: {tweak_name}")
                else:
                    logging.warning(f"No action defined for tweak: {tweak_name}")


                if success:
                    logging.info(f"Successfully applied tweak: {tweak_name}")
                    successful_tweaks.append(tweak_name)
                else:
                    failed_tweaks.append(tweak_name)


            except Exception as e:
                logging.error(f"Error applying tweak {tweak_name}: {str(e)}")
                failed_tweaks.append(tweak_name)

        # Update UI on the main thread *after* all tweaks are done
        QApplication.instance().postEvent(self, TweakCompleteEvent(successful_tweaks, failed_tweaks))


    def apply_service_tweaks(self, service_settings):
        """Apply service startup type changes."""
        try:
            success = True
            for service_item in service_settings:
              service_name = service_item.get("Name", "")
              startup_type = service_item.get("StartupType", "")

              if not service_name or not startup_type:
                logging.warning(f"Skipping incomplete service tweak: {service_name}")
                continue  # Skip to the next service if any info is missing

              logging.info(f"Setting service {service_name} to {startup_type}")
              command = f"Set-Service -Name '{service_name}' -StartupType '{startup_type}'"
              result = self.run_powershell_command(command)

              if not result:
                success = False
                logging.error(f"Failed to set service {service_name} to {startup_type}")
            return success

        except Exception as e:
            logging.error(f"Exception during service tweak application: {str(e)}")
            return False


    def run_powershell_command(self, command):
        """Run a PowerShell command"""
        try:
            # Execute PowerShell command
            result = subprocess.run(
                ["powershell", "-Command", command],
                capture_output=True,
                text=True,
                check=False  # Don't raise an exception on non-zero exit code
            )

            # Log the output
            logging.info(f"PowerShell command: {command}")
            logging.info(f"PowerShell stdout: {result.stdout}")
            logging.debug(f"PowerShell stderr: {result.stderr}") # Log stderr as debug

            if result.returncode != 0:
                logging.warning(f"PowerShell command likely succeeded with warnings, check stderr for details: {result.stderr}") # Changed to warning
                return True # Return True even with non-zero exit, assuming success with warnings

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
                value_type = reg_item.get("Type", "REG_DWORD") # Default to REG_DWORD if type is missing

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
      return type_mapping.get(reg_type, "String") # Default to String if not

    def load_app_list(self):
        """Load application list from JSON file"""
        try:
            app_list_path = self.get_resource_path("apps/app_list.json")
            logging.info(f"Loading app list from: {app_list_path}")

            with open(app_list_path, 'r') as f:
                app_data = json.load(f)

            self.app_data_categories = app_data["Apps"]  # Load categories from 'Apps' key
            logging.info(f"Successfully loaded app categories: {', '.join(self.app_data_categories.keys())}")


        except FileNotFoundError:
            logging.error(f"App list file not found: {app_list_path}")
            messagebox.showerror("Error", "Failed to load app list: File not found.")
            self.app_data_categories = {}  # Set to empty dict to prevent further errors
        except json.JSONDecodeError:
            logging.error(f"Error decoding JSON in app list: {app_list_path}")
            messagebox.showerror("Error", "Failed to load app list: Invalid JSON format.")
            self.app_data_categories = {}
        except Exception as e:
            logging.error(f"Error loading app list: {str(e)}")
            messagebox.showerror("Error", f"Failed to load app list: {str(e)}")
            self.app_data_categories = {} #Ensure its a empty dict

    def load_chris_titus_tweaks(self):
      """Load Chris Titus standard tweaks from JSON file."""
      try:
          tweaks_path = self.get_resource_path("config/chris_titus_standard_tweaks.json")
          logging.info(f"Loading Chris Titus standard tweaks from: {tweaks_path}")

          with open(tweaks_path, 'r') as f:
              tweaks_data = json.load(f)
          processed_tweaks = []
          for tweak in tweaks_data["Tweaks"]:
            processed_tweak = {
                "Name": tweak.get("Name", "Unnamed Tweak"),
                "Description": tweak.get("Description", "No description available"),
                "Category": tweak.get("Category", "General"),
                "Command": tweak.get("Command", ""),
                "Registry": tweak.get("Registry", None),
                "Service": tweak.get("Service", None)  # Include the Service key
              }
            processed_tweaks.append(processed_tweak)

          logging.info(f"Successfully loaded {len(processed_tweaks)} Chris Titus standard tweaks")
          return processed_tweaks
      except FileNotFoundError:
          logging.error(f"Tweaks file not found at {tweaks_path}")
          messagebox.showerror("Error", "Failed to load tweaks: File not found.")
          return []
      except json.JSONDecodeError as e: # added the error to the except
          logging.error(f"Error decoding JSON in tweaks file: {tweaks_path}: {e}")
          messagebox.showerror("Error", "Failed to load tweaks: Invalid JSON format.")
          return []
      except Exception as e:
          logging.error(f"Error loading Chris Titus standard tweaks: {str(e)}")
          messagebox.showerror("Error", f"Failed to load Chris Titus standard tweaks: {str(e)}")
          return []
    # --- Custom Event Handling ---
    def event(self, event):
        """Handles custom events for UI updates (from threads)."""
        if event.type() == InstallCompleteEvent.EVENT_TYPE:
            self.handle_install_complete(event)
            return True  # Indicate that we've handled the event
        elif event.type() == TweakCompleteEvent.EVENT_TYPE:
            self.handle_tweak_complete(event)
            return True
        return super().event(event)

    def handle_install_complete(self, event):
        """Handles the InstallCompleteEvent to update UI after app installation."""
        if event.successful:
            successful_str = "\n".join([f"• {app}" for app in event.successful])
            messagebox.showinfo("Installation Complete",
                                f"Successfully installed {len(event.successful)} apps:\n\n{successful_str}")
        if event.failed:
            failed_str = "\n".join([f"• {app}" for app in event.failed])
            messagebox.showwarning("Installation Issues",
                                    f"Failed to install {len(event.failed)} apps:\n\n{failed_str}")
        # Re-enable install button
        self.install_button.setEnabled(True)
        self.install_button.setText("Install Selected Apps")

    def handle_tweak_complete(self, event):
        """Handles the TweakCompleteEvent to update UI after applying tweaks."""
        if event.successful:
            successful_str = "\n".join([f"• {tweak}" for tweak in event.successful])
            messagebox.showinfo("Tweaks Applied",
                              f"Successfully applied {len(event.successful)} tweaks:\n\n{successful_str}")
        if event.failed:
            failed_str = "\n".join([f"• {tweak}" for tweak in event.failed])
            messagebox.showwarning("Tweak Application Issues",
                                  f"Failed to apply {len(event.failed)} tweaks:\n\n{failed_str}")
        # Re-enable apply tweaks button
        self.apply_tweaks_button.setEnabled(True)
        self.apply_tweaks_button.setText("Apply Selected Tweaks")


    def closeEvent(self, event):
      """Handle application close event"""
      logging.info("Trinity Debloater closing.")
      event.accept()

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
        self.setStyleSheet(""" /* Stylesheet - No Changes Needed Here */
            QMainWindow {
                background-color: #121212;
            }
             QTabWidget::pane { /* The tab widget frame */
                border: none;
                background-color: #121212;
            }
            QTabWidget::tab-bar {
                alignment: center;
            }
            QTabBar::tab {
                background-color: rgba(255, 255, 255, 0.05);
                color: #B3B3B3;
                border: none;
                padding: 10px 30px;
                margin: 4px;
                border-radius: 8px;
                font-size: 12pt;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: rgba(80, 126, 254, 0.2);
                color: #507EFE;
                border-bottom: 2px solid #507EFE;
            }
            QTabBar::tab:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            QLabel {
                color: #FFFFFF;
            }
            QPushButton {
                background-color: #507EFE;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 11pt;
                color: white;
                border: none;
            }
            QPushButton:hover {
                background-color: #3A6EEF;
            }
            QPushButton:pressed {
                background-color: #2A5EDF;
            }
            QPushButton:disabled {
                background-color: #5D5D5D;
                color: #8D8D8D;
            }
            QCheckBox {
                spacing: 6px;
                margin-left: 0px;
                padding-left: 0px;
                margin-right: 6px;
                font-size: 10pt;
                color: #FFFFFF;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 4px;
            }
            QCheckBox::indicator:unchecked {
                border: 1px solid rgba(255, 255, 255, 0.3);
                background-color: rgba(30, 30, 30, 0.7);
            }
            QCheckBox::indicator:checked {
                border: 1px solid #507EFE;
                background-color: #507EFE;
            }
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background-color: #1E1E1E;
                border-radius: 12px;
            }
            QScrollBar:vertical {
                background-color: rgba(255, 255, 255, 0.03);
                width: 6px;
                margin: 16px 0 16px 0;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background-color: rgba(255, 255, 255, 0.2);
                min-height: 20px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: rgba(80, 126, 254, 0.5);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
                width: 0px;
                height: 0px;
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            /* Category headers */
            QLabel[category="true"] {
                font-size: 14pt;
                font-weight: bold;
                color: #FFFFFF;
                padding-top: 12px;
                padding-bottom: 6px;
            }
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

        # --- Activation Tab ---
        self.activation_tab = QWidget()
        self.create_activation_tab_content()  # Create content function
        self.tabs.addTab(self.activation_tab, "Activation")

        # --- Appearance Tab ---
        self.appearance_tab = QWidget()
        self.create_appearance_tab_content()
        self.tabs.addTab(self.appearance_tab, "Appearance")


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
        header_label.setStyleSheet("""
            font-size: 18pt;
            font-weight: bold;
            margin-bottom: 16px;
            color: #FFFFFF;
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

        # Iterate through categories and apps, adding headings and checkboxes
        for category_name, apps in self.app_data_categories.items():
            # Category container with its own layout
            category_container = QWidget()
            category_container.setStyleSheet("""
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
            line.setStyleSheet("""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                          stop:0 #507EFE,
                                          stop:1 rgba(80, 126, 254, 0.1));
            """)
            category_layout.addWidget(line)

            # Grid layout for apps in this category
            apps_grid = QGridLayout()
            apps_grid.setSpacing(8)

            # Sort apps alphabetically by display name
            sorted_apps = sorted(
                apps,
                key=lambda app_info: app_info.get("display_name", app_info.get("name", "")).lower()
            )
            logging.debug(f"Sorted apps for category '{category_name}': {[app_info.get('display_name') or app_info.get('name') for app_info in sorted_apps]}") # Debug logging for sorting

            # Add checkboxes for apps in this category
            row = col = 0  # Initialize row and col here
            max_cols = 4

            for app_info in sorted_apps:
                app_name = app_info.get("name", "Unknown App")
                display_name = app_info.get("display_name")
                winget_id = app_info.get("winget_id")
                logo_filename = app_info.get("logo")

                if winget_id:
                    checkbox_text = display_name if display_name else app_name

                    # Create a container for each app item
                    app_item = QWidget()
                    app_item.setStyleSheet("""
                        QWidget {
                            background-color: rgba(255, 255, 255, 0.07);
                            border-radius: 8px;
                            padding: 8px;
                        }
                        QWidget:hover {
                            background-color: rgba(255, 255, 255, 0.12);
                            border: 1px solid rgba(80, 126, 254, 0.3);
                        }
                    """)
                    app_layout = QHBoxLayout(app_item)
                    app_layout.setContentsMargins(8, 8, 8, 8)

                    logo_label = QLabel()
                    if logo_filename:
                        logo_path = self.get_resource_path(os.path.join("assets", logo_filename))
                        logo_pixmap = QPixmap(logo_path).scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        logo_label.setPixmap(logo_pixmap)
                    else:
                        # Default app icon (e.g., if logo is missing)
                        logo_label.setText("📱")  # Or any suitable default
                        logo_label.setStyleSheet("font-size: 16pt; margin-right: 4px;")

                    checkbox = QCheckBox(checkbox_text)
                    checkbox.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

                    # Store checkbox and app info
                    self.app_checkboxes[app_name] = {
                        'checkbox': checkbox,
                        'winget_id': winget_id,
                        'logo_label': logo_label  # Store the logo label
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


        # Add a bottom action section
        action_container = QWidget()
        action_container.setStyleSheet("""
            background-color: rgba(30, 30, 30, 0.7);
            border-radius: 12px;
            margin-top: 10px;
        """)
        action_layout = QHBoxLayout(action_container)

        # The Install button, defined *before* it's used in __init__.
        self.install_button = QPushButton("Install Selected Apps")
        self.install_button.clicked.connect(self.install_selected_apps)
        action_layout.addStretch()  # Push button to the right
        action_layout.addWidget(self.install_button)
        action_layout.addStretch()

        apps_layout.addWidget(action_container)


    def create_tweaks_tab_content(self):
      logging.info("Creating Tweaks tab content with Chris Titus standard tweaks.")
      tweaks_layout = QVBoxLayout(self.tweaks_tab) # Define tweaks_layout here
      self.tweak_checkboxes = {}  # Store tweak checkboxes

      # Load Chris Titus standard tweaks
      standard_tweaks = self.load_chris_titus_tweaks()

      # Header for Tweaks Tab
      header_layout = QHBoxLayout()
      header_label = QLabel("Chris Titus Standard Tweaks")
      header_label.setStyleSheet("""
          font-size: 18pt;
          font-weight: bold;
          margin-bottom: 16px;
          color: #FFFFFF;
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
          category_container.setStyleSheet("""
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
          line.setStyleSheet("""
              background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                        stop:0 #507EFE,
                                        stop:1 rgba(80, 126, 254, 0.1));
          """)
          category_layout.addWidget(line)

          # Add tweaks for this category
          for tweak in tweaks:
              tweak_name = tweak.get("Name", "Unknown Tweak")
              tweak_description = tweak.get("Description", "No description available")

              # Tweak container
              tweak_item = QWidget()
              tweak_item.setStyleSheet("""
                  QWidget {
                      background-color: rgba(255, 255, 255, 0.07);
                      border-radius: 8px;
                      padding: 8px;
                      margin-bottom: 4px;
                  }
                  QWidget:hover {
                      background-color: rgba(255, 255, 255, 0.12);
                      border: 1px solid rgba(80, 126, 254, 0.3);
                  }
              """)
              tweak_layout_item = QVBoxLayout(tweak_item) # Use a different name here to avoid conflict
              tweak_layout_item.setContentsMargins(10, 10, 10, 10)

              # Tweak checkbox
              checkbox = QCheckBox(tweak_name)
              checkbox.setStyleSheet("font-weight: bold; font-size: 11pt;")

              # Description label
              description_label = QLabel(tweak_description)
              description_label.setStyleSheet("color: #B3B3B3; font-size: 9pt;")
              description_label.setWordWrap(True)

              tweak_layout_item.addWidget(checkbox)
              tweak_layout_item.addWidget(description_label)

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
      action_container.setStyleSheet("""
          background-color: rgba(30, 30, 30, 0.7);
          border-radius: 12px;
          margin-top: 10px;
          padding: 10px;
      """)
      action_layout = QHBoxLayout(action_container)

      # Select All button
      select_all_button = QPushButton("Select All")
      select_all_button.clicked.connect(self.select_all_tweaks)
      action_layout.addWidget(select_all_button)

      # Deselect All button
      deselect_all_button = QPushButton("Deselect All")
      deselect_all_button.clicked.connect(self.deselect_all_tweaks)
      action_layout.addWidget(deselect_all_button)

      action_layout.addStretch()  # Add stretch to push the next button to the right

      # Apply Tweaks button
      self.apply_tweaks_button = QPushButton("Apply Selected Tweaks") # Corrected: Define button
      self.apply_tweaks_button.clicked.connect(self.apply_selected_tweaks) # Connect the button click to the function
      action_layout.addWidget(self.apply_tweaks_button)

      tweaks_layout.addWidget(action_container)  # Add the action container to the main layout

    def select_all_tweaks(self):
      """Select all tweaks in the tweaks tab"""
      for tweak_data in self.tweak_checkboxes.values():
        tweak_data['checkbox'].setChecked(True)
      logging.info("All tweaks selected.")

    def deselect_all_tweaks(self):
      """Deselect all tweaks in the tweaks tab."""
      for tweak_data in self.tweak_checkboxes.values():
        tweak_data['checkbox'].setChecked(False)
      logging.info("All tweaks deselected.")

    def create_activation_tab_content(self):
      logging.info("Creating Activation tab content.")
      activation_layout = QVBoxLayout(self.activation_tab)

      # Header
      header_layout = QHBoxLayout()
      header_label = QLabel("Windows Activation")
      header_label.setStyleSheet("""
          font-size: 18pt;
          font-weight: bold;
          margin-bottom: 16px;
          color: #FFFFFF;
      """)
      header_layout.addWidget(header_label)
      header_layout.addStretch()
      activation_layout.addLayout(header_layout)

      # Scroll area (even with one button, good practice)
      activation_scroll_area = QScrollArea()
      activation_scroll_area.setWidgetResizable(True)
      activation_scroll_content = QWidget()
      main_layout = QVBoxLayout(activation_scroll_content)
      activation_scroll_area.setWidget(activation_scroll_content)
      activation_layout.addWidget(activation_scroll_area)

      # Activation Button
      self.activate_button = QPushButton("Activate Permanently")
      self.activate_button.clicked.connect(self.activate_windows)
      main_layout.addWidget(self.activate_button)

      # Credit Link
      credit_label = QLabel()
      credit_label.setText('<a href="https://github.com/massgravel/Microsoft-Activation-Scripts">All credits to Microsoft-Activation-Scripts on GitHub</a>')
      credit_label.setOpenExternalLinks(True) # Make links clickable
      credit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
      credit_label.setStyleSheet("margin-top: 20px; color: #B3B3B3;") # Style as secondary text
      main_layout.addWidget(credit_label)


    def create_appearance_tab_content(self):
      logging.info("Creating Appearance tab content.")
      appearance_layout = QVBoxLayout(self.appearance_tab)

      # Header
      header_layout = QHBoxLayout()
      header_label = QLabel("Appearance Settings")
      header_label.setStyleSheet("""
          font-size: 18pt;
          font-weight: bold;
          margin-bottom: 16px;
          color: #FFFFFF;
      """)
      header_layout.addWidget(header_label)
      header_layout.addStretch()
      appearance_layout.addLayout(header_layout)

      # Scroll area
      appearance_scroll_area = QScrollArea()
      appearance_scroll_area.setWidgetResizable(True)
      appearance_scroll_content = QWidget()
      appearance_scroll_content.setContentsMargins(15, 15, 15, 15)
      main_layout = QVBoxLayout(appearance_scroll_content)
      main_layout.setSpacing(12)
      appearance_scroll_area.setWidget(appearance_scroll_content)
      appearance_layout.addWidget(appearance_scroll_area)

      # Sleek Minimal Button
      self.sleek_minimal_button = QPushButton("Sleek Minimal")
      self.sleek_minimal_button.clicked.connect(self.apply_sleek_minimal)
      main_layout.addWidget(self.sleek_minimal_button)

    def activate_windows(self):
        logging.info("Starting Windows activation using M.A.S.")
        # MAS Activation Script - Using new command as suggested in logs
        mas_command = "powershell -ExecutionPolicy Bypass -Command \"irm https://get.activated.win | iex\"" # Enclose command in quotes
        result = self.run_powershell_command(mas_command)
        if result:
            messagebox.showinfo("Activation Complete", "Windows activated successfully!")
        else:
            messagebox.showerror("Activation Failed", "Windows activation failed. Check the logs for details.")

    def is_translucent_tb_installed(self):
        """Check if TranslucentTB is installed by looking for its executable."""
        possible_paths = [
            os.path.expandvars(r"%ProgramFiles%\\TranslucentTB\\TranslucentTB.exe"),
            os.path.expandvars(r"%LocalAppData%\\Microsoft\\WindowsApps\\TranslucentTB.exe"),
            os.path.expandvars("C:\\Program Files\\WindowsApps\\28017CharlesMilette.TranslucentTB_2024.3.0.0_x64__v826wp6bftszj\\TranslucentTB.exe"), # User provided path - WindowsApps
            os.path.expandvars(r"%LocalAppData%\\Programs\\TranslucentTB\\TranslucentTB.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\\TranslucentTB\\TranslucentTB.exe"),
            "TranslucentTB.exe" # Check if it's in PATH
        ]
        logging.debug(f"Checking TranslucentTB installation paths: {possible_paths}") # Log paths being checked
        for path in possible_paths:
            if os.path.exists(path):
                logging.debug(f"TranslucentTB found at: {path}") # Log if found
                return True
            else:
                logging.debug(f"TranslucentTB not found at: {path}") # Log if not found
        logging.debug("TranslucentTB not found in any checked paths.") # Log if not found in any path
        return False

    def install_translucent_tb(self):
        """Install TranslucentTB using winget."""
        logging.info("Attempting to install TranslucentTB using winget.")
        try:
            # Install TranslucentTB using winget
            result = self.install_app_winget("TranslucentTB") # Winget ID is "TranslucentTB"
            if result:
                logging.info("TranslucentTB installed successfully via winget.")
                return True
            else:
                logging.error("Winget installation of TranslucentTB failed.")
                return False
        except Exception as e:
            logging.error(f"Exception during TranslucentTB winget installation: {e}")
            return False

    def uninstall_translucent_tb_winget(self):
        """Uninstalls TranslucentTB using winget, attempts to uninstall any version."""
        logging.info("Attempting to uninstall TranslucentTB using winget (fallback).")
        try:
            # Uninstall TranslucentTB using winget, try different IDs if needed
            uninstall_ids = ["TranslucentTB", "CharlesMilette.TranslucentTB"] # Common names/IDs, add more if needed
            uninstall_success = False
            for app_id in uninstall_ids:
                command = ['winget', 'uninstall', '--id', app_id, '--silent'] # Attempt silent uninstall
                logging.info(f"Attempting to uninstall TranslucentTB with winget command: {' '.join(command)}")
                result = subprocess.run(command, capture_output=True, text=True, check=False) # check=False to handle non-zero exit codes

                logging.info(f"Winget uninstall stdout: {result.stdout}")
                if result.returncode == 0:
                    logging.info(f"Successfully uninstalled TranslucentTB using winget with ID: {app_id}")
                    uninstall_success = True # Mark as successful if any uninstall command works
                    break # Exit loop if uninstalled successfully
                else:
                    logging.warning(f"Winget uninstall failed for ID: {app_id}. Stderr: {result.stderr}")

            return uninstall_success # Return True if uninstalled by any ID, False otherwise

        except Exception as e:
            logging.error(f"Exception during TranslucentTB winget uninstallation (fallback): {e}")
            return False


    def start_translucent_tb(self):
        """Start TranslucentTB by directly executing from Program Files."""
        possible_executable_paths = [
            os.path.expandvars(r"%ProgramFiles%\\TranslucentTB\\TranslucentTB.exe"),
            os.path.expandvars(r"%LocalAppData%\\Microsoft\\WindowsApps\\TranslucentTB.exe"),
            os.path.expandvars("C:\\Program Files\\WindowsApps\\28017CharlesMilette.TranslucentTB_2024.3.0.0_x64__v826wp6bftszj\\TranslucentTB.exe"), # User provided path - WindowsApps
            os.path.expandvars(r"%LocalAppData%\\Programs\\TranslucentTB\\TranslucentTB.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\\TranslucentTB\\TranslucentTB.exe"),
            "TranslucentTB.exe" # Fallback to PATH
        ]

        executable_path = None
        for path in possible_executable_paths:
            if os.path.exists(path):
                executable_path = path
                logging.info(f"TranslucentTB executable found at: {executable_path}")
                break # Use the first found path

        if not executable_path:
            logging.warning("TranslucentTB executable not found in common locations or PATH.")
            return False # Indicate start failed, allowing fallback to trigger

        logging.info(f"Attempting to start TranslucentTB directly from: {executable_path}")

        try:
            process = subprocess.Popen([executable_path], start_new_session=True, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
            logging.info("TranslucentTB start process initiated directly.")
            return True
        except Exception as e:
            logging.error(f"Exception while starting TranslucentTB directly: {e}")
            return False


def main():
    if not is_admin():
        root = tk.Tk()
        root.withdraw()
        messagebox.showwarning("Administrator Rights Required",
                               "Some features of Trinity Debloater require admin rights.\nRun as administrator.")
        root.destroy()

    app = QApplication(sys.argv)
    window = TrinityDebloaterGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()