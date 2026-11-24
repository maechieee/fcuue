from django.db import migrations, models


def backfill_student_ids(apps, schema_editor):
    UserProfile = apps.get_model('store', 'UserProfile')
    for profile in UserProfile.objects.select_related('user').filter(role='student', student_id__isnull=True):
        profile.student_id = profile.user.username
        profile.save(update_fields=['student_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0008_store_closures_and_pickup_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='department_year_level',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='student_id',
            field=models.CharField(blank=True, max_length=50, null=True, unique=True),
        ),
        migrations.RunPython(backfill_student_ids, migrations.RunPython.noop),
    ]
