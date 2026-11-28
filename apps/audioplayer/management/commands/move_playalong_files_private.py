"""
Move playalong files from public MEDIA_ROOT to PRIVATE_MEDIA_ROOT.

Moves every file in the four playalong upload folders, including files no
longer referenced by any piece, so nothing is left publicly reachable at
/media/audioplayer/. Names stored in the database are unchanged: the same
relative path is used under the private root.

Safe to run more than once. Use --dry-run to see what would move.
"""
import os
import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

FOLDERS = [
    'audioplayer/stems',
    'audioplayer/pdf_scores',
    'audioplayer/svg_images',
    'audioplayer/collection_pdfs',
]


class Command(BaseCommand):
    help = 'Move playalong stems, score PDFs and images into private storage'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='List what would move without moving it')

    def handle(self, *args, dry_run=False, **options):
        public_root = Path(settings.MEDIA_ROOT)
        private_root = Path(settings.PRIVATE_MEDIA_ROOT)
        if public_root.resolve() == private_root.resolve():
            raise CommandError('MEDIA_ROOT and PRIVATE_MEDIA_ROOT are the same folder')

        moved = skipped = 0
        for folder in FOLDERS:
            source_dir = public_root / folder
            if not source_dir.is_dir():
                continue
            for source in sorted(p for p in source_dir.rglob('*') if p.is_file()):
                relative = source.relative_to(public_root)
                target = private_root / relative
                if target.exists():
                    self.stderr.write(f'Skipped (already in private storage): {relative}')
                    skipped += 1
                    continue
                if dry_run:
                    self.stdout.write(f'Would move {relative}')
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(source), str(target))
                moved += 1

            if not dry_run:
                # Remove now-empty folders so /media/audioplayer/ holds nothing
                for path in sorted(source_dir.rglob('*'), reverse=True):
                    if path.is_dir() and not any(path.iterdir()):
                        path.rmdir()
                if not any(source_dir.iterdir()):
                    source_dir.rmdir()

        verb = 'Would move' if dry_run else 'Moved'
        self.stdout.write(self.style.SUCCESS(f'{verb} {moved} file(s); skipped {skipped}.'))
