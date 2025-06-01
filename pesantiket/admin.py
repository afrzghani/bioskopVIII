from django.contrib import admin
from .models import Film, Jadwal, Kursi, Pemesanan, User


admin.site.register(User)
admin.site.register(Film)
admin.site.register(Jadwal)
admin.site.register(Kursi)
admin.site.register(Pemesanan)

# Register your models here.
