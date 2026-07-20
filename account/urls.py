from django.urls import path

from account.views import AccountBalanceView

urlpatterns = [
    path('balance/', AccountBalanceView.as_view(), name='account-balance'),
]
