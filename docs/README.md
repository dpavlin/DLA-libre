# 3M Library Systems DLA Client - Operations & Deployment Guide

This guide describes how to deploy, configure, and operate the original **3M Library Systems Data Manager (DLA client)** software on a new Windows environment, using the original administrative access controls and directory configurations.

---

## 1. System Requirements & Registry Configuration

Before running the DLA client (`DataManager.exe`) on a new Windows machine or clean Wine environment, you must configure the environment with validation parameters and folder structures.

### Registry Setup
Create a `.reg` file containing the following settings to validate barcodes and bypass software checks:

```registry
Windows Registry Editor Version 5.00

; Define Handheld Software Installation Path
[HKEY_LOCAL_MACHINE\SOFTWARE\3M\Library Systems\DLA]
"Install"="C:\\Program Files\\3M Library Systems\\DLA"

; Configure Barcode Validation Parameters
[HKEY_LOCAL_MACHINE\SOFTWARE\3M\Library Systems\Data Manager\3.00\BCValidation]
"MinLength"=dword:0000000a
"MaxLength"=dword:0000000a
"Digit Characters"=dword:00000001
"Upper Case Characters"=dword:00000000
"Lower Case Characters"=dword:00000000
"Other Characters"=dword:00000000
```

### Necessary Dummy Binaries
The DLA application checks the installer path resolved in the registry for specific handheld files. If these are not present, it will throw a *"DLA Software not installed"* warning. Ensure the following dummy files exist:
*   `C:\Program Files\3M Library Systems\DLA\dla.prc`
*   `C:\Program Files\3M Library Systems\DLA\dla_app.prc`
*   `C:\Program Files\3M Library Systems\DLA\FlashPro.prc`

---

## 2. Administrator Access & Authentication

To adjust directory paths, validation constraints, or format definitions, you must authenticate as an administrator.

### Step 1: Open Admin Setup
In the main window menu bar, click **Admin Setup** and select **DLA Category/Folders...**:

![Admin Menu Selection](images/01_admin_menu.png)

### Step 2: Input Admin Password
The software will prompt you with an authorization dialog:

![Admin Password Validation](images/02_password_prompt.png)

Enter the factory-set administrative password:
```text
technician
```

![Entering Admin Password](images/03_password_entered.png)

Press **Return** or click **OK** to authenticate. The configuration fields will now unlock for editing:

![Unlocked Admin Configuration](images/06_admin_unlocked.png)

---

## 3. Directory Configuration

Once authenticated, you will be presented with the **DLA Category and Folders** dialog:

![Folders Dialog](images/04_folders_dialog.png)

### Parameters to Set:
1.  **DLA Category/Format:** Ensure the active category is set to `"Default"` (for standard library workflows) or `"Inventory"`.
2.  **Upload/Download Folders:**
    *   **Lists Directory:** Path where the source `.tab` delimited files exported from the ILS (e.g. Koha) are placed (e.g. `D:\DLA\ShelfOrderList\`).
    *   **Export/Data Directory:** Destination path where the compiled PalmOS `.pdb` database catalogs and search mappings are written (e.g. `D:\DLA\Card\`).

Confirm settings. A success popup should confirm validation:

![Folders Configured successfully](images/05_folders_configured.png)

---

## 4. Compiling and Exporting Catalogs

The application continuously monitors the lists directory. Follow these operational steps to build handheld catalogs:

### Step 1: Refresh Monitored Lists
Press **F5** or select the refresh option to scan the lists folder. The tree view will populate under `SHELF ORDER LISTS`.

![Main Interface with populated lists](images/07_main_interface.png)

### Step 2: Check Lists for Export
Double-click or check the checkbox next to the lists (floors) you wish to compile. 

### Step 3: Trigger Export Compilation
1.  Select **File** -> **Export...** from the menu (or press **Alt+F**, then **E**).
2.  In the confirmation dialog, press **Return** or click **OK**.
3.  The application will start building the primary indexes, sorting data, and compiling search indexes. A progress bar will show "Building Secondary find index, sorting...".
4.  Once completed, it will write the database structure under the target directory:
    *   `000-3MLH.pdb`: Master segments lookup list.
    *   `id01/001-3MLH.pdX` (and subsequent segments): Barcode indexes (dynamic 14/16-byte records depending on item count).
    *   `md01/001d-3MLH.pdb` (and subsequent segments): Book details (Titles & Callnumbers).
    *   `ndex/3F3F4431/` and `ndex/3F3F4432/`: Title and Callnumber search indexes.
