from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from account.models import AccountStatus
from authentication.models import EmailConfirmationToken
from authentication.serializers import LogoutSerializer, ResendConfirmationSerializer
from authentication.services import send_confirmation_email

User = get_user_model()


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


class ConfirmEmailView(APIView):

    permission_classes = [AllowAny]

    def get(self, request: Request, token: str) -> Response:

        try:
            confirmation = EmailConfirmationToken.objects.select_related('user__customer__account').get(token=token)
        except EmailConfirmationToken.DoesNotExist:
            return Response({'detail': 'Invalid confirmation token.'}, status=status.HTTP_404_NOT_FOUND)

        if confirmation.confirmed_at is not None:
            return Response({'detail': 'This confirmation link was already used.'}, status=status.HTTP_400_BAD_REQUEST)

        if confirmation.is_expired():
            return Response({'detail': 'This confirmation link has expired.'}, status=status.HTTP_400_BAD_REQUEST)

        confirmation.confirmed_at = timezone.now()
        confirmation.save()

        user = confirmation.user
        user.is_active = True
        user.save()

        account = user.customer.account
        account.change_status(AccountStatus.ACTIVE)
        account.save()

        return Response({'detail': 'Email confirmed successfully.'}, status=status.HTTP_200_OK)


class ResendConfirmationView(APIView):

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'resend-confirmation'

    def post(self, request: Request) -> Response:
        serializer = ResendConfirmationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(username=serializer.validated_data['username'], is_active=False).first()
        if user is not None:
            send_confirmation_email(user)
        return Response({'detail': 'If the account exists and is not confirmed yet, a new email was sent.'}, status=status.HTTP_200_OK)

