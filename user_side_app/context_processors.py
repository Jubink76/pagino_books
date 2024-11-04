from adminside_app.models import CategoryTable
from adminside_app.models import BookTable
# Create your views here.
def list_items(request):
    categories = CategoryTable.objects.filter(is_available=True, is_deleted=False)
    books = BookTable.objects.prefetch_related('images').all() 
    return {'categories':categories,'books':books}