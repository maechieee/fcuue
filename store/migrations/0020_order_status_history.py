from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('store', '0019_product_description_optional'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrderStatusHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('from_status', models.CharField(blank=True, choices=[('pending', 'Pending'), ('confirmed', 'Approved'), ('rejected', 'Rejected'), ('processing', 'Available / Preparing'), ('ready', 'Ready for Pickup'), ('completed', 'Claimed / Picked Up'), ('cancelled', 'Cancelled'), ('expired', 'Expired / Unclaimed'), ('refunded', 'Refunded')], max_length=20)),
                ('to_status', models.CharField(choices=[('pending', 'Pending'), ('confirmed', 'Approved'), ('rejected', 'Rejected'), ('processing', 'Available / Preparing'), ('ready', 'Ready for Pickup'), ('completed', 'Claimed / Picked Up'), ('cancelled', 'Cancelled'), ('expired', 'Expired / Unclaimed'), ('refunded', 'Refunded')], max_length=20)),
                ('note', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='order_status_actions', to=settings.AUTH_USER_MODEL)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='status_history', to='store.order')),
            ],
            options={
                'verbose_name_plural': 'Order status history',
                'ordering': ['-created_at'],
            },
        ),
    ]
