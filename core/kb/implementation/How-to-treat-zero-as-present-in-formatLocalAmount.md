# How to treat numeric zero as present in formatLocalAmount

**Scope:** `as`
**Applies to:** XP 7 Nashorn amount tags in reminder / confirmation / booking-page
**Related:** [How-to-fill-missing-payment-condition-availability-with-valid-dates.md](./How-to-fill-missing-payment-condition-availability-with-valid-dates.md)

## Scope

`{deposit_payment_local_amount}` (and the same local-amount tags) must not stringify
to the word `undefined` when the amount is `0`. Nashorn copies of `formatLocalAmount`
treat a truthy amount as present, so `0` takes the missing branch and returns
`undefined`. Default product meaning is amount received (EUR 0.00), not a calculated
percentage. Do not extract a shared helper; do not change CMS templates.

## Prerequisites

- Four `formatLocalAmount` copies plus `formatSimpleLocalAmount` on the booking page:

  - `lib/util/tasks/sendBookingPaymentRemind.js`
  - `lib/modules/bookings/index.js` (cancel-payment and `replaceBookingTags`)
  - `site/layouts/booking-page/booking-page.js` (`formatLocalAmount` and
    `formatSimpleLocalAmount`)

- Keep each copy's existing `formatMoney` last argument (`true` vs `false`).

## Procedure

1. In each copy, replace truthy checks with:

   ```js
   const hasLocal = localAmount != null && localAmount !== ''
   const hasFallback = fallbackAmount != null && fallbackAmount !== ''
   ```

2. Use `hasLocal` / `hasFallback` in the `if` / `else if` that previously tested
   `localAmount` / `fallbackAmount`. Leave the formatted string templates unchanged.

## Pitfalls

- `if (fallbackAmount)` is false for `0`, so the function returns `undefined` and
  the template prints that word.
- `{deposit_payment}` already goes through `formatSiteAmount` and would print
  `EUR 0.00`; production reminder bodies use the local-amount tag instead.
- Do not change the caller that skips the cancel-payment local-amount replace when
  `localAmount` is falsy — only the formatter.

## Sample data (minimal)

| Field | Example |
|-------|---------|
| Booking with no deposit txn | ASFI118836 / ASFI118815 |
| Wrong render | `undefined` |
| Expected render | `EUR 0.00` |
