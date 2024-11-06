from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import render,redirect,get_object_or_404
from . forms import *
from .models import *
from django.contrib.auth.decorators import login_required
from adminclick.models import *
from donors.models import *
from django.core.mail import send_mail
from django.contrib import messages
from django.views.decorators.cache import never_cache
from django.http import HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt 
from django.conf import settings
from django.db import transaction
from artist.models import *
from category.models import *
import json
from django.core.serializers.json import DjangoJSONEncoder

import logging

logger = logging.getLogger(__name__)

# Create your views here.
@login_required
@never_cache

def artist_dashboard(request):
       if request.user.is_authenticated and request.user.artist:
        artist= request.user.artist
        expressed_interest_count = Interest.objects.filter(artist=artist).count()
        accepted_interest_count = InterestRequest.objects.filter(
            artist=artist,
            status='accepted'
        ).count()
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        unread_notifications_count = ProNotification.objects.filter(artist=artist, is_read=False).count()
        context={
            'artist':artist,
            'unread_count':unread_count,
            'expressed_interest_count':expressed_interest_count,
            'accepted_interest_count':accepted_interest_count,
            'unread_notifications_count':unread_notifications_count,
        }
        return render(request,'artist/dashboard.html',context)
def profile_update(request):
    if request.method=='POST':
        user_form_artist = UserUpdateFormArtist(request.POST,instance=request.user)
        profile_form_artist=ProfileUpdateFormArtist(request.POST, request.FILES,instance=request.user.artist)

        if user_form_artist.is_valid() and profile_form_artist.is_valid():
            user_form_artist.save()
            profile_form_artist.save()
            return redirect ('artist_dashboard')
    else:
        if request.user.is_authenticated and request.user.artist:
         artist= request.user.artist
        user_form_artist = UserUpdateFormArtist(instance=request.user)
        profile_form_artist=ProfileUpdateFormArtist(instance=request.user.artist)
    context = {
     'user_form_artist': user_form_artist,
     'profile_form_artist':profile_form_artist,
      'artist':artist,
     
    }
    return render(request,'artist/updateprofile.html', context)

def pending_approval(request):
    return render(request, 'artist/pending_approval.html',{'user':request.user})


def upload_certificate(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        certificate = request.FILES.get('certificate')

        if not username:
            return JsonResponse({'success': False, 'error': 'Username not provided'})

        try:
            artist = Artist.objects.get(user__username=username)
        except Artist.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Artist not found'})

        # Check if the artist is already approved
        if artist.is_approved:
            return JsonResponse({'success': False, 'error': 'Account is already approved'})

        # Check if the certificate is provided in the request
        if certificate:
            # Check if the artist already has a certificate uploaded
            if artist.certificate:
                return JsonResponse({'success': False, 'error': 'Certificate already uploaded. Verification is under processing.'})
            else:
                # If no certificate is uploaded yet, save the new certificate
                artist.certificate = certificate
                artist.save()
                return JsonResponse({'success': True, 'message': 'Certificate uploaded successfully. Verification is under processing.'})
        else:
            return JsonResponse({'success': False, 'error': 'No file uploaded'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


def notifications(request):
    notifications = Notification.objects.filter(user=request.user)
    notifications.update(is_read=True)
    artist= request.user.artist
    expressed_interest_count = Interest.objects.filter(artist=artist).count()
    accepted_interest_count = InterestRequest.objects.filter(
        artist=artist,
        status='accepted'
        ).count()
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    context={
            'artist':artist,
            'unread_count':unread_count,
            'expressed_interest_count':expressed_interest_count,
            'accepted_interest_count':accepted_interest_count,
            'notifications': notifications
    }
    return render(request, 'artist/notifications.html', context)

@login_required
@never_cache

def view_ratesartist(request):
  
     artist=request.user.artist
     mediums=MediumOfWaste.objects.all()
     expressed_interest_count = Interest.objects.filter(artist=artist).count()
     accepted_interest_count = InterestRequest.objects.filter(
            artist=artist,
            status='accepted'
        ).count()
     unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
     context={
         'mediums': mediums , 
         'artist':artist,
        'unread_count':unread_count,
        'expressed_interest_count':expressed_interest_count,
        'accepted_interest_count':accepted_interest_count
     }
     return render(request, 'artist/view_rates.html',context )

@login_required
@never_cache

def express_interest(request,donation_id):
    donation=get_object_or_404(Donation, id=donation_id)
    artist = get_object_or_404(Artist, user=request.user)
    donor=donation.donor


    interest_request= InterestRequest.objects.create(
        artist=artist,
        donor=donor,
        donation=donation,
    )

    send_mail(
        'Interest in Donation',
        f'Artist {artist.user.username} has expressed interest in your donation:\n'
        f'Medium : {donation.medium_of_waste.name}\n'
        f'Quantity : {donation.quantity}\n'
        f'Location : {donation.location}\n'
        f'Please visit your dashboard and furthur proceed with accept or reject',
        'reartvault@gmail.com',
        [donor.user.email],
        fail_silently=False,
    )

    DonorNotification.objects.create(
        donor=donor,
        message=f'Artist{artist.user.username} has expressed interest in your donotation',
        interest_request=interest_request
    )
    
    return redirect('notifications')

from django.db.models import Max

@login_required
@never_cache
def artist_interest_status(request):
    artist = request.user.artist
    expressed_interest_count = Interest.objects.filter(artist=artist).count()
    accepted_interest_count = InterestRequest.objects.filter(
        artist=artist,
        status='accepted'
    ).count()
    interests = InterestRequest.objects.filter(artist=artist).select_related('donation', 'donor')
    
    # Fetch the most recent payment status for each interest
    for interest in interests:
        latest_payment = Payment.objects.filter(interest_request=interest).order_by('-created_at').first()
        if latest_payment:
            interest.payment_status = latest_payment.status
        else:
            interest.payment_status = None

    context = {
        'interests': interests,
        'expressed_interest_count': expressed_interest_count,
        'accepted_interest_count': accepted_interest_count,
        'artist': artist,
        'razorpay_api_key': settings.RAZORPAY_API_KEY,
    }
    return render(request, 'artist/interest_status.html', context)
    
from django.shortcuts import render, get_object_or_404
from .models import Interest

from django.shortcuts import render, get_object_or_404
from .models import Interest, Payment

from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO
from django.shortcuts import get_object_or_404
from .models import InterestRequest, Payment

def view_receipt(request, interest_id):
    interest = get_object_or_404(InterestRequest, id=interest_id)
    try:
        # Get the latest payment
        payment = Payment.objects.filter(interest_request=interest).latest('created_at')
        payment_status = payment.status
    except Payment.DoesNotExist:
        payment = None
        payment_status = "No payment found"
    
    context = {
        'interest': interest,
        'payment': payment,
        'payment_status': payment_status
    }
    
    # Generate PDF
    template = get_template('artist/receipt_template.html')
    html = template.render(context)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("ISO-8859-1")), result)
    
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="receipt_{interest_id}.pdf"'
        return response
    else:
        return HttpResponse('Error generating PDF', status=400)

def delete_notification(request, notification_id):
    notification=get_object_or_404(Notification,id=notification_id,user=request.user)
    notification.delete()
    return render('notifications')

@login_required
@never_cache
def add_mediums(request):
    if not request.user.artist.is_approved:
        return HttpResponseForbidden("You are not allowed to access this page.")

    artist=request.user.artist
    expressed_interest_count = Interest.objects.filter(artist=artist).count()
    accepted_interest_count = InterestRequest.objects.filter(
            artist=artist,
            status='accepted'
        ).count()
    if request.method == 'POST':
        mediums = request.POST.getlist('mediums')
        custom_medium_name = request.POST.get('custom_medium')
        
        if custom_medium_name:
            custom_medium, created = MediumOfWaste.objects.get_or_create(name=custom_medium_name)
            artist.mediums.add(custom_medium)
        
        for medium_id in mediums:
            medium = MediumOfWaste.objects.get(id=medium_id)
            artist.mediums.add(medium)

        messages.success(request, 'Mediums added successfully.')
        return redirect('artist_dashboard')

    context = {
        'mediums': MediumOfWaste.objects.all(),
        'expressed_interest_count':expressed_interest_count,
        'accepted_interest_count':accepted_interest_count,
        'artist':artist,

    }
    return render(request, 'artist/add_mediums.html',context)

import razorpay
def create_payment(request, interest_id):
    logger.debug(f"create_payment called with interest_id: {interest_id}")
    
    interest_request = get_object_or_404(InterestRequest, id=interest_id)
    logger.debug(f"InterestRequest retrieved: {interest_request}")
    
    medium_of_waste = interest_request.donation.medium_of_waste
    logger.debug(f"MediumOfWaste retrieved: {medium_of_waste}")
    
    amount = medium_of_waste.rate * interest_request.donation.quantity  
    logger.debug(f"Calculated amount: {amount}")

    client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET_KEY))
    logger.debug("Razorpay client initialized")
    
    order_data = {
        'amount': int(amount * 100),  # Amount in paise
        'currency': 'INR',
        'payment_capture': '1'
    }
    logger.debug(f"Order data prepared: {order_data}")
    
    try:
        order = client.order.create(order_data)
        logger.debug(f"Order created: {order}")
    except Exception as e:
        logger.error(f"Error creating order: {e}")
        return JsonResponse({'success': False, 'error': str(e)})
    
    payment = Payment.objects.create(
        artist=interest_request.artist,
        amount=amount,
        order_id=order['id'],
        interest_request=interest_request
    )
    logger.debug(f"Payment created: {payment}")

    context = {
        'order_id': order['id'],
        'razorpay_key': settings.RAZORPAY_API_KEY,
        'amount': amount,
        'interest_request': interest_request,
        'payment': payment
    }
    logger.debug(f"Context prepared: {context}")

    return render(request, 'artist/payment_page.html', context)


def payment_success(request):
    return render(request, 'artist/payment_success.html')

def payment_failed(request):
    return render(request, 'artist/payment_failed.html')

def verify_payment(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id)
    client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET_KEY))

    if request.method == "POST":
        try:
            params_dict = {
                'razorpay_order_id': request.POST.get('razorpay_order_id'),
                'razorpay_payment_id': request.POST.get('razorpay_payment_id'),
                'razorpay_signature': request.POST.get('razorpay_signature')
            }

            client.utility.verify_payment_signature(params_dict)
            payment.payment_id = params_dict['razorpay_payment_id']
            payment.status = 'completed'
            payment.save()

            # Handle post-payment processing
            return redirect('payment_success')

        except razorpay.errors.SignatureVerificationError:
            payment.status = 'failed'
            payment.save()
            return redirect('payment_failed')

    return render(request, 'artist/payment_failed.html')


@csrf_exempt
def payment_callback(request):
    if request.method == "POST":
        client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET_KEY))
        
        try:
            params_dict = {
                'razorpay_payment_id': request.POST['razorpay_payment_id'],
                'razorpay_order_id': request.POST['razorpay_order_id'],
                'razorpay_signature': request.POST['razorpay_signature']
            }

            client.utility.verify_payment_signature(params_dict)

            interest_id = request.POST['interest_id']
            interest = InterestRequest.objects.get(id=interest_id)
            interest.payment_status = 'paid'
            interest.save()

            return redirect('payment_success')

        except razorpay.errors.SignatureVerificationError:
            return redirect('payment_failed')
    
    return HttpResponseBadRequest()

@login_required
@never_cache
def artist_shop(request):
    if not hasattr(request.user, 'artist'):
        return HttpResponseForbidden("You are not allowed to access this page.")
    artist=request.user.artist
    products=Product.objects.filter(artist=artist)
    context={
        'products':products,
        'artist':artist,
    }
    return render(request, 'artist/shop_overview.html',context)

@login_required
@never_cache
def add_product(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        price = request.POST.get('price')
        image = request.FILES.get('image')
        stock = request.POST.get('stock')
        category_ids = request.POST.getlist('categories')

        product = Product.objects.create(
            artist=request.user.artist,
            name=name,
            description=description,
            price=price,
            image=image,
            stock=stock,
        )
        for category_id in category_ids:
            try:
                category = Category.objects.get(id=category_id)
                product.categories.add(category)
            except Category.DoesNotExist:
                continue


        product.save()
        messages.success(request, 'Product added successfully.')
        return redirect('artist_dashboard') 

    categories = Category.objects.all()
    return render(request, 'artist/add_product.html', {'categories': categories})

@login_required
@never_cache
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id, artist=request.user.artist)

    if request.method == 'POST':
        product.name = request.POST.get('name')
        product.description = request.POST.get('description')
        product.price = request.POST.get('price')
        if 'image' in request.FILES:
            product.image = request.FILES['image']
        product.stock = request.POST.get('stock')
        category_ids = request.POST.getlist('categories')
        custom_category = request.POST.get('custom_category')

        product.categories.clear()  

        for category_id in category_ids:
            try:
                category = Category.objects.get(id=category_id)
                product.categories.add(category)
            except Category.DoesNotExist:
                continue

        product.save()
        messages.success(request, 'Product updated successfully.')
        return redirect('artist_dashboard')

    categories = Category.objects.all()
    return render(request, 'artist/edit_product.html', {'product': product, 'categories':categories})


@login_required
@never_cache
def shopdash(request):
    artist=request.user.artist
    context={
        'artist':artist,
    }
    return render(request, 'artist/shopdash.html',context)




from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import render,redirect,get_object_or_404
from . forms import *
from .models import *
from django.contrib.auth.decorators import login_required
from adminclick.models import *
from donors.models import *
from django.core.mail import send_mail
from django.contrib import messages
from django.views.decorators.cache import never_cache
from django.http import HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt 
from django.conf import settings
from django.db import transaction
from artist.models import *
from category.models import *
import json
from django.core.serializers.json import DjangoJSONEncoder
# from .ml_utils import get_art_project_recommendations
from django.db.models import Sum
import logging

logger = logging.getLogger(__name__)


@login_required
@never_cache
def buyed_items(request):
    artist = request.user.artist
    expressed_interest_count = Interest.objects.filter(artist=artist).count()
    accepted_interest_count = InterestRequest.objects.filter(
            artist=artist,
            status='accepted'
        ).count()
    
    try:
        completed_payments = Payment.objects.filter(
            status='completed',
            artist=artist
        ).select_related('interest_request')
        
        donations = []
        for payment in completed_payments:
            donation = payment.interest_request.donation
            
            recommendations = get_art_project_recommendations(
                donation.medium_of_waste.name
            )

            donations.append({
                'id': donation.id,
                'image': donation.images.first().image.url if donation.images.exists() else None,
                'images': [img.image.url for img in donation.images.all()],
                'description': f"Donation of {donation.medium_of_waste.name}",
                'quantity': donation.quantity,
                'medium_of_waste': donation.medium_of_waste.name,
                'amount': payment.amount,
                'date': payment.created_at,
                'recommendations': recommendations
            })

        # Calculate totals
        total_items = len(donations)
        total_amount = sum(donation['amount'] for donation in donations)
        
        # Get the medium of waste summary
        medium_summary = completed_payments.values(
            'interest_request__donation__medium_of_waste__name'
        ).annotate(
            total_quantity=Sum('interest_request__donation__quantity'),
            total_amount=Sum('amount')
        )
        
        context = {
            'donations': donations,
            'donations_json': json.dumps(list(donations), cls=DjangoJSONEncoder),
            'total_items': total_items,
            'total_amount': total_amount,
            'medium_summary': medium_summary,
            'artist': artist,
            'expressed_interest_count':expressed_interest_count,
            'accepted_interest_count':accepted_interest_count,
        }
        return render(request, 'artist/buyed_items.html', context)
    except Exception as e:
        logger.error(f"Error in buyed_items view: {str(e)}")
        messages.error(request, "Unable to load donation data. Please try again later.")
        return redirect('artist_dashboard')

# def get_recommendations_view(request):
#     waste_material = request.GET.get('material', '')

#     if not waste_material:
#         return JsonResponse({'error': 'No waste material provided'}, status=400)

#     try:
#         recommendations = get_art_project_recommendations(waste_material)
#         logger.info(f"Generated recommendations for {waste_material}: {recommendations}")
#         return JsonResponse({'recommendations': recommendations})
#     except Exception as e:
#         logger.error(f"Error in get_recommendations_view: {str(e)}")
#         return JsonResponse({'error': 'Failed to generate recommendations'}, status=500)
    




from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from donors.models import Donation

import logging

logger = logging.getLogger(__name__)

def get_donation_details(request, donation_id):
    logger.debug(f"get_donation_details called with donation_id: {donation_id}")
    try:
        donation = get_object_or_404(Donation, id=donation_id)
        logger.debug(f"Donation found: {donation}")
        images = [img.image.url for img in donation.images.all()]
        data = {
            'id': donation.id,
            'medium_of_waste': donation.medium_of_waste.name if donation.medium_of_waste else 'N/A',
            'quantity': donation.quantity,
            'price': donation.medium_of_waste.rate if donation.medium_of_waste else 'N/A',
            'location': donation.location,
            'images': images,
        }
        logger.debug(f"Donation data: {data}")
        return JsonResponse(data)
    except Donation.DoesNotExist:
        logger.error(f"Donation not found with id: {donation_id}")
        return JsonResponse({'error': 'Donation not found'}, status=404)
    except Exception as e:
        logger.error(f"Error in get_donation_details: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'An unexpected error occurred'}, status=500)

@login_required
def order_notifications(request):

    notif = ProNotification.objects.filter(artist=request.user.artist, order__isnull=False).order_by('-created_at')
    return render(request, 'artist/ordernotifications.html', {'notif': notif})

from shop.models import Order
def update_order_status(request, order_id):
   

    order = get_object_or_404(Order, id=order_id)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        order.status = new_status
        order.save()
        return redirect('order_notifications')
       
    return render(request,'artist/statusupdate.html', {'order': order})
    
