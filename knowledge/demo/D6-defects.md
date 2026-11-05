# D6 / Known defect log
DEF-12: The synthetic Python checkout function accepts expired coupons.
Reproduction: checkout(coupon={"expired":true}) returns 200; R-02 expects 422.
Likely cause: missing expiry validation. Confirm from test output before claiming an observed failure.
The frontend suite provides independent evidence of pending-submission behavior.
