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
        return Order.objects.filter(is_paid=False).order_by('-placed_at')

class MyOrderListAPIView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-placed_at')

class OrderMarkPaidAPIView(APIView):
    permission_classes = [AllowAny] # Or IsAdminOrStaff

    def post(self, request, order_id, *args, **kwargs):
        order = get_object_or_404(Order, order_id=order_id)
        order.is_paid = True
        order.save()
        return Response({'message': 'Order marked as paid'}, status=status.HTTP_200_OK)
