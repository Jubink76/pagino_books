# Generated by Django 5.1.2 on 2024-11-18 14:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order_detail_app', '0007_alter_orderdetails_order_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderitem',
            name='is_canceled',
            field=models.BooleanField(default=False),
        ),
    ]
