# Generated by Django 5.0.7 on 2024-08-31 10:31

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('adminclick', '0002_category'),
        ('artist', '0005_alter_product_categories'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Category',
        ),
    ]