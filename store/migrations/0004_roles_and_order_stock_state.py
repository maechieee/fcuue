from django.conf import settings
from django.db import migrations, models


def assign_existing_roles(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    UserProfile = apps.get_model('store', 'UserProfile')

    for user in User.objects.all():
        role = 'manager' if user.is_superuser or user.is_staff else 'student'
        UserProfile.objects.get_or_create(user=user, defaults={'role': role})
        UserProfile.objects.filter(user=user).update(role=role)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('store', '0003_add_variant_price'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='role',
            field=models.CharField(choices=[('student', 'Student / Customer'), ('staff', 'Staff / Store Clerk'), ('manager', 'Admin / Store Manager')], default='student', max_length=20),
        ),
        migrations.AddField(
            model_name='order',
            name='stock_deducted',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('confirmed', 'Approved'), ('processing', 'Available / Preparing'), ('ready', 'Ready for Pickup'), ('completed', 'Claimed / Picked Up'), ('cancelled', 'Cancelled')], default='pending', max_length=20),
        ),
        migrations.RunPython(assign_existing_roles, migrations.RunPython.noop),
    ]
