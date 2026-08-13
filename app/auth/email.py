from flask_mail import Message
from app import mail
from flask import render_template, current_app
def send_email(subject, sender, recipients, text_body, html_body):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    try:
        mail.send(msg)
        current_app.logger.info("Email delivered to SMTP for %s", recipients)
        return True
    except Exception:
        current_app.logger.exception("Email delivery failed for %s", recipients)
        return False

def send_password_reset_email(user, code):
    return send_email('[Silver Clean] Reset Your Password',
               sender=current_app.config.get('MAIL_DEFAULT_SENDER') or current_app.config.get('MAIL_USERNAME'),
               recipients=[user.email],
               text_body=render_template('email/reset_code.txt',
                                         user=user, code=code),
               html_body=render_template('email/reset_code.html',
                                         user=user, code=code))
