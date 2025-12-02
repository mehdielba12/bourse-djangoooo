from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),          # /  → dashboard
    path('marche/', views.stock_list, name='stock_list'), # /marche
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('transactions/', views.transaction_list, name='transaction_list'),
    path('cash/', views.cash_operation, name='cash_operation'),
   path('order/', views.place_order, name='place_order'),

]



