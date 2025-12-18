import smtplib
from email.message import EmailMessage

def send_ticket_email(to_email: str, pdf_path: str):
    msg = EmailMessage()
    msg["Subject"] = "Your Flight Ticket"
    msg["From"] = "yourgmail@gmail.com"
    msg["To"] = to_email
    msg.set_content("Your booking is confirmed. Your flight ticket PDF is attached.")

    with open(pdf_path, "rb") as f:
        file_data = f.read()
        filename = pdf_path.split("/")[-1]

    msg.add_attachment(file_data, maintype="application", subtype="pdf", filename=filename)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login("ai.flighter.io@gmail.com", "stjb csnx wnqc kggx")
        smtp.send_message(msg)
