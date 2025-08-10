from typing import cast
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from ...models import User


class Command(BaseCommand):
    help = 'Seed the database with an admin user.'

    def handle(self, *args, **options) -> None:
        UserModel = cast(type[User], get_user_model())
        email = 'admin@gmail.com'
        password = '1234'
        if not UserModel.objects.filter(email=email).exists():
            user: User = UserModel.objects.create_user(
                email=email, password=password, username=email)
            user.is_staff = True
            user.is_superuser = True
            user.save()
            self.stdout.write(self.style.SUCCESS(
                f'Admin user {email} created.'))
        else:
            self.stdout.write(self.style.WARNING(
                f'Admin user {email} already exists.'))
