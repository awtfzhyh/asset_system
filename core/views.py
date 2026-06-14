from django.shortcuts import render, get_object_or_404, redirect
from .models import Asset, Request
import csv
from .utils import render_to_pdf
from django.http import HttpResponse
from django.utils.timezone import now
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from .forms import BorrowRequestForm
from .forms import ReturnRequestForm
from .forms import ExtendRequestForm
from django.contrib import messages
from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.db.models import Q
import qrcode
from io import BytesIO

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome {user.username}, you have successfully logged in.")
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, 'login.html')

def logout_view(request):
    storage = messages.get_messages(request)
    for message in storage:
        pass  
    
    logout(request)
    return redirect('/login/')

def borrow_request(request, id=None):
    all_assets = Asset.objects.filter(status='Available')
    
    selected_asset = None
    if id:
        selected_asset = get_object_or_404(Asset, id=id)
        assets = Asset.objects.all().filter(Q(status='Available') | Q(id=id))
    else:
        assets = all_assets

    if request.method == 'POST':
        asset_id = request.POST.get('asset')
        asset_to_borrow = get_object_or_404(Asset, id=asset_id)
        
        current_user = request.user if request.user.is_authenticated else None

        new_request = Request.objects.create(
            asset=asset_to_borrow, 
            user=request.user,
            department=request.POST.get('department'),
            user_name=request.POST.get('user_name'),
            phone=request.POST.get('phone'),
            email=request.POST.get('email'),
            item_count=request.POST.get('item_count'), 
            purpose=request.POST.get('purpose'),
            date_borrowed=request.POST.get('date_borrowed'),
            return_date=request.POST.get('return_date'),
            request_type='borrow',
            status='pending'
        )
        
        pass
        messages.success(request, f"Request for {asset_to_borrow.name} submitted!")
        return redirect('manage_assets' if request.user.is_authenticated else 'borrow_request_empty')
        
    return render(request, 'borrow.html', {
        'assets': assets,
        'selected_asset': selected_asset
    })

def return_request(request, id):
    asset = get_object_or_404(Asset, id=id)
    borrower_data = Request.objects.filter(asset=asset, status='approved', request_type='borrow').last()

    if not borrower_data:
        messages.error(request, f"No active borrow record found for {asset.name}. Cannot process extension.")
        return redirect('manage_assets')

    if request.method == 'POST':
        user_name = request.POST.get('user_name') or (borrower_data.user_name if borrower_data else "Unknown Staff")
        department = request.POST.get('department') or (borrower_data.department if borrower_data else "Unknown")
        email = request.POST.get('email') or (borrower_data.email if borrower_data else "")
        phone = request.POST.get('phone') or (borrower_data.phone if borrower_data else "")
      
        Request.objects.create(
            asset=asset,
            user=request.user,
            user_name=user_name,
            department=department,
            email=email,
            phone=phone,
            return_date=request.POST.get('return_date'),
            condition=request.POST.get('condition', ''),
            remarks=request.POST.get('remarks', ''),
            request_type='return',
            status='pending'
        )
        messages.success(request, f"Return request for {asset.name} submitted.")
        return redirect('manage_assets' if request.user.is_authenticated else 'dashboard')

    return render(request, 'return.html', {
        'asset': asset, 
        'borrower': borrower_data
    })

def extend_request(request, id):
    asset = get_object_or_404(Asset, id=id)
    borrower_data = Request.objects.filter(asset=asset, status='approved', request_type='borrow').last()

    if not borrower_data:
        messages.error(request, f"No active borrow record found for {asset.name}. Cannot process return.")
        return redirect('manage_assets')

    if request.method == 'POST':
        user_name = request.POST.get('user_name') or (borrower_data.user_name if borrower_data else "Unknown Staff")
        department = request.POST.get('department') or (borrower_data.department if borrower_data else "Unknown")
        email = request.POST.get('email') or (borrower_data.email if borrower_data else "")
        phone = request.POST.get('phone') or (borrower_data.phone if borrower_data else "")
        
        Request.objects.create(
            asset=asset,
            user=request.user if request.user.is_authenticated else None,
            user_name=user_name,
            department=department,
            email=email,
            phone=phone,
            return_date=request.POST.get('return_date'),
            purpose=request.POST.get('purpose'),
            request_type='extend',
            status='pending'
        )
        messages.warning(request, f"Extension request for {asset.name} submitted.")
        return redirect('manage_assets' if request.user.is_authenticated else 'dashboard')

    return render(request, 'extend.html', {
        'asset': asset, 
        'borrower': borrower_data
    })
@login_required
def dashboard(request):
    from .models import Asset, Request
    from django.utils.timezone import now
    today = now().date()

    # --- Stats ---
    total_assets = Asset.objects.count()
    borrowed_count = Asset.objects.filter(status='Borrowed').count()
    pending_return = Request.objects.filter(request_type='return', status='pending').count()
    history = Request.objects.count()

    # --- FIX: Active Tracking Logic ---
    # We only want the LATEST approved borrow request for assets that are currently 'Borrowed'
    currently_out = Request.objects.filter(
        status='approved',
        request_type='borrow',
        asset__status='Borrowed'
    ).order_by('asset', '-created_at').distinct('asset') 
    # .distinct('asset') ensures only 1 row per asset (Works on PostgreSQL)

    # IF YOU ARE USING SQLITE (Default):
    # Use this logic instead if the .distinct('asset') above gives an error:
    active_asset_ids = Asset.objects.filter(status='Borrowed').values_list('id', flat=True)
    currently_out = []
    for asset_id in active_asset_ids:
        latest_req = Request.objects.filter(
            asset_id=asset_id, 
            status='approved', 
            request_type='borrow'
        ).order_by('-created_at').first()
        if latest_req:
            currently_out.append(latest_req)

        # --- Overdue Logic ---
        overdue_list = Request.objects.filter(
        status='approved',
        request_type='borrow',
        return_date__lt=today,        
        asset__status='Borrowed'      
    ).order_by('-return_date')
        
    overdue_assets = Asset.objects.filter(status='Borrowed')
        
    overdue_list = []
    
    for asset in overdue_assets:
        # Check if the latest approved borrow request for this specific asset is overdue
        latest_borrow = Request.objects.filter(
            asset=asset,
            status='approved',
            request_type='borrow'
        ).order_by('-created_at').first()
        
        if latest_borrow and latest_borrow.return_date < today:
            overdue_list.append(latest_borrow)

    return render(request, 'dashboard.html', {
        'total_assets': total_assets,
        'borrowed': borrowed_count,
        'pending_return': pending_return,
        'history': history,
        'overdue': overdue_list,
        'currently_out': currently_out,
        'now': now()
    })
@login_required
def send_overdue_reminder(request, id):
    req = get_object_or_404(Request, id=id)
    
    # Use request.get_host() for more reliability in different environments
    domain = f"{request.scheme}://{request.get_host()}"
    
    # Construct the action links
    return_url = f"{domain}/return/{req.asset.id}/"
    extend_url = f"{domain}/extend/{req.asset.id}/"

    subject = f"🚨 URGENT: Overdue Asset Reminder - {req.asset.name}"
    from_email = settings.DEFAULT_FROM_EMAIL
    
    recipient_list = [req.email]

    context = {
        'user_name': req.user_name,
        'asset_name': req.asset.name,
        'due_date': req.return_date.strftime("%d %B %Y"),
        'return_url': return_url,
        'extend_url': extend_url,
    }

    html_body = render_to_string('overdue_reminder.html', context)
    text_body = strip_tags(html_body)

    try:
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=from_email,
            to=recipient_list
        )
        email.attach_alternative(html_body, "text/html")
        email.send()

        messages.success(request, f"Overdue reminder sent to {req.user_name}!")
    except Exception as e:
        messages.error(request, f"Failed to send email: {str(e)}")

    return redirect('dashboard')

@login_required
def manage_assets(request):
    assets = Asset.objects.all()

    # 1. Get filter values from the URL parameters
    search = request.GET.get('search')
    category = request.GET.get('category') # This line was missing
    status = request.GET.get('status')
    
    # 2. Get unique categories for the dropdown list
    existing_categories = Asset.objects.values_list('category', flat=True).distinct()

    # 3. Apply filters to the queryset
    if search:
        assets = assets.filter(name__icontains=search)

    if category:
        assets = assets.filter(category=category)

    if status:
        assets = assets.filter(status=status)

    # 4. Return everything to the template
    return render(request, 'assets.html', {
        'assets': assets, 
        'categories': existing_categories,
    })

@login_required
def add_asset(request):
    if request.method == "POST":
        Asset.objects.create(
            name=request.POST.get('name'),
            category=request.POST.get('category'),
            brand=request.POST.get('brand'),
            model=request.POST.get('model'),
            serial_num=request.POST.get('serial_num'), # This MUST match models.py
            location=request.POST.get('location')
        )
        return redirect('/assets/')
    return render(request, 'add_assets.html')

@login_required
def edit_asset(request, id):
    asset = get_object_or_404(Asset, id=id)
    if request.method == "POST":
        asset.name = request.POST.get('name')
        asset.category = request.POST.get('category')
        asset.status = new_status = request.POST.get('status')
        asset.brand = request.POST.get('brand')
        asset.model = request.POST.get('model')
        asset.serial_num = request.POST.get('serial_num') # Fixed name here
        asset.location = request.POST.get('location')
        asset.save()

        if new_status == "Available":
            last_request = asset.request_set.filter(return_date__isnull=True).last()
            if last_request:
                from datetime import date
                last_request.return_date = date.today()
                last_request.save()

        return redirect('/assets/')
    
    return render(request, 'edit_asset.html', {'asset': asset})

@login_required
def delete_asset(request, pk):
    # This finds the asset by its ID (pk), or shows a 404 if not found
    asset = get_object_or_404(Asset, id=pk)
    
    # This deletes the asset from the database
    asset.delete()
    
    # This sends the user back to the manage assets page
    return redirect('/assets/')

def asset_detail(request, asset_id):
    from django.shortcuts import get_object_or_404
    asset = get_object_or_404(Asset, id=asset_id)
    
    return render(request, 'asset_detail.html', {'asset': asset})

@login_required
def manage_requests(request):
    requests = Request.objects.all()

    pending = Request.objects.filter(status='pending').count()
    approved_today = Request.objects.filter(status='approved', created_at__date=now().date()).count()
    rejected_today = Request.objects.filter(status='rejected', created_at__date=now().date()).count()

    return render(request, 'requests.html', {
        'requests': requests,
        'pending': pending,
        'approved_today': approved_today,
        'rejected_today': rejected_today
    })

from django.template.loader import render_to_string
from django.utils.html import strip_tags
import resend
import os

@login_required
def approve_request(request, id):
    req = get_object_or_404(Request, id=id)
    asset = req.asset
    
    # Update Statuses
    req.status = 'approved'
    req.save()

    if req.request_type == 'borrow':
        asset.status = 'Borrowed'
    elif req.request_type == 'return':
        asset.status = 'Available'
    elif req.request_type == 'extend':
        asset.status = 'Borrowed'
    
    original_borrow = Request.objects.filter(
            asset=asset, 
            status='approved', 
            request_type='borrow'
        ).order_by('-created_at').first()
        
    if original_borrow and req.return_date:
        original_borrow.return_date = req.return_date
        original_borrow.save()
            
    asset.save()

    safe_due_date = ""
    if req.return_date:
        try:
            safe_due_date = req.return_date.strftime("%d %B %Y")
        except AttributeError:
            safe_due_date = str(req.return_date)
            
    context = {
        'user_name': req.user_name,
        'status': 'approved',
        'request_type': req.request_type,
        'asset_name': asset.name,
        'serial_num': asset.serial_num,
        'feedback_message': "Your request has been verified and approved. Please ensure the asset is handled according to COE guidelines.",
        'due_date': safe_due_date,
    }
    
    html_content = render_to_string('asset_status_email.html', context)
    text_content = strip_tags(html_content)

   # Inside approve_request
    try:
        resend.api_key = os.environ.get("RESEND_API_KEY")
        resend.Emails.send({
            "from": "CoE Asset System <onboarding@resend.dev>",
            "to": req.email if req.email else "your_test_email@gmail.com",
            "subject": f"APPROVED: {asset.name} - COE Asset Management",
            "html": html_content
        })
        messages.success(request, "Request processed and staff notified.")
    except Exception as e:
        messages.warning(request, f"Processed successfully, but notification skipped: {e}")
        return redirect('dashboard')

@login_required
def reject_request(request, id):
    req = get_object_or_404(Request, id=id)
    req.status = 'rejected'
    req.save()

    # Prepare HTML Email
    context = {
        'user_name': req.user_name,
        'status': 'rejected',
        'request_type': req.request_type,
        'asset_name': req.asset.name,
        'serial_num': req.asset.serial_num,
        'feedback_message': "Unfortunately, your request could not be approved at this time. This may be due to scheduling conflicts or maintenance requirements."
    }

    html_content = render_to_string('asset_status_email.html', context)
    text_content = strip_tags(html_content)

    try:
        send_mail(
            subject=f"REJECTED: {req.asset.name} - COE Asset Management",
            message=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[req.email],
            html_message=html_content
        )
        messages.success(request, "Request rejected and user notified.")
    except Exception as e:
        messages.error(request, f"Rejection saved, but email failed: {e}")

    return redirect('dashboard')

@login_required
def report(request):
    start = request.GET.get('start')
    end = request.GET.get('end')
    status = request.GET.get('status')
    requests_qs = Request.objects.all()
    request_type = request.GET.get('type')

    if start and end:
        requests_qs = requests_qs.filter(created_at__range=[start, end])
    if status:
        requests_qs = requests_qs.filter(status=status)
    if request_type:
        requests_qs = requests_qs.filter(request_type=request_type)

    total_borrow = requests_qs.filter(request_type='borrow').count()
    total_return = requests_qs.filter(request_type='return').count()

    return render(request, 'report.html', {
        'requests': requests_qs,
        'total_borrow': total_borrow,
        'total_return': total_return
    })
@login_required
def export_pdf(request):
    start = request.GET.get('start')
    end = request.GET.get('end')
    status = request.GET.get('status')
    requests_qs = Request.objects.all()
    request_type = request.GET.get('type')

    if start and end:
        requests_qs = requests_qs.filter(created_at__range=[start, end])
    if status:
        requests_qs = requests_qs.filter(status=status)
    if request_type:
        requests_qs = requests_qs.filter(request_type=request_type)

    data = {
        'requests': requests_qs,
        'total_borrow': requests_qs.filter(request_type='borrow').count(),
        'total_return': requests_qs.filter(request_type='return').count(),
    }
    return render_to_pdf('report_pdf_template.html', data)

import csv
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .models import Request  # Ensure your model is imported

@login_required
def export_requests_csv(request):
    # 1. Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="COE_Asset_Report.csv"'

    # 2. Capture filters from the request (Matches your Report Page filters)
    start_date = request.GET.get('start')
    end_date = request.GET.get('end')
    status = request.GET.get('status')
    request_type = request.GET.get('type')

    # 3. Start with all objects and apply filters
    queryset = Request.objects.all().select_related('asset') # select_related makes it faster

    if start_date:
        queryset = queryset.filter(created_at__date__gte=start_date)
    if end_date:
        queryset = queryset.filter(created_at__date__lte=end_date)
    if status:
        queryset = queryset.filter(status=status)
    if request_type:
        queryset = queryset.filter(request_type=request_type)

    writer = csv.writer(response)
    
    # 4. Improved Headers (More professional for COE/SDEC)
    writer.writerow(['Request ID', 'Staff Name', 'Asset Name', 'Serial Number', 'Type', 'Status', 'Date/Time'])

    # 5. Write data rows
    for req in queryset:
        writer.writerow([
            req.id,
            req.user_name,
            req.asset.name,
            req.asset.serial_num,
            req.request_type.upper(),
            req.status.capitalize(),
            req.created_at.strftime("%Y-%m-%D %H:%M")
        ])

    return response


def print_labels(request):
    assets = Asset.objects.all()
    return render(request, 'print_labels.html', {'assets': assets})


def generate_qr(request, asset_id):
    # This creates the link the phone will open when scanned
    detail_url = request.build_absolute_uri(f'/asset-detail/{asset_id}/')
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(detail_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    
    return HttpResponse(buffer.getvalue(), content_type="image/png")