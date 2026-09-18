# How to fill missing payment-condition Availability with valid dummy dates

**Scope:** `as`
**Applies to:** XP 7 Nashorn (`lib/modules/paymentCondition`)
**Related:** [How-to-fix-dual-shape-viewmodel-xdata-reads-in-xp-apps.md](./How-to-fix-dual-shape-viewmodel-xdata-reads-in-xp-apps.md)

## Scope

Unique `booking-payment-condition` options whose Availability is omitted must apply
to every travel date. `fillMissingWithDummyDates` fills empty start/end with min/max
sentinels so `isAfterOrEqual` / `isBeforeOrEqual` succeed. Explicit Availability that
does **not** cover the travel date must still yield to the site default (schema
help-text). Do not set Availability on a live booking to hide the bug.

## Prerequisites

- Confirm `/lib/external/date-fns` does not export `minTime` / `maxTime`, and the
  bundled `date-fns.min.js` does not contain those identifiers.
- `grep -n "DateFns.minTime\\|DateFns.maxTime" xp/src/main/resources` — expected
  empty after the fix.

## Procedure

1. In `lib/modules/paymentCondition/index.js`, replace sentinel construction with
   date-fns v2 extremes. Do not import them from the wrapper:

   ```js
   const minDate = new Date(-8640000000000000)
   const maxDate = new Date(8640000000000000)
   ```

2. Leave `fillMissingWithDummyDates` / `cleanUpFilledMissingWithDummyDates` logic
   unchanged. Cleanup still strips via `DateFns.isSameDay(..., minDate|maxDate)`.
   `parseDate` accepts a `Date` (`getTime`) then `startOfDay`; `isSameDay` still
   matches the sentinel calendar day.

3. Do not widen the three AS-1167 `viewModel`-only reads
   (`viewModel.bookingPaymentCondition`, two `viewModel.bookingInfo`). Do not add a
   reminder-only `paymentDueDate` shortcut.

## Pitfalls

- `new Date(DateFns.minTime)` is `Invalid Date` when `minTime` is `undefined`.
  `isAfter` / `isBefore` on an invalid date return false and do not throw, so matching
  silently fails and `getOptionForTravelDate` falls through to the site default.
- Do not re-export `minTime` / `maxTime` from the date-fns wrapper — they are not in
  the bundled min file.

## Sample data (minimal)

| Field | Example |
|-------|---------|
| Booking | ASFI118815 (no Availability, `paymentDueDate.endDate` 2026-09-08) |
| Wrong date | travel − 65 (site default) |
| Expected date | 2026-09-08 |
