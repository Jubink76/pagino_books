from django.shortcuts import render, redirect
from adminside_app.models import BookTable
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404

def shop_page(request):
    books = BookTable.objects.prefetch_related('images').all()

    # Set up pagination
    paginator = Paginator(books, 16)  # Display 16 books per page
    page_number = request.GET.get('page')
    books = paginator.get_page(page_number)
    return render(request,'shop_page.html',{'books':books})

def single_detail(request,pk):
    book = get_object_or_404(BookTable,id=pk)
    images = book.images.all()

    # fetch related products exclude the main book
    related_books = BookTable.objects.filter(
        category = book.category,
        is_available = True,
        is_deleted = False
    ).exclude(id=pk)[:6]
    return render(request,'single_detail.html',{'book':book,'images':images,'related_books':related_books})