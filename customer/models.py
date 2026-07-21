from django.conf import settings
from django.db import models

from customer.domain import CPF


class Customer(models.Model):

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='customer')

    cpf = models.CharField(max_length=11, unique=True)
    phone = models.CharField(max_length=20)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    birth_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'customer'

    def __str__(self):
        return self.first_name + self.last_name

    def save(self, *args, **kwargs) -> None:
        CPF(self.cpf)
        super().save(*args, **kwargs)


class Address(models.Model):

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='addresses')

    number = models.CharField(max_length=20)
    street = models.CharField(max_length=255)
    complement = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2)
    country = models.CharField(max_length=2, default="BR")
    zip_code = models.CharField(max_length=8)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'customer_address'

    def __str__(self):
        return f"{self.street}, {self.number} - {self.city}/{self.state}"

