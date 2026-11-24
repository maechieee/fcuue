from .models import Cart, Notification


def cart_count(request):
    count = 0
    notification_count = 0
    if request.user.is_authenticated:
        try:
            cart = request.user.cart
            count = cart.get_item_count()
        except Cart.DoesNotExist:
            pass
        notification_count = Notification.objects.filter(user=request.user, is_read=False).count()
    return {
        'cart_item_count': count,
        'notification_count': notification_count,
    }
