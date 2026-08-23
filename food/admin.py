from django.contrib import admin
from .models import Category, Food, Banner, Combo, Order


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'tag', 'image_url', 'show')
    search_fields = ('title', 'tag')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'image_url', 'is_deleted', 'deleted_at')
    list_filter = ('is_deleted',)
    search_fields = ('name',)

    def get_queryset(self, request):
        return Category.all_objects.all()


@admin.register(Food)
class FoodAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category', 'price', 'discount_price', 'veg', 'image_url', 'is_deleted', 'deleted_at')
    list_filter = ('category', 'veg', 'is_deleted')
    search_fields = ('name',)

    def get_queryset(self, request):
        return Food.all_objects.all()


@admin.register(Combo)
class ComboAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'original_total', 'combo_reduced_price', 'veg', 'image_url', 'is_deleted', 'deleted_at')
    list_filter = ('veg', 'is_deleted')
    search_fields = ('name',)
    filter_horizontal = ('foods',)

    def get_queryset(self, request):
        return Combo.all_objects.all()


admin.site.register(Order)
