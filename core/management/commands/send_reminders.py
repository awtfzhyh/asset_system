from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.utils.timezone import now
from datetime import timedelta
from core.models import Request

class Command(BaseCommand):
    help = 'Sends automated reminders with direct links'

    def handle(self, *args, **options):
        today = now().date()
        tomorrow = today + timedelta(days=1)
        
        # Change this to your actual server domain (e.g., http://127.0.0.1:8000 or http://asset-system.com)
        domain = "http://127.0.0.1:8000" 

        reminders_needed = Request.objects.filter(
            status='approved',
            request_type='borrow',
            return_date__in=[today, tomorrow]
        ).exclude(asset__status='Available')

        for req in reminders_needed:
            day_type = "today" if req.return_date == today else "tomorrow"
            
            # Construct absolute URLs
            return_url = f"{domain}/return/{req.asset.id}/"
            extend_url = f"{domain}/extend/{req.asset.id}/"
            
            subject = f"ACTION REQUIRED: Asset Due {day_type.upper()}"
            message = f"""
Hi {req.user_name},

This is a reminder that the asset '{req.asset.name}' is due {day_type} ({req.return_date}).

If you are ready to return it, please fill out the return form here:
{return_url}

If you need more time, please request an extension here:
{extend_url}

Thank you,
CoE Admin Team
            """
            
            try:
                send_mail(
                    subject,
                    message,
                    'admin@unimas.my',
                    [req.email],
                    fail_silently=False,
                )
                self.stdout.write(self.style.SUCCESS(f'Sent link-enabled reminder to {req.user_name}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Failed to send: {e}'))