# Getting started

All-in-One Desk is a local desktop productivity suite that groups document, text, analytics and OCR tools behind one Flask interface. It is designed for files that should stay on the user's machine.

## Run from source

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Optional engines such as Tesseract and LibreOffice are required only for the tools that use them. The packaged Windows executable is described in the main README.

## Choose the right tool

Use the document converters for format changes, text tools for cleanup and comparison, analytics tools for structured files, and OCR only when the source is an image or scanned document. Keep sensitive files local and review generated output before sharing it.

## Scope boundary

This is a local productivity utility, not a hosted SaaS, records system or guarantee of conversion fidelity. Some operations depend on installed optional software and file-specific quality.
