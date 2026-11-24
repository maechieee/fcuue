from django.db import migrations, models
import django.db.models.deletion
from django.utils.text import slugify


TYPE_NAMES = ['Polo', 'PE Uniform', 'Blouse', 'Pants', 'Skirt', 'Accessories', 'Uniform Set']
SIZE_OPTIONS = [
    ('XS', 'Extra Small', 10),
    ('S', 'Small', 20),
    ('M', 'Medium', 30),
    ('L', 'Large', 40),
    ('XL', 'Extra Large', 50),
    ('XXL', 'Double Extra Large', 60),
    ('XXXL', 'Triple Extra Large', 70),
    ('FREE', 'Free Size', 80),
]


def infer_type_name(product_name):
    name = product_name.lower()
    if 'pe' in name:
        return 'PE Uniform'
    if 'blouse' in name:
        return 'Blouse'
    if 'pants' in name or 'slacks' in name:
        return 'Pants'
    if 'skirt' in name:
        return 'Skirt'
    if 'belt' in name or 'socks' in name or 'tie' in name:
        return 'Accessories'
    if 'set' in name:
        return 'Uniform Set'
    return 'Polo'


def seed_types_and_sizes(apps, schema_editor):
    UniformType = apps.get_model('store', 'UniformType')
    SizeOption = apps.get_model('store', 'SizeOption')
    Product = apps.get_model('store', 'Product')

    type_map = {}
    for name in TYPE_NAMES:
        uniform_type, _ = UniformType.objects.get_or_create(
            slug=slugify(name),
            defaults={'name': name},
        )
        type_map[name] = uniform_type

    for code, label, sort_order in SIZE_OPTIONS:
        SizeOption.objects.get_or_create(
            code=code,
            defaults={'label': label, 'sort_order': sort_order, 'is_active': True},
        )

    fallback_type = type_map['Polo']
    for product in Product.objects.all():
        product.uniform_type = type_map.get(infer_type_name(product.name), fallback_type)
        product.save(update_fields=['uniform_type'])


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0005_convert_categories_to_departments'),
    ]

    operations = [
        migrations.CreateModel(
            name='SizeOption',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=10, unique=True)),
                ('label', models.CharField(max_length=50)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['sort_order', 'code'],
            },
        ),
        migrations.CreateModel(
            name='UniformType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('slug', models.SlugField(blank=True, max_length=100, unique=True)),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='product',
            name='uniform_type',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='products', to='store.uniformtype'),
        ),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('confirmed', 'Approved'), ('rejected', 'Rejected'), ('processing', 'Available / Preparing'), ('ready', 'Ready for Pickup'), ('completed', 'Claimed / Picked Up'), ('cancelled', 'Cancelled')], default='pending', max_length=20),
        ),
        migrations.RunPython(seed_types_and_sizes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='product',
            name='uniform_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='products', to='store.uniformtype'),
        ),
    ]
