from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from account.serializers import AccountCreateSerializer, AccountSerializer
from account.services import create_account


class AccountCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        input_serializer = AccountCreateSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        account = create_account(owner=request.user, **input_serializer.validated_data)

        output_serializer = AccountSerializer(account)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

