# Generated by Django 5.1.2 on 2024-12-09 15:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order_detail_app', '0027_remove_reviewtable_book'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderdetails',
            name='is_returned',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='orderitem',
            name='is_returned',
            field=models.BooleanField(default=False),
        ),
    ]
