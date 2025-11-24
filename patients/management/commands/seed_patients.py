import random
from django.core.management.base import BaseCommand
from faker import Faker
from patients.models import Patient


class Command(BaseCommand):
    help = "Generates patients with random data"

    def add_arguments(self, parser):
        parser.add_argument("total", type=int, help="How many patients?")

    def handle(self, *args, **kwargs):
        total = kwargs["total"]
        fake = Faker(["pl_PL"])

        self.stdout.write(f"Creating {total} patients...")

        created_count = 0

        for _ in range(total):
            try:
                sex_choice = random.choice([Patient.Sex.MALE, Patient.Sex.FEMALE])

                if sex_choice == Patient.Sex.MALE:
                    first_name = fake.first_name_male()
                    last_name = fake.last_name_male()
                else:
                    first_name = fake.first_name_female()
                    last_name = fake.last_name_female()

                pesel = fake.pesel(sex=sex_choice)

                document_id = fake.bothify(text="??#######").upper()

                birth_date = fake.date_of_birth(minimum_age=18, maximum_age=90)

                weight = round(random.uniform(50.0, 120.0), 1)
                height = random.randint(150, 200)

                Patient.objects.create(
                    pesel=pesel,
                    document_id=document_id,
                    first_name=first_name,
                    last_name=last_name,
                    birth_date=birth_date,
                    sex=sex_choice,
                    weight_kg=weight,
                    height_cm=height,
                )
                created_count += 1

            except Exception as e:
                continue

        self.stdout.write(self.style.SUCCESS(f"Created {created_count} new patients"))
