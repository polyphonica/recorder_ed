# Free Play-Along Library — Plan

Status: **built** (28 Nov 2026), on staging for testing. Decisions taken: the recommended option for each question in section 14. See "As built" at the end.

## 1. Goal

Turn the play-along library into a free, public resource that:

- brings new visitors to Recorder-ed (search engines, teachers sharing links);
- gives recorder players something useful every week, so they come to know the teaching;
- leads naturally to paid lessons, workshops and courses;
- respects copyright: in-copyright music is never offered publicly without permission, and never with its sheet music.

Brand fit: a **curated library of carefully recorded play-alongs, with Recorder-ed Editions of early music**, not a mass stock of tracks. Academic, premium, no ratings.

## 2. What exists today (28 Nov 2026)

| Area | Current state |
|---|---|
| Library page | `/audioplayer/library/`. Search, filters, All/Pieces/Collections toggle. Built as a student tool, so its wording is about "your teacher" and "assigned pieces". |
| Visitors who aren't logged in | Default view shows public **pieces only, no collections** (bug), plus a "My Assigned Pieces" tab that means nothing to them. `?mode=browse_all` shows everything public. |
| How people find it | Only from the private-teaching menus and the student dashboard. **Nothing on the home page, main menu or footer.** Not in the sitemap. |
| Home page | Four cards: Workshops, Private Lessons, Courses, Digital Products. |
| Digital Products | A shop: prices, cart, checkout. Has a "Play-Along" product type. Two play-along products: **William Williams Sonata (free, 9 "purchases")** and **Mattheson Sonata in G minor (£1.99, 0 purchases)**. |
| Copyright | `in_copyright` on Composer and Piece. In-copyright items can't be public (lock, done). Giesbert, Bonsor and Elizabeth Cooper marked. All their material is private and reached only through student assignments. |
| Files | Stems, PDFs and images in private storage behind expiring signed links (done). |
| Player | Multi-track: mute and solo per part, on-screen score image, PDF download. No tempo control. |

The 9 sign-ups for the free Williams sonata, against none for the £1.99 Mattheson, are the best evidence so far that free play-alongs bring people in, and that asking for a free account is acceptable to them.

## 3. Where the library lives (home page and navigation)

### Options

**A. Inside Digital Products.** Add "Free Playalong Library" to the Digital Products card and list play-alongs as £0 products.
- For: no new section on the home page.
- Against: Digital Products is a shop. A free library inside it gets a cart icon, prices and a checkout step, which makes it feel like a "free sample" rather than a resource. The library is something you return to every week; a shop is somewhere you buy once. It also mixes two different jobs in one admin area.

**B. A fifth card on the home page, alongside the other four.**
- For: equal prominence.
- Against: the four cards are things people pay for; a free library among them blurs that. Five cards don't sit well in the current four-across grid (the stylesheet has no five-column layout, so it would need custom CSS).

**C. Its own section and landing page, shown on the home page as a separate "free resource" strip beneath the four cards (recommended).**
- For: makes clear it's free and different from the paid areas. Gives it its own address, which helps search engines. Leaves the four-card grid alone. Easy to link from everywhere else.
- Against: one more section to maintain (small).

### Recommendation: option C

- **Address:** `/playalongs/` for the landing page. Individual pieces and collections get readable addresses, e.g. `/playalongs/mattheson-sonata-in-g-minor/`. Old `/audioplayer/library/...` addresses redirect, so existing links keep working.
- **Name:** "The Recorder-ed Play-Along Library", shortened to "Play-Alongs" in menus.
- **Home page:** a full-width strip under the four cards: *"Free Play-Along Library: practise with professionally recorded parts. Recorder-ed Editions of early music to download."*, with a "Browse the library" button.
- **Main menu:** a "Play-Alongs" link for everyone, logged in or not, next to Workshops / Private Lessons / Courses / Digital Products.
- **Footer:** a link.
- **Digital Products:** a small banner on the catalogue: "Looking for play-alongs? They're free in the Play-Along Library." The "Play-Along" product type is retired for new products (see section 8).
- **Student dashboard and private-teaching menus:** keep the existing links, pointing to the new address.

## 4. The landing page and library

### Landing page (`/playalongs/`)
1. **Introduction:** what a play-along is, who it's for, that it's free. One short paragraph and a "Start browsing" button.
2. **How it works:** three steps with icons: choose a piece, mute your part, play along. Optionally a short demo video.
3. **Featured:** three to six hand-picked items (an editable "featured" tick box on pieces and collections).
4. **Browse by:** composer, grade and period, as quick links into the library with filters already set.
5. **Recorder-ed Editions:** what they are and why they're trustworthy (sources, editorial method), linking to an "About our editions" page.
6. **Next step:** lessons, workshops and courses, presented as "Want feedback on your playing?", not a sales pitch.

### Library page changes
- Visitors who aren't logged in, and teachers, always see the full public library: public pieces **and** collections. This fixes the missing-collections bug.
- Logged-in students see two tabs: **"From my teacher"** (assigned) and **"Library"** (everything public). Visitors don't see the first tab.
- Rewrite wording that assumes a teacher ("your teacher hasn't assigned...") so it only appears to students.
- Each card shows a **music badge**:
  - "Recorder-ed Edition included" (score download available), or
  - "Bring your own copy" with a "Get the music" link (in copyright, with permission for the audio).
- Optional **"Period"** filter (Baroque, Renaissance, etc., from the composer's period).

### Piece and collection pages (new)
A public page per piece and collection, ahead of the player:
- title, composer (with dates and biography), grade, difficulty, description, parts included;
- the edition information or the "Get the music" panel;
- a **Play** button (see section 5 on accounts);
- related pieces (same composer or collection).

These are the pages search engines will find. The player itself stays as it is.

## 5. Free account or fully open? (decision needed)

| | Fully open | Free account to play (recommended) |
|---|---|---|
| Search traffic | Full | Full: piece pages are open, only playing needs an account |
| Mailing list | None | Every user is a contact (with consent) |
| Friction | None | One sign-up, then nothing |
| Evidence | — | 9 sign-ups for the free Williams sonata |

**Recommendation:** piece pages, descriptions and a 30-second preview of the full mix are open to everyone. Playing in full, muting and soloing parts, and downloading editions need a free, logged-in account. The sign-up page names the reason ("Create a free account to use the play-along library"), and after sign-up the visitor goes straight back to the piece.

The existing spam protection (Turnstile, honeypot) already covers sign-up.

## 6. Copyright model

### Three statuses

| Status | In the public library? | Audio | Sheet music | Shown to the player |
|---|---|---|---|---|
| **Public domain** (composer died 70+ years ago, own edition) | Yes | Yes | Recorder-ed Edition PDF and on-screen score | "Recorder-ed Edition" panel and download |
| **In copyright, permission for audio** | Yes | Yes | **Never** (no PDF, no on-screen image) | "Get the music" panel: publication, publisher, buy link |
| **In copyright, no permission** | No: private, own students only (current lock) | To assigned students only | Never in the library | Not listed |

Your own compositions and exercises count as public domain for this purpose: you own them.

### Data changes
- **Composer:** keep `in_copyright` (done).
- **Piece and Collection:**
  - `in_copyright` (pieces have it; add to collections for arrangements or books).
  - **Permission record:** `audio_permission` (yes/no), `permission_granted_by` (e.g. "Schott Music"), `permission_date`, `permission_notes`, optional `permission_document` (the letter or email, as a private file), optional `permission_expires`.
  - **"Get the music":** `music_source_title` (e.g. "Giesbert: Method for the Treble Recorder"), `music_publisher`, `music_edition` (e.g. "ED 2561"), `music_purchase_url`.
  - **Edition** (public-domain items): `edition_source` (e.g. "Mattheson, Op. 1, Amsterdam 1708, facsimile"), `edition_notes` (preface), `edition_editor` (default "Michael Piraner").
- **Collection values flow down to pieces:** set the permission and "Get the music" details once on a collection (usually one book) and every piece in it uses them, unless the piece has its own.

### Rules (extending the existing lock)
1. An in-copyright item can only be public if it has `audio_permission`. Without permission the current lock applies: the form explains why, and other saves keep it private.
2. Sheet music files **can't be attached** to in-copyright items: the upload fields are hidden and validation rejects them. Any already attached aren't served to anyone except you.
3. If a permission has an expiry date and it passes, the item goes back to private automatically (a nightly job) and you get an email a month before.
4. An in-copyright item that's public must have "Get the music" details. The form requires at least the source title.
5. "Get the music" links open the publisher's or shop's page in a new tab. Use plain links (no affiliate tracking) unless you decide otherwise.

### Copyright wording for users
- **On in-copyright items:** *"This music is still in copyright. To play along, you'll need your own copy: [Get the music]. The recording is provided with the kind permission of [publisher]."*
- **On editions:** *"Recorder-ed Edition, edited by Michael Piraner from [source]. Free for personal study and teaching. Please don't redistribute or sell it."*
- **An "About our editions & copyright" page**, linked from both, explaining the policy in plain English.
- **Terms & Conditions:** add a short clause setting out how editions may be used (personal and educational use, no redistribution).

## 7. Recorder-ed Editions (public domain)

- **Sources:** prepare from original prints, manuscripts or facsimiles (e.g. IMSLP), never from a modern edition.
- **Contents of each PDF:** title page with "Recorder-ed Edition", source, editor, year and usage terms; a short preface; editorial additions shown as such (brackets, dashed slurs). Add these in your notation software; the site doesn't change the PDF.
- **Downloads** need a free account (section 5). Each download is counted (section 11).
- **Score image** on screen for practice: unchanged.

## 8. Existing Digital Products play-alongs

| Product | Proposal |
|---|---|
| William Williams Sonata (free, 9 users) | Move to the library as a Recorder-ed Edition. Archive the product. The 9 users must keep access through **My Purchases**; check that archived products stay playable there, and fix it if not. The product page redirects to the library page. |
| Mattheson Sonata in G minor (£1.99, no sales) | Same as above, made free. |
| "Play-Along" product type | Hidden from the create-product form for new products. Existing purchases keep working. |

A paid **bundle** later (e.g. a printed-quality edition set with performance notes, or a video masterclass on the piece) could still go in Digital Products and link from the free piece page.

## 9. Managing the library (teacher side)

Additions to **Manage Library**:
- **Status badges on every card:** Public / Private, and Public domain / In copyright (permission) / In copyright (students only).
- **"Needs attention" filter:**
  - public-domain items with no edition PDF;
  - in-copyright public items with no "Get the music" link;
  - permissions expiring within 60 days;
  - public collections containing private pieces (playable through the collection; flagged so it's deliberate).
- **One-step "Publish collection":** makes a collection and all its pieces public together (where the lock allows), instead of editing each piece.
- **"View as visitor":** opens the public page logged out, so you see exactly what a visitor sees.
- **Permission screen per collection:** record or update the permission, attach the letter, set the expiry.
- **Featured tick box** for the landing page.
- **Composer page:** shows the in-copyright setting (done) and counts of public and private pieces.

## 10. Search engines (SEO)

- Readable addresses (`/playalongs/<slug>/`). Add slug fields to Piece, Collection and Composer, generated from the titles.
- Page titles and descriptions per piece, e.g. *"Mattheson Sonata in G minor — free recorder play-along & edition | Recorder-ed"*.
- Add the landing page, piece pages, collection pages and composer pages to `sitemap.xml`. Only public items.
- Structured data (schema.org `MusicComposition` / `CreativeWork`) on piece pages.
- Composer pages (`/playalongs/composers/mattheson/`) with the biography and list of pieces: good search pages in their own right.
- `robots.txt` already blocks search-result pages. Keep it.

## 11. Measuring it

GA4 events (the site already sends GA4 purchase events):
- `playalong_view`, `playalong_play` (first play per page view), `edition_download`, `get_music_click`, `playalong_signup` (sign-up started from the library).
- After a month, check which pieces are played most, how many sign-ups come from the library, and how many of those go on to book or buy.

## 12. Turning library users into students

- After a few plays, a gentle panel in the player: *"Enjoying this piece? Get personal feedback in a private lesson."*, plus links to upcoming workshops featuring that repertoire.
- Optional welcome email after sign-up from the library: three suggested pieces, plus what Recorder-ed offers. Uses the existing notification system and respects email preferences.
- Practice log link: logged-in students can log practice against a play-along (practice clips already exist).

## 13. Phases

| Phase | Contents | Size |
|---|---|---|
| **1. Open the door** | Fix visitor view (collections, tabs, wording); `/playalongs/` landing page; home page strip; menu and footer links; Digital Products banner; sitemap entries for landing page | Small–medium |
| **2. Copyright & editions** | Permission fields and rules; "Get the music" panel; edition fields and panel; block score uploads on in-copyright items; About our editions page; T&Cs clause | Medium |
| **3. Piece pages & SEO** | Slugs, piece/collection/composer pages, redirects from old addresses, structured data, full sitemap | Medium |
| **4. Accounts & measurement** | Preview vs full play for visitors; sign-up return-to-piece; GA4 events | Small–medium |
| **5. Management tools** | Status badges, Needs attention filter, Publish collection, View as visitor, Featured, permission expiry job and reminder | Medium |
| **6. Content moves** | Move Williams and Mattheson products into the library; retire Play-Along product type | Small |
| **7. Growth** | Player prompts, welcome email | Small |

Phases 1 and 2 can go live together for a launch. The others follow independently.

**Content work (yours, alongside):** prepare editions for the public-domain pieces, write the composer biographies, write to Schott about Giesbert and Bonsor, and decide whether to ask Elizabeth Cooper (or her publisher) for permission too.

## 14. Decisions needed

1. **Home page placement:** separate strip under the four cards (recommended), a fifth card, or inside Digital Products?
2. **Address and name:** `/playalongs/` and "The Recorder-ed Play-Along Library"?
3. **Accounts:** free account to play in full, with an open preview (recommended), or fully open?
4. **Old products:** move the Williams and Mattheson products into the library, and make Mattheson free?
5. **"Get the music" links:** plain links, or affiliate links where available?
6. **Permission expiry:** do you want expiry dates and reminders, or are permissions open-ended?
7. **Featured items** for launch: which three to six?


## As built (28 Nov 2026)

| Plan item | Where |
|---|---|
| Public pages | `apps/audioplayer/public_views.py`, `public_urls.py` (namespace `playalongs`, mounted at `/playalongs/`), templates in `apps/audioplayer/templates/playalongs/` |
| Addresses | `/playalongs/` landing, `/playalongs/library/`, `/playalongs/piece/<slug>/`, `/playalongs/collection/<slug>/`, `/playalongs/composer/<slug>/`, `/playalongs/editions/`. Old `/audioplayer/library/...` player addresses redirect (301). JSON endpoints unchanged. |
| Piece and collection pages | Built on `audioplayer/audio_player.html`, which now has blocks `player_breadcrumbs`, `player_header`, `player_after`, `player_back` |
| Data | `LibraryItemFields` abstract model (slug, featured, permission, "Get the music", edition) on Piece and PieceCollection; `Composer.slug`; `PieceCollection.in_copyright`; `UserProfile.signup_source`. Migrations audioplayer 0016–0018, accounts 0018 |
| Copyright rules | `Piece.is_copyright_locked` / `PieceCollection.is_copyright_locked` now allow a valid permission (own, or a collection's for its pieces). `clean()` also requires "Get the music" details for public in-copyright items and rejects sheet music on in-copyright items. `views._score_url` hides scores of in-copyright items from everyone but teachers, and PDFs from visitors |
| Preview | Visitors get 30 seconds and disabled track controls (`audio_player.js`, `#is-preview`). The audio files themselves are still reachable through the JSON, so this is a nudge, not a lock |
| Accounts | Log-in now honours `?next=`; sign-up remembers `next` and marks library sign-ups (`signup_source='playalongs'`); first email verification sends the library welcome email |
| Analytics | GA4 events `playalong_view`, `playalong_play`, `edition_download`, `get_music_click`, `playalong_signup` |
| Management | Status badges, "Needs attention" tab, "Publish" (collection and its pieces), "View as visitor" (`?as_visitor=1`), Featured, permission fields, composer counts |
| Expiry | `manage.py expire_playalong_permissions` (daily): makes expired items private, emails 30 days ahead and on expiry |
| Products | `manage.py move_playalong_products_to_library` (run once): publishes linked collections/pieces and archives the product. Archived play-along product pages redirect to the library. New products can't be play-alongs |
| Terms | Section 6.3 in `templates/core/terms.html` |

### Deploy steps (each server)
1. Deploy as usual (migrations run).
2. `python manage.py move_playalong_products_to_library --dry-run`, then without `--dry-run`.
3. Add the daily cron line:
   `15 3 * * * cd /var/www/recorder_ed && venv/bin/python manage.py expire_playalong_permissions >> /var/log/recordered/playalongs.log 2>&1`
4. Mark featured items and fill in edition details in Manage Library.
