"""
Mark composers whose music is still in copyright (decided 28 Nov 2026), and
make sure nothing of theirs is public. Those items were already made private
by hand; this keeps every server consistent.
"""
from django.db import migrations

IN_COPYRIGHT = ['Franz J. Giesbert', 'Brian Bonsor', 'Elizabeth Cooper']


def mark(apps, schema_editor):
    Composer = apps.get_model('audioplayer', 'Composer')
    Piece = apps.get_model('audioplayer', 'Piece')
    PieceCollection = apps.get_model('audioplayer', 'PieceCollection')

    composers = Composer.objects.filter(name__in=IN_COPYRIGHT)
    composers.update(in_copyright=True)
    pieces = Piece.objects.filter(composer__in=composers)
    pieces.update(is_public=False)
    PieceCollection.objects.filter(collection_memberships__piece__in=pieces).update(is_public=False)
    PieceCollection.objects.filter(composer__in=composers).update(is_public=False)


def unmark(apps, schema_editor):
    # Only clears the marker; visibility is left as it is
    Composer = apps.get_model('audioplayer', 'Composer')
    Composer.objects.filter(name__in=IN_COPYRIGHT).update(in_copyright=False)


class Migration(migrations.Migration):

    dependencies = [
        ('audioplayer', '0014_copyright_lock'),
    ]

    operations = [
        migrations.RunPython(mark, unmark),
    ]
