from flask_mail import Message
from app import mail
from flask import render_template, current_app
from threading import Thread

def send_async_email(app, msg):
    with app.app_context():
        try:
            print(f"Async Thread: Sending email to {msg.recipients}...")
            mail.send(msg)
            print(f"Async Thread: Email sent successfully to {msg.recipients}")
        except Exception as e:
            # Print to stdout/stderr so it shows in Gunicorn logs
            print(f"Async Thread ERROR: Failed to send email to {msg.recipients}")
            print(f"Error details: {str(e)}")
            import traceback
            traceback.print_exc()
            # Also use app logger if available
            try:
                app.logger.error(f"Async Email Failed: {str(e)}")
            except:
                pass

def send_email(subject, sender, recipients, text_body, html_body):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    Thread(target=send_async_email, args=(current_app._get_current_object(), msg)).start()

def send_password_reset_email(user, code):
    send_email('[Silver Clean] Reset Your Password',
               sender=current_app.config['ADMINS'][0],
               recipients=[user.email],
               text_body=render_template('email/reset_code.txt',
                                         user=user, code=code),
               html_body=render_template('email/reset_code.html',
                                         user=user, code=code))
