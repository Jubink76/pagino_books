from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.simple_tag
def get_proper_elided_page_range(paginator, current_page, on_each_side=2, on_ends=1):
    """
    Return a list of page numbers to display, with ellipses where appropriate.
    
    Args:
    - paginator: Django Paginator object
    - current_page: Current page number
    - on_each_side: Number of pages to show on each side of the current page
    - on_ends: Number of pages to show at the start and end
    
    Returns a list that can include integers and the string 'ELLIPSIS'
    """
    num_pages = paginator.num_pages
    page = current_page

    # If total pages are less than what we want to show, just return all page numbers
    if num_pages <= (on_each_side * 2 + on_ends * 2 + 1):
        return range(1, num_pages + 1)

    # Compute the range of pages to display
    page_range = []

    # Add first page(s)
    for i in range(1, on_ends + 1):
        page_range.append(i)

    # Add last page(s)
    for i in range(num_pages - on_ends + 1, num_pages + 1):
        page_range.append(i)

    # Add pages around current page
    left = max(on_ends + 1, page - on_each_side)
    right = min(num_pages - on_ends, page + on_each_side)

    for i in range(left, right + 1):
        if i not in page_range:
            page_range.append(i)

    # Sort and remove duplicates while maintaining order
    page_range = sorted(set(page_range))

    # Insert ellipses where appropriate
    final_range = []
    prev = None
    for num in page_range:
        if prev is not None and num > prev + 1:
            final_range.append('ELLIPSIS')
        final_range.append(num)
        prev = num

    return final_range