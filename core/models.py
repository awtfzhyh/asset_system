from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone

class Asset(models.Model):
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=100)
    brand = models.CharField(max_length=100, null=True, blank=True)
    model = models.CharField(max_length=100, null=True, blank=True)
    serial_num = models.CharField(max_length=100, null=True, blank=True) 
    location = models.CharField(max_length=100)
    status = models.CharField(max_length=20)

    def __str__(self):
        return self.name
    
class Request(models.Model):
    REQUEST_TYPE = [
        ('borrow', 'Borrow'),
        ('return', 'Return'),
        ('extend', 'Extend'),
    ]

    STATUS = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    user_name = models.CharField(max_length=100)

    department = models.CharField(max_length=100, default="General")
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    item_count = models.TextField() 
    purpose = models.TextField()
    borrow_date = models.DateField(null=True, blank=True)
    return_date = models.DateField(null=True, blank=True)
    date_borrowed = models.DateField(default=timezone.now)
    request_type = models.CharField(max_length=10, choices=REQUEST_TYPE)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS, default='pending')
    department = models.CharField(max_length=100, null=True, blank=True)
    condition = models.CharField(max_length=50, null=True, blank=True)
    reason = models.TextField(null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True
    )


    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.status == 'approved':
            if self.request_type == 'borrow':
                self.asset.status = 'Borrowed'
            elif self.request_type == 'return':
                self.asset.status = 'Available'

            self.asset.save()