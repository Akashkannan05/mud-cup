import io
from PIL import Image
from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient
from user.models import UserDetails
from .models import Category, Food, Banner, Combo, Order



def create_test_image():
    file = io.BytesIO()
    image = Image.new('RGB', (10, 10), color='red')
    image.save(file, 'png')
    file.seek(0)
    return SimpleUploadedFile("test.png", file.read(), content_type="image/png")


class BannerListCreateAPIViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = UserDetails.objects.create_user(
            username='admin_user_banner', password='password123', role='admin'
        )
        self.customer = UserDetails.objects.create_user(
            username='customer_user_banner', password='password123', role='customer'
        )

    def test_get_banners_public(self):
        Banner.objects.create(title='Summer Sale', tag='Discount', show=True)
        Banner.objects.create(title='Hidden Sale', tag='Hidden', show=False)
        url = reverse('banner-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['title'], 'Summer Sale')
        self.assertEqual(data[0]['tag'], 'Discount')
        self.assertTrue(data[0]['show'])


    def test_post_banner_customer_forbidden(self):
        self.client.force_authenticate(user=self.customer)
        url = reverse('banner-list')
        response = self.client.post(url, {'title': 'New Banner', 'tag': 'Special', 'show': True})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_post_banner_admin_success(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('banner-list')
        image = create_test_image()
        response = self.client.post(url, {'title': 'Weekend Offer', 'tag': '50% OFF', 'show': True, 'image': image}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data['title'], 'Weekend Offer')
        self.assertEqual(data['tag'], '50% OFF')
        self.assertTrue(data['show'])
        self.assertTrue('/media/banners/' in data['image_url'])




class CategoryListCreateAPIViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = UserDetails.objects.create_user(
            username='admin_user', password='password123', role='admin'
        )
        self.customer = UserDetails.objects.create_user(
            username='customer_user', password='password123', role='customer'
        )

    def test_post_category_unauthorized_for_customer(self):
        self.client.force_authenticate(user=self.customer)
        url = reverse('category-list')
        response = self.client.post(url, {'name': 'Dessert'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_post_category_admin_with_image_upload(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('category-list')
        image = create_test_image()
        response = self.client.post(url, {'name': 'Beverages', 'image': image}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data['name'], 'Beverages')
        self.assertTrue('/media/categories/' in data['image_url'])

    def test_get_categories_public(self):
        cat = Category.objects.create(name='Starters')
        Food.objects.create(name='Soup', category=cat, price=120.00)
        Food.objects.create(name='Spring Roll', category=cat, price=180.00)
        Food.objects.create(name='Deleted Salad', category=cat, price=100.00, is_deleted=True)
        url = reverse('category-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(len(data) >= 1)
        first = data[0]
        self.assertIn('food_count', first)
        self.assertEqual(first['food_count'], 2)


    def test_get_foods_by_category_id_success(self):
        cat1 = Category.objects.create(name='Starters')
        cat2 = Category.objects.create(name='Desserts')
        Food.objects.create(name='Soup', category=cat1, price=120.00, veg=True)
        Food.objects.create(name='Ice Cream', category=cat2, price=90.00, veg=True)

        url = reverse('category-foods-list', kwargs={'category_id': cat1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'Soup')
        self.assertEqual(data[0]['category'], 'Starters')

    def test_get_foods_by_category_id_404(self):
        url = reverse('category-foods-list', kwargs={'category_id': 9999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)




class FoodListCreateAPIViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name='Main Course')

        # Users
        self.customer = UserDetails.objects.create_user(
            username='customer_user', password='password123', role='customer'
        )
        self.staff_user = UserDetails.objects.create_user(
            username='staff_user', password='password123', role='staff'
        )
        self.admin_user = UserDetails.objects.create_user(
            username='admin_user', password='password123', role='admin'
        )

        # Pre-populate items for GET pagination test
        for i in range(20):
            Food.objects.create(
                name=f'Food Item {i+1}',
                category=self.category,
                price=100.00 + i,
                discount_price=10.00,
                veg=(i % 2 == 0)
            )

    def test_get_food_list_public_access(self):
        url = reverse('food-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['count'], 20)
        self.assertEqual(len(data['results']), 16)

    def test_get_food_list_filtered_by_veg(self):
        url = reverse('food-list') + '?veg=true'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['count'], 10)
        for item in data['results']:
            self.assertTrue(item['isVeg'])

        url_nonveg = reverse('food-list') + '?veg=false'
        response_nonveg = self.client.get(url_nonveg)
        self.assertEqual(response_nonveg.status_code, status.HTTP_200_OK)
        data_nonveg = response_nonveg.json()
        self.assertEqual(data_nonveg['count'], 10)
        for item in data_nonveg['results']:
            self.assertFalse(item['isVeg'])


    def test_post_food_unauthenticated_forbidden(self):
        url = reverse('food-list')
        payload = {
            'name': 'Pasta',
            'category_id': self.category.id,
            'price': '250.00',
            'discount_price': '200.00',
            'veg': True
        }
        response = self.client.post(url, payload)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_post_food_customer_forbidden(self):
        self.client.force_authenticate(user=self.customer)
        url = reverse('food-list')
        payload = {
            'name': 'Pasta',
            'category_id': self.category.id,
            'price': '250.00',
            'discount_price': '200.00',
            'veg': True
        }
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_post_food_staff_success_with_image(self):
        self.client.force_authenticate(user=self.staff_user)
        url = reverse('food-list')
        image = create_test_image()
        payload = {
            'name': 'Paneer Butter Masala',
            'category_id': self.category.id,
            'price': '350.00',
            'discount_price': '300.00',
            'veg': True,
            'image': image
        }
        response = self.client.post(url, payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data['name'], 'Paneer Butter Masala')
        self.assertEqual(data['category'], 'Main Course')
        self.assertTrue(data['isVeg'])
        self.assertTrue('/media/foods/' in data['image_url'])

    def test_post_food_admin_success(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('food-list')
        payload = {
            'name': 'Chicken Biryani',
            'category_id': self.category.id,
            'price': '400.00',
            'discount_price': '350.00',
            'veg': False
        }
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data['name'], 'Chicken Biryani')
        self.assertFalse(data['isVeg'])

    def test_post_food_validation_errors(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('food-list')

        # Invalid price (<= 0) and discount_price >= price
        payload = {
            'name': '',
            'category_id': self.category.id,
            'price': '0.00',
            'discount_price': '10.00',
            'veg': True
        }

        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertIn('name', data)
        self.assertIn('price', data)

    def test_offer_food_list_ordering_by_discount_difference(self):
        cat = Category.objects.create(name='Special Offers')
        # Item 1: diff = 250 (300 - 50)
        item1 = Food.objects.create(name='Pizza', category=cat, price=300.00, discount_price=50.00)
        # Item 2: diff = 350 (500 - 150) -> Highest offer
        item2 = Food.objects.create(name='Combo Meal', category=cat, price=500.00, discount_price=150.00)
        # Item 3: diff = 0 (No offer)
        item3 = Food.objects.create(name='Regular Soda', category=cat, price=50.00, discount_price=0.00)


        url = reverse('offer-food-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.json()['results']

        # Ensure regular soda without discount_price is excluded
        offer_names = [item['name'] for item in results]
        self.assertIn('Combo Meal', offer_names)
        self.assertIn('Pizza', offer_names)
        self.assertNotIn('Regular Soda', offer_names)

        # Ensure highest discount diff (Combo Meal = 150) comes before Pizza (50)
        combo_index = offer_names.index('Combo Meal')
        pizza_index = offer_names.index('Pizza')
        self.assertTrue(combo_index < pizza_index)

    def test_soft_delete_food_api(self):
        self.client.force_authenticate(user=self.admin_user)
        food_item = Food.objects.create(name='Tacos', category=self.category, price=150.00)
        url = reverse('food-detail', kwargs={'pk': food_item.pk})
        
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Check default manager excludes it
        self.assertFalse(Food.objects.filter(pk=food_item.pk).exists())

        # Check all_objects contains soft deleted item
        deleted_item = Food.all_objects.get(pk=food_item.pk)
        self.assertTrue(deleted_item.is_deleted)
        self.assertIsNotNone(deleted_item.deleted_at)

    def test_soft_delete_category_api(self):
        self.client.force_authenticate(user=self.admin_user)
        cat = Category.objects.create(name='Snacks')
        food_item = Food.objects.create(name='Chips', category=cat, price=40.00)
        url = reverse('category-detail', kwargs={'pk': cat.pk})

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Check category soft deleted
        self.assertFalse(Category.objects.filter(pk=cat.pk).exists())
        self.assertTrue(Category.all_objects.get(pk=cat.pk).is_deleted)

        # Check related food items soft deleted
        self.assertFalse(Food.objects.filter(pk=food_item.pk).exists())
        self.assertTrue(Food.all_objects.get(pk=food_item.pk).is_deleted)


class ComboAPIViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name='Combo Items')
        self.admin_user = UserDetails.objects.create_user(
            username='admin_combo', password='password123', role='admin'
        )
        self.customer = UserDetails.objects.create_user(
            username='customer_combo', password='password123', role='customer'
        )
        self.food1 = Food.objects.create(name='Burger', category=self.category, price=150.00)
        self.food2 = Food.objects.create(name='Fries', category=self.category, price=100.00)

    def test_post_combo_admin_success(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('combo-list')
        payload = {
            'name': 'Burger & Fries Combo',
            'combo_reduced_price': '200.00',
            'food_ids': [self.food1.id, self.food2.id],
            'veg': True
        }
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data['name'], 'Burger & Fries Combo')
        self.assertEqual(float(data['original_total']), 250.00)
        self.assertEqual(len(data['foods']), 2)

    def test_post_combo_admin_with_string_food_ids(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('combo-list')
        payload = {
            'name': 'String Combo Test',
            'combo_reduced_price': '180.00',
            'food_ids': f"['{self.food1.id}', '{self.food2.id}']",
            'veg': 'True'
        }
        response = self.client.post(url, payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data['name'], 'String Combo Test')
        self.assertEqual(len(data['foods']), 2)


    def test_get_combo_list_public(self):
        combo = Combo.objects.create(
            name='Party Pack',
            original_total=500.00,
            combo_reduced_price=400.00,
            veg=False
        )
        combo.foods.add(self.food1, self.food2)

        url = reverse('combo-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()['results']
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'Party Pack')

    def test_soft_delete_combo_api(self):
        self.client.force_authenticate(user=self.admin_user)
        combo = Combo.objects.create(
            name='Delete Me',
            original_total=300.00,
            combo_reduced_price=250.00
        )
        url = reverse('combo-detail', kwargs={'pk': combo.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertFalse(Combo.objects.filter(pk=combo.pk).exists())
        deleted_combo = Combo.all_objects.get(pk=combo.pk)
        self.assertTrue(deleted_combo.is_deleted)


class DashboardAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = UserDetails.objects.create_user(username='admin_dash', password='pwd', role='admin')
        self.customer_user = UserDetails.objects.create_user(username='cust_dash', password='pwd', role='customer')

        # Order 1: Paid, Food items + Combo item
        Order.objects.create(
            order_id='ORD1',
            user=self.customer_user,
            customer_name='John Doe',
            table_number='Table 1',
            items=[
                {'name': 'Classic Mud Cup', 'price': 150.0, 'quantity': 2, 'tag': None},
                {'name': 'Couples Combo', 'price': 450.0, 'quantity': 1, 'tag': 'COMBO'}
            ],
            total_amount=750.00,
            final_amount=750.00,
            is_paid=True
        )

        # Order 2: Active / Unpaid, Food items
        Order.objects.create(
            order_id='ORD2',
            user=self.customer_user,
            customer_name='Jane Smith',
            table_number='Table 2',
            items=[
                {'name': 'Cold Coffee', 'price': 90.0, 'quantity': 3, 'tag': None},
                {'name': 'Spicy Paneer Wrap', 'price': 120.0, 'quantity': 1, 'tag': 'OFFER'}
            ],
            total_amount=390.00,
            final_amount=390.00,
            is_paid=False
        )

    def test_dashboard_metrics_unauthenticated_forbidden(self):
        url = reverse('dashboard-metrics')
        response = self.client.get(url)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_dashboard_metrics_customer_forbidden(self):
        self.client.force_authenticate(user=self.customer_user)
        url = reverse('dashboard-metrics')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_dashboard_metrics_admin_success(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('dashboard-metrics')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['active_orders'], 1)
        self.assertEqual(data['payment_till_now'], 750.00)
        self.assertEqual(data['items_sales_count'], 6)  # 2 Mud Cup + 3 Cold Coffee + 1 Wrap = 6
        self.assertEqual(data['combo_sales_count'], 1)  # 1 Couples Combo
        self.assertEqual(data['total_orders'], 2)
        self.assertEqual(data['total_customers'], 1)

    def test_recent_item_sales_admin_success(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('recent-item-sales')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['count'], 4)
        results = data['results']
        item_names = [item['item_name'] for item in results]
        self.assertIn('Classic Mud Cup', item_names)
        self.assertIn('Couples Combo', item_names)
        self.assertIn('Cold Coffee', item_names)
        self.assertIn('Spicy Paneer Wrap', item_names)

        mud_cup = next(item for item in results if item['item_name'] == 'Classic Mud Cup')
        self.assertEqual(mud_cup['qty_sold'], 2)
        self.assertEqual(mud_cup['total_amount'], 300.0)

    def test_dashboard_metrics_with_preset_today(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('dashboard-metrics') + '?preset=today'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIsNotNone(data['date_filter']['start_date'])
        self.assertIsNotNone(data['date_filter']['end_date'])





