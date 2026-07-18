from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from account.serializers import AccountSerializer
from customer.domain import CPF
from customer.models import Address, Customer

User = get_user_model()


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            'number',
            'street',
            'complement',
            'city',
            'state',
            'country',
            'zip_code'
        ]


class CustomerCreateSerializer(serializers.Serializer):

    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    cpf = serializers.CharField(max_length=11)
    phone = serializers.CharField(max_length=20)
    first_name = serializers.CharField(max_length=255)
    last_name = serializers.CharField(max_length=255)
    birth_date = serializers.DateField(required=False, allow_null=True)
    address = AddressSerializer()

    def validate_username(self, value: str) -> str:
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('Username already registered.')
        return value

    def validate_cpf(self, value: str) -> str:
        try:
            CPF(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        if Customer.objects.filter(cpf=value).exists():
            raise serializers.ValidationError('CPF already registered.')
        return value

    def validate_password(self, value: str) -> str:
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value


class CustomerSerializer(serializers.ModelSerializer):

    addresses = AddressSerializer(many=True, read_only=True)
    account = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            'id',
            'cpf',
            'phone',
            'first_name',
            'last_name',
            'birth_date',
            'addresses',
            'account',
            'created_at',
        ]
        read_only_fields = fields

    def get_account(self, obj: Customer):
        if not hasattr(obj, 'account'):
            return None
        return AccountSerializer(obj.account).data

