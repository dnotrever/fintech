from django.urls import path

from account.views import AccountBalanceView, DepositView

urlpatterns = [
    path('balance/', AccountBalanceView.as_view(), name='account-balance'),
    path('deposit/', DepositView.as_view(), name='account-deposit'),
]
