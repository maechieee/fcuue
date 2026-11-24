from django.urls import path
from . import views

urlpatterns = [
    # Public
    path('', views.home, name='home'),
    path('products/', views.product_list, name='product_list'),
    path('products/<slug:slug>/', views.product_detail, name='product_detail'),

    # Auth
    path('auth/register/', views.register_view, name='register'),
    path('auth/login/', views.login_view, name='login'),
    path('auth/logout/', views.logout_view, name='logout'),

    # Profile
    path('profile/', views.profile_view, name='profile'),

    # Cart
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.update_cart, name='update_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),

    # Orders
    path('checkout/', views.checkout_view, name='checkout'),
    path('order/success/<int:order_id>/', views.order_success, name='order_success'),
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/<int:notification_id>/order/', views.notification_order_redirect, name='notification_order_redirect'),
    path('orders/', views.order_list, name='order_list'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('orders/<int:order_id>/receipt/', views.order_receipt, name='order_receipt'),
    path('orders/<int:order_id>/pickup-date/', views.order_pickup_date, name='order_pickup_date'),
    path('orders/<int:order_id>/cancel/', views.order_cancel, name='order_cancel'),

    # Admin / Manage
    path('manage/', views.manage_dashboard, name='manage_dashboard'),
    path('manage/products/', views.manage_products, name='manage_products'),
    path('manage/products/add/', views.manage_product_add, name='manage_product_add'),
    path('manage/products/<int:pk>/edit/', views.manage_product_edit, name='manage_product_edit'),
    path('manage/products/<int:pk>/delete/', views.manage_product_delete, name='manage_product_delete'),
    path('manage/products/<int:pk>/toggle/', views.manage_product_toggle, name='manage_product_toggle'),
    path('manage/categories/', views.manage_categories, name='manage_categories'),
    path('manage/categories/<int:pk>/delete/', views.manage_category_delete, name='manage_category_delete'),
    path('manage/types/', views.manage_uniform_types, name='manage_uniform_types'),
    path('manage/types/<int:pk>/delete/', views.manage_uniform_type_delete, name='manage_uniform_type_delete'),
    path('manage/sizes/', views.manage_sizes, name='manage_sizes'),
    path('manage/sizes/<int:pk>/toggle/', views.manage_size_toggle, name='manage_size_toggle'),
    path('manage/closures/', views.manage_store_closures, name='manage_store_closures'),
    path('manage/closures/<int:pk>/toggle/', views.manage_store_closure_toggle, name='manage_store_closure_toggle'),
    path('manage/inventory/', views.manage_inventory, name='manage_inventory'),
    path('manage/orders/', views.manage_orders, name='manage_orders'),
    path('manage/orders/<int:pk>/', views.manage_order_detail, name='manage_order_detail'),
    path('manage/notifications/', views.manage_notifications, name='manage_notifications'),
    path('manage/notifications/<int:notification_id>/order/', views.manage_notification_order_redirect, name='manage_notification_order_redirect'),
    path('manage/students/', views.manage_students, name='manage_students'),
    path('manage/students/<int:pk>/edit/', views.manage_student_edit, name='manage_student_edit'),
    path('manage/students/<int:pk>/toggle/', views.manage_student_toggle, name='manage_student_toggle'),
    path('manage/staff/', views.manage_staff, name='manage_staff'),
    path('manage/staff/add/', views.manage_staff_add, name='manage_staff_add'),
    path('manage/staff/<int:pk>/edit/', views.manage_staff_edit, name='manage_staff_edit'),
    path('manage/staff/<int:pk>/toggle/', views.manage_staff_toggle, name='manage_staff_toggle'),
]
