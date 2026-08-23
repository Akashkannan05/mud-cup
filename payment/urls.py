from django.urls import path
from .views import CreateRazorpayOrderView, VerifyRazorpayPaymentView

urlpatterns = [
    path('create-order/', CreateRazorpayOrderView.as_view(), name='create_razorpay_order'),
    path('verify/', VerifyRazorpayPaymentView.as_view(), name='verify_razorpay_payment'),
]
