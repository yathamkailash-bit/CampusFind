from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Item, Report, Claim, Student, Category
from .forms import ItemForm, ReportForm, ClaimForm, StudentForm
from .forms import RegistrationForm, LostItemForm
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.shortcuts import HttpResponse
from django.views import View
from django.contrib import messages
from django.utils.safestring import mark_safe


def home(request):
    # Provide approved claims as success stories (if any)
    claims = Claim.objects.filter(status='APPROVED').select_related('item','claimer')[:6]
    return render(request, 'home.html', {'claims': claims})


def items_list(request):
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()
    category_id = request.GET.get('category', '').strip()
    sort_by = request.GET.get('sort', 'recent').strip()

    items = Item.objects.select_related('category', 'location').all()
    if q:
        items = items.filter(Q(name__icontains=q) | Q(description__icontains=q))
    if status:
        items = items.filter(status=status)
    if category_id:
        items = items.filter(category_id=category_id)

    if sort_by == 'oldest':
        items = items.order_by('found_date', 'item_id')
    elif sort_by == 'alphabetical':
        items = items.order_by('name')
    else:
        items = items.order_by('-found_date', '-item_id')

    paginator = Paginator(items, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    categories = Category.objects.all()

    query_params = request.GET.copy()
    query_params.pop('page', None)
    query_string = query_params.urlencode()

    total_items = paginator.count
    if total_items == 1:
        showing_text = 'Showing 1 item'
    else:
        showing_text = f'Showing {page_obj.start_index()}-{page_obj.end_index()} of {total_items} items'

    context = {
        'items': page_obj.object_list,
        'page_obj': page_obj,
        'q': q,
        'status': status,
        'category_id': category_id,
        'sort': sort_by,
        'categories': categories,
        'showing_text': showing_text,
        'query_string': query_string,
        'total_items': total_items,
        'found_count': Item.objects.filter(status='FOUND').count(),
        'lost_count': Item.objects.filter(status='LOST').count(),
    }
    return render(request, 'items_list.html', context)


def item_detail(request, item_id):
    item = get_object_or_404(Item, item_id=item_id)
    return render(request, 'item_detail.html', {'item': item})


def add_item(request):
    if request.method == 'POST':
        form = ItemForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('items_list')
    else:
        form = ItemForm()
    return render(request, 'item_form.html', {'form': form})


def unclaimed_found(request):
    items = Item.objects.filter(status='FOUND').exclude(claims__isnull=False).order_by('-item_id')
    return render(request, 'unclaimed_found.html', {'items': items})


def student_reports(request, student_id):
    student = get_object_or_404(Student, student_id=student_id)
    reports = student.reports.all().order_by('-report_date')
    return render(request, 'student_reports.html', {'student': student, 'reports': reports})


def submit_report(request):
    if request.method == 'POST':
        if request.POST.get('report_type'):
            data = request.POST.copy()
            data['report_type'] = request.POST.get('report_type')
        else:
            data = request.POST
        form = ReportForm(data, request.FILES)
        if form.is_valid():
            report = form.save(commit=False)
            if request.user.is_authenticated and hasattr(request.user, 'student_profile'):
                report.reporter = request.user.student_profile
            report.save()
            messages.success(request, 'Your report has been submitted successfully.')
            return redirect('items_list')
    else:
        form = ReportForm()
    return render(request, 'report_wizard.html', {'form': form})


def submit_claim(request, item_id=None):
    item = None
    if item_id:
        item = get_object_or_404(Item, item_id=item_id)

    if request.method == 'POST':
        form = ClaimForm(request.POST, request.FILES, item=item)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your claim has been submitted successfully and is now under review.')
            return redirect('item_detail', item_id=item.item_id if item else form.cleaned_data['item'].item_id)
    else:
        form = ClaimForm(item=item)

    return render(request, 'submit_claim.html', {'form': form, 'item': item})


def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            name = form.cleaned_data.get('name')
            email = form.cleaned_data.get('email')
            phone = form.cleaned_data.get('phone')
            Student.objects.create(user=user, name=name, email=email or '', phone=phone or '')
            login(request, user)
            return redirect('profile')
    else:
        form = RegistrationForm()
        
    return render(request, 'register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('profile')
        else:
            # Provide clearer feedback when the username does not exist
            username = request.POST.get('username')
            if username:
                try:
                    User.objects.get(username=username)
                except User.DoesNotExist:
                    msg = mark_safe(
                        'User not found. This account is not registered. '
                        '<a href="/accounts/register/">Register here</a>.')
                    messages.error(request, msg)
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('home')


@login_required
def profile(request):
    user = request.user
    try:
        student = user.student_profile
    except Exception:
        student = None
    try:
        adminp = user.admin_profile
    except Exception:
        adminp = None
    return render(request, 'profile.html', {'user': user, 'student': student, 'adminp': adminp})


def students_crud(request):
    students = Student.objects.all()
    return render(request, 'students_list.html', {'students': students})


def add_student(request):
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('students')
    else:
        form = StudentForm()
    return render(request, 'student_form.html', {'form': form})


