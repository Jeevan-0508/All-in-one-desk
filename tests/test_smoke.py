"""Offline smoke tests for All-in-One Desk.

Stubs the heavy optional dependencies (pandas, pdf2docx, pytesseract) so the
routes can be exercised without Tesseract or LibreOffice installed.

    python tests/test_smoke.py
"""
import io
import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _stub_heavy_dependencies():
    sys.modules.setdefault("pandas", types.ModuleType("pandas"))

    pdf2docx = types.ModuleType("pdf2docx")
    pdf2docx.Converter = object
    sys.modules.setdefault("pdf2docx", pdf2docx)

    pytesseract = types.ModuleType("pytesseract")
    pytesseract.TesseractNotFoundError = type(
        "TesseractNotFoundError", (Exception,), {}
    )
    pytesseract.pytesseract = types.SimpleNamespace(tesseract_cmd=None)
    pytesseract.image_to_string = lambda image: "  INVOICE 12345  "
    sys.modules.setdefault("pytesseract", pytesseract)
    return pytesseract


def _png_upload():
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (8, 8), "white").save(buf, "PNG")
    buf.seek(0)
    return {"file": (buf, "sample.png")}


def main():
    pytesseract = _stub_heavy_dependencies()
    sys.path.insert(0, ROOT)
    os.chdir(ROOT)

    import app as application

    application.app.config["TESTING"] = True
    client = application.app.test_client()

    failures = []

    def check(label, condition, detail=""):
        print(("PASS  " if condition else "FAIL  ") + label
              + ("" if condition else "  -> " + str(detail)))
        if not condition:
            failures.append(label)

    response = client.get("/")
    check("GET / returns 200", response.status_code == 200, response.status_code)
    check("POST / is rejected", client.post("/").status_code == 405)

    # The frontend reads this response with res.text() and writes it straight
    # into the output box, so it must be the extracted text and nothing else.
    response = client.post(
        "/image_to_text", data=_png_upload(), content_type="multipart/form-data"
    )
    body = response.get_data(as_text=True)
    check("OCR returns 200", response.status_code == 200, response.status_code)
    check("OCR returns bare text", body == "INVOICE 12345", body[:80])
    check("OCR response is not a page", "<html" not in body.lower(), len(body))

    response = client.post(
        "/image_to_text", data={}, content_type="multipart/form-data"
    )
    check("OCR without a file returns 400", response.status_code == 400,
          response.status_code)

    leftovers = [f for f in os.listdir(application.UPLOAD_FOLDER)
                 if f.endswith(".png")]
    check("OCR removes its temp upload", leftovers == [], leftovers)

    def _raise(image):
        raise pytesseract.TesseractNotFoundError()

    original = pytesseract.image_to_string
    pytesseract.image_to_string = _raise
    try:
        response = client.post(
            "/image_to_text", data=_png_upload(),
            content_type="multipart/form-data",
        )
        check("missing Tesseract explains how to install it",
              "not installed" in response.get_data(as_text=True),
              response.get_data(as_text=True)[:60])
    finally:
        pytesseract.image_to_string = original

    check("removed /knowledge route returns 404",
          client.get("/knowledge/knowledge_index.json").status_code == 404)
    response = client.get("/static/knowledge/knowledge_index.json")
    check("knowledge index is still served", response.status_code == 200,
          response.status_code)

    response = client.post("/kpi", data={"total": "200", "defects": "50",
                                        "fp": "10"})
    body = response.get_data(as_text=True)
    check("KPI defect rate", "Defect Rate: 25.00%" in body, body[:60])
    check("KPI false positive rate", "False Positive Rate: 20.00%" in body,
          body[:60])
    response = client.post("/kpi", data={"total": "0", "defects": "0",
                                        "fp": "0"})
    check("KPI handles zero totals", response.status_code == 200,
          response.status_code)

    response = client.post("/dedupe", data={"data": "a, b, a, c, b"})
    check("dedupe responds", response.status_code == 200, response.status_code)

    # A second colon used to raise "too many values to unpack".
    response = client.post(
        "/generate_flow",
        json={"text": "Start -> Review\n- Check ID: Team A: EU"},
    )
    check("flowchart accepts extra colons", response.status_code == 200,
          response.get_data(as_text=True)[:120])
    diagram = response.get_json().get("diagram", "")
    check("flowchart builds edges", "Start --> Review" in diagram, diagram)

    # pandas needs openpyxl for .xlsx and xlrd for legacy .xls. pandas is
    # stubbed here, so assert the declaration instead of the import.
    with io.open(os.path.join(ROOT, "requirements.txt"), encoding="utf-8") as fh:
        declared = fh.read()
    check("requirements declares openpyxl", "openpyxl" in declared, declared)
    check("requirements declares xlrd", "xlrd" in declared, declared)

    application.shutil.which = lambda name: None
    application.os.path.exists = lambda path: False
    check("soffice lookup returns None when absent",
          application.get_soffice_path() is None)

    print()
    if failures:
        print("%d failed: %s" % (len(failures), ", ".join(failures)))
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
