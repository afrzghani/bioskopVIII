from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    role_choices = (
        ('admin', 'Admin'),
        ('customer', 'Customer'),
    )

    nama = models.CharField(max_length=25)
    noTelepon = models.CharField(max_length=15, unique=True)
    role = models.CharField(max_length=10, choices=role_choices, default='customer')
    def noTelpLengkap(self):
        return f"+62{self.noTelepon}"

class Film(models.Model):
    judulFilm = models.CharField(max_length=45)
    genre = models.CharField(max_length=25)
    deskripsi = models.TextField()
    ratingUsia = models.CharField(max_length=10)
    durasi = models.IntegerField()
    poster = models.ImageField(upload_to='poster/', null=True, blank=True)
    
    def __str__(self):
        return self.judulFilm
    

class Jadwal(models.Model):
    film = models.ForeignKey(Film, on_delete=models.CASCADE)
    tanggal = models.DateField()
    jamTayang = models.TimeField()
    namaBioskop = models.CharField(max_length=20, null=True, blank=True)
    jenisStudio = models.CharField(max_length=20, null=True, blank=True)
    studio = models.CharField(max_length=10)
    
    def save(self, *args, **kwargs):
        is_baru = self.pk is None
        super().save(*args, **kwargs)

        # Jika ini data baru (baru saja dibuat), buat kursi
        if is_baru:
            baris = ['A', 'B', 'C', 'D', 'E']
            jumlah_kolom = 10
            for b in baris:
                for i in range(1, jumlah_kolom + 1):
                    nomor = f"{b}{i}"
                    Kursi.objects.create(
                        jadwal=self,
                        nomorKursi=nomor,
                        status=False,
                        harga=35000
                    )
    

class Kursi(models.Model):
    jadwal = models.ForeignKey(Jadwal, on_delete=models.CASCADE)
    nomorKursi = models.CharField(max_length=5)
    status = models.BooleanField(default=False)
    harga = models.FloatField()
    
class Pemesanan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    jadwal = models.ForeignKey(Jadwal, on_delete=models.CASCADE)
    tanggalPemesanan = models.DateField(auto_now_add=True)
    kursi = models.ManyToManyField(Kursi)
    totalHarga = models.FloatField()
    status = models.BooleanField(default=False)

class Pembayaran(models.Model):
    pemesanan = models.ForeignKey(Pemesanan, on_delete=models.CASCADE)
    metodePembayaran = models.CharField(max_length=50)

class Tiket(models.Model):
    pemesanan = models.ForeignKey(Pemesanan, on_delete=models.CASCADE)
    kursi = models.ForeignKey(Kursi, on_delete=models.CASCADE)
    kodeTiket = models.CharField(max_length=20, unique=True)
    jamTayang = models.TimeField()
    status = models.BooleanField(default=False)

    def cetakTiket(self):
        return f"Tiket untuk {self.pemesanan.user.nama} - Film: {self.pemesanan.jadwal.film.judulFilm} pada {self.jadwal.tanggal} jam {self.jadwal.jamTayang} di studio {self.jadwal.studio} dengan kursi {self.kursi.nomorKursi}"

# Create your models here.
