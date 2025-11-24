import uuid
from django.db import models
from datetime import date
from dateutil.relativedelta import relativedelta
from django.core.validators import MinLengthValidator


class Patient(models.Model):
    class Sex(models.TextChoices):
        MALE = "M", "Male"
        FEMALE = "F", "Female"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    pesel = models.CharField(
        max_length=11,
        unique=True,
        db_index=True,
        null=True,
        blank=True,
        validators=[MinLengthValidator(4)],
    )

    document_id = models.CharField(max_length=20, unique=True, db_index=True)

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    birth_date = models.DateField()
    sex = models.CharField(max_length=1, choices=Sex.choices)

    weight_kg = models.FloatField(null=True, blank=True)
    height_cm = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        identifier = self.pesel if self.pesel else self.document_id
        return f"{self.first_name} {self.last_name} ({identifier})"

    @property
    def age(self) -> int | None:
        birth_date: date = self.birth_date
        if not birth_date:
            return None
        today: date = date.today()
        return relativedelta(today, birth_date).years
