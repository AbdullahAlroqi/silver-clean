import os
from dotenv import load_dotenv
import smtplib
from flask import Flask
from flask_mail import Mail, Message
import logging

# Load environment variables
load_dotenv()

def check_env_vars():
    """Verify that all required environment variables are set."""
    print("Checking environment variables...")
    required_vars = ['MAIL_SERVER', 'MAIL_PORT', 'MAIL_USERNAME', 'MAIL_PASSWORD']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        return False
    
    print("✅ Environment variables present.")
    print(f"   MAIL_SERVER: {os.environ.get('MAIL_SERVER')}")
    print(f"   MAIL_PORT: {os.environ.get('MAIL_PORT')}")
    print(f"   MAIL_USERNAME: {os.environ.get('MAIL_USERNAME')}")
    # Don't print the password!
    return True

def test_smtp_connection():
    """Test raw SMTP connectivity."""
    server = os.environ.get('MAIL_SERVER')
    port = int(os.environ.get('MAIL_PORT', 587))
    use_tls = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    
    print(f"\nTesting connection to {server}:{port}...")
    try:
        with smtplib.SMTP(server, port, timeout=10) as smtp:
            smtp.set_debuglevel(1)
            print("   Connected to server.")
            if use_tls:
                smtp.starttls()
                print("   TLS started.")
            
            smtp.login(os.environ.get('MAIL_USERNAME'), os.environ.get('MAIL_PASSWORD'))
            print("   ✅ Login successful!")
            return True
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return False

def send_test_email():
    """Send a test email using Flask-Mail application context."""
    print("\nAttempting to send test email via Flask-Mail...")
    
    app = Flask(__name__)
    
    # Configure Flask-Mail
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME')
    
    mail = Mail(app)
    
    # Enable debugging
    logging.basicConfig(level=logging.DEBUG)
    
    with app.app_context():
        try:
            msg = Message("Test Email from Server",
                          sender=app.config['MAIL_USERNAME'],
                          recipients=[app.config['MAIL_USERNAME']]) # Send to self
            msg.body = "If you are reading this, email sending is working correctly on the server!"
            mail.send(msg)
            print("   ✅ Test email sent successfully!")
        except Exception as e:
            print(f"   ❌ Failed to send email: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("=== Email Verification Script ===")
    if check_env_vars():
        if test_smtp_connection():
            send_test_email()
    print("================================")
