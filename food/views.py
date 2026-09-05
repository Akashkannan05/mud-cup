from django.db.models import Count, F, ExpressionWrapper, DecimalField, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Food, Category, Banner, Combo, Order
from .serializers import (
    FoodListSerializer,
    FoodCreateSerializer,
    CategorySerializer,
    BannerSerializer,
    ComboListSerializer,
    ComboCreateSerializer,
    OrderSerializer
)
from .permissions import IsAdminOrStaff


class PublicGETMixin:
    """
    Mixin that bypasses authentication for public GET, HEAD, and OPTIONS requests.
    Prevents 401 Unauthorized errors on public endpoints when frontend passes an expired or bad token.
    """
    def get_authenticators(self):
        if self.request.method in ['GET', 'HEAD', 'OPTIONS']:
            return []
        return super().get_authenticators()


class FoodPagination(PageNumberPagination):
    page_size = 16
    page_size_query_param = 'page_size'
    max_page_size = 100


class ComboListCreateAPIView(PublicGETMixin, generics.ListCreateAPIView):
    """
    API endpoint to list combos (GET) and create a combo (POST).
    GET is public. POST requires admin or staff permissions.
    Supports optional veg filtering: ?veg=true|false or ?isVeg=true|false
    """
    pagination_class = FoodPagination

    def get_queryset(self):
        queryset = Combo.objects.filter(is_deleted=False).prefetch_related('foods__category').order_by('id')
        veg_param = self.request.query_params.get('veg') or self.request.query_params.get('isVeg')
        if veg_param is not None:
            if veg_param.lower() in ['true', '1']:
                queryset = queryset.filter(veg=True)
            elif veg_param.lower() in ['false', '0']:
                queryset = queryset.filter(veg=False)
        return queryset

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminOrStaff()]
        return [AllowAny()]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ComboCreateSerializer
        return ComboListSerializer


class ComboDetailAPIView(PublicGETMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    API endpoint to retrieve, update, or soft-delete a Combo item.
    GET is public. PUT/PATCH/DELETE require admin or staff permissions.
    """
    queryset = Combo.objects.filter(is_deleted=False).prefetch_related('foods__category')

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsAdminOrStaff()]
        return [AllowAny()]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ComboCreateSerializer
        return ComboListSerializer

    def perform_destroy(self, instance):
        instance.delete()


class BannerListCreateAPIView(PublicGETMixin, generics.ListCreateAPIView):
    """
    API endpoint to list banners (GET) and create a banner (POST).
    GET is public and returns banners where show=True. POST requires admin or staff permissions.
    """
    serializer_class = BannerSerializer

    def get_queryset(self):
        return Banner.objects.filter(show=True).order_by('id')

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminOrStaff()]
        return [AllowAny()]


class CategoryListCreateAPIView(PublicGETMixin, generics.ListCreateAPIView):
    """
    API endpoint to list categories (GET) and create a category (POST).
    GET is public. POST requires admin or staff permissions.
    Annotates food_count for total active food items (is_deleted=False) available in each category.
    """
    queryset = Category.objects.annotate(
        food_count=Count('foods', filter=Q(foods__is_deleted=False))
    ).order_by('id')
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminOrStaff()]
        return [AllowAny()]


class CategoryDetailAPIView(PublicGETMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    API endpoint to retrieve, update, or soft-delete a Category.
    GET is public. PUT/PATCH/DELETE require admin or staff permissions.
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsAdminOrStaff()]
        return [AllowAny()]

    def perform_destroy(self, instance):
        instance.delete()


class CategoryFoodListAPIView(PublicGETMixin, generics.ListAPIView):
    """
    API endpoint to list all food items belonging to a specific category ID.
    GET /api/categories/<category_id>/foods/
    """
    serializer_class = FoodListSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        category_id = self.kwargs.get('category_id')
        category = get_object_or_404(Category, pk=category_id, is_deleted=False)
        return Food.objects.filter(category=category, is_deleted=False).select_related('category').order_by('id')


class OfferFoodListAPIView(PublicGETMixin, generics.ListAPIView):
    """
    API endpoint to list food items currently on offer (discount_price > 0).
    Excludes soft-deleted foods (is_deleted=True) and soft-deleted categories.
    Ordered by the difference between price and discount_price from highest to lowest.
    GET /api/foods/offers/
    """
    serializer_class = FoodListSerializer
    pagination_class = FoodPagination
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Food.objects.filter(
            is_deleted=False,
            category__is_deleted=False,
            discount_price__gt=0
        ).annotate(
            discount_diff=ExpressionWrapper(F('price') - F('discount_price'), output_field=DecimalField())
        ).filter(
            discount_diff__gt=0
        ).order_by('-discount_diff', 'id').select_related('category')


class FoodListCreateAPIView(PublicGETMixin, generics.ListCreateAPIView):
    """
    API endpoint to list food items (GET) and create food items (POST).
    GET is public. POST requires admin or staff role permissions.
    Supports optional category filtering: ?category_id=<id> or ?category=<id> also ?veg=True | False
    """
    pagination_class = FoodPagination

    def get_queryset(self):
        queryset = Food.objects.filter(is_deleted=False, category__is_deleted=False).select_related('category').order_by('id')
        category_id = self.request.query_params.get('category_id') or self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        veg_param = self.request.query_params.get('veg') or self.request.query_params.get('isVeg')
        if veg_param is not None:
            if veg_param.lower() in ['true', '1']:
                queryset = queryset.filter(veg=True)
            elif veg_param.lower() in ['false', '0']:
                queryset = queryset.filter(veg=False)

        return queryset

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminOrStaff()]
        return [AllowAny()]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return FoodCreateSerializer
        return FoodListSerializer


class FoodDetailAPIView(PublicGETMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    API endpoint to retrieve, update, or soft-delete a Food item.
    GET is public. PUT/PATCH/DELETE require admin or staff permissions.
    """
    queryset = Food.objects.all().select_related('category')

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsAdminOrStaff()]
        return [AllowAny()]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return FoodCreateSerializer
        return FoodListSerializer

    def perform_destroy(self, instance):
        instance.delete()

class OrderCreateAPIView(generics.CreateAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            {'message': 'Order created successfully', 'order_id': serializer.data['orderId']},
            status=status.HTTP_201_CREATED,
            headers=headers
        )

class ActiveOrderListAPIView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [AllowAny] # Matching old behavior, alternatively IsAdminOrStaff
    
    def get_queryset(self):
        return Order.objects.filter(is_deleted=False).order_by('-placed_at')

class MyOrderListAPIView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-placed_at')

class OrderMarkPaidAPIView(APIView):
    permission_classes = [AllowAny] # Or IsAdminOrStaff

    def post(self, request, order_id, *args, **kwargs):
        order = get_object_or_404(Order, order_id=order_id)
        order.delete()
        return Response({'message': 'Order deleted successfully'}, status=status.HTTP_200_OK)


from datetime import datetime, time, timedelta
from django.utils import timezone
from django.db.models import Sum


def parse_date_range(request):
    """
    Parses optional start_date, end_date, or preset query parameters.
    Returns (start_datetime, end_datetime).
    If date filters are not provided or empty, returns (None, None) so all records are returned.
    """
    start_date_str = request.query_params.get('start_date') or request.query_params.get('startDate')
    end_date_str = request.query_params.get('end_date') or request.query_params.get('endDate')
    preset = request.query_params.get('preset')

    now = timezone.now()
    today = now.date()

    if preset:
        preset = preset.lower().strip()
        if preset == 'today':
            start = timezone.make_aware(datetime.combine(today, time.min))
            end = timezone.make_aware(datetime.combine(today, time.max))
            return start, end
        elif preset == 'yesterday':
            yesterday = today - timedelta(days=1)
            start = timezone.make_aware(datetime.combine(yesterday, time.min))
            end = timezone.make_aware(datetime.combine(yesterday, time.max))
            return start, end
        elif preset == 'this_week':
            start_of_week = today - timedelta(days=today.weekday())
            start = timezone.make_aware(datetime.combine(start_of_week, time.min))
            end = timezone.make_aware(datetime.combine(today, time.max))
            return start, end
        elif preset == 'this_month':
            start_of_month = today.replace(day=1)
            start = timezone.make_aware(datetime.combine(start_of_month, time.min))
            end = timezone.make_aware(datetime.combine(today, time.max))
            return start, end

    start_dt, end_dt = None, None

    if start_date_str:
        try:
            d = datetime.strptime(start_date_str.split('T')[0], '%Y-%m-%d').date()
            start_dt = timezone.make_aware(datetime.combine(d, time.min))
        except (ValueError, AttributeError):
            pass

    if end_date_str:
        try:
            d = datetime.strptime(end_date_str.split('T')[0], '%Y-%m-%d').date()
            end_dt = timezone.make_aware(datetime.combine(d, time.max))
        except (ValueError, AttributeError):
            pass

    return start_dt, end_dt


class DashboardMetricsAPIView(APIView):
    """
    API endpoint to retrieve aggregated dashboard metrics:
    - Active Orders
    - Payment Till Now (Total Revenue)
    - Items Sales Count
    - Combo Sales Count
    - Total Orders
    - Total Customers
    
    Supports optional date filtering via ?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
    or ?preset=today|yesterday|this_week|this_month.
    If no date filter is provided, returns all-time data.
    Only accessible by Admin or Staff users.
    """
    permission_classes = [IsAdminOrStaff]

    def get(self, request, *args, **kwargs):
        start_dt, end_dt = parse_date_range(request)

        orders = Order.objects.filter(is_deleted=False)

        if start_dt:
            orders = orders.filter(placed_at__gte=start_dt)
        if end_dt:
            orders = orders.filter(placed_at__lte=end_dt)

        # 1. Active Orders (is_paid=False and is_deleted=False)
        active_orders = orders.filter(is_paid=False).count()

        # 2. Payment Till Now (Total sum of final_amount for paid orders, fallback to all non-deleted orders if none marked paid yet)
        paid_orders = orders.filter(is_paid=True)
        payment_till_now_val = paid_orders.aggregate(total=Sum('final_amount'))['total']
        if payment_till_now_val is None:
            payment_till_now_val = orders.aggregate(total=Sum('final_amount'))['total'] or 0.00
        payment_till_now = float(payment_till_now_val)

        # 3 & 4. Items Sales Count & Combo Sales Count
        items_sales_count = 0
        combo_sales_count = 0

        for order in orders:
            order_items = order.items if isinstance(order.items, list) else []
            for item in order_items:
                if not isinstance(item, dict):
                    continue
                qty = int(item.get('quantity') or item.get('qty') or item.get('count') or 1)
                tag = str(item.get('tag') or item.get('type') or '').upper()
                is_combo = (tag == 'COMBO') or bool(item.get('is_combo')) or bool(item.get('isCombo'))

                if is_combo:
                    combo_sales_count += qty
                else:
                    items_sales_count += qty

        # 5. Total Orders
        total_orders = orders.count()

        # 6. Total Customers (unique users or customer names)
        unique_user_ids = set(orders.exclude(user__isnull=True).values_list('user_id', flat=True))
        unique_guest_names = set(orders.filter(user__isnull=True).values_list('customer_name', flat=True))
        total_customers = len(unique_user_ids.union(unique_guest_names))

        return Response({
            'active_orders': active_orders,
            'payment_till_now': payment_till_now,
            'items_sales_count': items_sales_count,
            'combo_sales_count': combo_sales_count,
            'total_orders': total_orders,
            'total_customers': total_customers,
            'date_filter': {
                'start_date': start_dt.isoformat() if start_dt else None,
                'end_date': end_dt.isoformat() if end_dt else None
            }
        }, status=status.HTTP_200_OK)


class RecentItemSalesAPIView(APIView):
    """
    API endpoint to retrieve item-wise sales summary:
    - Item Name
    - Price (1 pc)
    - Qty Sold
    - Total Amount
    - Tag (e.g. COMBO, OFFER, or null)
    
    Supports optional date filtering via ?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
    or ?preset=today|yesterday|this_week|this_month.
    If no date filter is provided, returns all-time data.
    Only accessible by Admin or Staff users.
    """
    permission_classes = [IsAdminOrStaff]

    def get(self, request, *args, **kwargs):
        start_dt, end_dt = parse_date_range(request)

        orders = Order.objects.filter(is_deleted=False)

        if start_dt:
            orders = orders.filter(placed_at__gte=start_dt)
        if end_dt:
            orders = orders.filter(placed_at__lte=end_dt)

        item_stats = {}

        for order in orders:
            order_items = order.items if isinstance(order.items, list) else []
            for item in order_items:
                if not isinstance(item, dict):
                    continue

                name = item.get('name') or item.get('item_name') or item.get('title')
                if not name:
                    continue

                qty = int(item.get('quantity') or item.get('qty') or item.get('count') or 1)
                price = float(item.get('price') or item.get('unit_price') or item.get('unitPrice') or 0.0)

                raw_tag = item.get('tag') or item.get('type')
                tag = str(raw_tag).upper() if raw_tag else None
                if tag and tag not in ['COMBO', 'OFFER']:
                    tag = str(raw_tag)

                key = name.strip()
                if key not in item_stats:
                    item_stats[key] = {
                        'item_name': key,
                        'price': price,
                        'qty_sold': 0,
                        'total_amount': 0.0,
                        'tag': tag
                    }

                item_stats[key]['qty_sold'] += qty
                item_stats[key]['total_amount'] += (qty * price)
                if tag and not item_stats[key]['tag']:
                    item_stats[key]['tag'] = tag

        sales_list = list(item_stats.values())
        sales_list.sort(key=lambda x: (x['qty_sold'], x['total_amount']), reverse=True)

        limit_param = request.query_params.get('limit')
        if limit_param:
            try:
                limit = int(limit_param)
                results_list = sales_list[:limit]
            except ValueError:
                results_list = sales_list
        else:
            results_list = sales_list

        return Response({
            'total_items': len(sales_list),
            'count': len(results_list),
            'results': results_list,
            'date_filter': {
                'start_date': start_dt.isoformat() if start_dt else None,
                'end_date': end_dt.isoformat() if end_dt else None
            }
        }, status=status.HTTP_200_OK)

