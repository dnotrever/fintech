from django.urls import path

from customer.views import CustomerCreateView

urlpatterns = [
    path('', CustomerCreateView.as_view(), name='customer-create'),
]
