import json
import os
import uuid
from datetime import date, timedelta

from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Q, Sum, Count
from django.db.models.deletion import ProtectedError
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from .models import (
    Category, UniformType, SizeOption, Product, ProductVariant, ProductImage,
    StoreClosure, Cart, CartItem, Order, OrderItem, OrderStatusHistory,
    UserProfile, Notification,
)
from .forms import (
    RegisterForm, LoginForm, UserUpdateForm, ProfileUpdateForm,
    CheckoutForm, ProductForm, ProductVariantFormSet, ProductImageFormSet,
    CategoryForm, UniformTypeForm, SizeOptionForm, StoreClosureForm,
    PickupDateForm, OrderStatusForm, StaffAccountForm, StudentAccountForm,
)


# ─── helpers ────────────────────────────────────────────────────────────────

def get_or_create_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


def get_user_role(user):
    if user.is_superuser:
        return UserProfile.ROLE_MANAGER
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile.role


def user_is_store_staff(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.is_staff and get_user_role(user) in {UserProfile.ROLE_STAFF, UserProfile.ROLE_MANAGER}


def user_is_manager(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.is_staff and get_user_role(user) == UserProfile.ROLE_MANAGER


def staff_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f'{settings.LOGIN_URL}?next={request.path}')
        if not user_is_store_staff(request.user):
            messages.error(request, 'Access denied. Store staff only.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


def manager_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f'{settings.LOGIN_URL}?next={request.path}')
        if not user_is_manager(request.user):
            messages.error(request, 'Access denied. Store manager only.')
            return redirect('manage_dashboard' if user_is_store_staff(request.user) else 'home')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


admin_required = manager_required
APPROVED_PICKUP_DATE_GRACE_DAYS = 3
STOCK_DEDUCTING_STATUSES = {'confirmed', 'processing', 'ready', 'completed'}
STOCK_RESTORING_STATUSES = {'cancelled', 'rejected', 'expired', 'refunded'}

STATUS_NOTIFICATION_MESSAGES = {
    'pending': 'Your order has been submitted and is waiting for store approval.',
    'confirmed': 'Your order was approved. You can now choose a pickup date.',
    'rejected': 'Your order was rejected. Please contact the school store if you need help.',
    'processing': 'Your order is available and being prepared.',
    'ready': 'Your order is ready for pickup. Please bring your order number and school ID.',
    'completed': 'Your order has been marked as claimed.',
    'cancelled': 'Your order has been cancelled.',
    'expired': 'Your order expired because it was not claimed.',
    'refunded': 'Your order has been marked as refunded.',
}


def notify_user(user, title, message, order=None):
    Notification.objects.create(
        user=user,
        order=order,
        title=title,
        message=message,
    )


def get_store_staff_users():
    return User.objects.filter(
        Q(is_superuser=True) | Q(is_staff=True, profile__role__in=[UserProfile.ROLE_STAFF, UserProfile.ROLE_MANAGER])
    ).distinct()


def notify_store_staff(title, message, order=None):
    for user in get_store_staff_users():
        notify_user(user, title, message, order)


def notify_order_status(order):
    label = order.get_status_display()
    message = STATUS_NOTIFICATION_MESSAGES.get(order.status, f'Your order status is now {label}.')
    notify_user(order.user, f'Order #{order.pk}: {label}', message, order)


def parse_quantity(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def has_protected_variant_delete(formset):
    has_conflict = False
    for variant_form in formset.forms:
        if not variant_form.cleaned_data:
            continue
        variant = variant_form.instance
        if (
            variant_form.cleaned_data.get('DELETE')
            and variant.pk
            and variant.order_items.exists()
        ):
            variant_form.add_error(
                None,
                'This size is used in order history. Set its stock to 0 or hide the product instead.'
            )
            has_conflict = True
    return has_conflict


def has_missing_variant_prices(formset):
    has_conflict = False
    for variant_form in formset.forms:
        data = variant_form.cleaned_data
        if not data or data.get('DELETE') or not data.get('size'):
            continue
        if data.get('price') is None:
            variant_form.add_error('price', 'Price is required for this size.')
            has_conflict = True
    return has_conflict


_TMP_IMAGE_SESSION_KEY = '_tmp_product_image'


def _stash_product_image(request, uploaded_file):
    _clear_product_image_stash(request)
    uploaded_file.seek(0)
    ext = os.path.splitext(uploaded_file.name)[1] or '.jpg'
    path = default_storage.save(
        f'temp/prod_{uuid.uuid4().hex}{ext}',
        ContentFile(uploaded_file.read()),
    )
    request.session[_TMP_IMAGE_SESSION_KEY] = path


def _clear_product_image_stash(request):
    path = request.session.pop(_TMP_IMAGE_SESSION_KEY, None)
    if path and default_storage.exists(path):
        default_storage.delete(path)



_TMP_GALLERY_KEY = '_tmp_gallery_images'


def _stash_gallery_images(request, files, formset):
    """Stash newly uploaded gallery image files; preserve previously stashed ones."""
    stash = dict(request.session.get(_TMP_GALLERY_KEY, {}))
    prefix = formset.prefix
    for i, img_form in enumerate(formset.forms):
        if img_form.instance.pk:
            continue
        field_key = f'{prefix}-{i}-image'
        if field_key in files:
            f = files[field_key]
            f.seek(0)
            ext = os.path.splitext(f.name)[1] or '.jpg'
            new_path = default_storage.save(
                f'temp/gallery_{uuid.uuid4().hex}{ext}',
                ContentFile(f.read()),
            )
            f.seek(0)
            old = stash.get(str(i))
            if old and old != new_path and default_storage.exists(old):
                default_storage.delete(old)
            stash[str(i)] = new_path
    request.session[_TMP_GALLERY_KEY] = stash
    return stash


def _clear_gallery_stash(request):
    stash = request.session.pop(_TMP_GALLERY_KEY, {})
    for path in stash.values():
        if default_storage.exists(path):
            default_storage.delete(path)


def _build_gallery_with_stash(image_formset, gallery_stash):
    """Return list of (form, stash_url_or_None) for the template."""
    result = []
    for i, img_form in enumerate(image_formset.forms):
        path = gallery_stash.get(str(i))
        url = default_storage.url(path) if path and default_storage.exists(path) else None
        result.append((img_form, url))
    return result


STAFF_ORDER_TRANSITIONS = {
    'pending': ['confirmed', 'rejected'],
    'confirmed': ['processing'],
    'processing': ['ready'],
    'ready': ['completed', 'expired'],
}

MANAGER_ORDER_OVERRIDES = {
    'pending': ['cancelled'],
    'confirmed': ['cancelled'],
    'processing': ['cancelled'],
    'ready': ['cancelled'],
    'completed': ['refunded'],
}


def deduct_stock_for_order(order):
    shortages = []
    for item in order.items.select_related('variant__product').all():
        if item.quantity > item.variant.stock:
            shortages.append(
                f'{item.variant.product.name} size {item.variant.size.code}: '
                f'needs {item.quantity}, only {item.variant.stock} left'
            )

    if shortages:
        return shortages

    for item in order.items.select_related('variant').all():
        item.variant.stock -= item.quantity
        item.variant.save(update_fields=['stock'])

    order.stock_deducted = True
    order.save(update_fields=['stock_deducted'])
    return []


def restore_stock_for_order(order):
    if not order.stock_deducted:
        return
    for item in order.items.select_related('variant').all():
        item.variant.stock += item.quantity
        item.variant.save(update_fields=['stock'])
    order.stock_deducted = False
    order.save(update_fields=['stock_deducted'])


def record_order_status_history(order, to_status, actor=None, from_status='', note=''):
    if from_status == to_status:
        return
    if actor is not None and not getattr(actor, 'is_authenticated', False):
        actor = None
    OrderStatusHistory.objects.create(
        order=order,
        actor=actor,
        from_status=from_status or '',
        to_status=to_status,
        note=note,
    )


def expire_approved_orders_without_pickup():
    cutoff = timezone.now() - timedelta(days=APPROVED_PICKUP_DATE_GRACE_DAYS)
    stale_orders = Order.objects.filter(
        status='confirmed',
        pickup_date__isnull=True,
        updated_at__lte=cutoff,
    ).select_related('user')

    expired_count = 0
    for stale_order in stale_orders:
        with transaction.atomic():
            order = Order.objects.select_for_update().select_related('user').get(pk=stale_order.pk)
            if order.status != 'confirmed' or order.pickup_date:
                continue
            old_status = order.status
            restore_stock_for_order(order)
            order.status = 'expired'
            order.save(update_fields=['status', 'updated_at'])
            record_order_status_history(
                order,
                order.status,
                from_status=old_status,
                note=f'Auto-expired because no pickup date was selected within {APPROVED_PICKUP_DATE_GRACE_DAYS} days.',
            )

        notify_user(
            order.user,
            f'Order #{order.pk}: Expired',
            f'Your approved order expired because no pickup date was selected within {APPROVED_PICKUP_DATE_GRACE_DAYS} days.',
            order,
        )
        notify_store_staff(
            f'Order #{order.pk}: Expired',
            f'{order.user.get_full_name() or order.user.username} did not set a pickup date within {APPROVED_PICKUP_DATE_GRACE_DAYS} days after approval.',
            order,
        )
        expired_count += 1
    return expired_count


def run_order_expiry_checks():
    return expire_approved_orders_without_pickup()


def get_order_transition_choices(order, user):
    allowed_statuses = list(STAFF_ORDER_TRANSITIONS.get(order.status, []))
    if user_is_manager(user):
        for status in MANAGER_ORDER_OVERRIDES.get(order.status, []):
            if status not in allowed_statuses:
                allowed_statuses.append(status)
    if not order.pickup_date:
        allowed_statuses = [
            status for status in allowed_statuses
            if status not in {'processing', 'ready'}
        ]

    status_labels = dict(Order._meta.get_field('status').choices)
    return [(status, status_labels[status]) for status in allowed_statuses]


def can_student_choose_pickup_date(order):
    return order.status == 'confirmed' and not order.pickup_date


RECEIPT_STATUSES = {'confirmed', 'processing', 'ready', 'completed', 'expired', 'refunded'}


def can_view_receipt(order):
    return order.status in RECEIPT_STATUSES


# ─── public pages ────────────────────────────────────────────────────────────

def home(request):
    categories = Category.objects.all()
    featured = Product.objects.filter(is_available=True).prefetch_related('variants')[:8]
    context = {'categories': categories, 'featured': featured}
    return render(request, 'home.html', context)


def product_list(request):
    products = Product.objects.filter(is_available=True).select_related('uniform_type').prefetch_related('category', 'variants')
    categories = Category.objects.all()
    uniform_types = UniformType.objects.all()

    category_slug = request.GET.get('category', '')
    type_slug = request.GET.get('type', '')
    query = request.GET.get('q', '')
    size_filter = request.GET.get('size', '')

    if category_slug:
        products = products.filter(category__slug=category_slug)
    if type_slug:
        products = products.filter(uniform_type__slug=type_slug)
    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(uniform_type__name__icontains=query) |
            Q(category__name__icontains=query)
        ).distinct()
    if size_filter:
        products = products.filter(variants__size__code=size_filter, variants__stock__gt=0).distinct()

    paginator = Paginator(products, 12)
    page = request.GET.get('page', 1)
    products_page = paginator.get_page(page)

    active_category = None
    if category_slug:
        active_category = categories.filter(slug=category_slug).first()
    active_type = None
    if type_slug:
        active_type = uniform_types.filter(slug=type_slug).first()

    context = {
        'products': products_page,
        'categories': categories,
        'uniform_types': uniform_types,
        'active_category': active_category,
        'active_type': active_type,
        'type_filter': type_slug,
        'query': query,
        'size_filter': size_filter,
        'size_choices': SizeOption.objects.filter(is_active=True),
    }
    return render(request, 'store/products.html', context)


def product_detail(request, slug):
    product = get_object_or_404(Product.objects.prefetch_related('images'), slug=slug, is_available=True)
    variants = product.variants.filter(stock__gt=0)
    related = Product.objects.filter(category__in=product.category.all(), is_available=True).exclude(pk=product.pk).distinct()[:4]
    gallery = list(product.images.all())
    context = {'product': product, 'variants': variants, 'related': related, 'gallery': gallery}
    return render(request, 'store/product_detail.html', context)


# ─── auth ────────────────────────────────────────────────────────────────────

def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        UserProfile.objects.create(
            user=user,
            role=UserProfile.ROLE_STUDENT,
            student_id=form.cleaned_data['student_id'],
            school_level=form.cleaned_data['school_level'],
        )
        login(request, user)
        messages.success(request, f'Welcome to UniShop, {user.get_full_name() or user.username}!')
        return redirect('home')
    return render(request, 'auth/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        next_url = request.GET.get('next')
        messages.success(request, f'Welcome back, {user.first_name or user.username}!')
        if next_url and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect(next_url)
        if user_is_store_staff(user):
            return redirect('manage_dashboard')
        return redirect('home')
    return render(request, 'auth/login.html', {'form': form})


@login_required
@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('home')


# ─── profile ─────────────────────────────────────────────────────────────────

@login_required
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    user_form = UserUpdateForm(instance=request.user)
    profile_form = ProfileUpdateForm(instance=profile)

    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile')

    orders = request.user.orders.all()[:5]
    context = {'user_form': user_form, 'profile_form': profile_form, 'orders': orders}
    return render(request, 'profile/profile.html', context)


# ─── cart ────────────────────────────────────────────────────────────────────

@login_required
def cart_view(request):
    cart = get_or_create_cart(request.user)
    items = cart.items.select_related('variant__product').all()
    context = {'cart': cart, 'items': items}
    return render(request, 'store/cart.html', context)


@login_required
@require_POST
def add_to_cart(request):
    variant_id = request.POST.get('variant_id')
    variant = get_object_or_404(
        ProductVariant.objects.select_related('product', 'size'),
        pk=variant_id,
        product__is_available=True,
    )
    quantity = parse_quantity(request.POST.get('quantity'))
    if quantity is None:
        messages.error(request, 'Please enter a valid quantity.')
        return redirect('product_detail', slug=variant.product.slug)

    if quantity < 1:
        quantity = 1
    if variant.stock <= 0:
        messages.error(request, f'{variant.product.name} size {variant.size.code} is currently out of stock.')
        return redirect('product_detail', slug=variant.product.slug)
    if quantity > variant.stock:
        messages.error(request, f'Only {variant.stock} items available for size {variant.size.code}.')
        return redirect('product_detail', slug=variant.product.slug)

    cart = get_or_create_cart(request.user)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, variant=variant)
    if not created:
        new_qty = cart_item.quantity + quantity
        if new_qty > variant.stock:
            new_qty = variant.stock
            messages.warning(request, f'Max stock reached for size {variant.size.code}.')
        cart_item.quantity = new_qty
    else:
        cart_item.quantity = quantity
    cart_item.save()

    messages.success(request, f'"{variant.product.name}" (Size {variant.size.code}) added to cart.')
    return redirect('cart')


@login_required
@require_POST
def update_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, pk=item_id, cart__user=request.user)
    quantity = parse_quantity(request.POST.get('quantity'))
    if quantity is None:
        messages.error(request, 'Please enter a valid quantity.')
        return redirect('cart')

    if quantity <= 0:
        cart_item.delete()
        messages.info(request, 'Item removed from cart.')
    elif quantity > cart_item.variant.stock:
        cart_item.quantity = cart_item.variant.stock
        cart_item.save()
        messages.warning(request, 'Quantity adjusted to available stock.')
    else:
        cart_item.quantity = quantity
        cart_item.save()

    return redirect('cart')


@login_required
@require_POST
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, pk=item_id, cart__user=request.user)
    cart_item.delete()
    messages.info(request, 'Item removed from cart.')
    return redirect('cart')


# ─── checkout & orders ───────────────────────────────────────────────────────

@login_required
def checkout_view(request):
    cart = get_or_create_cart(request.user)
    items = cart.items.select_related('variant__product').all()

    if not items.exists():
        messages.warning(request, 'Your cart is empty.')
        return redirect('cart')

    initial = {'contact_email': request.user.email}
    form = CheckoutForm(initial=initial)

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            # Stock validation
            for item in items:
                if item.quantity > item.variant.stock:
                    messages.error(request, f'Not enough stock for {item.variant.product.name} (Size {item.variant.size.code}).')
                    return redirect('cart')

            subtotal = cart.get_total()
            order = form.save(commit=False)
            order.user = request.user
            order.subtotal = subtotal
            order.contact_email = form.cleaned_data['contact_email']
            order.save()
            record_order_status_history(
                order,
                order.status,
                actor=request.user,
                note='Order submitted by student.',
            )

            for item in items:
                OrderItem.objects.create(
                    order=order,
                    variant=item.variant,
                    quantity=item.quantity,
                    unit_price=item.variant.get_price(),
                )

            cart.items.all().delete()
            notify_order_status(order)
            notify_store_staff(
                f'New order #{order.pk}',
                f'{order.user.get_full_name() or order.user.username} submitted a new order worth ₱{order.subtotal}.',
                order,
            )
            messages.success(request, f'Order #{order.pk} submitted successfully and is waiting for store approval.')
            return redirect('order_success', order_id=order.pk)

    context = {'form': form, 'cart': cart, 'items': items}
    return render(request, 'store/checkout.html', context)


@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    return render(request, 'store/order_success.html', {'order': order})


@login_required
def order_list(request):
    run_order_expiry_checks()
    orders = request.user.orders.prefetch_related('items__variant__product').all()
    return render(request, 'store/orders.html', {'orders': orders, 'receipt_statuses': RECEIPT_STATUSES})


@login_required
def notifications_view(request):
    run_order_expiry_checks()
    notifications = request.user.notifications.select_related('order').all()
    if request.method == 'POST':
        notifications.filter(is_read=False).update(is_read=True)
        messages.success(request, 'Notifications marked as read.')
        return redirect('notifications')
    return render(request, 'store/notifications.html', {'notifications': notifications})


@login_required
def notification_order_redirect(request, notification_id):
    notification = get_object_or_404(
        request.user.notifications.select_related('order'),
        pk=notification_id,
        order__isnull=False,
    )
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=['is_read'])
    return redirect('order_detail', order_id=notification.order_id)


@staff_required
def manage_notifications(request):
    notifications = request.user.notifications.select_related('order').all()
    if request.method == 'POST':
        notifications.filter(is_read=False).update(is_read=True)
        messages.success(request, 'Notifications marked as read.')
        return redirect('manage_notifications')
    return render(request, 'manage/notifications.html', {'notifications': notifications})


@staff_required
def manage_notification_order_redirect(request, notification_id):
    notification = get_object_or_404(
        request.user.notifications.select_related('order'),
        pk=notification_id,
        order__isnull=False,
    )
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=['is_read'])
    return redirect('manage_order_detail', pk=notification.order_id)


@login_required
def order_detail(request, order_id):
    run_order_expiry_checks()
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    return render(request, 'store/order_detail.html', {
        'order': order,
        'can_choose_pickup_date': can_student_choose_pickup_date(order),
        'can_view_receipt': can_view_receipt(order),
    })


@login_required
def order_receipt(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related('user').prefetch_related('items__variant__product'),
        pk=order_id,
        user=request.user,
    )
    if not can_view_receipt(order):
        messages.error(request, 'Digital receipts are available after order approval.')
        return redirect('order_detail', order_id=order.pk)

    response = render(request, 'store/receipt.html', {'order': order})
    if request.GET.get('download') == '1':
        response['Content-Disposition'] = f'attachment; filename="order-{order.pk}-receipt.html"'
    return response


@login_required
def order_pickup_date(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    if order.status != 'confirmed':
        messages.error(request, 'You can choose a pickup date after your order is approved.')
        return redirect('order_detail', order_id=order.pk)
    if order.pickup_date:
        messages.info(request, 'Pickup date is already set for this order.')
        return redirect('order_detail', order_id=order.pk)

    form = PickupDateForm(request.POST or None, instance=order)
    if request.method == 'POST' and form.is_valid():
        form.save()
        notify_user(
            order.user,
            f'Order #{order.pk}: Pickup date set',
            f'Your pickup date is set to {order.pickup_date:%B %d, %Y}.',
            order,
        )
        notify_store_staff(
            f'Order #{order.pk}: Pickup date set',
            f'{order.user.get_full_name() or order.user.username} selected {order.pickup_date:%B %d, %Y} as pickup date.',
            order,
        )
        messages.success(request, f'Pickup date set to {order.pickup_date:%B %d, %Y}.')
        return redirect('order_detail', order_id=order.pk)

    closed_ranges = [
        {'from': c.start_date.isoformat(), 'to': c.end_date.isoformat(), 'reason': c.reason}
        for c in StoreClosure.objects.filter(is_active=True)
    ]
    return render(request, 'store/pickup_date.html', {
        'order': order,
        'form': form,
        'closed_ranges_json': json.dumps(closed_ranges),
    })


@login_required
@require_POST
def order_cancel(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    if order.status != 'pending':
        messages.error(request, 'Only pending orders can be cancelled.')
        return redirect('order_detail', order_id=order.pk)
    old_status = order.status
    order.status = 'cancelled'
    order.save(update_fields=['status', 'updated_at'])
    record_order_status_history(
        order,
        order.status,
        actor=request.user,
        from_status=old_status,
        note='Student cancelled pending order.',
    )
    notify_order_status(order)
    notify_store_staff(
        f'Order #{order.pk} cancelled',
        f'{order.user.get_full_name() or order.user.username} cancelled a pending order.',
        order,
    )
    messages.success(request, f'Order #{order.pk} cancelled.')
    return redirect('order_detail', order_id=order.pk)


# ─── admin / manage ──────────────────────────────────────────────────────────

@staff_required
def manage_dashboard(request):
    run_order_expiry_checks()
    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status='pending').count()
    ready_orders = Order.objects.filter(status='ready').count()
    completed_orders = Order.objects.filter(status='completed').count()
    total_revenue = Order.objects.filter(status='completed').aggregate(
        total=Sum('subtotal')
    )['total'] or 0
    total_products = Product.objects.count()
    total_staff = User.objects.filter(is_staff=True).count()
    low_stock = ProductVariant.objects.filter(stock__lte=5, stock__gt=0).select_related('product')
    out_of_stock = ProductVariant.objects.filter(stock=0).select_related('product')
    recent_orders = Order.objects.select_related('user').order_by('-created_at')[:10]
    status_counts = Order.objects.values('status').annotate(count=Count('id')).order_by('status')
    school_level_sales = OrderItem.objects.filter(
        order__status__in=['confirmed', 'processing', 'ready', 'completed']
    ).values('variant__product__category__name').annotate(
        units=Sum('quantity')
    ).order_by('-units')[:3]
    store_closures = StoreClosure.objects.filter(
        is_active=True,
        end_date__gte=date.today(),
    ).order_by('start_date', 'end_date')[:5]

    context = {
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'ready_orders': ready_orders,
        'completed_orders': completed_orders,
        'total_revenue': total_revenue,
        'total_products': total_products,
        'total_staff': total_staff,
        'low_stock': low_stock,
        'out_of_stock': out_of_stock,
        'recent_orders': recent_orders,
        'status_counts': status_counts,
        'school_level_sales': school_level_sales,
        'store_closures': store_closures,
        'is_manager': user_is_manager(request.user),
    }
    return render(request, 'manage/dashboard.html', context)


@manager_required
def manage_products(request):
    products = Product.objects.select_related('uniform_type').prefetch_related('category', 'variants').order_by('-created_at')
    query = request.GET.get('q', '')
    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(category__name__icontains=query) |
            Q(uniform_type__name__icontains=query)
        )
    paginator = Paginator(products, 15)
    page = request.GET.get('page', 1)
    context = {'products': paginator.get_page(page), 'query': query}
    return render(request, 'manage/products.html', context)


@manager_required
def manage_product_add(request):
    form = ProductForm()
    formset = ProductVariantFormSet()
    image_formset = ProductImageFormSet()
    temp_image_url = None

    gallery_stash = {}

    if request.method == 'GET':
        _clear_product_image_stash(request)
        _clear_gallery_stash(request)

    elif request.method == 'POST':
        # Cover image: stash if just uploaded
        if 'image' in request.FILES:
            _stash_product_image(request, request.FILES['image'])
            request.FILES['image'].seek(0)

        stash_path = request.session.get(_TMP_IMAGE_SESSION_KEY)
        stash_ok = bool(stash_path and default_storage.exists(stash_path))
        using_stash = stash_ok and 'image' not in request.FILES

        if stash_ok:
            temp_image_url = default_storage.url(stash_path)

        form = ProductForm(request.POST, request.FILES)
        if stash_ok:
            form.fields['image'].required = False

        formset = ProductVariantFormSet(request.POST)
        image_formset = ProductImageFormSet(request.POST, request.FILES)

        # Gallery images: stash any new uploads, keep previous stashes
        gallery_stash = _stash_gallery_images(request, request.FILES, image_formset)
        # Remove browser required on slots that have a stash so resubmission isn't blocked
        for i, img_form in enumerate(image_formset.forms):
            if not img_form.instance.pk and str(i) in gallery_stash:
                img_form.fields['image'].required = False

        if form.is_valid() and formset.is_valid() and image_formset.is_valid():
            if has_missing_variant_prices(formset):
                messages.error(request, 'Set a price for each size you want to offer.')
            else:
                product = form.save(commit=False)
                if using_stash:
                    fname = os.path.basename(stash_path)
                    with default_storage.open(stash_path, 'rb') as f:
                        product.image.save(fname, ContentFile(f.read()), save=False)
                _clear_product_image_stash(request)
                product.save()
                form.save_m2m()
                formset.instance = product
                formset.save()
                image_formset.instance = product
                image_formset.save()
                # Save gallery images that were stashed but not re-uploaded in this request
                prefix = image_formset.prefix
                for i, img_form in enumerate(image_formset.forms):
                    if img_form.instance.pk:
                        continue
                    fkey = f'{prefix}-{i}-image'
                    s = gallery_stash.get(str(i))
                    if fkey not in request.FILES and s and default_storage.exists(s):
                        pi = ProductImage(product=product)
                        with default_storage.open(s, 'rb') as f:
                            pi.image.save(os.path.basename(s), ContentFile(f.read()), save=True)
                _clear_gallery_stash(request)
                messages.success(request, f'Product "{product.name}" added.')
                return redirect('manage_products')

    context = {
        'form': form, 'formset': formset, 'image_formset': image_formset,
        'action': 'Add', 'temp_image_url': temp_image_url,
        'gallery_with_stash': _build_gallery_with_stash(image_formset, gallery_stash),
    }
    return render(request, 'manage/product_form.html', context)


@manager_required
def manage_product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(instance=product)
    formset = ProductVariantFormSet(instance=product)
    image_formset = ProductImageFormSet(instance=product)

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        formset = ProductVariantFormSet(request.POST, instance=product)
        image_formset = ProductImageFormSet(request.POST, request.FILES, instance=product)
        if form.is_valid() and formset.is_valid() and image_formset.is_valid():
            if has_protected_variant_delete(formset):
                messages.error(request, 'One or more sizes cannot be removed because they are used in order history.')
            elif has_missing_variant_prices(formset):
                messages.error(request, 'Set a price for each size you want to offer.')
            else:
                form.save()
                formset.save()
                image_formset.save()
                messages.success(request, f'Product "{product.name}" updated.')
                return redirect('manage_products')

    context = {
        'form': form, 'formset': formset, 'image_formset': image_formset,
        'product': product, 'action': 'Edit',
        'gallery_with_stash': _build_gallery_with_stash(image_formset, {}),
    }
    return render(request, 'manage/product_form.html', context)


@manager_required
@require_POST
def manage_product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    name = product.name
    try:
        product.delete()
        messages.success(request, f'Product "{name}" deleted.')
    except ProtectedError:
        product.is_available = False
        product.save(update_fields=['is_available'])
        messages.warning(
            request,
            f'Product "{name}" is used in order history, so it was hidden instead of deleted.'
        )
    return redirect('manage_products')


@manager_required
@require_POST
def manage_product_toggle(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.is_available = not product.is_available
    product.save()
    status = 'available' if product.is_available else 'unavailable'
    messages.success(request, f'"{product.name}" marked as {status}.')
    return redirect('manage_products')


@manager_required
def manage_categories(request):
    categories = Category.objects.annotate(product_count=Count('products'))
    form = CategoryForm()

    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'School level added.')
            return redirect('manage_categories')

    context = {'categories': categories, 'form': form}
    return render(request, 'manage/categories.html', context)


@manager_required
@require_POST
def manage_category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if category.products.exists():
        messages.error(request, 'Cannot delete a school level with existing uniform items.')
    else:
        category.delete()
        messages.success(request, 'School level deleted.')
    return redirect('manage_categories')


@manager_required
def manage_uniform_types(request):
    uniform_types = UniformType.objects.annotate(product_count=Count('products'))
    form = UniformTypeForm()

    if request.method == 'POST':
        form = UniformTypeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Uniform type added.')
            return redirect('manage_uniform_types')

    return render(request, 'manage/uniform_types.html', {'uniform_types': uniform_types, 'form': form})


@manager_required
@require_POST
def manage_uniform_type_delete(request, pk):
    uniform_type = get_object_or_404(UniformType, pk=pk)
    if uniform_type.products.exists():
        messages.error(request, 'Cannot delete a uniform type with existing products.')
    else:
        uniform_type.delete()
        messages.success(request, 'Uniform type deleted.')
    return redirect('manage_uniform_types')


@manager_required
def manage_sizes(request):
    sizes = SizeOption.objects.all()
    form = SizeOptionForm()

    if request.method == 'POST':
        form = SizeOptionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Size added.')
            return redirect('manage_sizes')

    return render(request, 'manage/sizes.html', {'sizes': sizes, 'form': form})


@manager_required
@require_POST
def manage_size_toggle(request, pk):
    size = get_object_or_404(SizeOption, pk=pk)
    size.is_active = not size.is_active
    size.save(update_fields=['is_active'])
    messages.success(request, f'Size {size.code} updated.')
    return redirect('manage_sizes')


@manager_required
def manage_store_closures(request):
    closures = StoreClosure.objects.all()
    form = StoreClosureForm()

    if request.method == 'POST':
        form = StoreClosureForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Store closure date added.')
            return redirect('manage_store_closures')

    return render(request, 'manage/store_closures.html', {'closures': closures, 'form': form})


@manager_required
@require_POST
def manage_store_closure_toggle(request, pk):
    closure = get_object_or_404(StoreClosure, pk=pk)
    closure.is_active = not closure.is_active
    closure.save(update_fields=['is_active'])
    status = 'active' if closure.is_active else 'inactive'
    messages.success(request, f'Store closure marked as {status}.')
    return redirect('manage_store_closures')


@staff_required
def manage_inventory(request):
    products = Product.objects.select_related('uniform_type').prefetch_related('category', 'variants').order_by('uniform_type__name', 'name')
    query = request.GET.get('q', '')
    low_only = request.GET.get('low_stock') == '1'
    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(category__name__icontains=query) |
            Q(uniform_type__name__icontains=query)
        )
    if low_only:
        products = products.filter(variants__stock__lte=5).distinct()
    paginator = Paginator(products, 20)
    return render(request, 'manage/inventory.html', {
        'products': paginator.get_page(request.GET.get('page', 1)),
        'query': query,
        'low_only': low_only,
    })


@staff_required
def manage_orders(request):
    run_order_expiry_checks()
    orders = Order.objects.select_related('user').prefetch_related('items').order_by('-created_at')
    status_filter = request.GET.get('status', '')
    if status_filter:
        orders = orders.filter(status=status_filter)
    paginator = Paginator(orders, 20)
    page = request.GET.get('page', 1)
    context = {
        'orders': paginator.get_page(page),
        'status_filter': status_filter,
        'status_choices': Order._meta.get_field('status').choices,
    }
    return render(request, 'manage/orders.html', context)


@staff_required
def manage_order_detail(request, pk):
    run_order_expiry_checks()
    order = get_object_or_404(Order, pk=pk)
    transition_choices = get_order_transition_choices(order, request.user)
    form = OrderStatusForm(instance=order, status_choices=transition_choices)

    if request.method == 'POST':
        form = OrderStatusForm(request.POST, instance=order, status_choices=transition_choices)
        if form.is_valid():
            new_status = form.cleaned_data['status']
            with transaction.atomic():
                order = Order.objects.select_for_update().get(pk=order.pk)
                allowed_statuses = {status for status, _ in get_order_transition_choices(order, request.user)}
                if new_status not in allowed_statuses:
                    messages.error(request, 'That status change is not allowed for your role.')
                    return redirect('manage_order_detail', pk=order.pk)
                if new_status == 'ready' and not order.pickup_date:
                    messages.error(request, 'Set a pickup date before marking this order as Ready for Pickup.')
                    return redirect('manage_order_detail', pk=order.pk)

                if new_status in STOCK_DEDUCTING_STATUSES and not order.stock_deducted:
                    shortages = deduct_stock_for_order(order)
                    if shortages:
                        for shortage in shortages:
                            messages.error(request, shortage)
                        return redirect('manage_order_detail', pk=order.pk)
                elif new_status in STOCK_RESTORING_STATUSES:
                    restore_stock_for_order(order)

                old_status = order.status
                order.status = new_status
                order.save(update_fields=['status', 'updated_at'])
                record_order_status_history(
                    order,
                    order.status,
                    actor=request.user,
                    from_status=old_status,
                    note='Status updated from the admin console.',
                )
                notify_order_status(order)
            messages.success(request, f'Order #{order.pk} status updated to "{order.get_status_display()}".')
            return redirect('manage_order_detail', pk=order.pk)

    context = {
        'order': order,
        'form': form,
        'transition_choices': transition_choices,
        'is_manager': user_is_manager(request.user),
        'status_history': order.status_history.select_related('actor')[:20],
    }
    return render(request, 'manage/order_detail.html', context)


@manager_required
def manage_staff(request):
    staff_users = User.objects.filter(is_staff=True).select_related('profile').order_by('first_name', 'username')
    return render(request, 'manage/staff.html', {'staff_users': staff_users})


@manager_required
def manage_students(request):
    students = User.objects.filter(profile__role=UserProfile.ROLE_STUDENT).select_related('profile').annotate(
        order_count=Count('orders')
    ).order_by('last_name', 'first_name', 'username')
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')

    if query:
        students = students.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query) |
            Q(profile__student_id__icontains=query) |
            Q(profile__school_level__name__icontains=query)
        )
    if status_filter == 'active':
        students = students.filter(is_active=True)
    elif status_filter == 'inactive':
        students = students.filter(is_active=False)

    paginator = Paginator(students, 20)
    return render(request, 'manage/students.html', {
        'students': paginator.get_page(request.GET.get('page', 1)),
        'query': query,
        'status_filter': status_filter,
    })


@manager_required
def manage_student_edit(request, pk):
    student = get_object_or_404(User, pk=pk)
    form = StudentAccountForm(request.POST or None, instance=student)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        messages.success(request, f'Account "{user.username}" updated.')
        if user.profile.role == UserProfile.ROLE_STUDENT:
            return redirect('manage_students')
        return redirect('manage_staff')
    return render(request, 'manage/student_form.html', {'form': form, 'student': student})


@manager_required
@require_POST
def manage_student_toggle(request, pk):
    student = get_object_or_404(User, pk=pk, profile__role=UserProfile.ROLE_STUDENT)
    student.is_active = not student.is_active
    student.save(update_fields=['is_active'])
    status = 'Active' if student.is_active else 'Inactive'
    messages.success(request, f'Account "{student.username}" marked as {status}.')
    return redirect('manage_students')


@manager_required
def manage_staff_add(request):
    form = StaffAccountForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        messages.success(request, f'Staff account "{user.username}" created.')
        return redirect('manage_staff')
    return render(request, 'manage/staff_form.html', {'form': form, 'action': 'Add'})


@manager_required
def manage_staff_edit(request, pk):
    staff_user = get_object_or_404(User, pk=pk, is_staff=True)
    form = StaffAccountForm(request.POST or None, instance=staff_user)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        messages.success(request, f'Staff account "{user.username}" updated.')
        return redirect('manage_staff')
    return render(request, 'manage/staff_form.html', {'form': form, 'staff_user': staff_user, 'action': 'Edit'})


@manager_required
@require_POST
def manage_staff_toggle(request, pk):
    staff_user = get_object_or_404(User, pk=pk, is_staff=True)
    if staff_user == request.user:
        messages.error(request, 'You cannot deactivate your own account.')
        return redirect('manage_staff')
    staff_user.is_active = not staff_user.is_active
    staff_user.save(update_fields=['is_active'])
    status = 'activated' if staff_user.is_active else 'deactivated'
    messages.success(request, f'Staff account "{staff_user.username}" {status}.')
    return redirect('manage_staff')
