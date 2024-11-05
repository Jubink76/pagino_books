from django.shortcuts import render,redirect,get_object_or_404
from log_reg_app.models import UserTable
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control,never_cache
from .models import CategoryTable,Language,Author,BookTable,BookImage
# Create your views here.

##############################################################################################################

@login_required(login_url='admin_login')
@never_cache
def admin_dashboard(request):
    return render(request,'admin_dashboard.html')


def admin_users(request):
    users = UserTable.objects.all().order_by('id')

    # search query
    search_query = request.GET.get('search','')

    if search_query:
        if search_query.isdigit():
            users = users.filter(id=search_query)
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

    paginator = Paginator(users, 5)
    page_number = request.GET.get('page')
    users = paginator.get_page(page_number)

    

    return render(request,'admin_users.html',{
        'users':users,
        'search_query':search_query
    })
######################################################################################################################

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

def admin_category(request):

    categories = CategoryTable.objects.all()

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

    paginator = Paginator(categories, 5)
    page_number = request.GET.get('page')
    categories = paginator.get_page(page_number)

    return render(request,'admin_category.html',{'categories':categories})

##############################################################################################################################

def add_category(request):
    if request.method == "POST":
        category_name = request.POST.get('category_name')
        description = request.POST.get('description')

        CategoryTable.objects.create(
            category_name = category_name,
            description = description
        )
        return redirect('admin_category')
        
    return render(request,'add_category.html')

################################################################################################################################

def edit_category(request, pk):
    category = get_object_or_404(CategoryTable,id = pk)
    if request.method == "POST":
        # Check which button was clicked
        if 'delete_category' in request.POST:
            # Handle delete category action
            category.is_available = False
            category.is_deleted = True
            category.save()
            messages.success(request, 'Category marked as deleted.')
            return redirect('admin_category')
        
        elif 'readd_category' in request.POST:
            # Handle re-add category action
            category.is_available = True
            category.is_deleted = False
            category.save()
            messages.success(request, 'Category re-added to the list successfully.')
            return redirect('admin_category')
        
        else:
            # Handle update category details action
            category_name = request.POST.get('category_name')
            description = request.POST.get('description')

            # Update category fields
            category.category_name = category_name
            category.description = description
            category.save()
            messages.success(request, 'Category details updated successfully.')
            return redirect('admin_category')
            
    return render(request,'edit_category.html',{'category':category})

######################################################################################################################

def delete_category(request, pk):  
    category = get_object_or_404(CategoryTable,id=pk)
    category.is_deleted = True
    category.is_available = False
    category.save()
    messages.success(request,'category deleted successfully')
    return redirect('admin_category')

######################################################################################################################

def admin_products(request):
    books = BookTable.objects.all()

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

    paginator = Paginator(books, 5)
    page_number = request.GET.get('page')
    books = paginator.get_page(page_number)
            
    return render(request,'admin_products.html',{'books':books})

#####################################################################################################################

def add_products(request):
    if request.method == 'POST':
        book_name = request.POST.get('book_name')
        description = request.POST.get('description')
        stock_quantity = request.POST.get('stock_quantity')
        price = request.POST.get('price')
        vat_amount = request.POST.get('vat_amount')
        discount_percentage = request.POST.get('discount_percentage')
        

        author_name = request.POST.get('author_name')
        bio = request.POST.get('bio')
        author, created = Author.objects.get_or_create(name=author_name)
        if created or not author.bio:
            author.bio = bio
            author.save()


        language_name = request.POST.get('language')
        new_language = request.POST.get('new_language')
        
        if language_name:  # Existing language selected
            language, created = Language.objects.get_or_create(name=language_name)
        elif new_language:  # New language input
            language, created = Language.objects.get_or_create(name=new_language)
        else:
            # Handle case when no language is provided (optional)
            language = None

        category_name = request.POST.get('category')
        
        if category_name:  # Ensure category_name is not empty
            category, created = CategoryTable.objects.get_or_create(category_name=category_name)
        else:
            # Handle the case where no category is provided (optional)
            category = None

        book = BookTable.objects.create(
            book_name = book_name,
            description = description,
            stock_quantity = stock_quantity,
            price = price,
            vat_amount = vat_amount,
            discount_percentage = discount_percentage,
            category = category,
            language = language,
            author = author
        )

        for image_file in request.FILES.getlist('book_images'):
            BookImage.objects.create(book=book, image=image_file)
        return redirect('admin_products')
    categories = CategoryTable.objects.filter(is_available=True, is_deleted=False)
    languages = Language.objects.all()
    return render(request,'add_products.html',{'categories':categories,'languages':languages})

########################################################################################################################

def view_product(request,pk):
    book = get_object_or_404(BookTable,id=pk)
    images = book.images.all()
    return render(request,'view_product.html',{'book':book,'images':images})

###########################################################################################################################

def edit_product(request, pk):
    book = get_object_or_404(BookTable, id=pk)
    
    if request.method == "POST":
        if 'delete_book' in request.POST:
            book.is_available = False
            book.is_deleted = True
            book.save()
            messages.success(request, 'Book marked as deleted.')
            return redirect('admin_products')
        
        elif 'readd_book' in request.POST:
            book.is_available = True
            book.is_deleted = False
            book.save()
            messages.success(request, 'Book re-added to the list successfully.')
            return redirect('admin_products')
        
        else:
            # Update book details
            book_name = request.POST.get('book_name')
            if book_name:
                book.book_name = book_name
            
            description = request.POST.get('description')
            if description:
                book.description = description
            
            stock_quantity = request.POST.get('stock_quantity')
            if stock_quantity:
                book.stock_quantity = stock_quantity
            
            price = request.POST.get('price')
            if price:
                book.price = price
            
            vat_amount = request.POST.get('vat_amount')
            if vat_amount:
                book.vat_amount = vat_amount
            
            discount_percentage = request.POST.get('discount_percentage')
            if discount_percentage:
                book.discount_percentage = discount_percentage
            # Update category, language, author only if new values are provided
            category_name = request.POST.get('category')
            if category_name:
                book.category, _ = CategoryTable.objects.get_or_create(category_name=category_name)
                
            language_name = request.POST.get('language')
            if language_name:
                book.language, _ = Language.objects.get_or_create(name=language_name)
                
            author_name = request.POST.get('author_name')
            bio = request.POST.get('bio')
            if author_name:
                author, _ = Author.objects.get_or_create(name=author_name)
                author.bio = bio  # Update the bio
                author.save()
                book.author = author
            
            book.save()

            # Handle image updates
            # Remove selected images
            new_images = request.FILES.getlist('book_images')
            if new_images:
                # Delete all existing images for this book
                BookImage.objects.filter(book=book).delete()
                
                # Add new images
                for image_file in new_images:
                    BookImage.objects.create(book=book, image=image_file)
            
            messages.success(request, 'Book details updated successfully.')
            return redirect('admin_products')
    
    # Retrieve existing categories, languages, authors, and images
    categories = CategoryTable.objects.filter(is_available=True, is_deleted=False)
    languages = Language.objects.all()
    authors = Author.objects.all()
    
    context = {
        'book': book,
        'categories': categories,
        'languages': languages,
        'authors': authors,
    }
    
    return render(request, 'edit_product.html', context)

############################################################################################################################

def delete_product(request,pk):
    book = get_object_or_404(BookTable, id=pk)
    book.is_deleted = True
    book.is_available = False
    book.save()
    messages.success(request,f"{book.book_name} is deleted successfully")
    return redirect('admin_products')