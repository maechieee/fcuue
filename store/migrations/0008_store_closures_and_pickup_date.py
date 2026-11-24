from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0007_order_override_statuses'),
    ]

    operations = [
        migrations.CreateModel(
            name='StoreClosure',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('reason', models.CharField(max_length=200)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-start_date', '-created_at'],
            },
        ),
        migrations.AddField(
            model_name='order',
            name='pickup_date',
            field=models.DateField(blank=True, null=True),
        ),
    ]
