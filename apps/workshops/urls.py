from django.urls import path
from . import views

app_name = 'workshops'

urlpatterns = [
    # Workshop listing and discovery
    path('', views.WorkshopListView.as_view(), name='list'),
    path('category/<slug:category_slug>/', views.WorkshopListView.as_view(), name='category'),
    
    # Smart dashboard routing (must come before workshop detail to avoid slug conflict)
    path('dashboard/', views.DashboardRedirectView.as_view(), name='dashboard'),
    path('my/dashboard/', views.StudentDashboardView.as_view(), name='student_dashboard'),
    path('my/registrations/', views.MyRegistrationsView.as_view(), name='my_registrations'),
    
    # Instructor dashboard
    path('instructor/dashboard/', views.InstructorDashboardView.as_view(), name='instructor_dashboard'),
    path('instructor/workshops/', views.InstructorWorkshopsView.as_view(), name='instructor_workshops'),
    path('instructor/workshop/create/', views.CreateWorkshopView.as_view(), name='create_workshop'),
    path('instructor/workshop/<slug:slug>/edit/', views.EditWorkshopView.as_view(), name='edit_workshop'),
    path('instructor/workshop/<slug:slug>/delete/', views.WorkshopDeleteView.as_view(), name='delete_workshop'),
    path('instructor/workshop/<slug:slug>/sessions/', views.ManageSessionsView.as_view(), name='manage_sessions'),
    path('instructor/session/<uuid:session_id>/edit/', views.EditSessionView.as_view(), name='edit_session'),
    path('instructor/session/<uuid:session_id>/registrations/',
         views.SessionRegistrationsView.as_view(), name='session_registrations'),
    path('instructor/session/<uuid:session_id>/attendance-sheet/',
         views.AttendanceSheetView.as_view(), name='attendance_sheet'),
    path('instructor/session/<uuid:session_id>/materials/',
         views.SessionMaterialsView.as_view(), name='session_materials'),
    path('instructor/session/<uuid:session_id>/materials/create/', 
         views.CreateSessionMaterialView.as_view(), name='create_session_material'),
    path('instructor/material/<uuid:material_id>/edit/', 
         views.EditSessionMaterialView.as_view(), name='edit_session_material'),
    path('instructor/session/<uuid:session_id>/material/<uuid:material_id>/delete/', 
         views.DeleteSessionMaterialView.as_view(), name='delete_session_material'),
    
    # Material downloads
    path('material/<uuid:material_id>/download/', 
         views.MaterialDownloadView.as_view(), name='material_download'),
    
    # Participant materials access
    path('session/<uuid:session_id>/materials/', 
         views.ParticipantMaterialsView.as_view(), name='participant_materials'),
    
    # Registration (also before workshop detail to avoid conflicts)
    path('registration/<uuid:registration_id>/confirm/',
         views.RegistrationConfirmView.as_view(), name='registration_confirm'),
    path('registration/<uuid:registration_id>/cancel/',
         views.RegistrationCancelView.as_view(), name='registration_cancel'),
    path('registration/<uuid:registration_id>/checkout/success/',
         views.WorkshopCheckoutSuccessView.as_view(), name='checkout_success'),
    path('registration/<uuid:registration_id>/checkout/cancel/',
         views.WorkshopCheckoutCancelView.as_view(), name='checkout_cancel'),
    path('promotion/<uuid:registration_id>/confirm/',
         views.PromotionConfirmView.as_view(), name='confirm_promotion'),
    path('<slug:workshop_slug>/session/<uuid:session_id>/register/',
         views.WorkshopRegistrationView.as_view(), name='register'),
    
    # Workshop interest requests
    path('<slug:slug>/request/', views.WorkshopInterestView.as_view(), name='request_interest'),

    # Cart functionality
    path('cart/', views.WorkshopCartView.as_view(), name='cart'),
    path('cart/add/<uuid:session_id>/', views.AddToCartView.as_view(), name='add_to_cart'),
    path('cart/remove/<uuid:session_id>/', views.RemoveFromCartView.as_view(), name='remove_from_cart'),
    path('cart/clear/', views.ClearWorkshopCartView.as_view(), name='clear_cart'),
    path('cart/process-payment/', views.ProcessCartPaymentView.as_view(), name='process_cart_payment'),
    path('cart/checkout/success/', views.CheckoutSuccessView.as_view(), name='cart_checkout_success'),
    path('cart/checkout/cancel/', views.CheckoutCancelView.as_view(), name='cart_checkout_cancel'),

    # Terms and Conditions
    path('terms-and-conditions/', views.WorkshopTermsView.as_view(), name='terms'),

    # Individual workshop (MUST BE LAST - catches all remaining slugs)
    path('<slug:slug>/', views.WorkshopDetailView.as_view(), name='detail'),
]