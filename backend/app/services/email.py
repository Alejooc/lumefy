from email.message import EmailMessage
from email.utils import formataddr
import logging

import aiosmtplib
from pydantic import EmailStr

from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    async def send_email(email_to: EmailStr, subject: str, html_content: str):
        message = EmailMessage()
        message["From"] = formataddr((settings.MAIL_FROM_NAME, settings.MAIL_FROM))
        message["To"] = str(email_to)
        message["Subject"] = subject
        message.set_content("Este mensaje requiere un cliente compatible con HTML.")
        message.add_alternative(html_content, subtype="html")

        credentials = (
            (settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
            if settings.USE_CREDENTIALS
            else (None, None)
        )
        try:
            await aiosmtplib.send(
                message,
                hostname=settings.MAIL_SERVER,
                port=settings.MAIL_PORT,
                username=credentials[0],
                password=credentials[1],
                start_tls=settings.MAIL_STARTTLS,
                use_tls=settings.MAIL_SSL_TLS,
                validate_certs=settings.VALIDATE_CERTS,
                timeout=30,
            )
        except Exception:
            logger.warning("Email send failed to %s", email_to, exc_info=True)
            # Don't re-raise in dev to allow flow testing
            if settings.ENVIRONMENT.lower() == "production":
                raise

    @staticmethod
    async def send_reset_password_email(email_to: str, token: str):
        project_name = settings.PROJECT_NAME
        subject = f"{project_name} - Recuperación de Contraseña"
        link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        
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

    @staticmethod
    async def send_storefront_reset_password_email(
        email_to: str,
        token: str,
        storefront_name: str,
        reset_link: str,
    ):
        subject = f"{storefront_name} - Password reset"
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <div style="background-color: #f4f6f9; padding: 20px;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 30px; border-radius: 8px;">
                        <h2 style="color: #1a237e; text-align: center;">{storefront_name}</h2>
                        <h3 style="color: #333;">Reset your password</h3>
                        <p style="color: #555;">We received a request to reset your password.</p>
                        <p style="color: #555;">If you did not request this change, you can ignore this email.</p>
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="{reset_link}" style="background-color: #1a237e; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 4px; font-weight: bold;">Reset Password</a>
                        </div>
                        <p style="color: #999; font-size: 12px; text-align: center;">This link expires in 1 hour.</p>
                    </div>
                </div>
            </body>
        </html>
        """
        await EmailService.send_email(email_to, subject, html_content)
