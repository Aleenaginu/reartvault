from django.shortcuts import get_object_or_404, render,redirect
from artist.models import Product
from shop.models import Customers, Wishlist
from .models import Cart,CartItem
from django.contrib.auth.decorators import login_required

# Create your views here.
def _cart_id(request):
    cart=request.session.session_key
    if not cart:
        cart=request.session.create()
    return cart

@login_required(login_url='customerlogin')
def add_cart(request,product_id):
    product=Product.objects.get(id=product_id)
    try:
        cart=Cart.objects.get(cart_id=_cart_id(request))
    except Cart.DoesNotExist:
        cart=Cart.objects.create(
            cart_id=_cart_id(request)
        )
    cart.save()
    try:
        cartitem=CartItem.objects.get(product=product,cart=cart)
        cartitem.Quantity+=1
        cartitem.save()
    except CartItem.DoesNotExist:
        cartitem=CartItem.objects.create(
            product=product,
            cart=cart,
            Quantity=1
        )
        cartitem.save()
    return redirect('cart')

def cart(request, total=0, cart_count=0, cartitems=None):
    tax = 0
    grand_total = 0
    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
        cartitems = CartItem.objects.filter(cart=cart, is_active=True)
        cart_count = cartitems.count()  # Count unique products in cart
        for item in cartitems:
            total += (item.product.price * item.Quantity)
        tax = (2 * total) / 100
        grand_total = total + tax
    except Cart.DoesNotExist:
        pass
    
    wishlist_count = 0
    if request.user.is_authenticated:
        try:
            customer = get_object_or_404(Customers, user=request.user)
            wishlist_count = Wishlist.objects.filter(user=customer).count()
        except Customers.DoesNotExist:
            wishlist_count = 0  # In case the customer is not found
    
    
    context = {
        'total': total,
        'cart_count': cart_count,
        'cartitems': cartitems,
        'tax': tax,
        'grand_total': grand_total,
        'wishlist_count':wishlist_count
    }
    return render(request, 'customers/cart.html', context)
            
   
def remove_cart(request,product_id):
    cart=Cart.objects.get(cart_id=_cart_id(request))
    product=Product.objects.get(id=product_id)
    cartitem=CartItem.objects.get(cart=cart,product=product)
    if cartitem.Quantity > 1:
        cartitem.Quantity-=1
        cartitem.save()
    else:
        cartitem.delete()
    return redirect('cart')

def remove_cartitem(request,product_id):
    cart=Cart.objects.get(cart_id=_cart_id(request))
    product=Product.objects.get(id=product_id)
    cartitem=CartItem.objects.get(cart=cart,product=product)
    cartitem.delete()
    return redirect('cart')