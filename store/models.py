from django.db import models
from django.db.models import Case, When, IntegerField
from django.contrib.auth.models import User
from django.utils.text import slugify

SIZE_ORDER = ['XS', 'S', 'M', 'L', 'XL', '2XL', '3XL', '4XL', '5XL', 'FREE']


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'School Level'
        verbose_name_plural = 'School Levels'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class UniformType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class SizeOption(models.Model):
    code = models.CharField(max_length=10, unique=True)
    label = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = [
            Case(
                *[When(code=code, then=i) for i, code in enumerate(SIZE_ORDER)],
                default=99,
                output_field=IntegerField(),
            ),
            'code',
        ]

    def __str__(self):
        return f'{self.code} - {self.label}'


class StoreClosure(models.Model):
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_date', '-created_at']

    def __str__(self):
        if self.start_date == self.end_date:
            return f'{self.start_date} - {self.reason}'
        return f'{self.start_date} to {self.end_date} - {self.reason}'

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.end_date < self.start_date:
            raise ValidationError({'end_date': 'End date cannot be before start date.'})


class Product(models.Model):
    category = models.ManyToManyField(Category, related_name='products')
    uniform_type = models.ForeignKey(UniformType, on_delete=models.PROTECT, related_name='products')
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    image = models.ImageField(upload_to='products/')
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def total_stock(self):
        return sum(v.stock for v in self.variants.all())

    def in_stock(self):
        return self.total_stock() > 0

    def get_min_price(self):
        prices = [v.get_price() for v in self.variants.all()]
        return min(prices) if prices else 0

    def prices_vary(self):
        prices = {v.get_price() for v in self.variants.all()}
        return len(prices) > 1


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    size = models.ForeignKey(SizeOption, on_delete=models.PROTECT, related_name='variants')
    stock = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                help_text='Leave blank to use the base product price.')

    class Meta:
        unique_together = ('product', 'size')
        ordering = [
            Case(
                *[When(size__code=code, then=i) for i, code in enumerate(SIZE_ORDER)],
                default=99,
                output_field=IntegerField(),
            ),
            'size__code',
        ]

    def __str__(self):
        return f'{self.product.name} - {self.size.code}'

    def get_price(self):
        if self.price is not None:
            return self.price
        if self.product.price is not None:
            return self.product.price
        return 0


class UserProfile(models.Model):
    ROLE_STUDENT = 'student'
    ROLE_STAFF = 'staff'
    ROLE_MANAGER = 'manager'
    ROLE_CHOICES = [
        (ROLE_STUDENT, 'Student / Customer'),
        (ROLE_STAFF, 'Staff / Store Clerk'),
        (ROLE_MANAGER, 'Admin / Store Manager'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_STUDENT)
    student_id = models.CharField(max_length=50, unique=True, blank=True, null=True)
    school_level = models.ForeignKey(
        'Category', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='students'
    )
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    def __str__(self):
        return f'{self.user.username} Profile'

    def is_store_staff(self):
        return self.role in {self.ROLE_STAFF, self.ROLE_MANAGER}

    def is_manager(self):
        return self.role == self.ROLE_MANAGER


class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Cart of {self.user.username}'

    def get_total(self):
        return sum(item.get_subtotal() for item in self.items.all())

    def get_item_count(self):
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('cart', 'variant')

    def __str__(self):
        return f'{self.quantity}x {self.variant}'

    def get_subtotal(self):
        return self.variant.get_price() * self.quantity


ORDER_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('confirmed', 'Approved'),
    ('rejected', 'Rejected'),
    ('processing', 'Available / Preparing'),
    ('ready', 'Ready for Pickup'),
    ('completed', 'Claimed / Picked Up'),
    ('cancelled', 'Cancelled'),
    ('expired', 'Expired / Unclaimed'),
    ('refunded', 'Refunded'),
]


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='orders')
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')
    stock_deducted = models.BooleanField(default=False)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    pickup_date = models.DateField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, default='')
    contact_email = models.EmailField(blank=True, default='')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Order #{self.pk} by {self.user.username}'

    def get_status_badge(self):
        badges = {
            'pending': 'warning',
            'confirmed': 'info',
            'processing': 'primary',
            'ready': 'success',
            'completed': 'success',
            'cancelled': 'danger',
            'rejected': 'danger',
            'expired': 'danger',
            'refunded': 'secondary',
        }
        return badges.get(self.status, 'secondary')


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='order_status_actions',
        blank=True,
        null=True,
    )
    from_status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, blank=True)
    to_status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Order status history'

    def __str__(self):
        actor = self.actor.get_username() if self.actor else 'System'
        return f'Order #{self.order_id}: {self.get_from_status_label()} -> {self.get_to_status_display()} by {actor}'

    def get_from_status_label(self):
        if not self.from_status:
            return 'Created'
        return dict(ORDER_STATUS_CHOICES).get(self.from_status, self.from_status.title())

    def get_actor_label(self):
        if not self.actor:
            return 'System'
        return self.actor.get_full_name() or self.actor.get_username()


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='notifications', blank=True, null=True)
    title = models.CharField(max_length=120)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} for {self.user.username}'


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'Image for {self.product.name}'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT, related_name='order_items')
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f'{self.quantity}x {self.variant} (Order #{self.order.pk})'

    def get_subtotal(self):
        return self.unit_price * self.quantity
