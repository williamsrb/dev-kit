# Jargon — keep vs translate

Analysts here already use Jira, Figma, Content Studio, publish, and review URLs.
Translate implementation and infrastructure terms. If a technical name is
unavoidable (legal, security, or the ticket itself uses it), keep the term and
add a short plain-language gloss once.

## Keep (shared product language)

acceptance criteria / AC, Content Studio, publish, draft, Figma, review
environment, live page, editor, heading, form, validation, screenshot.

## Translate

| Instead of | Use |
|------------|-----|
| processor / dataFetcher / componentRegistry | "the part" / "what the editor configured" |
| React, React4XP, hydration, prototype wire-up | "the approved design on the live page" |
| CSS class, BEM, `lg+`, Swiper, a11y label | "on a wide / small screen", "carousel", "previous/next labels" |
| `sendFormEmail`, `emailReceiver`, HTTP 200/303 | "the form sends mail to the recipient set in Content Studio" |
| Git SHA, grep, Docker, `system.properties` | "the review-branch change" / "the committed config" |
| mogrify, Playwright, storage-state, `fileId` | *(omit — chat only)* |
| localhost, `~/.agents`, evidence folder | the captured live page URL (full path), plus Admin CS edit when relevant |
| "wired the prototype" | "the live page now matches the approved design" |
| "stub replaced" | "the placeholder is gone; the real block is on the page" |
| "Option B in the processor" | "if sending fails, the button stays on Send" |

## Lead with impact

| Technical | Analyst-facing |
|-----------|----------------|
| "We implemented Redis caching to reduce database load" | "The page should feel faster; the same content is shown." |
| "Valid submits post to sendFormEmail with server-resolved emailReceiver" | "A valid submit sends mail to the address set in Content Studio, without showing that address on the page." |
| "At lg+: carousel track/Swiper" | "On a wide desktop window, extra cards sit in a carousel." |

## "So what?" 

If you cannot say why the analyst should care, drop the sentence from the
Jira/Slack body. Implementation detail belongs in chat or the spec, not in
the evidence comment.
