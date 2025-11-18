from django.db import migrations


def fill_translations(apps, schema_editor):
    Substance = apps.get_model("analysis", "Substance")

    Substance.objects.filter(name_en="Ethanol").update(name_pl="Etanol")
    Substance.objects.filter(name_en="ethanol").update(name_pl="etanol")

    translations = {
        "Water (H2O)": "Woda (H2O)",
        "Redbull": "Redbull",
        "morphine": "Morfina",
        "cocaine": "Kokaina",
        "ketamine": "Ketamina",
        "tetrodotoxin": "Tetrodotoksyna",
        "Nothing": "Nic",
    }

    for english, polish in translations.items():
        Substance.objects.filter(name_en=english).update(name_pl=polish)


class Migration(migrations.Migration):

    dependencies = [
        ("analysis", "0009_videoanalysis_error_message"),
    ]

    operations = [
        migrations.RunPython(fill_translations),
    ]
