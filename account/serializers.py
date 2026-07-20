from decimal import Decimal

from rest_framework import serializers

from account.models import Account, Transaction


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


class BalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['balance', 'currency']
        read_only_fields = fields


class DepositSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal('0.01'))


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'type', 'amount', 'balance_after', 'status', 'created_at']
        read_only_fields = fields
