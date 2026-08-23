from rest_framework import serializers
from .models import PaymentTransaction

class CreateRazorpayOrderSerializer(serializers.Serializer):
    order_id = serializers.CharField(max_length=100)

class VerifyRazorpayPaymentSerializer(serializers.Serializer):
    razorpay_order_id = serializers.CharField(max_length=100)
    razorpay_payment_id = serializers.CharField(max_length=100)
    razorpay_signature = serializers.CharField(max_length=255)
