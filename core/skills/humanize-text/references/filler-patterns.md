# Filler and hedging


### 23. Filler phrases

**Before → After:**
- "In order to achieve this goal" → "To achieve this"
- "Due to the fact that it was raining" → "Because it was raining"
- "At this point in time" → "Now"
- "In the event that you need help" → "If you need help"
- "The system has the ability to process" → "The system can process"
- "It is important to note that the data shows" → "The data shows"

### 24. Too many qualifiers

**Phrases to watch:** to be fair, it's also possible, could potentially, might arguably, in some cases it may, this is an inference
**Problem:** Repeated editing can add one qualifier after another until every claim sounds uncertain. Keep a qualifier only when the source supports it and the meaning needs it. Remove caveats that only repair an earlier overstatement.
**Before:**
> It could potentially possibly be argued that the policy might have some effect on outcomes.
**After:**
> The policy may affect outcomes.

### 25. Generic positive endings
**Problem:** AI writing often ends with vague optimism instead of the last useful fact.
**Before:**
> The future looks bright for the company. Exciting times lie ahead as they continue their journey toward excellence. This represents a major step in the right direction.
**After:**
> (Cut the paragraph. End on the last concrete fact instead of a send-off. If the source states real plans, use those.)

### 26. Too many hyphenated word pairs

**Words to watch:** third-party, cross-functional, client-facing, data-driven, decision-making, well-known, high-quality, real-time, long-term, end-to-end
**Problem:** AI writing often hyphenates these pairs everywhere. Keep the hyphen before a noun when grammar needs it, as in `a high-quality report`. Drop it after the noun, as in `the report is high quality`.
**Before:**
> The cross-functional team delivered a high-quality, data-driven report. The team is cross-functional, the report is high-quality, and the methodology is data-driven.
**After:**
> The cross-functional team delivered a high-quality, data-driven report. The team is cross functional, the report is high quality, and the methodology is data driven.

### 27. Pretending to reveal a deeper truth

**Phrases to watch:** The real question is, at its core, in reality, what really matters, fundamentally, the deeper issue, the heart of the matter
**Problem:** AI writing uses these phrases to make an ordinary point sound like a hidden truth.
**Before:**
> The real question is whether teams can adapt. At its core, what really matters is organizational readiness.
**After:**
> The question is whether teams can adapt. That mostly depends on whether the organization is ready to change its habits.

### 28. Announcing the next point

**Phrases to watch:** Let's dive in, let's explore, let's break this down, here's what you need to know, now let's look at, without further ado, heads up, quick note, before I forget
**Problem:** AI writing often announces the next point instead of stating it. A casual phrase such as "one thing that bit me" can have the same problem. Remove the announcement, not just its formal tone.
**Before:**
> Let's dive into how caching works in Next.js. Here's what you need to know.
**After:**
> Next.js caches data at multiple layers, including request memoization, the data cache, and the router cache.
**Before (casual register):**
> One thing that bit me hard, so pay attention to this part: the webpack dev server doesn't send the CORS header by default.
**After:**
> The webpack dev server doesn't send the CORS header by default.

### 29. A heading repeated in the first sentence

**Signs to watch:** A heading followed by a one-line paragraph that simply restates the heading before the real content begins.
**Problem:** AI writing often follows a heading with a sentence that only repeats the heading. Remove the repeated sentence.
**Before:**
> ## Performance
>
> Speed matters.
>
> When users hit a slow page, they leave.
**After:**
> ## Performance
>
> When users hit a slow page, they leave.

### 30. Writing about the previous version
**Problem:** Documentation and comments should describe the current behavior. Mention the previous version only in change logs, release notes, migration guides, and other documents about change.
**Before:**
> This function was added to replace the previous approach of iterating through all items, which caused O(n²) performance.
**After:**
> This function uses a hash map for O(1) lookups, avoiding the O(n²) cost of naive iteration.

### 31. Forced punchlines and dramatic fragments
**Problem:** AI writing often turns each sentence into a dramatic closing line. One short sentence can add emphasis. A row of short fragments usually feels forced.
**Before:**
> Then AlphaEvolve arrived. It had no preference for symmetry. No aesthetic prior. No nostalgia for human taste. The old rules were gone.
**After:**
> AlphaEvolve changed the search because it did not favor symmetry or human-looking designs. That made some of the older assumptions less useful.

### 32. Formulaic sayings

**Words to watch:** X is the Y of Z, X becomes a trap, X is not a tool but a mirror, the language of, the currency of, the architecture of
**Problem:** AI writing often turns an ordinary claim into a saying that sounds deep but adds no detail. Replace the saying with the specific claim.
**Before:**
> Symmetry is the language of trust. Efficiency becomes a trap when teams forget the human layer.
**After:**
> Symmetric layouts often feel more predictable to users. Teams can over-optimize workflows and miss how people actually use them.

### 33. Fake-candid openings

**Phrases to watch:** Honestly?, Look, Here's the thing, The thing is, Let's be honest, Real talk, when used as standalone hooks or fake-candid pauses before an ordinary point.
**Problem:** AI writing often starts with a staged pause or claim of honesty before making a routine point. State the point directly.
**Before:**
> Is it worth the price? Honestly? It depends on how often you'll use it.
**After:**
> Whether it's worth the price depends on how often you'll use it.

### 34. Answering objections no one raised

**Phrases to watch:** This isn't (mainly/really) about, I'm not saying/arguing/trying to, To be clear, Don't get me wrong, This is not to say, You could argue/frame this differently but, Some might say... but
**Problem:** AI writing may answer an objection that does not appear in the text. Watch for an unattributed statement about what the writer does not mean, especially when the topic appears nowhere else. A direct claim such as "the API is not thread-safe" is not this pattern.
**Before:**
> This isn't mainly about prompt length, and I'm not arguing that documentation doesn't matter. You could categorize the problem another way, but the issue is whether the agent can use the instruction when it acts.
**After:**
> The issue is whether the agent can use the instruction when it acts.

Remove only the unsupported defense. If it contains a real claim, state that claim directly. Keep an objection when the text names its source or answers it in full.

### 35. Rejecting fake alternatives

**Phrases to watch:** A tempting option/approach would be, One might be tempted to, An obvious approach would be, You might think... but, It would be easy to just, Some would suggest
**Problem:** AI writing may introduce an option that no reader would consider, reject it in a clause, and never mention it again. This often leaves an old drafting idea in the final text. Remove the fake option and state the real constraint directly.
**Before:**
> Session tokens are rotated every 24 hours. A tempting approach would be to rotate them by restarting the auth service on a cron job, but that would drop every active session. Rotation happens in place, and clients refresh transparently.
**After:**
> Session tokens are rotated every 24 hours, in place, and clients refresh transparently.

One rejected option may be valid. Several short, unrelated rejections are a stronger sign. Ask what new information each sentence adds. If it only records an earlier edit, rewrite the paragraph around its main point.
