from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from account.selectors import get_account_for_user, get_statement
from account.serializers import (
    BalanceSerializer,
    DepositSerializer,
    StatementFilterSerializer,
    TransactionSerializer,
)
from account.services import IdempotencyKeyConflictError, deposit


class AccountBalanceView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        account = get_account_for_user(request.user)
        return Response(BalanceSerializer(account).data)


class DepositView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        
        idempotency_key = request.headers.get('Idempotency-Key')
        if not idempotency_key:
            return Response({'detail': 'Idempotency-Key header is required.'}, status=400)

        serializer = DepositSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        account = get_account_for_user(request.user)
        try:
            created = deposit(
                account=account,
                amount=serializer.validated_data['amount'],
                idempotency_key=idempotency_key,
            )
        except IdempotencyKeyConflictError as e:
            return Response({'detail': str(e)}, status=409)

        return Response(TransactionSerializer(created).data, status=201)


class AccountStatementView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:

        filters = StatementFilterSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)

        account = get_account_for_user(request.user)
        transactions = get_statement(
            account=account,
            start_date=filters.validated_data['start_date'],
            end_date=filters.validated_data['end_date'],
        )

        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(transactions, request)
        
        return paginator.get_paginated_response(TransactionSerializer(page, many=True).data)

