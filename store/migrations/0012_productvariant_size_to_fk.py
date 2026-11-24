from django.db import migrations, models
import django.db.models.deletion


def migrate_size_codes_to_fk(apps, schema_editor):
    ProductVariant = apps.get_model('store', 'ProductVariant')
    SizeOption = apps.get_model('store', 'SizeOption')

    code_map = {so.code: so for so in SizeOption.objects.all()}
    # Map legacy codes that may exist in existing data
    legacy = {'XS': 'S', 'XXL': '2XL', 'XXXL': '3XL'}

    for variant in ProductVariant.objects.all():
        old_code = variant.size_code
        so = code_map.get(old_code)
        if not so:
            mapped = legacy.get(old_code)
            if mapped:
                so = code_map.get(mapped)
        if not so:
            so, _ = SizeOption.objects.get_or_create(
                code=old_code,
                defaults={'label': old_code, 'sort_order': 99, 'is_active': True},
            )
            code_map[old_code] = so
        variant.size = so
        variant.save()


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0011_remove_userprofile_department_year_level_and_more'),
    ]

    operations = [
        # Remove unique constraint that references the old CharField 'size'
        migrations.AlterUniqueTogether(
            name='productvariant',
            unique_together=set(),
        ),
        # Rename old CharField to preserve its data during migration
        migrations.RenameField(
            model_name='productvariant',
            old_name='size',
            new_name='size_code',
        ),
        # Add the new nullable FK field
        migrations.AddField(
            model_name='productvariant',
            name='size',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                to='store.sizeoption',
            ),
        ),
        # Populate FK from the old char codes
        migrations.RunPython(migrate_size_codes_to_fk, migrations.RunPython.noop),
        # Drop the old char column
        migrations.RemoveField(
            model_name='productvariant',
            name='size_code',
        ),
        # Make the FK non-nullable
        migrations.AlterField(
            model_name='productvariant',
            name='size',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='variants',
                to='store.sizeoption',
            ),
        ),
        # Restore unique_together with FK field
        migrations.AlterUniqueTogether(
            name='productvariant',
            unique_together={('product', 'size')},
        ),
        # Update ordering to traverse FK
        migrations.AlterModelOptions(
            name='productvariant',
            options={
                'ordering': ['size__sort_order', 'size__code'],
            },
        ),
    ]
