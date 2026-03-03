import pdfplumber

def extract_pdf(path):
    print(f"--- Extracting text from {path} ---")
    with pdfplumber.open(path) as pdf:
        first_page = pdf.pages[0]
        print(first_page.extract_text()[:1000])
        print("...\n")

extract_pdf("docs/reports/CAPITAL GAIN(2).pdf")
extract_pdf("docs/reports/P&L REPORT(2).pdf")
extract_pdf("docs/reports/TRANSACTION STATEMENT.pdf")
extract_pdf("docs/reports/WEALTH REPORT.pdf")
