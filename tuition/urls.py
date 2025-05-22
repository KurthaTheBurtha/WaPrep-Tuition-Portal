from django.urls import path
from . import views

app_name = 'tuition'

urlpatterns = [
    path('', views.home, name='home'),
    path('login/parent/', views.parent_login, name='parent_login'),
    path('login/accountant/', views.accountant_login, name='accountant_login'),
    # path('signup/parent/', views.parent_signup, name='parent_signup'),
    path('logout/', views.logout_view, name='logout'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('students/', views.students, name='students'),
    path('students/add/', views.add_student, name='add_student'),
    path('students/delete/', views.delete_student, name='delete_student'),
    path('students/update/', views.update_student, name='update_student'),
    path('students/update-notes/', views.update_student_notes, name='update_student_notes'),
    path('payment/', views.payment, name='payment'),
    path('payment/process/', views.process_payment, name='process_payment'),
    path('payment/history/', views.payment_history, name='payment_history'),
    path('payment/receipt/<int:payment_id>/', views.download_receipt, name='download_receipt'),
    path('accountant/dashboard/', views.accountant_dashboard, name='accountant_dashboard'),
    path('accountant/reports/', views.accountant_reports, name='accountant_reports'),
    path('parent/dashboard/', views.parent_dashboard, name='parent_dashboard'),
    path('parent/welcome/', views.parent_welcome, name='parent_welcome'),
    path('parent/add-student/', views.add_student_to_parent, name='add_student_to_parent'),
    path('students/add-parent/', views.add_parent_to_student, name='add_parent_to_student'),
    path('students/remove-parent/', views.remove_parent_from_student, name='remove_parent_from_student'),
    path('student/<int:student_id>/', views.student_profile, name='student_profile'),
    path('student/add-parent/', views.add_parent_to_student, name='add_parent_to_student'),
    path('student/remove-parent/', views.remove_parent_from_student, name='remove_parent_from_student'),
    path('request-account/', views.request_account_view, name='request_account'),
    path('parent/profile/', views.parent_profile_view, name='parent_profile'),
] 