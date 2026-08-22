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
    OfferFoodListAPIView
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
]


