from checkout import checkout

def test_successful_order_R01(): assert checkout()==200

def test_expired_coupon_R02(): assert checkout(coupon={'expired':True})==422, 'DEF-12: expired coupon accepted; observed 200, expected 422'

def test_rejected_card_R03(): assert checkout(card='rejected')==402

def test_no_overselling_R04(): assert checkout(quantity=6,stock=5)==409

def test_positive_amount_R05(): assert checkout(amount=0)==422
