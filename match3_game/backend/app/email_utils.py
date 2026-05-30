import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")


def send_verification_email(to_email: str, code: str) -> bool:
    if not SMTP_USER or not SMTP_PASSWORD:
        print(f"⚠️ Email не настроен. Код для {to_email}: {code}")
        return False
    
    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_USER
        msg["To"] = to_email
        msg["Subject"] = "Подтверждение регистрации в ВесёлыйРяд"
        
        body = f"""
        <html>
        <body style="font-family: Arial;">
            <h2 style="color: #ff1493;">Добро пожаловать в ВесёлыйРяд!</h2>
            <p>Ваш код подтверждения:</p>
            <h1 style="color: #ff1493;">{code}</h1>
            <p>Введите этот код в приложении для завершения регистрации.</p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, "html"))
        
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"✅ Письмо отправлено на {to_email}")
        return True
    except Exception as e:
        print(f"❌ Ошибка отправки письма: {e}")
        return False