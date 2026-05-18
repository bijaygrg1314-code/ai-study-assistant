import PyPDF2
import io

def extract_text_from_pdf(uploaded_file):
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.read()))
        text = ""
        for page in pdf_reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        if not text.strip():
            return None, "Could not extract text from this PDF. It may be scanned or image-based."
        return text.strip(), None
    except Exception as e:
        return None, str(e)