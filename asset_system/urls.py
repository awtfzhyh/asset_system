"""
URL configuration for asset_system project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from core import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('send-reminder/<int:id>/', views.send_overdue_reminder, name='send_overdue_reminder'),

    # AUTH
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # ASSET
    path('assets/', views.manage_assets, name='manage_assets'),
    path('add-assets/', views.add_asset, name='add_asset'),
    path('edit-asset/<int:id>/', views.edit_asset, name='edit_asset'),
    path('delete-asset/<int:pk>/', views.delete_asset, name='delete_asset'),

    # REQUESTS
    path('requests/', views.manage_requests),
    path('approve/<int:id>/', views.approve_request),
    path('reject/<int:id>/', views.reject_request),

    # FORMS
    path('borrow/', views.borrow_request, name='borrow_request_empty'),
    path('borrow/<int:id>/', views.borrow_request, name='borrow_asset'),
    path('return/<int:id>/', views.return_request, name='return_asset'),
    path('extend/<int:id>/', views.extend_request, name='extend_asset'),

    # REPORT
    path('report/', views.report, name='report'),
    path('export-pdf/', views.export_pdf, name='export_pdf'),
    path('export-csv/', views.export_requests_csv, name='export_requests_csv'),

    path('print-labels/', views.print_labels, name='print_labels'),
    path('asset-qr/<int:asset_id>/', views.generate_qr, name='asset_qr'),
    path('asset-detail/<int:asset_id>/', views.asset_detail, name='asset_detail'),
]
