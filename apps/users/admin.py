from django.contrib import admin
from .models import User
# Register your models here.

admin.site.register(User)  # Add your user model here inside the register() method