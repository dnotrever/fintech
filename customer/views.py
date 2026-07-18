from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from customer.serializers import CustomerCreateSerializer, CustomerSerializer
from customer.services import register_customer


class CustomerCreateView(APIView):

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        input_serializer = CustomerCreateSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        customer = register_customer(**input_serializer.validated_data)
        output_serializer = CustomerSerializer(customer)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

