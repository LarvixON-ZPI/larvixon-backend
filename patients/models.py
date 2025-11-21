import uuid
from django.db import models
from datetime import date


class Patient(models.Model):
    class Sex(models.TextChoices):
        MALE = "M", "Male"
        FEMALE = "F", "Female"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    pesel = models.CharField(
        max_length=11, unique=True, db_index=True, null=True, blank=True
    )

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    birth_date = models.DateField()
    sex = models.CharField(max_length=1, choices=Sex.choices)

    weight_kg = models.FloatField(null=True, blank=True)
    height_cm = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        identifier = self.pesel if self.pesel else "No PESEL"
        return f"{self.first_name} {self.last_name} ({identifier})"

    @property
    def age(self):
        if not self.birth_date:
            return None
        today = date.today()
        return (
            today.year
            - self.birth_date.year
            - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
        )
