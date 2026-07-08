import os
import logging
import yagmail
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

class EmailDeliverer:
    def __init__(self):
        load_dotenv()
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_pass = os.getenv("SMTP_PASS")
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = os.getenv("SMTP_PORT", "465")
        self.recipient = os.getenv("RECIPIENT_EMAIL")

    def is_configured(self) -> bool:
        """
        Check if the required SMTP credentials are present in the environment.
        """
        return bool(self.smtp_user and self.smtp_pass)

    def send_email(self, subject: str, html_content: str, recipient: str = None) -> bool:
        """
        Send an HTML email via SMTP using yagmail.
        """
        if not self.is_configured():
            logger.warning("[Delivery] SMTP credentials not complete in `.env`. Skipping email sending.")
            return False

        target_recipient = recipient or self.recipient
        if not target_recipient:
            logger.error("[Delivery] No recipient email specified.")
            return False

        logger.info(f"[Delivery] Connecting to SMTP server {self.smtp_host}:{self.smtp_port} as {self.smtp_user}...")
        try:
            # yagmail handles SMTP/SSL ports and headers automatically
            yag = yagmail.SMTP(
                user=self.smtp_user,
                password=self.smtp_pass,
                host=self.smtp_host,
                port=int(self.smtp_port)
            )
            
            logger.info(f"[Delivery] Sending email to {target_recipient}...")
            yag.send(
                to=target_recipient,
                subject=subject,
                contents=html_content
            )
            logger.info(f"[Delivery] HTML email report delivered successfully to {target_recipient}! ✅")
            return True
        except Exception as e:
            logger.error(f"[Delivery] Failed to deliver email via SMTP: {e}")
            return False
