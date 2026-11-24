from django.db import migrations, models


def migrate_category_fk_to_m2m(apps, schema_editor):
    Product = apps.get_model('store', 'Product')
    for product in Product.objects.all():
        if product.category_id:
            product.categories_new.add(product.category_id)


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0012_productvariant_size_to_fk'),
    ]

    operations = [
        # Add a temporary M2M field to collect the new data
        migrations.AddField(
            model_name='product',
            name='categories_new',
            field=models.ManyToManyField(blank=True, to='store.category'),
        ),
        # Copy the existing single FK value into the M2M table
        migrations.RunPython(migrate_category_fk_to_m2m, migrations.RunPython.noop),
        # Remove the old FK column
        migrations.RemoveField(
            model_name='product',
            name='category',
        ),
        # Rename temp M2M field to 'category'
        migrations.RenameField(
            model_name='product',
            old_name='categories_new',
            new_name='category',
        ),
        # Set the proper related_name
        migrations.AlterField(
            model_name='product',
            name='category',
            field=models.ManyToManyField(related_name='products', to='store.category'),
        ),
    ]
