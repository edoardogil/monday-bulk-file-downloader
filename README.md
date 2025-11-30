# monday-bulk-file-downloader  
**Bulk File Downloader for Monday.com using Cursor-Based Pagination**

A Python tool designed to download **large volumes of files** from Monday.com boards using the official API and **cursor-based pagination**.  

Originally built to handle thousands of PDF deliverables per client, but fully compatible with **any file type** stored in Monday.com file columns.

This project is based on a real operational need where Monday’s native “Download all files” feature freezes or fails when handling very large boards.

---

## Background

In our organization, Monday.com is used to store compliance deliverables for multiple clients.  
A typical board contains:

- **Groups** → each representing a type of compliance norm (e.g., NOM-022-STPS-2015, NOM-025-STPS-2008, etc.)  
- **Items** → each representing a client location/branch  
- **File columns per year** → e.g. `2019`, `2020`, `2021`, `2022`, `2023`

Each location uploads one or two file per year.  
With hundreds of locations and several compliance norms, boards can easily reach:

- 350+ items per group  
- 6 compliance groups per board  
- 1,000+ files per year column  
- Thousands of files overall

Monday works perfectly for online viewing, but **clients frequently require full offline backups** for audits, local archives, or regulatory checks.

Monday's native export options cannot handle this volume reliably.  
This tool solves that.

---

## Key Features

- **Cursor-based pagination** (`items_page` + `next_items_page`)  
  Handles thousands of items without hitting Monday’s 500-item limit.
- **Bulk file download** for a specified file column (e.g., a specific year)
- **Multi-file per item support** with auto-numbering (`_00`, `_01`, `_02`, …)
- Automatically **resumes interrupted downloads** using `cursor_state.json`
- Skips items already downloaded  
- Detailed **session logging**
- Builds a clean folder structure:

```
/YEAR / GROUP_NAME / LOCATION_NAME / FILE.ext
```

- Fully **file-type agnostic** (PDF, JPG, PNG, XLSX, DOCX, ZIP, etc.)

---

## Example Use Case

A board for inspection report may look like this:

- Groups: NOM-022-STPS-2015, NOM-015-STPS-2001, NOM-025-STPS-2008  
- Items: “Sucursal 5 de Mayo”, “Sucursal 9 Poniente”, etc.  
- Columns: 2019, 2020, 2021, 2022, 2023…

The script can download:

- Hundreds of locations  
- Across multiple norms  
- With thousands of files per board  

Reliably and automatically.

---

## How It Works

1. Connects to Monday via API key  
2. Loads board items using cursor-based pagination  
3. For each item:
   - Reads the file column
   - Extracts `assetId`s
   - Retrieves each asset’s `public_url`
   - Downloads each file
4. Creates folders dynamically  
5. Saves cursor and progress regularly  
6. Logs every operation  

---

## Requirements

- Python **3.8+**
- `requests` package
- Monday.com API key
- Board ID and column IDs

Install dependency:

```bash
pip install requests
```

---

## Usage

Run the script:

```bash
python monday-bulk-file-downloader.py
```

Files will be saved in the directory configured inside the script.

---

## Limitations

These limitations are known and scheduled for improvement:

- Column-to-year mapping is manual  
- Assets without public URLs cannot be downloaded  
- Timeout is fixed (default 30s)  
- File extension is inferred from URL  
- Filenames with special characters may require sanitization  
- Comments and variable names are currently in Spanish  

---

## Roadmap (Planned Improvements)

### Immediate
- [ ] Translate all comments to English  
- [ ] Rename variables and constants to English  
- [ ] Move configuration into external `config.json`  
- [ ] Better file extension detection  
- [ ] Detect all file columns automatically
- [ ] Improve filename sanitization
- [ ] Add example board schema  
- [ ] Add support for multi-column batch export (2018–2025)

### Future
- [ ] Publish as installable module (`pip install monday-bulk-downloader`)  
- [ ] Add CLI mode with flags (`--column 2023`, etc.)  
- [ ] Improve parallel download support  
- [ ] Optional GUI for non-technical users  
- [ ] Handle Monday API complexity limits more efficiently  

---

## Disclaimer

This tool was originally developed for internal use in a production environment.  
It has been adapted for open-source publication, but your Monday board structure may differ.

Expect to adjust:
- Column IDs  
- Group naming  
- Folder conventions  
- Board schemas  

---

## Contributing

Contributions are welcome.  
If you use Monday.com and want to improve this tool, feel free to fork the repo and submit PRs.

---

## License

MIT License.  
Free for personal or commercial use.
