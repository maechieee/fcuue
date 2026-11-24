from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils.text import slugify
from store.models import Category, UniformType, SizeOption, Product, ProductVariant, UserProfile


CATEGORIES = [
    {'name': 'Kindergarten', 'description': 'Uniform items for kindergarten students.'},
    {'name': 'Elementary', 'description': 'Uniform items for elementary students.'},
    {'name': 'College', 'description': 'Official college uniform items.'},
    {'name': 'Senior High School', 'description': 'Uniform items for SHS students.'},
    {'name': 'Junior High School', 'description': 'Uniform items for JHS students.'},
]

PRODUCTS = [
    {'name': 'College White Long-Sleeve Polo Shirt', 'category': 'College', 'type': 'Polo', 'price': '350.00',
     'description': 'Crisp white long-sleeve polo shirt with embroidered school logo. Made from high-quality cotton blend.',
     'sizes': [('S',20),('M',25),('L',20),('XL',15),('2XL',10)]},
    {'name': 'College White Short-Sleeve Polo Shirt', 'category': 'College', 'type': 'Polo', 'price': '280.00',
     'description': 'Classic white short-sleeve polo shirt. Comfortable and breathable for daily school wear.',
     'sizes': [('S',18),('M',22),('L',18),('XL',12),('2XL',8)]},
    {'name': 'College Navy Blue Slacks', 'category': 'College', 'type': 'Pants', 'price': '450.00',
     'description': 'Formal navy blue slacks with comfortable waistband. Ideal for male students.',
     'sizes': [('S',15),('M',20),('L',18),('XL',12),('2XL',8)]},
    {'name': 'SHS Khaki Pants', 'category': 'Senior High School', 'type': 'Pants', 'price': '420.00',
     'description': 'Classic khaki pants made from durable fabric. Easy to maintain and long-lasting.',
     'sizes': [('S',10),('M',15),('L',12),('XL',8),('2XL',5)]},
    {'name': 'SHS Pleated Skirt (Knee Length)', 'category': 'Senior High School', 'type': 'Skirt', 'price': '380.00',
     'description': 'Elegant knee-length pleated skirt in school colors. Comfortable and modest design.',
     'sizes': [('S',15),('M',18),('L',14),('XL',8)]},
    {'name': 'SHS PE Shirt (Dry-Fit)', 'category': 'Senior High School', 'type': 'PE Uniform', 'price': '250.00',
     'description': 'Moisture-wicking dry-fit PE shirt for active students. Features school colors and logo.',
     'sizes': [('S',25),('M',30),('L',25),('XL',20),('2XL',15)]},
    {'name': 'JHS PE Shorts', 'category': 'Junior High School', 'type': 'PE Uniform', 'price': '200.00',
     'description': 'Comfortable athletic shorts for PE classes and sports activities.',
     'sizes': [('S',22),('M',25),('L',20),('XL',15),('2XL',10)]},
    {'name': 'JHS Complete Uniform Set (Male)', 'category': 'Junior High School', 'type': 'Uniform Set', 'price': '750.00',
     'description': 'Complete male school uniform set including polo shirt and slacks. Best value bundle.',
     'sizes': [('S',10),('M',15),('L',12),('XL',8),('2XL',5)]},
    {'name': 'JHS Complete Uniform Set (Female)', 'category': 'Junior High School', 'type': 'Uniform Set', 'price': '700.00',
     'description': 'Complete female school uniform set including polo shirt and pleated skirt.',
     'sizes': [('S',12),('M',15),('L',10),('XL',6)]},
    {'name': 'College Necktie', 'category': 'College', 'type': 'Accessories', 'price': '120.00',
     'description': 'Official school necktie in school colors. Pre-tied clip design available.',
     'sizes': [('FREE',50)]},
    {'name': 'SHS Black School Belt', 'category': 'Senior High School', 'type': 'Accessories', 'price': '95.00',
     'description': 'Classic black leather-look school belt with metal buckle.',
     'sizes': [('FREE',40)]},
    {'name': 'JHS White School Socks (3-pack)', 'category': 'Junior High School', 'type': 'Accessories', 'price': '85.00',
     'description': 'Pack of 3 pairs of white school socks. Made from cotton blend material.',
     'sizes': [('FREE',60)]},
]

UNIFORM_TYPES = ['Polo', 'PE Uniform', 'Blouse', 'Pants', 'Skirt', 'Accessories', 'Uniform Set']
SIZES = [
    ('S', 'Small'),
    ('M', 'Medium'),
    ('L', 'Large'),
    ('XL', 'Extra Large'),
    ('2XL', 'Double Extra Large'),
    ('3XL', 'Triple Extra Large'),
    ('FREE', 'Free Size'),
]


class Command(BaseCommand):
    help = 'Seeds the database with sample school levels, products, and admin user.'

    def handle(self, *args, **kwargs):
        # Create admin user
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser(
                username='admin',
                email='admin@unishop.ph',
                password='admin123',
                first_name='Admin',
                last_name='UniShop',
            )
            UserProfile.objects.get_or_create(user=admin, defaults={'role': UserProfile.ROLE_MANAGER})
            self.stdout.write(self.style.SUCCESS('Created admin user: admin / admin123'))
        else:
            admin = User.objects.get(username='admin')
            UserProfile.objects.update_or_create(user=admin, defaults={'role': UserProfile.ROLE_MANAGER})
            self.stdout.write('Admin user already exists.')

        if not User.objects.filter(username='clerk1').exists():
            clerk = User.objects.create_user(
                username='clerk1',
                email='clerk1@unishop.ph',
                password='clerk123',
                first_name='Store',
                last_name='Clerk',
                is_staff=True,
            )
            UserProfile.objects.get_or_create(user=clerk, defaults={'role': UserProfile.ROLE_STAFF})
            self.stdout.write(self.style.SUCCESS('Created clerk user: clerk1 / clerk123'))

        # Create school levels
        cat_map = {}
        for cat_data in CATEGORIES:
            cat, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={'description': cat_data['description']}
            )
            cat_map[cat.name] = cat
            if created:
                self.stdout.write(f'  School level: {cat.name}')

        # Create test student user. Students log in using Student ID as username.
        if not User.objects.filter(username='2026-0001').exists():
            student = User.objects.create_user(
                username='2026-0001',
                email='student1@school.edu.ph',
                password='student123',
                first_name='Maria',
                last_name='Santos',
            )
            UserProfile.objects.get_or_create(user=student, defaults={
                'role': UserProfile.ROLE_STUDENT,
                'student_id': '2026-0001',
                'school_level': cat_map.get('College'),
                'phone': '+63 912 345 6789',
                'address': 'Block 1 Lot 2, School Dormitory, Campus Road'
            })
            self.stdout.write(self.style.SUCCESS('Created student user: 2026-0001 / student123'))

        size_map = {}
        for code, label in SIZES:
            so, _ = SizeOption.objects.get_or_create(
                code=code,
                defaults={'label': label, 'is_active': True}
            )
            size_map[so.code] = so

        type_map = {}
        for type_name in UNIFORM_TYPES:
            uniform_type, created = UniformType.objects.get_or_create(
                slug=slugify(type_name),
                defaults={'name': type_name}
            )
            type_map[uniform_type.name] = uniform_type
            if created:
                self.stdout.write(f'  Uniform type: {uniform_type.name}')

        # Create products
        for p_data in PRODUCTS:
            category = cat_map.get(p_data['category'])
            if not category:
                continue
            product, created = Product.objects.get_or_create(
                name=p_data['name'],
                defaults={
                    'uniform_type': type_map[p_data['type']],
                    'price': p_data['price'],
                    'description': p_data['description'],
                    'is_available': True,
                    'image': '',
                }
            )
            if created:
                product.category.add(category)
                for size_code, stock in p_data['sizes']:
                    size_option = size_map.get(size_code)
                    if size_option:
                        ProductVariant.objects.get_or_create(
                            product=product,
                            size=size_option,
                            defaults={'stock': stock}
                        )
                self.stdout.write(f'  Product: {product.name}')

        self.stdout.write(self.style.SUCCESS('\nSeed complete! Login at /auth/login/'))
        self.stdout.write('  Admin:   admin / admin123')
        self.stdout.write('  Student: 2026-0001 / student123')
        self.stdout.write('  Admin panel: /manage/')
