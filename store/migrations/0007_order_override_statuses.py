from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0006_uniform_types_sizes_and_rejected_orders'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('confirmed', 'Approved'), ('rejected', 'Rejected'), ('processing', 'Available / Preparing'), ('ready', 'Ready for Pickup'), ('completed', 'Claimed / Picked Up'), ('cancelled', 'Cancelled'), ('expired', 'Expired / Unclaimed'), ('refunded', 'Refunded')], default='pending', max_length=20),
        ),
    ]
