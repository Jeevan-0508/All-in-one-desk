from flask import Flask, render_template, request, send_file, jsonify, send_from_directory
import os
import uuid
import pandas as pd
from pdf2docx import Converter
import sys
import tempfile
import webbrowser
import pytesseract
from PIL import Image
import cv2
import numpy as np
import subprocess
import threading
import time

app = Flask(__name__)

# ================= UPLOAD FOLDER =================
def get_upload_folder():
    if getattr(sys, 'frozen', False):
        path = os.path.join(tempfile.gettempdir(), "personal_automation_uploads")
    else:
        path = os.path.join(os.getcwd(), "uploads")
    os.makedirs(path, exist_ok=True)
    return path

UPLOAD_FOLDER = get_upload_folder()

# ================= LIBREOFFICE =================
def get_soffice_path():
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.getcwd()

    return os.path.join(
        base,
        "libreoffice",
        "App",
        "libreoffice",
        "program",
        "soffice.exe"
    )

# ================= TESSERACT =================
def get_tesseract_path():
    # Bundled via PyInstaller
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, "tesseract", "tesseract.exe")
    # Check PATH first (works on Mac/Linux after brew/apt install)
    import shutil
    path_result = shutil.which("tesseract")
    if path_result:
        return path_result
    # Windows common install locations
    for p in [r"C:\Program Files\Tesseract-OCR\tesseract.exe", r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"]:
        if os.path.exists(p):
            return p
    # Mac/Linux fallback
    for p in ["/usr/local/bin/tesseract", "/opt/homebrew/bin/tesseract", "/usr/bin/tesseract"]:
        if os.path.exists(p):
            return p
    return "tesseract"  # last resort — assumes it is on PATH

pytesseract.pytesseract.tesseract_cmd = get_tesseract_path()

# ================= HOME =================
@app.route("/", methods=["GET", "POST"])
def index():
    return render_template(
        "index.html",
        output="",
        dedupe_output="",
        risk_output="",
        kpi_output="",
        sheet_output="",
        active_tab="text"
    )

# ================= KNOWLEDGE =================
@app.route("/knowledge/<path:filename>")
def serve_knowledge(filename):
    return send_from_directory("knowledge", filename)

# ================= IMAGE → TEXT =================
@app.route("/image_to_text", methods=["GET", "POST"])
def image_to_text():
    if request.method == "GET":
        return render_template(
            "index.html",
            ocr_output="",
            active_tab="image_to_text"
        )

    try:
        file = request.files.get("file")
        if not file:
            return render_template(
                "index.html",
                ocr_output="No file uploaded",
                active_tab="image_to_text"
            )

        uid = str(uuid.uuid4())
        img_path = os.path.join(UPLOAD_FOLDER, f"{uid}.png")
        file.save(img_path)

        text = pytesseract.image_to_string(Image.open(img_path))

        return render_template(
            "index.html",
            ocr_output=text,
            active_tab="image_to_text"
        )

    except Exception as e:
        return render_template(
            "index.html",
            ocr_output=f"OCR failed: {e}",
            active_tab="image_to_text"
        )

# ================= DEDUPE =================
@app.route("/dedupe", methods=["POST"])
def dedupe():
    raw = request.form.get("data", "")
    items = raw.replace(",", " ").split()
    unique_items = list(dict.fromkeys(items))
    return render_template(
        "index.html",
        dedupe_output="\n".join(unique_items),
        active_tab="dedupe"
    )

# ================= FLOW =================
@app.route("/generate_flow", methods=["POST"])
def generate_flow():
    try:
        data = request.json.get("text", "")
        diagram = convert_text_to_mermaid(data)
        return jsonify({"diagram": diagram})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ================= RISK NOTES =================
@app.route("/risk_note", methods=["POST"])
def risk_note():
    output = f"""
Risk Title: {request.form.get("title")}
Region: {request.form.get("region")}
Description:
{request.form.get("description")}
Root Cause:
{request.form.get("root")}
Impact:
{request.form.get("impact")}
Mitigation:
{request.form.get("mitigation")}
"""
    return render_template(
        "index.html",
        risk_output=output,
        active_tab="risk"
    )

# ================= KPI =================
@app.route("/kpi", methods=["POST"])
def kpi():
    try:
        total = float(request.form.get("total", 0))
        defects = float(request.form.get("defects", 0))
        fp = float(request.form.get("fp", 0))

        defect_rate = (defects / total * 100) if total else 0
        fp_rate = (fp / defects * 100) if defects else 0

        return (
            f"Defect Rate: {defect_rate:.2f}%\n"
            f"False Positive Rate: {fp_rate:.2f}%\n\n"
            f"📘 Interpretation:\n"
            f"- Defect Rate shows overall process quality\n"
            f"- False Positive Rate shows detection accuracy"
        )

    except Exception as e:
        return f"KPI calculation failed: {e}", 400

# ================= PDF → WORD =================
@app.route("/pdf_to_word", methods=["POST"])
def pdf_to_word():
    try:
        file = request.files.get("file")
        if not file:
            return jsonify({"error": "No file uploaded"}), 400

        uid = str(uuid.uuid4())
        pdf_path = os.path.join(UPLOAD_FOLDER, f"{uid}.pdf")
        docx_path = os.path.join(UPLOAD_FOLDER, f"{uid}.docx")

        file.save(pdf_path)

        cv = Converter(pdf_path)
        cv.convert(docx_path)
        cv.close()

        return jsonify({"success": True, "file_id": uid})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ================= WORD → PDF (ORIGINAL, WORKING) =================
@app.route("/word_to_pdf", methods=["POST"])
def word_to_pdf():
    try:
        file = request.files.get("file")
        if not file:
            return jsonify({"error": "No file uploaded"}), 400

        uid = str(uuid.uuid4())
        docx_path = os.path.join(UPLOAD_FOLDER, f"{uid}.docx")
        file.save(docx_path)

        soffice = get_soffice_path()
        if soffice != "soffice" and not os.path.exists(soffice):
            return jsonify({"error": "LibreOffice not found. Please install LibreOffice."}), 500

        subprocess.run(
            [
                soffice,
                "--headless",
                "--nologo",
                "--nofirststartwizard",
                "--convert-to", "pdf",
                "--outdir", UPLOAD_FOLDER,
                docx_path
            ],
            check=True,
            timeout=30
        )

        return jsonify({"success": True, "file_id": uid})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ================= DOWNLOAD =================
@app.route("/download/pdf/<file_id>")
def download_pdf(file_id):
    return send_file(
        os.path.join(UPLOAD_FOLDER, f"{file_id}.pdf"),
        as_attachment=True
    )

@app.route("/download/docx/<file_id>")
def download_docx(file_id):
    return send_file(
        os.path.join(UPLOAD_FOLDER, f"{file_id}.docx"),
        as_attachment=True
    )

# ================= SHEET → TEXT =================
@app.route("/sheet_to_text", methods=["POST"])
def sheet_to_text():
    try:
        file = request.files["file"]

        if file.filename.lower().endswith(".csv"):
            df = pd.read_csv(file, dtype=str)
        else:
            df = pd.read_excel(file, dtype=str)

        df = df.fillna("")
        lines = [" ".join(row.astype(str)) for _, row in df.iterrows()]
        return "\n".join(lines)

    except Exception as e:
        return f"Sheet conversion failed: {e}", 400

# ================= FLOW HELPER =================
def convert_text_to_mermaid(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    mermaid = ["graph TD"]
    last_parent = None
    generated = False

    for line in lines:
        if "->" in line:
            nodes = [n.strip().replace(" ", "_") for n in line.split("->")]
            for i in range(len(nodes) - 1):
                mermaid.append(f"{nodes[i]} --> {nodes[i+1]}")
            last_parent = nodes[-1]
            generated = True

        elif line.startswith("-") and ":" in line and last_parent:
            item, owner = line[1:].split(":")
            item = item.strip().replace(" ", "_")
            owner = owner.strip().replace(" ", "_")
            mermaid.append(f"{last_parent} --> {item}")
            mermaid.append(f"{item} --> {owner}")
            generated = True

    if not generated:
        mermaid.append("Input_Text --> Unsupported_Format")

    return "\n".join(mermaid)

# ================= RUN =================
if __name__ == "__main__":
    def open_browser():
        time.sleep(2)
        webbrowser.open("http://127.0.0.1:5000")

    threading.Thread(target=open_browser).start()
    app.run(host="127.0.0.1", port=5000)
