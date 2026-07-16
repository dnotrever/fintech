from django.urls import path

from account.views import AccountCreateView

urlpatterns = [
    path('', AccountCreateView.as_view(), name='account-create'),
]
