from typing import List, Any, Dict
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr
from app.core.config import settings
from pathlib import Path

# Basic configuration
conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    USE_CREDENTIALS=settings.USE_CREDENTIALS,
    VALIDATE_CERTS=settings.VALIDATE_CERTS
)

class EmailService:
    @staticmethod
    async def send_email(email_to: EmailStr, subject: str, html_content: str):
        message = MessageSchema(
            subject=subject,
            recipients=[email_to],
            body=html_content,
            subtype=MessageType.html
        )
        fm = FastMail(conf)
        try:
            await fm.send_message(message)
        except Exception as e:
            print(f"EMAIL ERROR: {e}")
            print(f"MOCKED EMAIL TO: {email_to}")
            print(f"SUBJECT: {subject}")
            # Don't re-raise in dev to allow flow testing
            if settings.ENVIRONMENT == "production":
                raise e

    @staticmethod
    async def send_reset_password_email(email_to: str, token: str):
        project_name = settings.PROJECT_NAME
        subject = f"{project_name} - Recuperación de Contraseña"
        link = f"http://localhost:4200/reset-password?token={token}"
        
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <div style="background-color: #f4f6f9; padding: 20px;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <h2 style="color: #1a237e; text-align: center;">{project_name}</h2>
                        <h3 style="color: #333;">Recuperación de Contraseña</h3>
                        <p style="color: #555;">Hola,</p>
                        <p style="color: #555;">Recibimos una solicitud para restablecer tu contraseña. Si no fuiste tú, puedes ignorar este correo.</p>
                        <p style="color: #555;">Para continuar, haz clic en el siguiente botón:</p>
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="{link}" style="background-color: #1a237e; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 4px; font-weight: bold;">Restablecer Contraseña</a>
                        </div>
                        <p style="color: #999; font-size: 12px; text-align: center;">Este enlace expirará en 1 hora.</p>
                        <hr style="border: 1px solid #eee; margin: 20px 0;">
                        <p style="color: #999; font-size: 10px; text-align: center;">&copy; {project_name}. Todos los derechos reservados.</p>
                    </div>
                </div>
            </body>
        </html>
        """
        await EmailService.send_email(email_to, subject, html_content)
