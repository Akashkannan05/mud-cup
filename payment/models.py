from django.db import models
from food.models import Order

class PaymentTransaction(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
    )

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    razorpay_order_id = models.CharField(max_length=100, unique=True)
    razorpay_payment_id = models.CharField(max_length=100, null=True, blank=True)
    razorpay_signature = models.CharField(max_length=255, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # In Rupees
    currency = models.CharField(max_length=10, default='INR')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payment_transaction'

    def __str__(self):
        return f"{self.razorpay_order_id} - {self.status}"
