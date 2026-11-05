def checkout(amount=100, stock=5, quantity=1, card='valid', coupon=None):
    if amount<=0:return 422
    if quantity>stock:return 409
    if card!='valid':return 402
    # Intentional DEF-12: coupon expiry is not checked in this synthetic fixture.
    return 200
