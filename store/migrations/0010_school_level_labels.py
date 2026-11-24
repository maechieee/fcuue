from django.db import migrations


SCHOOL_LEVELS = [
    ('kindergarten', 'Kindergarten', 'Uniform items for kindergarten students.'),
    ('elementary', 'Elementary', 'Uniform items for elementary students.'),
    ('junior-high-school', 'Junior High School', 'Uniform items for JHS students.'),
    ('senior-high-school', 'Senior High School', 'Uniform items for SHS students.'),
    ('college', 'College', 'Official college uniform items.'),
]


def ensure_school_levels(apps, schema_editor):
    Category = apps.get_model('store', 'Category')
    for slug, name, description in SCHOOL_LEVELS:
        level, _ = Category.objects.get_or_create(
            slug=slug,
            defaults={'name': name, 'description': description},
        )
        changed = False
        if level.name != name:
            level.name = name
            changed = True
        if not level.description:
            level.description = description
            changed = True
        if changed:
            level.save(update_fields=['name', 'description'])


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0009_student_registration_fields'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='category',
            options={'ordering': ['name'], 'verbose_name': 'School Level', 'verbose_name_plural': 'School Levels'},
        ),
        migrations.RunPython(ensure_school_levels, migrations.RunPython.noop),
    ]
