# Generated by Django 5.1.2 on 2024-12-10 06:47

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('adminside_app', '0013_booktable_applied_offer'),
        ('order_detail_app', '0029_alter_orderdetails_order_status_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='reviewtable',
            name='book',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='adminside_app.booktable'),
        ),
    ]
