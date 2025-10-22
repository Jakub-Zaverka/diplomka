from flask import Flask, url_for
from flask import render_template
import os
from itsdangerous import URLSafeTimedSerializer
from flask_mail import Message
import jwt
import time
#TODO:Uninstall mailman
#from flask_mailman import EmailMessage


# from app.templates.auth.reset_password_email_content import (
#     reset_password_email_html_content
# )

# def send_reset_password_email(user):
#     reset_password_url = url_for(
#         "auth.reset_password",
#         token=user.generate_reset_password_token(),
#         user_id=user.id,
#         _external=True,
#     )

#     # email_body = render_template_string(
#     #     reset_password_email_html_content, reset_password_url=reset_password_url
#     # )
#     email_body = reset_password_url

#     message = EmailMessage(
#         subject="Reset your password",
#         body=email_body,
#         to=[user.email],
#     )
#     message.content_subtype = "html"

#     message.send()


# def generate_reset_password_token(self):
#     serializer = URLSafeTimedSerializer(os.getenv("FLASK_CONFIG_SECRET"))
#     return serializer.dumps(self.email, salt=self.password_hash)

#https://itsdangerous.palletsprojects.com/en/stable/



# def send_mail(email):
#     #import je zde aby se předešlo cyklickému importu
#     from app import mail
#     msg = Message()
#     msg.subject = "Password reset"
#     msg.recipients = [email]
#     msg.body = 'Email body'
#     print(msg)
#     mail.send(msg)

def send_reset_email(user):
    from app import app, mail
    token = user.get_reset_token()
    
    with app.app_context():  # <<< TADY JE KLÍČOVÉ
        msg = Message(
            subject="Password reset",
            recipients=[user.email],
        )
        reset_url = url_for('reset_with_token', token=token, _external=True)
        msg.html = msg.html = f"""
<p>Ahoj {user.username},</p>
<p>Pro reset hesla klikni na následující odkaz:</p>
<p><a href="{reset_url}">Resetovat heslo</a></p>
<p>Pokud jsi o reset nepožádal, tento e-mail ignoruj.</p>
"""
        mail.send(msg)


# def get_reset_token(self, expires=500):
#     return jwt.encode({'reset_password': self.username,
#                         'exp':    time() + expires},
#                         key=os.getenv('SECRET_KEY_FLASK'))