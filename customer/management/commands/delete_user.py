from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from customer.services import delete_user_completely

User = get_user_model()


class Command(BaseCommand):

    help = 'Deletes a user and all related data (customer, address, account, transactions, tokens).'

    def add_arguments(self, parser):
        parser.add_argument('username')
        parser.add_argument(
            '--noinput',
            '--no-input',
            action='store_false',
            dest='interactive',
            help='Do not prompt for confirmation before deleting.',
        )

    def handle(self, *args, **options):

        username = options['username']

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist as exc:
            raise CommandError(f'User "{username}" does not exist.') from exc

        if options['interactive']:
            confirm = input(
                f'This will permanently delete user "{username}" and all related data '
                f'(customer, address, account, transactions, tokens). Continue? [y/N] '
            )
            if confirm.lower() != 'y':
                self.stdout.write('Aborted.')
                return

        delete_user_completely(user=user)
        
        self.stdout.write(self.style.SUCCESS(f'User "{username}" and related data deleted.'))

