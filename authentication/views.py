from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from authentication.serializers import LogoutSerializer


class LogoutView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        input_serializer = LogoutSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        try:
            RefreshToken(input_serializer.validated_data['refresh']).blacklist()
        except TokenError as exc:
            raise serializers.ValidationError({'refresh': str(exc)}) from exc
        return Response(status=status.HTTP_205_RESET_CONTENT)

