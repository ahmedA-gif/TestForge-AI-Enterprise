# D2 / Payment validation specification
R-03: A rejected payment card must return HTTP 402 and must not create a paid order.
R-05: A zero or negative payment amount must return HTTP 422.
Positive, negative and boundary amounts require distinct test cases.
