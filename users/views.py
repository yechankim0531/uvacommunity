from django.shortcuts import render, redirect
from django.contrib.auth import logout

# Create your views here.

def home(request):
    # Check if the user is authenticated
    if request.user.is_authenticated:
        user_email = request.user.email
        user_name = request.user.get_full_name() or request.user.username  # Use full name if available, otherwise username
        is_pma = request.user.groups.filter(name="PMA").exists()  # Check if the user is in the PMA group    
    else:
        user_email = None
        user_name = None
        is_pma = False

    return render(request, 'home.html', {
    'user_email': user_email,
    'user_name': user_name,
    'is_pma': is_pma,
    })

def logout_view(request):
    logout(request)
    return redirect("/login")