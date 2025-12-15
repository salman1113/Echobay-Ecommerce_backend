from django.db.models.signals import post_save
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
import threading

User = get_user_model()

# --- 1. WELCOME EMAIL (Registration) ---
def send_welcome_email_thread(user_email, username):
    try:
        subject = 'Welcome to EchoBay! 🎉'
        message = f'Hi {username},\n\nThank you for registering with EchoBay. We are excited to have you on board!\n\nHappy Shopping!'
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user_email],
            fail_silently=False,
        )
        print(f"✅ Welcome email sent to {user_email}")
    except Exception as e:
        print(f"❌ Failed to send welcome email: {e}")

@receiver(post_save, sender=User)
def on_user_signup(sender, instance, created, **kwargs):
    # 'created=True' means it's a new user
    if created and instance.email:
        print(f"🆕 New User Registered: {instance.username}")
        
        display_name = instance.name if hasattr(instance, 'name') and instance.name else instance.username
        
        email_thread = threading.Thread(
            target=send_welcome_email_thread, 
            args=(instance.email, display_name)
        )
        email_thread.start()


# --- 2. LOGIN ALERT (Login) ---
def send_login_email_thread(user_email, username):
    try:
        subject = 'Security Alert: New Login Detected'
        message = f'Hi {username},\n\nYou have successfully logged into your EchoBay account.\n\nIf this was not you, please contact support immediately.'
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user_email],
            fail_silently=False,
        )
        print(f"✅ Login email sent to {user_email}")
    except Exception as e:
        print(f"❌ Failed to send login email: {e}")

@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    print(f"🔔 User logged in: {user.username}")
    
    if user.email:
        first = getattr(user, 'first_name', '')
        last = getattr(user, 'last_name', '')
        full_name = f"{first} {last}".strip()
        display_name = full_name if full_name else user.username

        email_thread = threading.Thread(
            target=send_login_email_thread, 
            args=(user.email, display_name)
        )
        email_thread.start()