from django.db import migrations
from django.utils.text import slugify


def _unique(seen, value, max_length=200):
    base = slugify(value)[:max_length].strip('-') or 'item'
    slug, n = base, 2
    while slug in seen:
        suffix = f'-{n}'
        slug = base[:max_length - len(suffix)] + suffix
        n += 1
    seen.add(slug)
    return slug


def fill_slugs(apps, schema_editor):
    Composer = apps.get_model('audioplayer', 'Composer')
    Piece = apps.get_model('audioplayer', 'Piece')
    PieceCollection = apps.get_model('audioplayer', 'PieceCollection')
    seen = set()
    for c in Composer.objects.order_by('pk'):
        c.slug = _unique(seen, c.name)
        c.save(update_fields=['slug'])
    seen = set()
    for p in Piece.objects.select_related('composer').order_by('pk'):
        p.slug = _unique(seen, f'{p.composer.name} {p.title}' if p.composer_id else p.title)
        p.save(update_fields=['slug'])
    seen = set()
    for col in PieceCollection.objects.order_by('pk'):
        col.slug = _unique(seen, col.title)
        col.save(update_fields=['slug'])




class Migration(migrations.Migration):

    dependencies = [
        ('audioplayer', '0016_library_rights_and_slugs'),
    ]

    operations = [
        migrations.RunPython(fill_slugs, migrations.RunPython.noop),
    ]
