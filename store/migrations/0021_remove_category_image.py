from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0020_order_status_history'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='category',
            name='image',
        ),
    ]
