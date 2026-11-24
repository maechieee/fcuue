from django.db import migrations


DEPARTMENTS = {
    'college': ('College', 'Official college uniform items.'),
    'senior-high-school': ('Senior High School', 'Uniform items for SHS students.'),
    'junior-high-school': ('Junior High School', 'Uniform items for JHS students.'),
}

SOURCE_TO_DEPARTMENT = {
    'school-uniform': 'college',
    'polo-shirt': 'college',
    'school-pants': 'college',
    'pe-uniform': 'senior-high-school',
    'school-skirt': 'senior-high-school',
    'accessories': 'junior-high-school',
}


def convert_categories(apps, schema_editor):
    Category = apps.get_model('store', 'Category')
    Product = apps.get_model('store', 'Product')

    department_map = {}
    for slug, (name, description) in DEPARTMENTS.items():
        department, _ = Category.objects.get_or_create(
            slug=slug,
            defaults={'name': name, 'description': description},
        )
        if department.name != name:
            department.name = name
            department.description = description
            department.save(update_fields=['name', 'description'])
        department_map[slug] = department

    for source_slug, department_slug in SOURCE_TO_DEPARTMENT.items():
        source = Category.objects.filter(slug=source_slug).first()
        if not source:
            continue
        target = department_map[department_slug]
        Product.objects.filter(category=source).update(category=target)
        if source.pk != target.pk and not source.products.exists():
            source.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0004_roles_and_order_stock_state'),
    ]

    operations = [
        migrations.RunPython(convert_categories, migrations.RunPython.noop),
    ]
