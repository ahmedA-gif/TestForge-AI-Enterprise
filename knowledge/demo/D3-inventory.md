# D3 / Inventory business rules
R-04: Ordered quantity must not exceed available stock. An oversell attempt must return HTTP 409.
At the stock boundary the request may succeed. Stock must never become negative.
