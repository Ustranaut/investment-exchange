from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        CLIENT = "client", "Клиент"
        MANAGER = "manager", "Менеджер"
        SUPERADMIN = "superadmin", "Супер-администратор"

    email = models.EmailField("Электронная почта", unique=True)
    role = models.CharField(
        "Роль",
        max_length=20,
        choices=Role.choices,
        default=Role.CLIENT,
    )

    def __str__(self):
        return self.email or self.username
