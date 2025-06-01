from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.template.loader import get_template
from .forms import RegisterForm, FilmForm, JadwalForm
from .models import Film, Jadwal, Kursi, Pemesanan, Tiket, User
from django.urls import reverse
from datetime import date, datetime
from django.db import transaction
from django.contrib import messages
import re
from random import sample
from django.http import HttpResponseForbidden, HttpResponse
from xhtml2pdf import pisa

def registerView(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Akun berhasil dibuat. Silakan login.")
            return redirect('loginView')  # ganti dengan nama URL login kamu
        else:
            print(form.errors)
            messages.error(request, "Registrasi gagal. Mohon periksa data Anda.")
        return redirect('registerView')
    else:
        form = RegisterForm()      
    return render(request, 'register.html', {'form': form})

def loginView(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if user.role == 'admin':
                return redirect('adminDashboard')
            else:
                return redirect('home')
        else:
            return render(request, 'login.html', {'error': True})
    return render(request, 'login.html')

def logoutView(request):
    logout(request)
    request.session.flush()  # Clear session data
    return redirect('loginView')

def home(request):
    daftarFilm = Film.objects.all()
    listFilm=list(daftarFilm)
    if len(listFilm) > 3:
        carouselFilm = sample(listFilm, 3)
    else:
        carouselFilm = listFilm
    return render(request, 'home.html', {'daftarFilm' : daftarFilm, 'carouselFilm': carouselFilm})

def detailFilm(request, id):
    film = Film.objects.get(pk=id)
    return render(request, 'detailFilm.html', {'film': film})

@login_required
def pilihJadwal(request, idFilm):
    film = get_object_or_404(Film, id=idFilm)
    tanggal = request.GET.get('tanggal')
    if tanggal:
        try:
            tanggal = datetime.strptime(tanggal, "%Y-%m-%d").date()
        except ValueError:
            tanggal = date.today()
    else:
        tanggal = date.today()
    jadwal = Jadwal.objects.filter(film=film, tanggal=tanggal).order_by('jamTayang')
    listTanggal = Jadwal.objects.filter(film=film).values_list('tanggal', flat=True).distinct()
    
    listJadwal = {}
    for j in jadwal:
        bioskop = j.namaBioskop
        jenis = j.jenisStudio
        if bioskop not in listJadwal:
            listJadwal[bioskop] = {}
        if jenis not in listJadwal[bioskop]:
            listJadwal[bioskop][jenis] = []
        listJadwal[bioskop][jenis].append(j)
        
    pilihJamid = request.GET.get('jam')
    pilihBioskop = pilihJenis = pilihJam = None
    if pilihJamid:
        try:
            jadwal= Jadwal.objects.get(pk=pilihJamid)
            pilihBioskop = jadwal.namaBioskop
            pilihJenis = jadwal.jenisStudio
            pilihJam = jadwal.jamTayang
        except Jadwal.DoesNotExist:
            pass
    else:
        pilihJamid = None

    context = {
        'film': film,
        'listJadwal': listJadwal,
        'listTanggal': listTanggal,
        'pilihTanggal': tanggal,
        'pilihBioskop': pilihBioskop,
        'pilihJenis': pilihJenis,
        'pilihJam': pilihJam,
        'pilihJamid': pilihJamid,
    }
    return render(request, 'pilihJadwal.html', context)

def penomoran(kursi):
    return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', kursi.nomorKursi)]

@login_required
def pilihKursi(request, idJadwal):
    jadwal = get_object_or_404(Jadwal, pk=idJadwal)
    listKursi = Kursi.objects.filter(jadwal=jadwal).order_by('nomorKursi')
    listKursi = sorted(listKursi, key=penomoran)
    
    if request.method == 'POST':
        idKursiTerpilih = request.POST.getlist('kursiTerpilih')
        if not idKursiTerpilih:
            return render(request, 'pilihKursi.html', {'jadwal': jadwal, 'listKursi': listKursi, 'error': 'Silahkan pilih minimal 1 kursi',})
    
        request.session['kursiTerpilih'] = idKursiTerpilih
        request.session['idJadwal'] = idJadwal
        return redirect('konfirmasiPembayaran')

    context = {
        'jadwal': jadwal,
        'listKursi': listKursi
    }      
    return render(request, 'pilihKursi.html', context)

@login_required
def konfirmasiPembayaran(request):
    idKursi=request.session.get('kursiTerpilih',[])
    idJadwal = request.session.get('idJadwal')
    
    if not idKursi or not idJadwal:
        return redirect('home')
    listKursi = Kursi.objects.filter(id__in=idKursi)
    jadwal = get_object_or_404(Jadwal, pk=idJadwal)
    biayaLayanan = 3000
    jumlahTiket = len(listKursi)
    totalHarga = sum(kursi.harga for kursi in listKursi) + (biayaLayanan * jumlahTiket)

    context = {
        'jadwal': jadwal,
        'listKursi': listKursi,
        'totalHarga': totalHarga
    }
    return render(request, 'konfirmasiPembayaran.html',context)

@login_required
def prosesPembayaran(request):
    idKursi = request.session.get('kursiTerpilih', [])
    idJadwal = request.session.get('idJadwal')

    if not idKursi or not idJadwal:
        messages.error(request, "Data pembayaran tidak ditemukan.")
        return redirect('home')
    
    jadwal = get_object_or_404(Jadwal, pk=idJadwal)
    listKursi = Kursi.objects.select_for_update().filter(id__in=idKursi, status=False)
    
    if listKursi.count() != len(idKursi):
        messages.error(request, "Beberapa kursi sudah tidak tersedia.")
        return redirect('pilihKursi', idJadwal=idJadwal)
    
    with transaction.atomic():
        for kursi in listKursi:
            kursi.status = True
            kursi.save()
            
        pemesanan = Pemesanan.objects.create(
            user=request.user,
            jadwal=jadwal,
            totalHarga=sum(kursi.harga for kursi in listKursi)
        )
        pemesanan.kursi.set(listKursi)

    request.session.pop('kursiTerpilih', None)
    request.session.pop('idJadwal', None)

    request.session.pop('kursiTerpilih', None)
    request.session.pop('idJadwal', None)
    
    return render(request, 'pembayaranSukses.html',{
        'listKursi': listKursi,
        'jadwal': Jadwal.objects.get(pk=idJadwal),
        'totalHarga': sum(kursi.harga for kursi in listKursi)
    })
    
@login_required
def verifikasiTiketTerpakai(request, id):
    tiket = get_object_or_404(Tiket, id=id)
    tiket.terpakai = True
    tiket.save()
    return redirect('kelolaTiket')

@login_required
def riwayatPemesanan(request):
    listPemesanan = Pemesanan.objects.filter(user=request.user).order_by('-tanggalPemesanan')
    context = {
        'listPemesanan': listPemesanan
    }
    return render(request, 'riwayat.html', context)

def detailTiket(request, idPemesanan):
    tiket = get_object_or_404(Pemesanan, pk=idPemesanan)
    listKursi = tiket.kursi.all()
    biayaLayanan = 3000
    jumlahKursi = listKursi.count()
    hargaKursi = listKursi[0].harga if jumlahKursi > 0 else 0
    promo = getattr(tiket, 'promo', 0) or 0
    totalHarga = (hargaKursi * jumlahKursi) + (biayaLayanan * jumlahKursi) - int(promo)

    context = {
        'tiket': tiket,
        'listKursi': listKursi,
        'hargaKursi': hargaKursi,
        'jumlahKursi': jumlahKursi,
        'biayaLayanan': biayaLayanan,
        'promo': promo,
        'totalHarga': totalHarga,
    }
    return render(request, 'tiket.html', context)

@login_required
def profilPengguna(request):
    user = request.user
    return render(request, 'profilPengguna.html', {'user': user})

@login_required
def ubahPassword(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            return redirect('profilPengguna')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'ubahPassword.html', {'form': form})

def cetakTiket(request, idPemesanan):
    pemesanan = get_object_or_404(Pemesanan, pk=idPemesanan)
    listKursi = pemesanan.kursi.all()
    biayaLayanan = 3000
    jumlahKursi = listKursi.count()
    hargaKursi = listKursi[0].harga if jumlahKursi > 0 else 0
    promo = getattr(pemesanan, 'promo', 0) or 0
    totalHarga = (hargaKursi * jumlahKursi) + (biayaLayanan * jumlahKursi) - int(promo)
    
    template = get_template('tiketPdf.html')  
    html = template.render({
        'pemesanan': pemesanan,
        'hargaKursi': hargaKursi,
        'jumlahKursi': jumlahKursi,
        'biayaLayanan': biayaLayanan,
        'promo': promo,
        'totalHarga': totalHarga,
    })

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="tiket_{idPemesanan}.pdf"'
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Terjadi error saat membuat PDF', status=500)
    return response




@login_required
def adminDashboard(request):
    if not hasattr(request.user, 'role') or request.user.role != 'admin':
        return HttpResponseForbidden("Anda tidak memiliki akses ke halaman ini.")

    totalFilm = Film.objects.count()
    totalJadwal = Jadwal.objects.count()
    totalPemesanan = Pemesanan.objects.count()

    context = {
        'totalFilm': totalFilm,
        'totalJadwal': totalJadwal,
        'totalPemesanan': totalPemesanan,
    }
    return render(request, 'admin/dashboard.html', context)

@login_required
def kelolaFilm(request):
    if not request.user.role == 'admin':
        return HttpResponseForbidden()
    daftarFilm = Film.objects.all()
    return render(request, 'admin/kelolaFilm.html', {'daftarFilm': daftarFilm})

@login_required
def tambahFilm(request):
    if request.user.role != 'admin':
        return HttpResponseForbidden()
    if request.method == 'POST':
        form = FilmForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('kelolaFilm')
    else:
        form = FilmForm()
    return render(request, 'admin/tambaheditFilm.html', {'form': form, 'judul': 'Tambah Film'})

@login_required
def editFilm(request, id):
    if request.user.role != 'admin':
        return HttpResponseForbidden()
    film = get_object_or_404(Film, pk=id)
    if request.method == 'POST':
        form = FilmForm(request.POST, request.FILES, instance=film)
        if form.is_valid():
            form.save()
            return redirect('kelolaFilm')
    else:
        form = FilmForm(instance=film)
    return render(request, 'admin/tambaheditFilm.html', {'form': form, 'edit': True})

@login_required
def hapusFilm(request, id):
    if request.user.role != 'admin':
        return HttpResponseForbidden()
    film = get_object_or_404(Film, pk=id)
    film.delete()
    return redirect('kelolaFilm')


def kelolaJadwal(request):
    daftarFilm = Film.objects.all()
    daftarJadwal = Jadwal.objects.select_related('film').all()
    return render(request, 'admin/kelolaJadwal.html', {'daftarFilm': daftarFilm, 'daftarJadwal': daftarJadwal})

def tambahJadwal(request):
    if request.method == 'POST':
        form = JadwalForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('kelolaJadwal')
    else:
        form = JadwalForm()
    return render(request, 'admin/tambaheditJadwal.html', {'form': form, 'edit': False})

def editJadwal(request, id):
    jadwal = get_object_or_404(Jadwal, id=id)
    if request.method == 'POST':
        form = JadwalForm(request.POST, instance=jadwal)
        if form.is_valid():
            form.save()
            return redirect('kelolaJadwal')
    else:
        form = JadwalForm(instance=jadwal)
    return render(request, 'admin/tambaheditJadwal.html', {'form': form, 'edit': True})

def hapusJadwal(request, id):
    jadwal = get_object_or_404(Jadwal, id=id)
    jadwal.delete()
    return redirect('kelolaJadwal')

def kelolaTiket(request):
    daftarPemesanan = Pemesanan.objects.select_related('user', 'jadwal', 'jadwal__film').prefetch_related('kursi').all()
    return render(request, 'admin/kelolaTiket.html', {'daftarPemesanan': daftarPemesanan})

def verifikasiTiketTerpakai(request, id):
    pemesanan = get_object_or_404(Pemesanan, id=id)
    pemesanan.status = True
    pemesanan.save()
    return redirect('kelolaTiket')

@login_required
def kelolaAkun(request):
    if not request.user.role == 'admin':
        return HttpResponseForbidden()
    daftarUser = User.objects.all()
    return render(request, 'admin/kelolaAkun.html', {'daftarUser': daftarUser})

def ubahRole(request, id):
    if request.user.role != 'admin':
        return HttpResponseForbidden()
    
    user = get_object_or_404(User, id=id)
    
    if user.role == 'admin':
        user.role = 'user'
    else:
        user.role = 'admin'
    
    user.save()
    return redirect('kelolaAkun')