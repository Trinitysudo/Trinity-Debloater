# Trinity Debloater: Streamline Your Windows Experience

**Trinity Debloater** is a modern PyQt6 application designed to optimize Windows performance by removing unnecessary bloatware and applying essential system tweaks. Reclaim valuable resources and ensure a faster, cleaner, and more responsive PC.

**Key Features:**

*   ✅ **Simplified App Removal:**  Easily uninstall unwanted pre-installed applications using Winget for efficient and silent removal.
*   ✅ **Curated System Tweaks:**  Integrates Chris Titus Tech's standard tweaks, allowing users to apply proven performance and privacy optimizations with simple checkboxes.
*   ✅ **Clean & Intuitive Dark UI:**  Features a sleek, modern dark theme built with PyQt6 for a user-friendly experience.
*   ✅ **Tabbed Interface:**  Organized into "Apps" and "Tweaks" tabs for straightforward navigation.
*   ✅ **Lightweight & Optimized:**  Designed for minimal resource usage and fast operation.
*   ✅ **Action Logging:**  Provides transparent logging of all changes made by the application.
*   ✅ **Administrator Privilege Management:**  Handles necessary administrator elevation seamlessly.
*   ✅ **Maintained: Yes** - Actively developed and updated.

**Effortless Installation:**

Install Trinity Debloater with a single line of PowerShell:

```powershell
Invoke-WebRequest -Uri "YOUR_DOWNLOAD_URL_HERE" -OutFile "$env:USERPROFILE\Downloads\TrinityDebloater.exe"; Start-Process -FilePath "$env:USERPROFILE\Downloads\TrinityDebloater.exe"
