from rest_framework import serializers

from account.models import Account


class AccountCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['account_type']


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = [
            'id',
            'account_number',
            'agency',
            'account_type',
            'status',
            'balance',
            'currency',
            'created_at',
        ]
        read_only_fields = fields

