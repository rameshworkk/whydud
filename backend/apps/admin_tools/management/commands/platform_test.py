"""
Full platform test — runs the complete pytest suite with formatted output.

Usage:
  python manage.py platform_test                  # Run all tests
  python manage.py platform_test --smoke          # Only smoke tests
  python manage.py platform_test --infra          # Only infrastructure tests
  python manage.py platform_test --api            # Only API tests
  python manage.py platform_test --auth           # Only auth tests
  python manage.py platform_test --quick          # Skip slow tests
  python manage.py platform_test --coverage       # With coverage report
  python manage.py platform_test --parallel       # Run in parallel (needs pytest-xdist)
"""
import os
import subprocess
import sys

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Run the full platform test suite'

    def add_arguments(self, parser):
        parser.add_argument('--smoke', action='store_true', help='Only smoke tests')
        parser.add_argument('--infra', action='store_true', help='Only infrastructure tests')
        parser.add_argument('--api', action='store_true', help='Only API tests')
        parser.add_argument('--auth', action='store_true', help='Only auth tests')
        parser.add_argument('--quick', action='store_true', help='Skip slow tests')
        parser.add_argument('--coverage', action='store_true', help='Generate coverage report')
        parser.add_argument('--parallel', action='store_true', help='Run tests in parallel')

    def handle(self, *args, **options):
        cmd = [sys.executable, '-m', 'pytest']

        # Marker filters
        markers = []
        if options['smoke']:
            markers.append('smoke')
        if options['infra']:
            markers.append('infra')
        if options['api']:
            markers.append('api')
        if options['auth']:
            markers.append('auth')
        if options['quick']:
            markers.append('not slow')

        if markers:
            cmd.extend(['-m', ' and '.join(markers)])

        # Options
        cmd.extend(['-v', '--tb=short'])

        if options['coverage']:
            cmd.extend(['--cov=apps', '--cov-report=term-missing', '--cov-report=html'])

        if options['parallel']:
            cmd.extend(['-n', 'auto'])

        cmd.append('tests/')

        # Run from the backend directory (where pytest.ini lives)
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )))

        self.stdout.write(self.style.WARNING(f'\nRunning: {" ".join(cmd)}'))
        self.stdout.write(self.style.WARNING(f'Working dir: {backend_dir}\n'))

        result = subprocess.run(cmd, cwd=backend_dir)
        sys.exit(result.returncode)
