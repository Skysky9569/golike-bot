from fpdf import FPDF

pdf = FPDF()
pdf.add_page()
pdf.set_font("Arial", size=12)
pdf.cell(200, 10, txt="Hello World! This is a test PDF.", ln=1, align="C")
pdf.cell(200, 10, txt="Markitdown conversion test.", ln=1, align="C")
pdf.output("D:/pythonadb/demo.pdf")
print("Created demo.pdf")