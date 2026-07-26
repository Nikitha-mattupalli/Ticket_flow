# Duplicate Charge Policy

## Overview

A duplicate charge occurs when a customer is billed more than once for the same product or service during the same billing period.

## Common Causes

- Payment gateway timeout
- Customer clicked Pay multiple times
- Retry logic created duplicate transactions
- System synchronization delay

## Verification Steps

1. Verify customer identity.
2. Check transaction IDs.
3. Compare payment timestamps.
4. Verify invoice history.

## Resolution

If duplicate billing is confirmed:

- Refund the duplicate payment.
- Refund should be processed within 5 business days.
- Notify the customer after initiating the refund.

## Human Escalation

Escalate when:

- More than two duplicate transactions exist.
- Refund cannot be initiated automatically.
- Fraud is suspected.