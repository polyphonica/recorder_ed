# Help Centre Upgrade Plan (without Wagtail)

**Status:** Proposed · **Date:** 2026-11-25 · **App:** `apps/help_center`

## Why not Wagtail

Help-centre articles fit Wagtail's page-tree model better than workshops do, but adopting it only for the help centre isn't worth the cost:

- Wagtail is a heavy dependency (dozens of tables, its own admin at a separate URL, upgrades tied to Django releases).
- Editors would have a third admin interface, next to Django admin and `admin_portal`.
- The project would have two rich-text editors (CKEditor 5 and Draftail), and existing articles would need converting.

Revisit this if the plan grows into a wider public content site (blog, news, marketing pages, teaching resources) with several non-technical editors and an approval step.

The current app is small (2 models, about 430 lines of Python, 4 templates) and already covers categories, draft/published/archived status, ordering, promoted articles, search, view counts, helpfulness counters and SEO meta. The plan below adds the Wagtail features that matter, using tools the project already has.

---

## Phase 1: Fix what's broken (small, do first)

### 1.1 "Was this article helpful?" doesn't save anything
`article_detail.html` lines 53–60: the Yes/No buttons only call `alert()`. No vote is recorded, so `helpful_count` and `not_helpful_count` are always 0 and the score never shows.

- Add a `POST /help/article/<slug>/feedback/` view that takes `helpful=yes|no`.
- Increment atomically with `F()` (`Article.objects.filter(pk=...).update(helpful_count=F('helpful_count') + 1)`).
- Allow one vote per article per session (store voted article IDs in `request.session`).
- Replace the alerts with an inline thank-you message (HTMX or a small fetch call). For a "No" vote, show an optional "What was missing?" text box and a link to the support app.
- Rate-limit the endpoint the same way as other public forms.

### 1.2 View count is non-atomic and inflated
`Article.increment_view_count()` does read, add 1, then save. Concurrent views lose counts, and staff and bots are counted.

- Use `F('view_count') + 1` with `.update()`.
- Skip staff users and obvious bot user agents.
- Optional: count once per session per article.

### 1.3 Help articles missing from the sitemap
`recordered/sitemaps.py` has no help-centre entries. Add `HelpArticleSitemap` (published articles, `lastmod=updated_at`) and `HelpCategorySitemap` (active categories).

### 1.4 Small query fixes
- `home()` prefetches *all* articles per category, including drafts. Use `Prefetch('articles', queryset=Article.objects.filter(status='published'))`.
- `Category.article_count` runs one query per category. Annotate with `Count('articles', filter=Q(articles__status='published'))` instead.

---

## Phase 2: Editorial workflow (the Wagtail features worth having)

### 2.1 Revision history and rollback
django-simple-history is already installed and its middleware is active.

- Add `history = HistoricalRecords()` to `Article` (and `Category`), and generate the migration.
- Switch `ArticleAdmin` and `CategoryAdmin` to `SimpleHistoryAdmin`. This gives per-version history, field diffs, `changed_by` and revert in admin.
- Consider `excluded_fields=['view_count', 'helpful_count', 'not_helpful_count']` so counter updates don't create revisions. Counters updated with `.update()` don't trigger history anyway, but excluding them is clearer.

### 2.2 Draft preview
- In `ArticleDetailView.get_queryset()`, let staff (or users with `help_center.change_article`) see any status.
- Show a "DRAFT – not visible to the public" banner when status isn't `published`.
- Add a "Preview on site" link in admin (`view_on_site` already works through `get_absolute_url`).
- Add `<meta name="robots" content="noindex">` to non-published previews.

### 2.3 Scheduled publishing
- Make `published_at` editable in admin. Public querysets become `status='published', published_at__lte=now()`.
- Centralise this in a custom manager/queryset (`Article.objects.published()`) and use it in the views, the sitemap and search, so the rule lives in one place.
- No Celery task needed. Visibility is worked out from `published_at` each time a page is requested.

### 2.4 Slug-change redirects
Renaming an article currently breaks old links and loses search ranking.

- Add an `ArticleSlugHistory(article FK, old_slug unique)` model, filled in `Article.save()` when the slug changes.
- In `ArticleDetailView`, on a 404, look up the old slug and issue a 301 to the current URL.

### 2.5 "Last reviewed" and stale-content flag
- Add `last_reviewed_at` (date) and an optional `owner` (FK to a staff user).
- Show "Updated <date>" on the article page.
- Add an admin list filter for articles not reviewed in 12+ months, so help content stays in step with feature changes.

---

## Phase 3: Reader experience

### 3.1 Better search
`SearchView` uses `icontains` on title, summary and content. This doesn't rank results or handle word variants (stemming), and it matches HTML markup inside `content`.

- Use PostgreSQL full-text search (`SearchVector` weighted title A, summary B, content C; `SearchRank`; `SearchQuery(search_type='websearch')`).
- Add a stored `search_vector` field with a GIN index, updated on save.
- Use `TrigramSimilarity` on the title as a fallback for typos (needs the `pg_trgm` extension migration).
- Log searches that return zero results (`SearchLog(query, results_count, created_at)`) to show which articles are missing.

### 3.2 Table of contents and heading anchors
- At render time, parse `content` headings (h2/h3), add `id`s and build a sticky table of contents for long articles. A small template filter using BeautifulSoup is enough. Check whether bs4 is already a dependency before adding it.

### 3.3 Hand-picked related articles
- Add `related_articles = ManyToManyField('self', blank=True, symmetrical=False)`. Use the hand-picked list when it's set, and fall back to same-category articles otherwise.

### 3.4 Role-based audience
Students, teachers and parents need different articles.

- Add `audience` (multi-choice or a small M2M: `student`, `teacher`, `guardian`, `all`).
- On the help home page, show the logged-in user's audience first. Optionally add audience filter tabs.

### 3.5 Contextual help links from the app
- Add a template tag such as `{% help_link "workshop-creation" %}` that renders a "?" link to an article by slug. Fail silently, and log a warning, if the article is missing or unpublished.
- Place it on complex screens (workshop creation, availability calendar, payouts, exam registration).

### 3.6 SEO and structured data
- Add a canonical URL, Open Graph tags and `Article`/`BreadcrumbList` JSON-LD on article pages. Use `FAQPage` JSON-LD for FAQ-style articles. See `SEO_PLAN.md`.

---

## Phase 4: Content structure (optional, only if needed)

If editors want consistent rich blocks (callouts, numbered steps, embedded audio/video, "Teachers only" notes) without a full StreamField:

- **Option A:** define CKEditor 5 styles/templates for callouts and step lists. No model change.
- **Option B:** an `ArticleBlock` inline (ordered, type + rich text + optional media) rendered by per-type templates. This is closer to StreamField, but only adopt it if Option A proves too limiting.

Start with Option A.

---

## Summary

| # | Item | Effort | Value |
|---|------|--------|-------|
| 1.1 | Working helpful/not-helpful feedback | S | High |
| 1.2 | Atomic, filtered view counts | XS | Medium |
| 1.3 | Sitemap entries | XS | High (SEO) |
| 1.4 | Query fixes | XS | Low |
| 2.1 | Revision history (simple-history) | XS | High |
| 2.2 | Draft preview for staff | S | High |
| 2.3 | Scheduled publishing + `published()` manager | S | Medium |
| 2.4 | Slug redirects | S | Medium |
| 2.5 | Last reviewed / stale flag | S | Medium |
| 3.1 | Postgres full-text search + zero-result log | M | High |
| 3.2 | Table of contents | S | Medium |
| 3.3 | Hand-picked related articles | XS | Low |
| 3.4 | Audience targeting | M | Medium |
| 3.5 | Contextual help links | S | High |
| 3.6 | Structured data | S | Medium |
| 4 | Content blocks | S–M | Optional |

**Suggested order:** Phase 1 → 2.1 → 2.2 → 2.3 → 1.3/3.6 (SEO) → 3.1 → 3.5 → others as needed.

**Migrations:** 2.1 (history tables), 2.3 (none if `published_at` is reused), 2.4 (slug history), 2.5, 3.1 (search vector + `pg_trgm`), 3.3, 3.4.

**Testing:** add `apps/help_center/tests/` covering visibility rules (draft, scheduled, archived; staff vs public), feedback voting (one per session, atomic), slug redirects, and search ranking.

**Rollout:** feature branch → staging → test → main → production, as usual.
