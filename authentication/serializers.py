from rest_framework import serializers


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class ResendConfirmationSerializer(serializers.Serializer):
    username = serializers.CharField()

