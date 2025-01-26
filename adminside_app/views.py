from django.shortcuts import render,redirect,get_object_or_404
from django.views.decorators.http import require_http_methods
from log_reg_app.models import UserTable
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control,never_cache
from .models import CategoryTable,Language,Author,BookTable,BookImage
from django.http import JsonResponse
from order_detail_app.models import OrderDetails,OrderItem
from django.db import transaction
import logging
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from decimal import Decimal, InvalidOperation
import re
from django.db import models
from django.views.decorators.csrf import csrf_exempt
import json
from order_detail_app.models import CouponTable,OfferTable,ReturnRequest
from django.utils import timezone
from datetime import datetime
from django.urls import reverse
from django.utils.timezone import now
from django.utils.dateparse import parse_datetime
import os
from io import BytesIO
import openpyxl
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from collections import Counter
from django.db.models import Sum,F, ExpressionWrapper, DecimalField
from collections import defaultdict
from datetime import datetime, timedelta
from django.db.models.functions import TruncMonth, TruncYear,TruncDay
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
# Create your views here.

##############################################################################################################

@login_required(login_url='admin_login')
@never_cache

def admin_dashboard(request):

    order_data = OrderDetails.objects.all()
    active_users_count = UserTable.objects.filter(is_blocked=False, is_deleted=False).count()
    current_date = timezone.now()
    current_year = current_date.year

    total_revenue = OrderDetails.objects.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_discount = OrderItem.objects.annotate(
    discount=ExpressionWrapper(
        F('book__base_price') - F('price_per_item'),
        output_field=DecimalField()
    )
).aggregate(total_discount=Sum(F('discount') * F('quantity')))['total_discount'] or 0
    previous_month_end = current_date.replace(day=1) - timedelta(days=1)
    previous_month_start = previous_month_end.replace(day=1)  
    previous_month_end = previous_month_start.replace(day=28) + timedelta(days=4)  

    previous_month_revenue = order_data.filter(
        order_date__gte=previous_month_start,
        order_date__lte=previous_month_end
    ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0

    percentage_change = 0
    if previous_month_revenue > 0:
        percentage_change = ((total_revenue - previous_month_revenue) / previous_month_revenue) * 100

    # daily data
    daily_data = order_data.annotate(
        day=TruncDay('order_date', output_field=models.DateTimeField())
    ).values('day').annotate(
        total_amount_sum=Sum('total_amount')
    ).order_by('day')

    current_month = current_date.month
    current_month_data = [entry for entry in daily_data if entry['day'].month == current_month]
    days = [entry['day'].strftime('%d %b') for entry in current_month_data]
    total_amounts_by_day = [float(entry['total_amount_sum']) for entry in current_month_data]


    #monthly data
    monthly_data = order_data.annotate(
        month=TruncMonth('order_date', output_field=models.DateTimeField())
    ).values('month').annotate(
        total_amount_sum=Sum('total_amount')
    ).order_by('month')

    all_months = [datetime(current_year, month, 1) for month in range(1, 13)]

    sales_by_month = {entry['month'].strftime('%B %Y'): float(entry['total_amount_sum']) for entry in monthly_data}
    months = [month.strftime('%B %Y') for month in all_months]
    total_amounts_by_month = [sales_by_month.get(month, 0) for month in months]

    # Yearly data
    yearly_data = order_data.annotate(
        year=TruncYear('order_date', output_field=models.DateTimeField())
    ).values('year').annotate(
        total_amount_sum=Sum('total_amount')
    ).order_by('year')

    years = [entry['year'].strftime('%Y') for entry in yearly_data]

    total_amounts_by_year = [float(entry['total_amount_sum']) for entry in yearly_data]

    order_counts = order_data.values('order_date').annotate(total_amount_sum=Sum('total_amount'))

    total_amounts = [float(order['total_amount_sum']) for order in order_counts]  


    product_sales = Counter()
    for order in order_data:
        for item in order.orderitem_set.all():
            product_sales[item.book.book_name] += item.quantity

    top_products = product_sales.most_common(3)

    category_sales = Counter()
    for order in order_data:
        for item in order.orderitem_set.all():
            category_sales[item.book.category.category_name] += item.quantity

    top_categories = category_sales.most_common(3)

    payment_methods = defaultdict(int)
    for order in order_data:
        payment_methods[order.payment_method] += 1

    payment_method_data = [
        {"label": "Online", "count": payment_methods.get("ONLINE", 0)},
        {"label": "COD", "count": payment_methods.get("COD", 0)},
        {"label": "Wallet", "count": payment_methods.get("WALLET", 0)},
    ]

    cancelled_count = order_data.filter(order_status='Canceled').count()
    delivered_count = order_data.filter(order_status='Delivered').count()
    returned_count = order_data.filter(order_status='Returned').count()
    total_orders = order_data.count()

    cancellation_rate = 0
    if total_orders > 0:
        cancellation_rate = (cancelled_count / total_orders) * 100
    # Prepare context data for template
    context = {
        'order_data':order_data,
        'total_amounts_by_day': json.dumps(total_amounts_by_day),
        'days': json.dumps(days),
        'leave_count_by_month': json.dumps(total_amounts_by_month),
        'months': json.dumps(months),
        'leave_count_by_year': json.dumps(total_amounts_by_year),
        'years': json.dumps(years),
        'top_products': json.dumps(top_products),
        'top_categories': json.dumps(top_categories),
        'payment_methods': json.dumps(payment_method_data),
        'products':top_products,
        'categories':top_categories,
        'payment_method_data':payment_method_data,
        'cancelled_count': cancelled_count,
        'delivered_count': delivered_count,
        'returned_count': returned_count,
        'cancellation_rate': round(cancellation_rate, 2),
        'total_orders':total_orders,
        'total_revenue': total_revenue,
        'percentage_change': round(percentage_change, 2),
        'active_users_count': active_users_count,
        'total_discount':total_discount,
    }
    return render(request, 'admin_dashboard.html', context)

###############################################################################################################
@login_required(login_url='admin_login')
def admin_users(request):
    users = UserTable.objects.all().order_by('id')

    users_per_page = request.GET.get('users_per_page', 5)
    try:
        users_per_page = int(users_per_page)
    except ValueError:
        users_per_page = 5


    # search query
    search_query = request.GET.get('search','')


    if search_query:
        if search_query.isdigit():
            users = users.filter(
                Q(id=search_query) |
                Q(phone_number__icontains=search_query)
            )
        else:
            users = UserTable.objects.filter(
                Q(first_name__icontains=search_query) | 
                Q(last_name__icontains=search_query) |
                Q(username__icontains=search_query) |
                Q(email__icontains=search_query)
            ).order_by('id')
    else:
        users = UserTable.objects.all().order_by('id')
    # implement pagination

    paginator = Paginator(users, users_per_page)
    page_number = request.GET.get('page')
    users = paginator.get_page(page_number)

    # Check for AJAX request and send JSON response
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        users_data = [{
            "counter": index + 1 + (users.number - 1) * users.paginator.per_page,
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "phone_number": user.phone_number,
            "gender": user.gender,
            "is_blocked": user.is_blocked,
            "date_joined": user.date_joined.strftime('%Y-%m-%d'),
        } for index, user in enumerate(users)]
        return JsonResponse({"users": users_data})

    

    return render(request,'admin_users.html',{
        'users':users,
        'search_query':search_query
    })

######################################################################################################################
@login_required(login_url='admin_login')
def add_users(request):
    if request.method == "POST":
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        phone_number = request.POST.get('phone_number')
        gender = request.POST.get('gender')

        # Validate required fields
        if not all([first_name, last_name, username, email, password, phone_number, gender]):
            messages.error(request, "All fields are required")
            return render(request, 'add_users.html')

        # Check if username or email already exists
        if UserTable.objects.filter(username=username).exists():
            messages.error(request, "Username is already taken")
            return render(request, 'add_users.html')

        if UserTable.objects.filter(email=email).exists():
            messages.error(request, "Email is already taken")
            return render(request, 'add_users.html')

        # Check if passwords match
        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return render(request, 'add_users.html')

        # Create the user
        try:
            user = UserTable.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                gender=gender
            )
            user.phone_number = phone_number
            user.save()
            messages.success(request, "User created successfully")
            return redirect('admin_users')

        except Exception as e:
            messages.error(request, f"Error occurred: {e}")
            return render(request, 'add_users.html')
        
    return render(request, 'add_users.html')

#######################################################################################################################
@login_required(login_url='admin_login')
def view_users(request, pk):
    # single user view
    #id = request.GET.get('pk')
    user_detail = get_object_or_404(UserTable,id = pk)

    #user block and unblock
    if request.method == "POST":
        if user_detail.is_blocked:
            user_detail.is_blocked = False
            messages.success(request,f"{user_detail.username} has been unblocked.")
        else:
            user_detail.is_blocked = True
            messages.success(request,f"{user_detail.username} has been blocked.")
        user_detail.save()
        return redirect('view_users', pk = user_detail.id)
    return render(request,'view_users.html',{'record':user_detail})

#######################################################################################################################
@login_required(login_url='admin_login')
def admin_category(request):
    categories = CategoryTable.objects.annotate(product_count=Count('booktable'))

    categories_per_page = request.GET.get('categories_per_page', 5)
    try:
        categories_per_page = int(categories_per_page)
    except ValueError:
        categories_per_page = 5

    search_query = request.GET.get('search', '')
    if search_query:
        if search_query.isdigit():
            categories = categories.filter(id=search_query)
        else:
            categories = categories.filter(
                Q(category_name__icontains=search_query) |
                Q(description__icontains=search_query)
            ).order_by('id')
    else:
        categories = categories.order_by('id')

    # Check if any active offer is associated with the category
    for category in categories:
        active_offer = category.category_offers.filter(is_active=True).first()
        category.has_offer = active_offer is not None
        category.active_offer_id = active_offer.id if active_offer else None

    paginator = Paginator(categories, categories_per_page)
    page_number = request.GET.get('page')
    categories = paginator.get_page(page_number)

    # If it's an AJAX request, return JSON response
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        categories_data = [
            {
                "counter": index + 1 + (categories.number - 1) * categories.paginator.per_page,
                "id": category.id,
                "category_name": category.category_name,
                "description": category.description or '',
                "is_available": category.is_available,
                "has_offer": category.has_offer,
                "active_offer_id": category.active_offer_id,
                "product_count": category.product_count,  # Include product count
            }
            for index, category in enumerate(categories)
        ]
        return JsonResponse({"categories": categories_data})

    return render(request, 'admin_category.html', {'categories': categories, 'categories_per_page': categories_per_page})

##############################################################################################################################
@login_required(login_url='admin_login')
def add_category(request):
    if request.method == "POST":
        category_name = request.POST.get('category_name').strip()
        description = request.POST.get('description', '').strip()

        if not category_name and description:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': "Fields can't be empty."
                })
            messages.error(request, "Fields can't be empty.")
            return render(request, 'add_category.html')
        
        if CategoryTable.objects.filter(category_name__iexact=category_name).exists():
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': f"The category '{category_name}' already exists"
                })
            messages.error(request, f"The category '{category_name}' already exists")
            return render(request, 'add_category.html')
        
        try:
            CategoryTable.objects.create(
                category_name=category_name,
                description=description
            )
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': f"The category '{category_name}' has been added successfully!"
                })
            messages.success(request, f"The category '{category_name}' has been added successfully!")
            return redirect('admin_category')
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': "An error occurred while saving the category."
                })
            messages.error(request, "An error occurred while saving the category.")
            return render(request, 'add_category.html')
        
    return render(request, 'add_category.html')

################################################################################################################################
@login_required(login_url='admin_login')
def edit_category(request, pk):
    category = get_object_or_404(CategoryTable, id=pk)

    if request.method == "POST":
        # Handle delete category action
        if 'delete_category' in request.POST:
            category.is_available = False
            category.is_deleted = True
            category.save()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': 'Category marked as deleted.'
                })
            messages.success(request, 'Category marked as deleted.')
            return redirect('admin_category')
        
        # Handle re-add category action
        elif 'readd_category' in request.POST:
            category.is_available = True
            category.is_deleted = False
            category.save()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': 'Category re-added to the list successfully.'
                })
            messages.success(request, 'Category re-added to the list successfully.')
            return redirect('admin_category')
        
        # Handle update category details
        else:
            category_name = request.POST.get('category_name').strip()
            description = request.POST.get('description', '').strip()

            if not category_name or not description:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'error',
                        'message': "Fields can't be empty."
                    })
                messages.error(request, "Fields can't be empty.")
                return render(request, 'edit_category.html', {'category': category})

            # Check if the new category name already exists (excluding current category)
            if CategoryTable.objects.filter(category_name__iexact=category_name).exclude(id=pk).exists():
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'error',
                        'message': f"The category '{category_name}' already exists"
                    })
                messages.error(request, f"The category '{category_name}' already exists")
                return render(request, 'edit_category.html', {'category': category})

            try:
                category.category_name = category_name
                category.description = description
                category.save()
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'success',
                        'message': 'Category details updated successfully.'
                    })
                messages.success(request, 'Category details updated successfully.')
                return redirect('admin_category')
            except Exception as e:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'error',
                        'message': 'An error occurred while updating the category.'
                    })
                messages.error(request, 'An error occurred while updating the category.')
                return render(request, 'edit_category.html', {'category': category})
            
    return render(request, 'edit_category.html', {'category': category})

######################################################################################################################
@login_required(login_url='admin_login')
def delete_category(request, pk):  
    category = get_object_or_404(CategoryTable,id=pk)
    category.is_deleted = True
    category.is_available = False
    category.save()
    messages.success(request,'category deleted successfully')
    return redirect('admin_category')

######################################################################################################################
@login_required(login_url='admin_login')
def admin_products(request):
    books = BookTable.objects.all()

    products_per_page = request.GET.get('product_per_page', 5)
    try:
        products_per_page = int(products_per_page)
    except:
        products_per_page = 5

    # search query for products
    search_query = request.GET.get('search','')

    if search_query:
        if search_query.isdigit():
            books = BookTable.objects.filter(id=search_query)
        else:
            books = BookTable.objects.filter(
                Q(book_name__icontains = search_query) | 
                Q(author__name__icontains = search_query) | 
                Q(language__name__icontains = search_query) |
                Q(category__category_name__icontains = search_query)
            ).order_by('id')
    else:
        books = BookTable.objects.all().order_by('id')

    # Check if any active offer is associated with the category
    for book in books:
        active_offer = book.product_offer.filter(is_active=True).first()
        book.has_offer = bool(active_offer)
        book.active_offer_id = active_offer.id if active_offer else None
    paginator = Paginator(books, products_per_page)
    page_number = request.GET.get('page')
    books = paginator.get_page(page_number)

    product_data = [
        {
            'id': product.id,
            'counter': index + 1,
            'book_name': product.book_name,
            'category': product.category,
            'author': product.author,
            'language': product.language,
            'stock_quantity': product.stock_quantity,
            'base_price': product.base_price,
            'discount_percentage':product.discount_percentage,
            'offer_price': product.offer_price,
            'description': product.description,
            'publication_date': product.publication_date.strftime('%Y-%m-%d'),
            'is_available': product.is_available,
            'image_url': product.images.first().image.url if product.images.exists() else None,
        }
        for index, product in enumerate(books, start=(books.start_index()))
    ]
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'products': product_data,
            'has_next': books.has_next(),
            'has_previous': books.has_previous(),
            'num_pages': paginator.num_pages,
            'current_page': books.number,
        })

            
    return render(request,'admin_products.html',{'books':books})

#####################################################################################################################

logger = logging.getLogger(__name__)

@login_required(login_url='admin_login')
def add_products(request):

    if request.method == 'POST':
        logger.info("Processing add product POST request")
        errors = []

        try:
            # Validate book name
            book_name = request.POST.get('book_name')
            if not book_name:
                errors.append('Book name is required.')
            elif len(book_name) > 100:  # Adjust max length as per your model
                errors.append('Book name is too long.')

            # Validate description
            description = request.POST.get('description')
            if not description:
                errors.append('Description is required.')
            elif len(description) > 1000:  # Adjust max length as per your model
                errors.append('Description is too long.')

            # Validate stock quantity
            try:
                stock_quantity = request.POST.get('stock_quantity')
                if not stock_quantity:
                    errors.append('Stock quantity is required.')
                else:
                    stock_quantity = int(stock_quantity)
                    if stock_quantity <= 0:
                        errors.append('Stock quantity must be a positive number.')
            except ValueError:
                errors.append('Invalid stock quantity value.')

            # Validate base price
            try:
                base_price = request.POST.get('base_price')
                if not base_price:
                    errors.append('Base price is required.')
                else:
                    base_price = Decimal(base_price)
                    if base_price <= 0:
                        errors.append('Base price must be a positive number.')
                    elif base_price > Decimal('999999.99'):  # Add reasonable maximum
                        errors.append('Base price is too high.')
            except (InvalidOperation, ValueError):
                errors.append('Invalid base price value.')

            # Validate discount percentage
            try:
                discount_percentage = request.POST.get('discount_percentage', '0')
                discount_percentage = Decimal(discount_percentage)
                if discount_percentage < 0 or discount_percentage > 95:
                    errors.append('Discount percentage must be between 0 and 95.')
            except (InvalidOperation, ValueError):
                errors.append('Invalid discount percentage value.')

            # Validate author information
            author_name = request.POST.get('author_name')
            if not author_name:
                errors.append('Author name is required.')
            elif len(author_name) > 100:  # Adjust max length as per your model
                errors.append('Author name is too long.')

            # Validate language
            language_name = request.POST.get('language')
            if not language_name:
                errors.append('Language is required.')

            # Validate category
            category_name = request.POST.get('category')
            if not category_name:
                errors.append('Category is required.')

            # Validate images
            image_files = [
                request.FILES.get('book_image_1'),
                request.FILES.get('book_image_2'),
                request.FILES.get('book_image_3'),
                request.FILES.get('book_image_4')
            ]
            
            if not any(image_files):
                errors.append('At least one book image is required.')

            # Validate image sizes and types
            allowed_types = ['image/jpeg', 'image/png', 'image/jpg']
            max_size = 5 * 1024 * 1024  # 5MB

            for i, image in enumerate(image_files, 1):
                if image:
                    if image.size > max_size:
                        errors.append(f'Image {i} is too large. Maximum size is 5MB.')
                    if image.content_type not in allowed_types:
                        errors.append(f'Image {i} must be JPEG or PNG format.')

            # If there are validation errors, return them
            if errors:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Validation failed',
                    'errors': errors
                }, status=400)

            # If validation passes, proceed with saving
            with transaction.atomic():
                # Calculate offer price
                offer_price = base_price * (1 - discount_percentage / 100)

                # Process Author
                author, created = Author.objects.get_or_create(
                    name=author_name,
                    defaults={'bio': request.POST.get('bio', '')}
                )
                if not created and request.POST.get('bio'):
                    author.bio = request.POST.get('bio')
                    author.save()

                # Process Language
                language, _ = Language.objects.get_or_create(
                    name=language_name
                )

                # Process Category
                category, _ = CategoryTable.objects.get_or_create(
                    category_name=category_name
                )

                # Create Book instance
                book = BookTable.objects.create(
                    book_name=book_name,
                    description=description,
                    stock_quantity=stock_quantity,
                    base_price=base_price,
                    discount_percentage=discount_percentage,
                    offer_price=offer_price,
                    author=author,
                    language=language,
                    category=category,
                )
                logger.debug(f"Uploaded files: {request.FILES}")
                # Save valid images
                for image in image_files:
                    if image:
                        BookImage.objects.create(
                            book=book,
                            image=image
                        )
                        logger.debug(f"Saved image: {image.name}")
                    else:
                        logger.debug("Skipped a missing image.")

                messages.success(request, 'Product added successfully')
                return JsonResponse({
                    'status': 'success',
                    'message': 'Product added successfully',
                    'redirect_url': reverse('admin_products')
                })

        except Exception as e:
            logger.error(f"Error adding product: {str(e)}", exc_info=True)
            return JsonResponse({
                'status': 'error',
                'message': 'An unexpected error occurred. Please try again.',
                'errors': [str(e)]
            }, status=500)

    # GET request - render form
    try:
        categories = CategoryTable.objects.filter(is_available=True, is_deleted=False)
        languages = Language.objects.all()
        context = {
            'categories': categories,
            'languages': languages,
            'max_upload_size': '5MB',
            'allowed_image_types': 'JPEG, PNG'
        }
        return render(request, 'add_products.html', context)
    except Exception as e:
        logger.error(f"Error loading form data: {str(e)}", exc_info=True)
        messages.error(request, 'Error loading form. Please try again.')
        return redirect('admin_products')

########################################################################################################################
@login_required(login_url='admin_login')
def view_product(request,pk):
    book = get_object_or_404(BookTable,id=pk)
    images = book.images.all()
    return render(request,'view_product.html',{'book':book,'images':images})

########################################################################################################################
@login_required(login_url='admin_login')
def view_product(request,pk):
    book = get_object_or_404(BookTable,id=pk)
    images = book.images.all()
    return render(request,'view_product.html',{'book':book,'images':images})

###########################################################################################################################
logger = logging.getLogger(__name__)

@login_required(login_url='admin_login')
def edit_product(request, pk):
    """
    Handle product editing with comprehensive field validation and image management.
    Supports both standard form submission and AJAX requests.
    """
    try:
        book = get_object_or_404(BookTable, id=pk)
        
        if request.method == 'POST':
            logger.info(f"Processing edit product POST request for product ID: {pk}")
            
            # Handle delete request
            if request.GET.get('action') == 'delete':
                try:
                    with transaction.atomic():
                        book.is_available = False
                        book.is_deleted = True
                        book.save()
                        return JsonResponse({
                            'status': 'success',
                            'message': 'Product deleted successfully'
                        })
                except Exception as e:
                    logger.error(f"Error deleting product: {str(e)}", exc_info=True)
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Error deleting product'
                    }, status=500)

            # Handle readd request
            if 'readd_book' in request.POST:
                try:
                    with transaction.atomic():
                        book.is_available = True
                        book.is_deleted = False
                        book.save()
                        return JsonResponse({
                            'status': 'success',
                            'message': 'Product restored successfully'
                        })
                except Exception as e:
                    logger.error(f"Error restoring product: {str(e)}", exc_info=True)
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Error restoring product'
                    }, status=500)

            # Handle update request
            if 'update_product' in request.POST:
                errors = []
                try:
                    # Extract and validate form data
                    form_data = {
                        'book_name': request.POST.get('book_name', '').strip(),
                        'description': request.POST.get('description', '').strip(),
                        'stock_quantity': request.POST.get('stock_quantity', ''),
                        'base_price': request.POST.get('price', ''),
                        'discount_percentage': request.POST.get('discount_percentage', '0'),
                        'author_name': request.POST.get('author_name', '').strip(),
                        'author_bio': request.POST.get('bio', '').strip(),
                        'language': request.POST.get('language', '').strip(),
                        'category': request.POST.get('category', '').strip()
                    }

                    # Validation checks
                    if not form_data['book_name']:
                        errors.append('Book name is required.')
                    elif len(form_data['book_name']) > 100:
                        errors.append('Book name must be less than 100 characters.')

                    if not form_data['description']:
                        errors.append('Description is required.')
                    elif len(form_data['description']) > 1000:
                        errors.append('Description must be less than 1000 characters.')

                    try:
                        stock_qty = int(form_data['stock_quantity'])
                        if stock_qty < 0:
                            errors.append('Stock quantity cannot be negative.')
                    except ValueError:
                        errors.append('Invalid stock quantity.')

                    try:
                        base_price = Decimal(form_data['base_price'])
                        if base_price <= 0:
                            errors.append('Base price must be greater than 0.')
                        elif base_price > Decimal('999999.99'):
                            errors.append('Base price exceeds maximum limit.')
                    except InvalidOperation:
                        errors.append('Invalid base price.')

                    try:
                        discount = Decimal(form_data['discount_percentage'])
                        if not (0 <= discount <= 100):
                            errors.append('Discount must be between 0 and 100.')
                    except InvalidOperation:
                        errors.append('Invalid discount percentage.')

                    if not form_data['author_name']:
                        errors.append('Author name is required.')
                    elif len(form_data['author_name']) > 100:
                        errors.append('Author name must be less than 100 characters.')

                    if not form_data['language']:
                        errors.append('Language is required.')

                    if not form_data['category']:
                        errors.append('Category is required.')

                    # Validate images
                    updated_images = []
                    for i in range(1, 5):  # Handle up to 4 images
                        image_key = f'updated_image_{i}'
                        if image_key in request.FILES:
                            image = request.FILES[image_key]
                            if image.size > 5 * 1024 * 1024:  # 5MB limit
                                errors.append(f'Image {i} exceeds 5MB size limit.')
                            if image.content_type not in ['image/jpeg', 'image/png']:
                                errors.append(f'Image {i} must be JPEG or PNG format.')
                            updated_images.append((i, image))

                    if errors:
                        return JsonResponse({
                            'status': 'error',
                            'message': 'Validation failed',
                            'errors': errors
                        }, status=400)

                    # Update product if validation passes
                    with transaction.atomic():
                        # Calculate offer price
                        base_price = Decimal(form_data['base_price'])
                        discount = Decimal(form_data['discount_percentage'])
                        offer_price = base_price * (1 - discount / 100)

                        # Update or create related objects
                        author, _ = Author.objects.update_or_create(
                            name=form_data['author_name'],
                            defaults={'bio': form_data['author_bio']}
                        )

                        language, _ = Language.objects.get_or_create(
                            name=form_data['language']
                        )

                        category, _ = CategoryTable.objects.get_or_create(
                            category_name=form_data['category']
                        )

                        # Update book details
                        book.book_name = form_data['book_name']
                        book.description = form_data['description']
                        book.stock_quantity = int(form_data['stock_quantity'])
                        book.base_price = base_price
                        book.discount_percentage = discount
                        book.offer_price = offer_price
                        book.author = author
                        book.language = language
                        book.category = category
                        book.save()

                        # Handle image updates
                        existing_images = list(book.images.all())
                        
                        for index, new_image in updated_images:
                            # Get or create image object at specified position
                            if index <= len(existing_images):
                                # Update existing image
                                image_obj = existing_images[index - 1]
                                image_obj.image = new_image
                                image_obj.save()
                            else:
                                # Create new image
                                BookImage.objects.create(
                                    book=book,
                                    image=new_image
                                )

                        return JsonResponse({
                            'status': 'success',
                            'message': 'Product updated successfully',
                            'redirect_url': reverse('admin_products')
                        })

                except Exception as e:
                    logger.error(f"Error updating product: {str(e)}", exc_info=True)
                    return JsonResponse({
                        'status': 'error',
                        'message': 'An unexpected error occurred while updating the product.',
                        'error_details': str(e)
                    }, status=500)

        # GET request - render form with existing data
        context = {
            'book': book,
            'categories': CategoryTable.objects.filter(is_available=True, is_deleted=False),
            'languages': Language.objects.all(),
            'authors': Author.objects.all(),
            'max_upload_size': '5MB',
            'allowed_image_types': 'JPEG, PNG'
        }
        return render(request, 'edit_product.html', context)

    except Exception as e:
        logger.error(f"Error in edit_product view: {str(e)}", exc_info=True)
        messages.error(request, 'Error loading product data. Please try again.')
        return redirect('admin_products')

############################################################################################################################
@login_required(login_url='admin_login')
def delete_product(request,pk):
    book = get_object_or_404(BookTable, id=pk)
    book.is_deleted = True
    book.is_available = False
    book.save()
    messages.success(request,f"{book.book_name} is deleted successfully")
    return redirect('admin_products')

############################################################################################################################
@login_required(login_url='admin_login')
def admin_orders(request):
    # Default orders per page
    orders_per_page = request.GET.get('orders_per_page', 5)
    try:
        orders_per_page = int(orders_per_page)
    except ValueError:
        orders_per_page = 5

    # Base queryset
    orders = OrderDetails.objects.select_related('user', 'address')

    # Get search and filter parameters
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '')

    # Apply status filter
    status_mapping = {
        'pending': 'Pending',
        'shipped': 'Shipped',
        'out of delivery': 'Out of delivery',
        'delivered': 'Delivered',
        'canceled': 'Canceled',
    }
    if status_filter and status_filter in status_mapping:
        orders = orders.filter(order_status=status_mapping[status_filter])

    # Apply search filter
    if search_query:
        query = Q(order_id__icontains=search_query) | \
                Q(user__first_name__icontains=search_query) | \
                Q(user__last_name__icontains=search_query) | \
                Q(payment_method__icontains=search_query) | \
                Q(order_status__icontains=search_query)

        # Check if search query is a date
        try:
            if re.match(r'^\d{4}-\d{2}-\d{2}$', search_query):  # YYYY-MM-DD format
                query |= Q(order_date__date=search_query)
        except ValueError:
            pass

        orders = orders.filter(query)

    # Get counts for each status
    status_counts = {
        'pending': OrderDetails.objects.filter(order_status='Pending').count(),
        'shipped': OrderDetails.objects.filter(order_status='Shipped').count(),
        'out of delivery': OrderDetails.objects.filter(order_status='Out of delivery').count(),
        'delivered': OrderDetails.objects.filter(order_status='Delivered').count(),
        'canceled': OrderDetails.objects.filter(order_status='Canceled').count(),
    }

    # Order by date
    orders = orders.order_by('-order_date')

    # Paginate results
    paginator = Paginator(orders, orders_per_page)
    page_number = request.GET.get('page')
    orders = paginator.get_page(page_number)

    # Handle AJAX requests for partial updates
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        orders_data = [
            {
                "counter": index + 1 + (orders.number - 1) * orders.paginator.per_page,
                "order_id": order.order_id,
                "user": f"{order.user.first_name} {order.user.last_name}",
                "order_date": order.order_date.strftime('%Y-%m-%d %H:%M'),
                "payment_method": order.payment_method,
                "total_amount": str(order.total_amount),
                "order_status": order.order_status,
            }
            for index, order in enumerate(orders)
        ]
        return JsonResponse({"orders": orders_data})

    # Render template with context
    context = {
        'orders': orders,
        'search_query': search_query,
        'orders_per_page': orders_per_page,
        'current_status': status_filter,
        'status_counts': status_counts,
    }

    return render(request, 'admin_orders.html', context)

    

############################################################################################################################
@login_required(login_url='admin_login')
def view_order(request,order_id):
    order_detail = get_object_or_404(
        OrderDetails.objects.select_related('delivery_address', 'user', 'coupon', 'offer'),
        order_id=order_id
    )
    book_detail = OrderItem.objects.filter(order=order_detail).select_related('book')
    return render(request,'view_order.html',{'order_detail':order_detail,'book_detail':book_detail})

############################################################################################################################
@login_required(login_url='admin_login')
def update_order(request,order_id):
    order_detail = get_object_or_404(
        OrderDetails.objects.select_related('delivery_address', 'user', 'coupon', 'offer'),
        order_id=order_id
    )
    book_detail = OrderItem.objects.filter(order=order_detail).select_related('book')
    statuses = ["Pending", "Shipped","Out of delivery", "Delivered"]
    return render(request,'update_order.html',{'order_detail':order_detail,'book_detail':book_detail,'statuses':statuses})

############################################################################################################################
@login_required(login_url='admin_login')
def admin_cancel_order(request,order_id):
    if request.method == "POST":
        order = get_object_or_404(OrderDetails, order_id=order_id)

        if order.order_status != 'Canceled':
            order.order_status = 'Canceled'
            order.is_canceled = True
            order.save()
            messages.success(request, f"Order {order.order_id} has been canceled.")
        else:
            messages.warning(request, f"Order {order.order_id} is already canceled.")
    return redirect('update_order')

#############################################################################################################################

@login_required(login_url='admin_login')
def admin_single_item_cancel(request,order_id,order_item_id):
    if request.method == "POST":
        order_detail= get_object_or_404(OrderDetails, order_id=order_id)
        order_item = get_object_or_404(OrderItem, order=order_detail, id=order_item_id)

        order_item.is_canceled = True
        order_item.order_status = 'Canceled'
        order_item.save()

        #update the order status if all items are canceled
        if not OrderItem.objects.filter(order=order_detail, is_canceled=False).exists():
            order_detail.order_status = 'Canceled'
            order_detail.save()

        messages.success(request, f"Item has been canceled in Order {order_detail.order_id}.")
    return redirect('update_order',order_id=order_id)

#############################################################################################################################
@login_required(login_url='admin_login')
def status_update(request, order_id):
    if request.method == "POST":
        order = get_object_or_404(OrderDetails, order_id=order_id)
        new_status = request.POST.get('new_status')

        # Check if the order is already in a final state
        final_states = ['Delivered', 'Canceled', 'Returned']
        if order.order_status in final_states:
            messages.warning(request, f"Order {order.order_id} cannot be modified as it is in {order.order_status} status.")
            return redirect('update_order', order_id=order_id)

        if new_status and new_status != order.order_status:
            # Filter out canceled and returned items
            returnable_items = order.orderitem_set.exclude(
                Q(order_status='Canceled') | 
                Q(order_status='Returned')
            )

            # Update status for non-canceled and non-returned items
            returnable_items.update(order_status=new_status)

            # Update overall order status
            order.order_status = new_status
            order.save()

            messages.success(request, f"Order {order.order_id} status updated to {new_status}.")
        else:
            messages.warning(request, f"Order {order.order_id} is already in the {new_status} status.")

    return redirect('update_order', order_id=order_id)

#########################################################################################################################################
@login_required(login_url='admin_login')
@require_http_methods(["GET", "POST"])
def admin_coupon(request, coupon_id=None):
    try:
        if request.method == 'POST':
            coupon_id = request.POST.get('code_id')
            
        if coupon_id:
            coupon = get_object_or_404(CouponTable, id=coupon_id)
        else:
            coupon = None

        if request.method == 'POST':
            try:
                # Get form data
                code = request.POST.get('code', '').strip()
                coupon_type = request.POST.get('coupon_type', '').strip()
                discount_value = request.POST.get('discount_value', '').strip()
                min_purchase_amount = request.POST.get('min_purchase_amount', '').strip()
                max_uses = request.POST.get('max_uses', '').strip()
                valid_from = request.POST.get('valid_from', '').strip()
                valid_to = request.POST.get('valid_to', '').strip()
                is_active = request.POST.get('is_active') == 'on'

                # Perform validations
                errors = []

                # Validate required fields
                if not code:
                    errors.append("Coupon code is required.")
                else:
                    # Check for duplicate code only when creating or changing the code
                    if not coupon or coupon.code != code:  # New creation or code modification
                        existing_coupon = CouponTable.objects.filter(code=code)
                        if coupon:  # If editing, exclude the current coupon
                            existing_coupon = existing_coupon.exclude(id=coupon.id)
                        
                        if existing_coupon.exists():
                            errors.append(f"Coupon code '{code}' already exists.")
                
                if not coupon_type:
                    errors.append("Coupon type is required.")
                
                if not discount_value:
                    errors.append("Discount value is required.")
                else:
                    try:
                        discount_value = float(discount_value)
                        if discount_value <= 0:
                            errors.append("Discount value must be greater than 0.")
                    except (ValueError, TypeError):
                        errors.append("Invalid discount value.")
                
                if not min_purchase_amount:
                    errors.append("Minimum purchase amount is required.")
                else:
                    try:
                        min_purchase_amount = float(min_purchase_amount)
                        if min_purchase_amount <= 0:
                            errors.append("Minimum purchase amount must be greater than 0.")
                    except (ValueError, TypeError):
                        errors.append("Invalid minimum purchase amount.")
                
                if not max_uses:
                    errors.append("Maximum uses is required.")
                else:
                    try:
                        max_uses = int(max_uses)
                        if max_uses <= 0:
                            errors.append("Maximum uses must be greater than 0.")
                    except (ValueError, TypeError):
                        errors.append("Invalid maximum uses.")
                
                # Validate date range
                try:
                    # Make datetime timezone-aware
                    valid_from = timezone.make_aware(timezone.datetime.fromisoformat(valid_from))
                    valid_to = timezone.make_aware(timezone.datetime.fromisoformat(valid_to))
                    
                    if valid_from >= valid_to:
                        errors.append("Valid from date must be before valid to date.")
                except (ValueError, TypeError) as e:
                    errors.append(f"Invalid date range: {str(e)}")

                # If there are validation errors, return them
                if errors:
                    return JsonResponse({
                        'status': 'error', 
                        'message': '; '.join(errors)
                    }, status=400)

                # Proceed with creation/update if validation passes
                if coupon:  # Editing existing coupon
                    coupon.code = code
                    coupon.coupon_type = coupon_type
                    coupon.discount_value = discount_value
                    coupon.min_purchase_amount = min_purchase_amount
                    coupon.max_uses = max_uses
                    coupon.valid_from = valid_from
                    coupon.valid_to = valid_to
                    coupon.is_active = is_active
                    coupon.save()
                    
                    return JsonResponse({
                        'status': 'success',
                        'message': 'Coupon updated successfully!',
                        'redirect_url': reverse('admin_coupon')
                    })
                else:  # Creating new coupon
                    CouponTable.objects.create(
                        code=code,
                        coupon_type=coupon_type,
                        discount_value=discount_value,
                        min_purchase_amount=min_purchase_amount,
                        max_uses=max_uses,
                        valid_from=valid_from,
                        valid_to=valid_to,
                        is_active=is_active
                    )
                    return JsonResponse({
                        'status': 'success',
                        'message': 'Coupon created successfully!',
                        'redirect_url': reverse('admin_coupon')
                    })

            except Exception as e:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Form processing error: {str(e)}'
                }, status=400) 

        # GET request - render the form
        context = {
            'coupon': coupon,
            'COUPON_TYPES': CouponTable._meta.get_field('coupon_type').choices,
            'default_coupon_type': 'percentage',
            'coupons': CouponTable.objects.all().order_by('-valid_to')
        }
        return render(request, 'admin_coupon.html', context)

    except Exception as e:
        if request.method == 'POST':
            return JsonResponse({
                'status': 'error',
                'message': f'Server error: {str(e)}'
            }, status=500)
        # For GET requests, you might want to render an error template or redirect
        messages.error(request, f'An error occurred: {str(e)}')
        return redirect('admin_coupon')  


#########################################################################################################################################
@login_required(login_url='admin_login')
def admin_offer(request):
    # Fetch all offers without any filtering
    all_offers = OfferTable.objects.all().order_by('-created_at') 
    
    return render(request, 'admin_offer.html', {'all_offers': all_offers})
#########################################################################################################################################
@login_required(login_url='admin_login')
#function to apply the discount to the product's price
def apply_discount(base_price, discount_type, discount_value):
    if discount_type == 'percentage':
        return base_price - (base_price * (discount_value / 100))
    elif discount_type == 'fixed':
        return base_price - discount_value
    return base_price

@transaction.atomic
def handle_expired_offers():
    current_time = timezone.now()
    
    # Find expired offers
    expired_offers = OfferTable.objects.filter(
        valid_to__lt=current_time,
        is_active=True
    )
    
    for offer in expired_offers:
        # Get all books with this expired offer
        affected_books = BookTable.objects.filter(
            applied_offer=offer
        ).select_for_update()
        
        for book in affected_books:
            # Restore previous offer price if exists, otherwise calculate regular price
            if book.previous_offer_price:
                book.offer_price = book.previous_offer_price
                book.previous_offer_price = None
            else:
                regular_discount = (book.base_price * book.discount_percentage) / Decimal('100')
                book.offer_price = book.base_price - regular_discount
            
            book.additional_offer_applied = False
            book.applied_offer = None
            
            book.save(update_fields=[
                'offer_price',
                'previous_offer_price',
                'additional_offer_applied',
                'applied_offer'
            ])
        
        # Mark offer as inactive
        offer.is_active = False
        offer.save(update_fields=['is_active'])
#########################################################################################################################################
@login_required(login_url='admin_login')
@require_http_methods(["GET", "POST"])
def add_category_offer(request, category_id):
    category = get_object_or_404(CategoryTable, id=category_id)
    if request.method == 'POST':
        try:
            # Validate form data
            offer_name = request.POST.get('offer_name')
            offer_type = request.POST.get('offer_type')
            discount_type = request.POST.get('discount_type')
            discount_value = request.POST.get('discount_value')
            valid_from = request.POST.get('valid_from')
            valid_to = request.POST.get('valid_to')
            description = request.POST.get('description')
            is_active = request.POST.get('is_active') == 'on'

            # Perform validations
            errors = []

            if not offer_name:
                errors.append("Offer name is required.")
            
            if not discount_type:
                errors.append("Discount type is required.")
            
            # Validate discount value based on discount type
            try:
                discount_value = float(discount_value)
                if discount_type == 'percentage' and (discount_value < 0 or discount_value > 95):
                    errors.append("Percentage discount must be between 0 and 95.")
                elif discount_type in ['fixed', 'bundle'] and discount_value <= 0:
                    errors.append("Discount value must be greater than 0.")
            except (ValueError, TypeError):
                errors.append("Invalid discount value.")
            
            # Validate date range
            try:
                # Parse valid_from and set time to start of day if no time specified
                valid_from_dt = timezone.datetime.fromisoformat(valid_from)
                if valid_from.find('T') == -1:  # No time specified
                    valid_from_dt = valid_from_dt.replace(hour=0, minute=0, second=0, microsecond=0)
                
                # Parse valid_to and set time to end of day if no time specified
                valid_to_dt = timezone.datetime.fromisoformat(valid_to)
                if valid_to.find('T') == -1:  # No time specified
                    valid_to_dt = valid_to_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
                
                # Make dates timezone-aware
                if timezone.is_naive(valid_from_dt):
                    valid_from_dt = timezone.make_aware(valid_from_dt)
                if timezone.is_naive(valid_to_dt):
                    valid_to_dt = timezone.make_aware(valid_to_dt)

                # Get current time
                current_time = timezone.now()
                
                # Check if valid_from is before current date
                if valid_from_dt.date() < current_time.date():
                    errors.append("Valid from date must be today or a future date.")

                # Check if valid_to is before valid_from
                if valid_from_dt.date() > valid_to_dt.date():
                    errors.append("Valid from date must be before valid to date.")

            except (ValueError, TypeError):
                errors.append("Invalid date range.")

            if errors:
                return JsonResponse({
                    'status': 'error',
                    'message': '; '.join(errors)
                }, status=400)

            with transaction.atomic():
           
                # Create new offer
                new_offer = OfferTable.objects.create(
                    category=category,
                    offer_name=offer_name,
                    offer_type=offer_type,
                    discount_type=discount_type,
                    discount_value=discount_value,
                    valid_from=valid_from,
                    valid_to=valid_to,
                    description=description,
                    is_active=is_active
                )
                
                # Apply offer to products in the category
                if new_offer.is_active:
                    products_in_category = BookTable.objects.filter(
                        category=category,
                        is_available=True
                    ).select_for_update()
                    
                    for product in products_in_category:
                        product.update_price_with_offer(new_offer)

            return JsonResponse({
                'status': 'success',
                'message': 'Category offer added successfully!',
                'redirect_url': reverse('admin_category')
            })

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

    default_offer_type = 'category'
    context = {
        'category': category,
        'OFFER_TYPES': OfferTable.OFFER_TYPES,
        'default_offer_type': default_offer_type,
    }
    return render(request, 'add_category_offer.html', context)

#################################################################################################################
@login_required(login_url='admin_login')
@require_http_methods(["GET", "POST"])
def edit_category_offer(request, category_id):
    # Get the specific category
    category = get_object_or_404(CategoryTable, id=category_id)

    # Get the existing active offer for the category
    offer = category.category_offers.all().order_by('-is_active', 'id').first()

    if not offer:
        return JsonResponse({
            'status': 'error', 
            'message': 'No active offer exists for this category.'
        }, status=404)

    if request.method == 'POST':
        try:
            # Get form data from POST request
            offer_name = request.POST.get('offer_name')
            offer_type = request.POST.get('offer_type')
            discount_type = request.POST.get('discount_type')
            discount_value = request.POST.get('discount_value')
            valid_from = request.POST.get('valid_from')
            valid_to = request.POST.get('valid_to')
            description = request.POST.get('description')
            is_active = request.POST.get('is_active') == 'on'

            # Perform form validation
            errors = []

            if not offer_name:
                errors.append("Offer name is required.")
            
            if not discount_type:
                errors.append("Discount type is required.")
            
            # Validate discount value
            try:
                discount_value = float(discount_value)
                if discount_type == 'percentage' and (discount_value < 0 or discount_value > 95):
                    errors.append("Percentage discount must be between 0 and 95.")
                elif discount_type in ['fixed', 'bundle'] and discount_value <= 0:
                    errors.append("Discount value must be greater than 0.")
            except (ValueError, TypeError):
                errors.append("Invalid discount value.")
            
            # Validate date range
            try:
                valid_from_dt = timezone.datetime.fromisoformat(valid_from)
                if valid_from.find('T') == -1:  # No time specified
                    valid_from_dt = valid_from_dt.replace(hour=0, minute=0, second=0, microsecond=0)
                
                valid_to_dt = timezone.datetime.fromisoformat(valid_to)
                if valid_to.find('T') == -1:  # No time specified
                    valid_to_dt = valid_to_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
                
                # Make dates timezone-aware
                if timezone.is_naive(valid_from_dt):
                    valid_from_dt = timezone.make_aware(valid_from_dt)
                if timezone.is_naive(valid_to_dt):
                    valid_to_dt = timezone.make_aware(valid_to_dt)
                
                # Get current time
                current_time = timezone.now()

                # Check if valid_from is before today when creating new dates
                if valid_from_dt != offer.valid_from and valid_from_dt < current_time.date():
                    errors.append("Valid from date must be today or a future date.")

                # Check if valid_to is before valid_from
                if valid_from_dt.date() > valid_to_dt.date():
                    errors.append("Valid from date must be before valid to date.")

            except (ValueError, TypeError):
                errors.append("Invalid date range.")

            if errors:
                return JsonResponse({
                    'status': 'error', 
                    'message': '; '.join(errors)
                }, status=400)
            
            # Store old values for comparison
            old_discount_type = offer.discount_type
            old_discount_value = offer.discount_value
            old_is_active = offer.is_active

            with transaction.atomic():
            # Update the existing offer details
                offer.offer_name = offer_name
                offer.offer_type = offer_type
                offer.discount_type = discount_type
                offer.discount_value = discount_value
                offer.valid_from = valid_from_dt
                offer.valid_to = valid_to_dt
                offer.description = description
                offer.is_active = is_active
                offer.save()

                # Only recalculate prices if discount details changed or offer status changed
                if (old_discount_type != discount_type or 
                    old_discount_value != discount_value or 
                    old_is_active != is_active):
                    
                    products_in_category = BookTable.objects.filter(
                        category=category,
                        is_available=True
                    ).select_for_update()
                    
                    if is_active:
                        # Apply new offer prices
                        for product in products_in_category:
                            product.update_price_with_offer(offer)
                            
                        else:
                        # Remove offer from products using it
                            affected_products = products_in_category.filter(applied_offer=offer)
                            for product in affected_products:
                                product.update_price_with_offer(None)

            return JsonResponse({
                'status': 'success',
                'message': 'Category offer updated successfully!',
                'redirect_url': reverse('admin_category')
            })

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

    # For GET request
    context = {
        'category': category,
        'offer': offer,
        'OFFER_TYPES': OfferTable.OFFER_TYPES,
    }
    return render(request, 'edit_category_offer.html', context)

################################################################################################################
@login_required(login_url='admin_login')
@require_http_methods(["POST"])
def delete_category_offer(request, id):
    try:
        offer = get_object_or_404(OfferTable, id=id)
        books_with_offer =  BookTable.objects.filter(applied_offer = offer)
        for book in books_with_offer:
            book.applied_offer = None
            book.additional_offer_applied = False

            if book.previous_offer_price is not None:
                book.offer_price = book.previous_offer_price
                book.previous_offer_price = None
            book.save()

        offer.delete()
        return JsonResponse({
            'status': 'success',
            'message': 'Offer deleted successfully',
            'redirect_url': reverse('admin_products')
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

##############################################################################################
@login_required(login_url='admin_login')
@require_http_methods(["GET", "POST"])
def add_product_offer(request, product_id):
    product = get_object_or_404(BookTable, id=product_id)
    if request.method == 'POST':
        try:
            # Validate form data
            offer_name = request.POST.get('offer_name')
            discount_type = request.POST.get('discount_type')
            discount_value = request.POST.get('discount_value')
            valid_from = request.POST.get('valid_from')
            valid_to = request.POST.get('valid_to')
            description = request.POST.get('description')
            is_active = request.POST.get('is_active') == 'on'

            errors = []

            if not offer_name:
                errors.append("Offer name is required.")
            if not discount_type:
                errors.append("Discount type is required.")

            # Validate discount value
            try:
                discount_value = float(discount_value)
                if discount_type == 'percentage' and (discount_value <= 0 or discount_value > 95):
                    errors.append("Percentage discount must be greater than 0 and less than 95.")
                elif discount_type in ['fixed', 'bundle'] and discount_value <= 0:
                    errors.append("Discount value must be greater than 0.")
            except (ValueError, TypeError):
                errors.append("Invalid discount value.")

            # Validate date range with proper time handling
            try:
                # Parse valid_from and set time to start of day if no time specified
                valid_from_dt = timezone.datetime.fromisoformat(valid_from)
                if valid_from.find('T') == -1:  # No time specified
                    valid_from_dt = valid_from_dt.replace(hour=0, minute=0, second=0, microsecond=0)
                
                # Parse valid_to and set time to end of day if no time specified
                valid_to_dt = timezone.datetime.fromisoformat(valid_to)
                if valid_to.find('T') == -1:  # No time specified
                    valid_to_dt = valid_to_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
                
                # Make dates timezone-aware
                if timezone.is_naive(valid_from_dt):
                    valid_from_dt = timezone.make_aware(valid_from_dt)
                if timezone.is_naive(valid_to_dt):
                    valid_to_dt = timezone.make_aware(valid_to_dt)

                # Get current time
                current_time = timezone.now()
                
                # Check if valid_from is before current date
                if valid_from_dt.date() < current_time.date():
                    errors.append("Valid from date must be today or a future date.")

                # Check if valid_to is before valid_from
                if valid_from_dt.date() > valid_to_dt.date():
                    errors.append("Valid from date must be before valid to date.")

            except (ValueError, TypeError):
                errors.append("Invalid date range.")

            if errors:
                return JsonResponse({
                    'status': 'error',
                    'message': '; '.join(errors)
                }, status=400)

            with transaction.atomic():
                # Create new offer
                new_offer = OfferTable.objects.create(
                    product=product,
                    offer_name=offer_name,
                    offer_type='product',
                    discount_type=discount_type,
                    discount_value=discount_value,
                    valid_from=valid_from_dt,
                    valid_to=valid_to_dt,
                    description=description,
                    is_active=is_active
                )

                # Apply offer to product if active
                if new_offer.is_active:
                    # Use the model's built-in method to update price
                    price_updated = product.update_price_with_offer(new_offer)
                    
                    if not price_updated:
                        # If price wasn't updated, it means the new offer wasn't better
                        # We should still keep the offer but might want to log or notify
                        pass

            return JsonResponse({
                'status': 'success',
                'message': 'Product offer added successfully!',
                'redirect_url': reverse('admin_products')
            })

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

    default_offer_type = 'product'
    context = {
        'product': product,
        'OFFER_TYPES': OfferTable.OFFER_TYPES,
        'default_offer_type': default_offer_type,
    }
    return render(request, 'add_product_offer.html', context)
##############################################################################################
@login_required(login_url='admin_login')
@require_http_methods(["GET", "POST"])
def edit_product_offer(request, product_id):
    # Get the specific product
    product = get_object_or_404(BookTable, id=product_id)

    # Get the existing active offer for the product
    offer = product.product_offer.order_by('-is_active', 'id').first()
    
    if not offer:
        return JsonResponse({
            'status': 'error', 
            'message': 'No active offer exists for this product.'
        }, status=404)

    if request.method == 'POST':
        try:
            # Get form data from POST request
            offer_name = request.POST.get('offer_name')
            offer_type = request.POST.get('offer_type', 'product')
            discount_type = request.POST.get('discount_type')
            discount_value = request.POST.get('discount_value')
            valid_from = request.POST.get('valid_from')
            valid_to = request.POST.get('valid_to')
            description = request.POST.get('description')
            is_active = request.POST.get('is_active') == 'on'  # Checkbox returns 'on' when checked

            # Perform form validation
            errors = []

            if not offer_name:
                errors.append("Offer name is required.")
            
            if not discount_type:
                errors.append("Discount type is required.")
            
            # Validate discount value
            try:
                discount_value = float(discount_value)
                if discount_type == 'percentage' and (discount_value <= 0 or discount_value > 95):
                    errors.append("Percentage discount must be greater than 0 and less than 95.")
                elif discount_type in ['fixed', 'bundle'] and discount_value <= 0:
                    errors.append("Discount value must be greater than 0.")
            except (ValueError, TypeError):
                errors.append("Invalid discount value.")
            
            # Validate date range
            try:
                valid_from = timezone.datetime.fromisoformat(valid_from)
                valid_to = timezone.datetime.fromisoformat(valid_to)
                valid_to = valid_to.replace(hour=23, minute=59, second=59, microsecond=999999)
                
                # Make dates timezone-aware if they aren't already
                if timezone.is_naive(valid_from):
                    valid_from = timezone.make_aware(valid_from)
                if timezone.is_naive(valid_to):
                    valid_to = timezone.make_aware(valid_to)
                
                # Get today's start
                today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

                # Check if valid_from is before today when creating new dates
                if valid_from != offer.valid_from and valid_from < today_start:
                    errors.append("Valid from date must be today or a future date.")

                # Check if valid_to is before valid_from
                if valid_from.date() > valid_to.date():
                    errors.append("Valid from date must be before valid to date.")

            except (ValueError, TypeError):
                errors.append("Invalid date range.")

            if errors:
                return JsonResponse({
                    'status': 'error', 
                    'message': '; '.join(errors)
                }, status=400)

            # Store old values for comparison
            old_discount_type = offer.discount_type
            old_discount_value = offer.discount_value
            old_is_active = offer.is_active
            
            # Update the existing offer details
            offer.offer_name = offer_name
            offer.offer_type = offer_type
            offer.discount_type = discount_type
            offer.discount_value = discount_value
            offer.valid_from = valid_from
            offer.valid_to = valid_to
            offer.description = description
            offer.is_active = is_active
            offer.save()

            # Recalculate price if discount details changed or offer status changed
            if (old_discount_type != discount_type or 
                old_discount_value != discount_value or 
                old_is_active != offer.is_active):
                
                if offer.is_active:
                    # Calculate and apply new offer price
                    new_offer_price = calculate_offer_price(
                        product.base_price,
                        discount_type,
                        discount_value
                    )
                    
                    if new_offer_price < product.offer_price:
                        product.previous_offer_price = product.offer_price
                        product.offer_price = new_offer_price
                        product.additional_offer_applied = True
                        product.applied_offer = offer
                        product.save(update_fields=[
                            'previous_offer_price',
                            'offer_price',
                            'additional_offer_applied',
                            'applied_offer'
                        ])
                else:
                    # Revert price if offer is deactivated
                    if product.previous_offer_price is not None:
                        product.offer_price = product.previous_offer_price
                        product.previous_offer_price = None
                    else:
                        # Calculate regular price if no previous offer price exists
                        regular_discount = (product.base_price * product.discount_percentage) / Decimal('100')
                        product.offer_price = product.base_price - regular_discount
                        
                    product.additional_offer_applied = False
                    product.applied_offer = None
                    product.save(update_fields=[
                        'previous_offer_price',
                        'offer_price',
                        'additional_offer_applied',
                        'applied_offer'
                    ])

            return JsonResponse({
                'status': 'success', 
                'message': 'Offer updated successfully!',
                'redirect_url': reverse('admin_products')
            })

        except Exception as e:
            return JsonResponse({
                'status': 'error', 
                'message': str(e)
            }, status=500)

    # For GET request
    context = {
        'product': product,
        'offer': offer,
        'OFFER_TYPES': OfferTable.OFFER_TYPES,
    }
    return render(request, 'edit_product_offer.html', context)

##############################################################################################
@login_required(login_url='admin_login')
@require_http_methods(["POST"])
def delete_product_offer(request, id):
    try:
        offer = get_object_or_404(OfferTable, id=id)
        books_with_offer = BookTable.objects.filter(applied_offer = offer)
        for book in books_with_offer:
            # Reset the applied offer and related fields
            book.product_offer.clear()  
            book.applied_offer = None
            book.additional_offer_applied = False
            
            # Revert to previous offer price if it exists
            if book.previous_offer_price is not None:
                book.offer_price = book.previous_offer_price
                book.previous_offer_price = None 
            book.save(update_fields=[
                'applied_offer',
                'additional_offer_applied',
                'offer_price',
                'previous_offer_price'
            ])
        offer.delete()
        return JsonResponse({
            'status': 'success',
            'message': 'Offer deleted successfully',
            'redirect_url': reverse('admin_products')
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)
    
####################################################################################################
@login_required(login_url='admin_login')
@require_http_methods(["GET"])
def get_coupon_details(request, coupon_id):
    try:
        coupon = get_object_or_404(CouponTable, id=coupon_id)
        return JsonResponse({
            'id': coupon.id,
            'code': coupon.code,
            'coupon_type': coupon.coupon_type,
            'discount_value': coupon.discount_value,
            'min_purchase_amount': coupon.min_purchase_amount,
            'max_uses': coupon.max_uses,
            'valid_from': coupon.valid_from.isoformat(),
            'valid_to': coupon.valid_to.isoformat(),
            'is_active': coupon.is_active
        })
    except CouponTable.DoesNotExist:
        return JsonResponse({'error': 'Coupon not found'}, status=404)
    
####################################################################################################################
@login_required(login_url='admin_login')   
def delete_coupon(request, coupon_id):
    coupon = get_object_or_404(CouponTable, id=coupon_id)
    
    if request.method == 'POST':
        try:
            coupon.delete()
            return JsonResponse({
                'status': 'success', 
                'message': 'Coupon deleted successfully!',
                'redirect_url': reverse('admin_coupon')
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error', 
                'message': str(e)
            }, status=500)
    
    return JsonResponse({
        'status': 'error', 
        'message': 'Invalid request method'
    }, status=400)

###########################################################################################################################
@login_required(login_url='admin_login')
def generate_detailed_sales_report_pdf(request):
    try:
        # Fetch orders categorized by their statuses
        orders_by_status = {
            'Ordered': OrderDetails.objects.filter(order_status='Ordered'),
            'Shipped': OrderDetails.objects.filter(order_status='Shipped'),
            'Out of Delivery': OrderDetails.objects.filter(order_status='Out of delivery'),
            'Delivered': OrderDetails.objects.filter(order_status='Delivered'),
            'Canceled': OrderDetails.objects.filter(order_status='Canceled'),
        }

        # Fetch payment method-based orders
        orders_by_payment = {
            'COD': OrderDetails.objects.filter(payment_method='COD'),
            'Online Payment': OrderDetails.objects.filter(payment_method='ONLINE'),
            'Wallet': OrderDetails.objects.filter(payment_method='WALLET'),
        }

        # Refund details
        refunded_orders = OrderDetails.objects.filter(is_refund=True)
        total_refunded_amount = sum(order.total_amount for order in refunded_orders)

        # Create PDF
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        # Title
        p.setFont("Helvetica-Bold", 18)
        p.drawCentredString(width / 2, height - 50, "Detailed Sales Report")

        # Header Information
        p.setFont("Helvetica", 12)
        p.drawString(100, height - 80, f"Report Generated on: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Section 1: Orders by Status
        y = height - 120
        p.setFont("Helvetica-Bold", 14)
        p.drawString(50, y, "Orders by Status:")
        y -= 20
        for status, orders in orders_by_status.items():
            p.setFont("Helvetica-Bold", 12)
            p.drawString(100, y, f"{status}: {orders.count()} orders")
            y -= 20

        # Section 2: Orders by Payment Method
        p.setFont("Helvetica-Bold", 14)
        p.drawString(50, y - 20, "Orders by Payment Method:")
        y -= 40
        for method, orders in orders_by_payment.items():
            p.setFont("Helvetica-Bold", 12)
            p.drawString(100, y, f"{method}: {orders.count()} orders")
            y -= 20

        # Section 3: Refund Details
        p.setFont("Helvetica-Bold", 14)
        p.drawString(50, y - 20, "Refund Details:")
        y -= 40
        p.setFont("Helvetica", 12)
        p.drawString(100, y, f"Total Refunded Orders: {refunded_orders.count()}")
        p.drawString(100, y - 20, f"Total Refunded Amount: ₹{total_refunded_amount}")
        y -= 40

        # Save and close
        p.save()

        # Save to file
        pdf_name = f"sales_report_{timezone.now().strftime('%Y%m%d%H%M%S')}.pdf"
        media_path = os.path.join('media', 'reports')
        pdf_path = os.path.join(media_path, pdf_name)
        os.makedirs(media_path, exist_ok=True)

        with open(pdf_path, 'wb') as f:
            f.write(buffer.getvalue())

        buffer.close()

        return JsonResponse({
            'status': 'success',
            'message': 'Sales report PDF generated successfully!',
            'file_url': f'/media/reports/{pdf_name}',
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
#######################################################################################################################################
@login_required(login_url='admin_login')
def generate_detailed_sales_report_excel(request):
    try:
        # Fetch orders categorized by their statuses
        orders_by_status = {
            'Ordered': OrderDetails.objects.filter(order_status='Ordered'),
            'Shipped': OrderDetails.objects.filter(order_status='Shipped'),
            'Out of Delivery': OrderDetails.objects.filter(order_status='Out of delivery'),
            'Delivered': OrderDetails.objects.filter(order_status='Delivered'),
            'Canceled': OrderDetails.objects.filter(order_status='Canceled'),
        }

        # Fetch payment method-based orders
        orders_by_payment = {
            'COD': OrderDetails.objects.filter(payment_method='COD'),
            'Online Payment': OrderDetails.objects.filter(payment_method='ONLINE'),
            'Wallet': OrderDetails.objects.filter(payment_method='WALLET'),
        }

        # Refund details
        refunded_orders = OrderDetails.objects.filter(is_refund=True)
        total_refunded_amount = sum(order.total_amount for order in refunded_orders)

        # Create Excel Workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Sales Report"

        # Add header row
        ws.append(["Report Generated On", timezone.now().strftime('%Y-%m-%d %H:%M:%S')])

        # Orders by Status
        ws.append([""])
        ws.append(["Orders by Status"])
        for status, orders in orders_by_status.items():
            ws.append([status, orders.count()])

        # Orders by Payment Method
        ws.append([""])
        ws.append(["Orders by Payment Method"])
        for method, orders in orders_by_payment.items():
            ws.append([method, orders.count()])

        # Refund Details
        ws.append([""])
        ws.append(["Refund Details"])
        ws.append(["Total Refunded Orders", refunded_orders.count()])
        ws.append(["Total Refunded Amount", total_refunded_amount])

        # Save the Excel file
        excel_name = f"sales_report_{timezone.now().strftime('%Y%m%d%H%M%S')}.xlsx"
        media_path = os.path.join('media', 'reports')
        excel_path = os.path.join(media_path, excel_name)
        os.makedirs(media_path, exist_ok=True)

        wb.save(excel_path)

        return JsonResponse({
            'status': 'success',
            'message': 'Sales report Excel generated successfully!',
            'file_url': f'/media/reports/{excel_name}',
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
############################################################################################################################################
@login_required(login_url='admin_login')
def return_requests(request):
    return_requests = ReturnRequest.objects.filter(status='Pending').order_by('-created_at')
    return render(request, 'return_request.html', {'return_requests': return_requests})