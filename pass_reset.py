from flask import Flask, url_for
import os
from itsdangerous import URLSafeTimedSerializer
from flask_mailman import EmailMessage

# from app.templates.auth.reset_password_email_content import (
#     reset_password_email_html_content
# )

def send_reset_password_email(user):
    reset_password_url = url_for(
        "auth.reset_password",
        token=user.generate_reset_password_token(),
        user_id=user.id,
        _external=True,
    )

    # email_body = render_template_string(
    #     reset_password_email_html_content, reset_password_url=reset_password_url
    # )
    email_body = reset_password_url

    message = EmailMessage(
        subject="Reset your password",
        body=email_body,
        to=[user.email],
    )
    message.content_subtype = "html"

    message.send()


def generate_reset_password_token(self):
    serializer = URLSafeTimedSerializer(os.getenv("FLASK_CONFIG_SECRET"))
    return serializer.dumps(self.email, salt=self.password_hash)

#https://itsdangerous.palletsprojects.com/en/stable/