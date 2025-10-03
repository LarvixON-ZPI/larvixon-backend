from django.core.management.base import BaseCommand
from typing import List, Dict
from analysis.models import Substance


SUBSTANCES: List[Dict[str, str]] = [
    {"en": "cocaine", "pl": "kokaina"},
    {"en": "ethanol", "pl": "etanol"},
    {"en": "ketamine", "pl": "ketamina"},
    {"en": "morphine", "pl": "morfina"},
    {"en": "tetrodotoxin", "pl": "tetrodotoksyna"},
]

class Command(BaseCommand):
    help = 'Seeds the database with initial Substance records.'

    def handle(self, *args, **options):
        self.stdout.write("Starting substance seeding...")
        
        created_count = 0
        
        for item in SUBSTANCES:
            substance, created = Substance.objects.update_or_create(
                name_en=item["en"],
                defaults={
                    'name_pl': item["pl"]
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created: {substance.name_en}'))
            else:
                self.stdout.write(f'Updated existing: {substance.name_en}')

        self.stdout.write(
            self.style.SUCCESS(f'\nSeeding complete! Total substances created: {created_count}/{len(SUBSTANCES)}')
        )