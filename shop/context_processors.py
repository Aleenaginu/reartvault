# from .models import Wishlist

# def wishlist_count(request):
#     if request.user.is_authenticated:
#         customer = request.user.customers
#         wishlist_count = Wishlist.objects.filter(user=customer).count()
#     else:
#         wishlist_count = 0
#     return {
#         'wishlist_count': wishlist_count
#     }