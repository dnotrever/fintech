from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from account.selectors import get_account_for_user
from account.serializers import BalanceSerializer


class AccountBalanceView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        account = get_account_for_user(request.user)
        return Response(BalanceSerializer(account).data)
