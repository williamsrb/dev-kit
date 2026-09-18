# Analyst-message examples

Rewrite the **prose**. Do not change posting gates, ADF `media` nodes, or section order.

## Evidence post — contact form

**Avoid (engineer log):**

> Contact CTA renders the prototype UI (accordion + react-hook-form) instead of the stub. Valid submits post to sendFormEmail with server-resolved emailReceiver (never in HTML/POST). Messaging-queue E-mails / SMTP confirm handoff.

**Prefer:**

> The contact block on the live page now matches the approved design: employee, expandable form, validation, and privacy link. Submitting the form sends mail to the recipient configured in Content Studio (the address is not exposed in the page). Review environment: `<review-url>`.

**Evidence unit — avoid:**

> 9. Happy-path submit: button shows Sent after successful sendFormEmail (AC6–AC7). emailReceiver absent from HTML/POST.

**Prefer:**

> 9. After a valid submit, the button changes to Sent. The recipient address configured in Content Studio does not appear in the page. (AC6–AC7)

## Evidence post — user-visible cards

**Avoid:**

> Wired the approved Featured Cards prototype on review: folder auto-list + Cards Override, layout by count (1 / 2 / 3+ carousel at lg+), mobile/tablet stacking, View All variants, carousel a11y labels, and title-less override rows dropped.

**Prefer:**

> Featured cards on the review page now follow the approved layout: cards from the selected folder (with optional overrides), a carousel when there are three or more on desktop, stacked cards on smaller screens, and the View All link variants. Empty-title override rows are omitted.

**Evidence unit — avoid:**

> 5. \[AC2\] At lg+: carousel track/Swiper with prev/next; start prev disabled when nothing to scroll back.

**Prefer:**

> 5. On a wide desktop window, three or more cards use a carousel. The previous control starts disabled when there is nothing to scroll back to. (AC2)

## Evidence post — user-transparent (source only)

**Avoid:**

> Removed hardcoded superuser credentials (`su` / `password`) from the toppfotball shared-content services… Screenshots ready: `~/.cursor/tasks/NTF-1218/evidence/`

**Prefer:**

> Default superuser credentials are no longer stored in the shared-content services or in the committed development config. The screenshots below are the GitLab diffs on the review branch. A remaining ops step (rotating any password that was already deployed) is called out under Additional details — it cannot be shown from the review site alone.

Never put local evidence-folder paths in the Jira body.

## Evidence post — do not attach TBD

**Avoid** (questions on the evidence comment):

> **Additional relevant details**
> 1. Max Items empty still caps at 100. Which do you want?
> - **a) Reword the help.** My recommendation.
> - b) Raise the cap.
> - c) Leave both. Without an answer we get (c).

**Prefer** — evidence states the shipped behaviour; any decision waits:

> **Additional relevant details**
> Max Items left empty still caps at 100, while the field help says it shows all content. That is the current behaviour on review. Open copy decisions are not part of this evidence.

Park the a/b/c list in a separate question comment, or in chat for the operator — not here.

## TBD question for the analyst

**Avoid:**

> - [ ] **Should `.video-block--macro` stay as a required class on the part root?**
>   - Blocks: processor className merge / CSS module
>   - Assumption: drop it; BEM lives in the React entry

**Also avoid** — a single assumption with no options, which makes the analyst compose the alternatives themselves:

> - [ ] **Does the video block still need the old video-block--macro class on the page?**
>   - Blocks: we cannot finish the visual pass until this is decided.
>   - Assumption (not decided): the new structure replaces it.

**Prefer** — options, recommendation first, answerable by picking a letter:

> ### 1. Does the video block still need the old `video-block--macro` class, or is the new markup enough?
>
> The ticket text still names that class, and we cannot finish the visual pass until this is settled.
>
> - **a) Drop it and rely on the new markup.** My recommendation — nothing we can find still reads that class.
> - b) Keep it alongside the new markup. Safer if editors or other scripts depend on it, and cheap for us to do.
> - c) Keep it and we audit what still references it first. Slower, but removes the guesswork.

Note the backticks moved out of the bold heading: in a Jira comment, an inline code span inside a bold run closes the bold early and the heading renders half-bold.

## Slack / Jira ask (decision)

**Avoid:**

> FYI we might need to delay, there's a thing with the part descriptor and Guillotine.

**Prefer:**

> We need a product decision on `<ISSUE-KEY>` before implementation: should empty override rows still show a title placeholder, or be hidden? This blocks the card layout.
>
> - **a) Hide them.** Our recommendation — a placeholder reads as a broken card to visitors.
> - b) Show a placeholder, so editors can see a row exists but has no title yet.
>
> Reply with a or b and we will lock the spec.
