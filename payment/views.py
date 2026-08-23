import razorpay
from django.conf import settings
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from food.models import Order
from .models import PaymentTransaction
from .serializers import CreateRazorpayOrderSerializer, VerifyRazorpayPaymentSerializer


def get_razorpay_client():
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


class CreateRazorpayOrderView(APIView):
    """
    Idempotently creates or retrieves an active Razorpay order.
    Requires authentication and verifies that the order belongs to the requesting user.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CreateRazorpayOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        local_order_id = serializer.validated_data['order_id']

        try:
            order = Order.objects.get(order_id=local_order_id)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

        # 1. Ownership & Authorization Check
        if order.user and order.user != request.user and not (request.user.is_staff or request.user.is_superuser):
            return Response({'error': 'You do not have permission to initiate payment for this order'}, status=status.HTTP_403_FORBIDDEN)

        # 2. Idempotency Check: Prevent payment if order is already marked as paid
        if order.is_paid:
            return Response({'error': 'Order has already been paid'}, status=status.HTTP_400_BAD_REQUEST)

        # 3. Idempotency Check: Reuse existing PENDING transaction if created
        existing_tx = PaymentTransaction.objects.filter(order=order, status='PENDING').first()
        if existing_tx:
            amount_in_paise = int(existing_tx.amount * 100)
            return Response({
                'razorpay_order_id': existing_tx.razorpay_order_id,
                'amount': amount_in_paise,
                'currency': existing_tx.currency,
                'key_id': settings.RAZORPAY_KEY_ID,
                'customer_name': order.customer_name,
                'reused': True
            }, status=status.HTTP_200_OK)

        # 4. Create new Razorpay order
        amount_in_paise = int(order.final_amount * 100)
        razorpay_order_data = {
            'amount': amount_in_paise,
            'currency': 'INR',
            'receipt': str(order.order_id),
            'payment_capture': 1
        }

        if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
            return Response({
                'error': 'Razorpay API keys are missing in server/.env file. Please configure RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            client = get_razorpay_client()
            rzp_order = client.order.create(data=razorpay_order_data)
            
            PaymentTransaction.objects.create(
                order=order,
                razorpay_order_id=rzp_order['id'],
                amount=order.final_amount,
                currency='INR',
                status='PENDING'
            )

            return Response({
                'razorpay_order_id': rzp_order['id'],
                'amount': amount_in_paise,
                'currency': 'INR',
                'key_id': settings.RAZORPAY_KEY_ID,
                'customer_name': order.customer_name,
                'reused': False
            }, status=status.HTTP_201_CREATED)
        except razorpay.errors.BadRequestError as e:
            if "Authentication failed" in str(e):
                return Response({
                    'error': 'Razorpay API Key Authentication failed. Please check that RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in server/.env are valid test keys from Razorpay dashboard.'
                }, status=status.HTTP_400_BAD_REQUEST)
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class VerifyRazorpayPaymentView(APIView):
    """
    Idempotently verifies Razorpay payment signature post-checkout.
    Uses database row-level locking (select_for_update) for thread safety.
    Requires authentication and verifies order ownership.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = VerifyRazorpayPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        rzp_order_id = serializer.validated_data['razorpay_order_id']
        rzp_payment_id = serializer.validated_data['razorpay_payment_id']
        rzp_signature = serializer.validated_data['razorpay_signature']

        with transaction.atomic():
            try:
                # Lock transaction row to avoid race condition between frontend callback & webhook
                payment_tx = PaymentTransaction.objects.select_for_update().get(razorpay_order_id=rzp_order_id)
            except PaymentTransaction.DoesNotExist:
                return Response({'error': 'Payment transaction not found'}, status=status.HTTP_404_NOT_FOUND)

            # 1. Ownership & Authorization Check
            if payment_tx.order.user and payment_tx.order.user != request.user and not (request.user.is_staff or request.user.is_superuser):
                return Response({'error': 'You do not have permission to verify payment for this order'}, status=status.HTTP_403_FORBIDDEN)

            # 2. Idempotency Check: If already SUCCESS, return HTTP 200 without re-verifying
            if payment_tx.status == 'SUCCESS':
                return Response({'status': 'Payment already verified successfully', 'already_processed': True}, status=status.HTTP_200_OK)

            # 3. Verify signature via SDK
            params_dict = {
                'razorpay_order_id': rzp_order_id,
                'razorpay_payment_id': rzp_payment_id,
                'razorpay_signature': rzp_signature
            }

            try:
                client = get_razorpay_client()
                client.utility.verify_payment_signature(params_dict)
                
                # Mark transaction & order as paid atomically
                payment_tx.razorpay_payment_id = rzp_payment_id
                payment_tx.razorpay_signature = rzp_signature
                payment_tx.status = 'SUCCESS'
                payment_tx.save()

                order = payment_tx.order
                order.is_paid = True
                order.save()

                return Response({'status': 'Payment verified successfully', 'already_processed': False}, status=status.HTTP_200_OK)
            except razorpay.errors.SignatureVerificationError:
                payment_tx.status = 'FAILED'
                payment_tx.save()
                return Response({'error': 'Invalid payment signature'}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
