from django.urls import path
from .views import (
    BannerListCreateAPIView,
    ComboListCreateAPIView,
    ComboDetailAPIView,
    FoodListCreateAPIView,
    FoodDetailAPIView,
    CategoryListCreateAPIView,
    CategoryDetailAPIView,
    CategoryFoodListAPIView,
    OfferFoodListAPIView,
    OrderCreateAPIView,
    ActiveOrderListAPIView,
    MyOrderListAPIView,
    OrderMarkPaidAPIView,
    DashboardMetricsAPIView,
    RecentItemSalesAPIView,
)

urlpatterns = [
    path('banners/', BannerListCreateAPIView.as_view(), name='banner-list'),
    path('categories/', CategoryListCreateAPIView.as_view(), name='category-list'),
    path('categories/<int:pk>/', CategoryDetailAPIView.as_view(), name='category-detail'),
    path('categories/<int:category_id>/foods/', CategoryFoodListAPIView.as_view(), name='category-foods-list'),
    path('foods/offers/', OfferFoodListAPIView.as_view(), name='offer-food-list'),
    path('foods/', FoodListCreateAPIView.as_view(), name='food-list'),
    path('foods/<int:pk>/', FoodDetailAPIView.as_view(), name='food-detail'),
    path('combos/', ComboListCreateAPIView.as_view(), name='combo-list'),
    path('combos/<int:pk>/', ComboDetailAPIView.as_view(), name='combo-detail'),
    path('orders/', OrderCreateAPIView.as_view(), name='order-create'),
    path('orders/active/', ActiveOrderListAPIView.as_view(), name='order-active'),
    path('orders/my-orders/', MyOrderListAPIView.as_view(), name='order-my'),
    path('orders/<str:order_id>/paid/', OrderMarkPaidAPIView.as_view(), name='order-mark-paid'),
    path('dashboard/metrics/', DashboardMetricsAPIView.as_view(), name='dashboard-metrics'),
    path('dashboard/recent-item-sales/', RecentItemSalesAPIView.as_view(), name='recent-item-sales'),
]


