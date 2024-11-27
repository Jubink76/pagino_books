from django.shortcuts import render,redirect,get_object_or_404
from log_reg_app.models import UserTable
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
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
from django.views.decorators.csrf import csrf_exempt
import json

# Create your views here.

##############################################################################################################

@login_required(login_url='admin_login')
@never_cache
def admin_dashboard(request):
    return render(request,'admin_dashboard.html')

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
    print(search_query)

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

    categories = CategoryTable.objects.all()

    categories_per_page = request.GET.get('categories_per_page', 5)
    try:
        categories_per_page = int(categories_per_page)
    except ValueError:
        categories_per_page = 5

    search_query = request.GET.get('search','')
    if search_query:
        if search_query.isdigit():
            categories = categories.filter(id=search_query)
        else:
            categories = CategoryTable.objects.filter(
                Q(category_name__icontains=search_query) | 
                Q(description__icontains=search_query)
            ).order_by('id')
    else:
        categories = CategoryTable.objects.all().order_by('id')

    paginator = Paginator(categories, categories_per_page)
    page_number = request.GET.get('page')
    categories = paginator.get_page(page_number)
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        categories_data = [{
            "counter": index + 1 + (categories.number - 1) * categories.paginator.per_page,
            "id": category.id,
            "category_name": category.category_name,
            "description": category.description or '',
            "is_available": category.is_available, 
            'is_deleted':category.is_deleted 
        } for index, category in enumerate(categories)]
        return JsonResponse({"categories": categories_data})

    return render(request,'admin_category.html',{'categories':categories,'categories_per_page':categories_per_page})

##############################################################################################################################
@login_required(login_url='admin_login')
def add_category(request):
    if request.method == "POST":
        category_name = request.POST.get('category_name').strip()
        description = request.POST.get('description', '').strip()

        if not category_name and description:
            messages.error(request, "Fields can't be empty.")
            return render(request, 'add_category.html')
        
        if CategoryTable.objects.filter(category_name__iexact = category_name).exists():
            messages.error(request,f"The category '{category_name}' already exists")
            return render(request,'add_category.html')
        
        CategoryTable.objects.create(
            category_name = category_name,
            description = description
        )
        messages.success(request, f"The category '{category_name}' has been added successfully!")
        return redirect('admin_category')
        
    return render(request,'add_category.html')

################################################################################################################################
@login_required(login_url='admin_login')
def edit_category(request, pk):
    category = get_object_or_404(CategoryTable, id=pk)

    if request.method == "POST":
        # Handle delete category action if 'delete_category' was added in the form
        if 'delete_category' in request.POST:
            category.is_available = False
            category.is_deleted = True
            category.save()
            messages.success(request, 'Category marked as deleted.')
            return redirect('admin_category')
        
        # Handle re-add category action
        elif 'readd_category' in request.POST:
            category.is_available = True
            category.is_deleted = False
            category.save()
            messages.success(request, 'Category re-added to the list successfully.')
            return redirect('admin_category')
        
        # Handle update category details
        else:
            category_name = request.POST.get('category_name')
            description = request.POST.get('description')

            category.category_name = category_name
            category.description = description
            category.save()
            messages.success(request, 'Category details updated successfully.')
            return redirect('admin_category')
            
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
    """Handle product addition with comprehensive field validation."""
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
                if discount_percentage < 0 or discount_percentage > 100:
                    errors.append('Discount percentage must be between 0 and 100.')
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
            print(image_files)
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
                    'redirect_url': 'admin_products'
                })

        except Exception as e:
            logger.error(f"Error adding product: {str(e)}", exc_info=True)
            return JsonResponse({
                'status': 'error',
                'message': 'An unexpected error occurred. Please try again.',
                'error_details': str(e)
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
                            'redirect_url': 'admin_products'
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
        OrderDetails.objects.select_related('address', 'user', 'coupon', 'offer'),
        order_id=order_id
    )
    book_detail = OrderItem.objects.filter(order=order_detail).select_related('book')
    return render(request,'view_order.html',{'order_detail':order_detail,'book_detail':book_detail})

############################################################################################################################
@login_required(login_url='admin_login')
def update_order(request,order_id):
    order_detail = get_object_or_404(
        OrderDetails.objects.select_related('address', 'user', 'coupon', 'offer'),
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
def status_update(request,order_id):
    if request.method =="POST":
        order = get_object_or_404(OrderDetails, order_id = order_id)
        new_status = request.POST.get('new_status')

        if new_status and new_status != order.order_status:
            order.order_status = new_status
            order.save()

             # Update the status of all items in the order
            order_items = OrderItem.objects.filter(order=order)
            order_items.update(order_status=new_status)

            messages.success(request,f"Order{order.order_id} status updated to {new_status}.")
        else:
            messages.warning(request, f"Order {order.order_id} is already in the {new_status} status.")

    return redirect('update_order', order_id=order_id)