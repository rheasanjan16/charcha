# Generated by Django 3.0.7 on 2020-07-15 19:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('discussions', '0009_comment_last_modified'),
    ]

    operations = [
        migrations.AlterField(
            model_name='comment',
            name='html',
            field=models.TextField(max_length=512),
        ),
        migrations.AlterField(
            model_name='post',
            name='html',
            field=models.TextField(max_length=8192),
        ),
    ]
