import json
from rest_framework import serializers
from .models import Food, Category, Banner, Combo




class BannerSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Banner
        fields = ['id', 'title', 'tag', 'image', 'image_url', 'show']

    def validate_title(self, value):
        if not value or len(value.strip()) < 1:
            raise serializers.ValidationError("Banner title must be at least 1 character long.")
        return value.strip()

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image:
            if request is not None:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class CategorySerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    image = serializers.ImageField(write_only=True, required=False)
    food_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'image', 'image_url', 'food_count']

    def validate_name(self, value):
        if not value or len(value.strip()) < 1:
            raise serializers.ValidationError("Category name must be at least 1 character long.")
        return value.strip()

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image:
            if request is not None:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

    def get_food_count(self, obj):
        if hasattr(obj, 'food_count'):
            return obj.food_count
        return obj.foods.filter(is_deleted=False).count()


class FoodListSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    category = serializers.CharField(source='category.name', read_only=True)
    isVeg = serializers.BooleanField(source='veg')
    discount_amount = serializers.SerializerMethodField()

    class Meta:
        model = Food
        fields = [
            'id',
            'image_url',
            'name',
            'category',
            'isVeg',
            'price',
            'discount_price',
            'discount_amount',
        ]

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image:
            if request is not None:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

    def get_discount_amount(self, obj):
        if obj.price is not None and obj.discount_price is not None:
            diff = obj.price - obj.discount_price
            if diff > 0 and obj.discount_price > 0:
                return str(diff)
        return "0.00"


class FoodCreateSerializer(serializers.ModelSerializer):
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        write_only=True
    )
    veg = serializers.BooleanField(default=True, required=False)

    class Meta:
        model = Food
        fields = [
            'id',
            'name',
            'category_id',
            'price',
            'discount_price',
            'veg',
            'image',
        ]

    def validate_name(self, value):
        if not value or len(value.strip()) < 1:
            raise serializers.ValidationError("Food name must be at least 1 character long.")
        return value.strip()

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than 0.")
        return value

    def validate_discount_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Discount price cannot be negative.")
        return value

    def validate(self, attrs):
        price = attrs.get('price')
        discount_price = attrs.get('discount_price', 0)

        if price is not None and discount_price is not None:
            if discount_price >= price:
                raise serializers.ValidationError({
                    'discount_price': "Discount price must be less than the regular price."
                })
        return attrs

    def to_representation(self, instance):
        return FoodListSerializer(instance, context=self.context).data


class ComboListSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    foods = FoodListSerializer(many=True, read_only=True)
    isVeg = serializers.BooleanField(source='veg')

    class Meta:
        model = Combo
        fields = [
            'id',
            'name',
            'original_total',
            'combo_reduced_price',
            'isVeg',
            'image_url',
            'foods',
        ]

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image:
            if request is not None:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class ComboCreateSerializer(serializers.ModelSerializer):
    food_ids = serializers.PrimaryKeyRelatedField(
        queryset=Food.objects.filter(is_deleted=False),
        many=True,
        source='foods',
        write_only=True
    )
    veg = serializers.BooleanField(default=True, required=False)

    class Meta:
        model = Combo
        fields = [
            'id',
            'name',
            'original_total',
            'combo_reduced_price',
            'food_ids',
            'veg',
            'image',
        ]

    def to_internal_value(self, data):
        if hasattr(data, 'getlist'):
            data = data.copy()
            food_ids = data.getlist('food_ids')
            if len(food_ids) == 1 and isinstance(food_ids[0], str):
                val = food_ids[0].strip()
                if val.startswith('[') and val.endswith(']'):
                    try:
                        parsed = json.loads(val.replace("'", '"'))
                        data.setlist('food_ids', [str(i) for i in parsed])
                    except Exception:
                        pass
                elif ',' in val:
                    parsed = [i.strip() for i in val.split(',') if i.strip()]
                    data.setlist('food_ids', parsed)
        elif isinstance(data, dict) and 'food_ids' in data:
            val = data['food_ids']
            if isinstance(val, str):
                val_str = val.strip()
                if val_str.startswith('[') and val_str.endswith(']'):
                    try:
                        parsed = json.loads(val_str.replace("'", '"'))
                        data = dict(data)
                        data['food_ids'] = parsed
                    except Exception:
                        pass
                elif ',' in val_str:
                    parsed = [i.strip() for i in val_str.split(',') if i.strip()]
                    data = dict(data)
                    data['food_ids'] = parsed

        return super().to_internal_value(data)


    def validate_name(self, value):
        if not value or len(value.strip()) < 1:
            raise serializers.ValidationError("Combo name must be at least 1 character long.")
        return value.strip()

    def validate_combo_reduced_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Combo reduced price must be greater than 0.")
        return value

    def validate_food_ids(self, value):
        if not value or len(value) < 1:
            raise serializers.ValidationError("Combo must include at least one food item.")
        return value

    def create(self, validated_data):
        foods = validated_data.pop('foods', [])
        original_total = validated_data.get('original_total', 0)
        if not original_total or original_total == 0:
            calculated_total = sum(food.price for food in foods)
            validated_data['original_total'] = calculated_total

        combo = Combo.objects.create(**validated_data)
        combo.foods.set(foods)
        return combo

    def update(self, instance, validated_data):
        foods = validated_data.pop('foods', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if foods is not None:
            instance.foods.set(foods)
        return instance

    def to_representation(self, instance):
        return ComboListSerializer(instance, context=self.context).data

