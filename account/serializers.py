from datetime import date, timedelta
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


class StatementFilterSerializer(serializers.Serializer):

    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)

    def validate(self, attrs: dict) -> dict:

        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')

        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=7)

        if start_date > end_date:
            raise serializers.ValidationError({'start_date': 'start_date must not be after end_date.'})

        attrs['start_date'] = start_date
        attrs['end_date'] = end_date

        return attrs

