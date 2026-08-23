import os
import sys
import django

# Add script directory to Python path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Dynamically detect settings module (handles 'server.settings' vs 'Server.settings' case differences)
settings_module = None
for candidate in ['server.settings', 'Server.settings']:
    try:
        import importlib
        importlib.import_module(candidate)
        settings_module = candidate
        break
    except ImportError:
        pass

if not settings_module:
    settings_module = os.environ.get('DJANGO_SETTINGS_MODULE', 'server.settings')

os.environ['DJANGO_SETTINGS_MODULE'] = settings_module
django.setup()

from food.models import Category, Food, Banner, Combo

def seed_data():
    print(f"Starting data seeding for Mud Cup using settings: '{settings_module}'...")

    # 1. Banners
    banners_data = [
        {"title": "20% off on orders above ₹300", "tag": "TASTY20", "show": True},
        {"title": "Free Delivery on your first 3 orders", "tag": "NEWBIE", "show": True},
        {"title": "Flat ₹150 off on orders above ₹600", "tag": "BIGMEAL", "show": True},
    ]

    for b_data in banners_data:
        banner, created = Banner.objects.get_or_create(title=b_data["title"], defaults=b_data)
        if created:
            print(f"Created Banner: {banner.title}")
        else:
            print(f"Banner already exists: {banner.title}")

    # 2. Categories
    categories_data = [
        "Hot Beverages",
        "Cold Beverages",
        "Snacks & Bakes",
        "Sandwiches & Wraps",
        "Desserts",
    ]

    categories = {}
    for cat_name in categories_data:
        category, created = Category.objects.get_or_create(name=cat_name)
        categories[cat_name] = category
        if created:
            print(f"Created Category: {category.name}")
        else:
            print(f"Category already exists: {category.name}")

    # 3. Foods
    foods_data = [
        # Hot Beverages
        {"name": "Espresso Coffee", "category": categories["Hot Beverages"], "price": 120.00, "discount_price": 100.00, "veg": True},
        {"name": "Cappuccino", "category": categories["Hot Beverages"], "price": 150.00, "discount_price": 130.00, "veg": True},
        {"name": "Masala Chai", "category": categories["Hot Beverages"], "price": 60.00, "discount_price": 50.00, "veg": True},
        {"name": "Hot Chocolate", "category": categories["Hot Beverages"], "price": 180.00, "discount_price": 160.00, "veg": True},

        # Cold Beverages
        {"name": "Classic Iced Coffee", "category": categories["Cold Beverages"], "price": 160.00, "discount_price": 140.00, "veg": True},
        {"name": "Chocolate Cold Coffee", "category": categories["Cold Beverages"], "price": 180.00, "discount_price": 150.00, "veg": True},
        {"name": "Fresh Lime Soda", "category": categories["Cold Beverages"], "price": 90.00, "discount_price": 80.00, "veg": True},

        # Snacks & Bakes
        {"name": "Butter Croissant", "category": categories["Snacks & Bakes"], "price": 110.00, "discount_price": 90.00, "veg": True},
        {"name": "Garlic Bread Sticks", "category": categories["Snacks & Bakes"], "price": 140.00, "discount_price": 120.00, "veg": True},
        {"name": "Chicken Puff", "category": categories["Snacks & Bakes"], "price": 90.00, "discount_price": 80.00, "veg": False},

        # Sandwiches & Wraps
        {"name": "Paneer Tikka Sandwich", "category": categories["Sandwiches & Wraps"], "price": 180.00, "discount_price": 150.00, "veg": True},
        {"name": "Grilled Chicken Sandwich", "category": categories["Sandwiches & Wraps"], "price": 210.00, "discount_price": 180.00, "veg": False},
        {"name": "Veg Cheese Wrap", "category": categories["Sandwiches & Wraps"], "price": 160.00, "discount_price": 140.00, "veg": True},

        # Desserts
        {"name": "Choco Lava Cake", "category": categories["Desserts"], "price": 130.00, "discount_price": 110.00, "veg": True},
        {"name": "Blueberry Cheesecake", "category": categories["Desserts"], "price": 220.00, "discount_price": 190.00, "veg": True},
    ]

    food_objects = {}
    for f_data in foods_data:
        food, created = Food.objects.get_or_create(name=f_data["name"], defaults=f_data)
        food_objects[f_data["name"]] = food
        if created:
            print(f"Created Food: {food.name} (Category: {food.category.name})")
        else:
            print(f"Food already exists: {food.name}")

    # 4. Combos
    combos_data = [
        {
            "name": "Morning Energy Combo",
            "foods": [food_objects["Cappuccino"], food_objects["Butter Croissant"]],
            "combo_reduced_price": 220.00,
            "veg": True,
        },
        {
            "name": "Evening Snack Deal",
            "foods": [food_objects["Chocolate Cold Coffee"], food_objects["Paneer Tikka Sandwich"]],
            "combo_reduced_price": 280.00,
            "veg": True,
        },
        {
            "name": "Chicken Snack Delight",
            "foods": [food_objects["Masala Chai"], food_objects["Chicken Puff"], food_objects["Choco Lava Cake"]],
            "combo_reduced_price": 220.00,
            "veg": False,
        },
    ]

    for c_data in combos_data:
        foods_list = c_data.pop("foods")
        original_total = sum(f.price for f in foods_list)
        c_data["original_total"] = original_total

        combo, created = Combo.objects.get_or_create(name=c_data["name"], defaults=c_data)
        combo.foods.set(foods_list)
        if created:
            print(f"Created Combo: {combo.name} (Original: ₹{original_total}, Reduced: ₹{combo.combo_reduced_price})")
        else:
            print(f"Combo already exists: {combo.name}")

    print("\nData Seeding Completed Successfully!")

if __name__ == "__main__":
    seed_data()
