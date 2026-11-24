from django.contrib import admin
from .models import (
    Category, UniformType, SizeOption, StoreClosure, Product, ProductVariant,
    UserProfile, Cart, CartItem, Order, OrderItem, OrderStatusHistory, Notification,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(UniformType)
class UniformTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(SizeOption)
class SizeOptionAdmin(admin.ModelAdmin):
    list_display = ('code', 'label', 'is_active')
    list_filter = ('is_active',)


@admin.register(StoreClosure)
class StoreClosureAdmin(admin.ModelAdmin):
    list_display = ('start_date', 'end_date', 'reason', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('reason',)


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 3


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'uniform_type', 'price', 'is_available', 'total_stock', 'created_at')
    list_filter = ('category', 'uniform_type', 'is_available')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductVariantInline]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('unit_price',)


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ('actor', 'from_status', 'to_status', 'note', 'created_at')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'contact_email', 'status', 'pickup_date', 'stock_deducted', 'subtotal', 'created_at')
    list_filter = ('status', 'stock_deducted')
    inlines = [OrderItemInline, OrderStatusHistoryInline]


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('order', 'from_status', 'to_status', 'actor', 'created_at')
    list_filter = ('to_status', 'created_at')
    search_fields = ('order__id', 'actor__username', 'actor__first_name', 'actor__last_name', 'note')
    readonly_fields = ('order', 'actor', 'from_status', 'to_status', 'note', 'created_at')

    def has_add_permission(self, request):
        return False


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'order', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('title', 'message', 'user__username', 'user__email')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'student_id', 'school_level', 'phone')
    list_filter = ('role', 'school_level')
    search_fields = ('student_id', 'school_level__name', 'user__username', 'user__first_name', 'user__last_name', 'user__email')


admin.site.register(Cart)
admin.site.register(CartItem)
