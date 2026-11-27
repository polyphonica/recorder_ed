# Practice Log Audio Clips: Implementation Plan

**Status:** Built on branch `practice-audio-clips`, awaiting staging tests · **Date:** 2026-11-25 (revised 2026-11-27) · **App:** `apps/practice`

## Summary

Let students record short audio excerpts of passages, scales or exercises they're struggling with and attach them to a practice log entry. The teacher listens and replies with a text and/or **recorded audio** reply, giving specific practice advice between lessons.

### Decisions already made
- **Available to all students.** No per-student switch.
- **Included in the practice log.** Not a paid extra.
- **Audio replies from the start**, as well as text replies.
- **Audio only.** No video.
- **Student follow-up replies in the first release** ("tried it, better?").
- **All phases released together**, tested on staging first.
- **Loudness normalisation optional.** Recorders have limited dynamics, so normalising doesn't distort what the teacher hears.

### Goals
- Make it quick to record on a phone: record → listen back → keep or redo → send.
- Keep it to excerpts (strict length and count limits).
- Recordings are private to the student, their guardian and their teacher. **No public URLs.**
- Reuse one recorder component, so the planned Aural Trainer mic work can use it too.

---

## User flows

### Student or guardian
1. On **Log practice** / **Edit practice** (`apps/practice` `log_practice`, `edit_practice`), they see a **Clips** section with **Record a clip** and **Upload a file**.
2. Recorder: mic permission prompt → live level meter → record (auto-stop at the limit) → playback → **Keep** / **Redo**.
3. For each clip they add:
   - **What is it?** Piece / Scale / Exercise / Other
   - **Title** (e.g. "Telemann Sonata in F, 2nd mvt", "G major 2 octaves")
   - **What do you want help with?** (e.g. "bars 12–16, the slur to top E cracks")
   - Optional link to an audioplayer `Piece`.
4. Save. The teacher gets an email once the clips have been processed.

   On **Log practice** the entry doesn't exist yet, so each kept clip is uploaded straight away as a *pending* clip (`entry=None`, owned by the uploader). The form sends the pending clip IDs with the entry, and the save links them to the new entry. Pending clips never linked are deleted after 24 hours. On **Edit practice** clips attach to the existing entry directly.
5. When the teacher replies, the student gets an email, and the reply (text and/or audio) appears under the clip in the practice log.
6. The student or guardian can send a follow-up in the same thread (text and/or a recording of up to 90 s). This reopens the clip in the teacher's inbox and emails the teacher.

For child accounts, the guardian (the `student` user on the entry, with `child_profile` set) does the recording or shares it. No separate approval step is needed, because the child doesn't have their own login.

### Teacher
1. **Clips inbox** (new page): clips not yet replied to from all students, oldest first, with a count badge in the teacher nav.
2. Clip detail: player, the student's note, a link to the parent practice entry, and any previous clips with the same title (to hear progress).
3. Reply: text box and/or **Record reply** (the same recorder component). Several replies are allowed, as a short thread.
4. Mark as **Done** without replying (e.g. "will cover in lesson") so it leaves the inbox.
5. Clips also appear inline in the existing `teacher_student_practice` view.

---

## Limits

| Setting | Value | Notes |
|---|---|---|
| Max clip length | 90 s | Auto-stop in the recorder; checked again on the server |
| Max clips per entry | 3 | |
| Max teacher reply length | 3 min | Teacher demonstrations may need longer |
| Max upload size | 10 MB | Checked in the browser before upload and again in the view (see below) |
| Accepted upload types | webm, ogg, mp4/m4a, mp3, wav, aiff | Content-sniffed, not trusted from the extension. AIFF because Mac users export it |
| Retention | 12 months after the last activity | Last reply, or creation if never replied to. Either party can **Keep** a clip to exempt it |
| Pending clips | 24 hours | Uploaded on Log practice but never attached to a saved entry |

Put these in `settings.py` (`PRACTICE_CLIP_MAX_SECONDS`, etc.) so they can be tuned.

**Where the upload size is enforced.** nginx allows 100 MB per request on production (`client_max_body_size 100M`). That limit is for the Creator Studio audio converter, which takes uncompressed AIFF/WAV backing tracks up to 45 MB, and it stays as it is. Django's `DATA_UPLOAD_MAX_MEMORY_SIZE` / `FILE_UPLOAD_MAX_MEMORY_SIZE` don't limit file size. So the 10 MB clip limit is enforced:
1. in the recorder JS, before uploading, so the user gets an instant message, and
2. in `AddClipView` / `AddClipReplyView` (`file.size`), before anything is saved or queued.

No separate nginx `location` for the clip URLs: it would duplicate the proxy config for little gain. Phone recordings are about 1 MB; the 10 MB limit mainly matters for the upload fallback (90 s of AIFF is about 15 MB, and is rejected).

Rough storage: Opus at about 64 kbps is about 0.5 MB per minute. 50 students × 3 clips a week × 1 minute is about 4 GB a year before retention deletes anything.

---

## Data model

New models in `apps/practice/models.py`:

```python
class PracticeClip(models.Model):
    KIND_CHOICES = [('piece', 'Piece'), ('scale', 'Scale'),
                    ('exercise', 'Exercise'), ('other', 'Other')]
    STATUS_CHOICES = [('processing', 'Processing'), ('ready', 'Ready'),
                      ('failed', 'Failed')]

    id = UUIDField(primary_key=True, default=uuid4, editable=False)
    entry = ForeignKey(PracticeEntry, on_delete=CASCADE, related_name='clips',
                       null=True, blank=True)   # None while pending (Log practice)
    uploaded_by = ForeignKey(User, on_delete=SET_NULL, null=True)  # owner of a pending clip

    kind = CharField(max_length=20, choices=KIND_CHOICES)
    title = CharField(max_length=200)
    note = TextField(blank=True)                 # "what do you want help with?"
    piece = ForeignKey('audioplayer.Piece', null=True, blank=True, on_delete=SET_NULL)

    original_file = FileField(storage=private_storage, upload_to=clip_upload_path)
    audio_file = FileField(storage=private_storage, upload_to=clip_upload_path, blank=True)  # converted
    duration_seconds = PositiveIntegerField(null=True)
    status = CharField(max_length=20, choices=STATUS_CHOICES, default='processing')

    teacher_listened_at = DateTimeField(null=True, blank=True)
    teacher_notified_at = DateTimeField(null=True, blank=True)  # see Notifications
    resolved_at = DateTimeField(null=True, blank=True)   # teacher replied or marked done
    keep = BooleanField(default=False)                   # exempt from retention
    last_activity_at = DateTimeField(auto_now_add=True)  # bumped on each reply; drives retention
    created_at = DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [Index(fields=['entry']), Index(fields=['resolved_at', 'created_at']),
                   Index(fields=['keep', 'last_activity_at'])]


class PracticeClipReply(models.Model):
    id = UUIDField(primary_key=True, default=uuid4, editable=False)
    clip = ForeignKey(PracticeClip, on_delete=CASCADE, related_name='replies')
    author = ForeignKey(User, on_delete=SET_NULL, null=True)   # teacher, or student/guardian follow-up
    text = TextField(blank=True)
    original_file = FileField(storage=private_storage, upload_to=reply_upload_path, blank=True)
    audio_file = FileField(storage=private_storage, upload_to=reply_upload_path, blank=True)
    duration_seconds = PositiveIntegerField(null=True, blank=True)
    status = CharField(max_length=20, choices=PracticeClip.STATUS_CHOICES,
                       default='ready')                  # 'processing' when audio attached
    read_at = DateTimeField(null=True, blank=True)       # the other party opened it
    created_at = DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [CheckConstraint(
            condition=~Q(text='') | ~Q(original_file='') | ~Q(audio_file=''),
            name='practice_clip_reply_has_content')]
```

- Upload paths are made from UUIDs, not names: `practice_clips/<uploader_id>/<uuid>.<ext>` (the entry may not exist yet, so the path can't use its ID).
- **Clip count limit:** check "3 per entry" inside a transaction with `select_for_update()` on the entry (or on the uploader's pending clips), so two quick uploads can't both pass a count-then-create check.
- **File deletion:** always delete files in `transaction.on_commit`, so a rolled-back delete doesn't lose them. This applies to deleting clips, the cascade, retention, and removing `original_file` after processing.
- Add `history = HistoricalRecords()`? **No.** The audit value is low, and history would keep metadata for deleted clips. Deletions are instead recorded in the application log.
- **Follow-ups:** a reply by the student/guardian sets `resolved_at = None` (back in the teacher's inbox) and bumps `last_activity_at`. Its audio limit is the clip limit (90 s), not the teacher's 3 min. Whose reply it is comes from `author == entry.teacher`.

---

## Private storage and serving

Uploads today go to `MEDIA_ROOT`, which nginx serves publicly at `/media/`. Clips must **not** go there.

1. **Storage:** `private_storage = FileSystemStorage(location=settings.PRIVATE_MEDIA_ROOT)`, with `PRIVATE_MEDIA_ROOT` outside both the web root and `MEDIA_ROOT` (e.g. `/var/www/recorder_ed/private_media/`). Set it in `.env` and add it to `.env.example`.
2. **Serving view:** `GET /practice/clips/<uuid>/audio/` (and `/practice/clip-replies/<uuid>/audio/`):
   - Allowed: the entry's `student` (adult or guardian), the entry's `teacher`, and superusers. Anyone else gets a 404, not a 403.
   - Production: return an empty response with `X-Accel-Redirect: /protected/practice_clips/...` so nginx streams the file. This supports `Range` requests, which mobile Safari needs for seeking.
   - Development and staging: fall back to `FileResponse`.
   - Headers: `Cache-Control: private, no-store`, `Content-Disposition: inline`, `X-Content-Type-Options: nosniff`.
3. **nginx** (production and staging):
   ```nginx
   location /protected/ {
       internal;
       alias /var/www/recorder_ed/private_media/;
   }
   ```
4. Add `private_media/` to `.gitignore` and to the backup script / `deploy.sh` checks. Do both the nginx block and the backup change in **phase 1**: without the `internal` location, `X-Accel-Redirect` returns 404 on production while staging (which uses `FileResponse`) works, so the bug wouldn't show up in testing.

---

## Recording in the browser

A reusable JS module, `static/js/audio-recorder.js`, plus a template partial, `templates/components/audio_recorder.html`:

- `navigator.mediaDevices.getUserMedia({audio: {echoCancellation: false, noiseSuppression: false, autoGainControl: false}})`. Turn off voice processing so the recorder's tone isn't distorted.
- `MediaRecorder` with the first supported type: `audio/webm;codecs=opus` → `audio/mp4` (Safari) → browser default.
- Level meter with `AnalyserNode`. Countdown timer, auto-stop at the limit, playback with `<audio>`, and Keep / Redo.
- On Keep, send the Blob with `fetch` as `multipart/form-data` and the CSRF token, with an upload progress indicator.
- Fallback: `<input type="file" accept="audio/*" capture>`. This opens the phone's voice recorder on some devices, and is used when `MediaRecorder` is unavailable or mic permission is denied.
- Accessibility: keyboard-operable buttons, status announced with `aria-live`, and the timer readable by screen readers.
- Clear guidance when permission is denied (per-browser instructions to re-enable the mic).

The same component handles the teacher's audio replies, with a `max-seconds` setting.

---

## Server-side processing (Celery)

`apps/practice/tasks.py` → `process_practice_audio(model_label, pk)`:

1. Check the type by content sniffing (ffprobe), not by the extension or browser-supplied content type.
2. Check duration with `ffprobe`, and reject anything over the limit plus 2 s of tolerance (`status='failed'`, notify the uploader).
3. Convert with ffmpeg to **AAC in .m4a at 96 kbps, mono**. This plays in every browser, including older iOS Safari.
4. Loudness normalisation (`loudnorm`) is optional and off by default (`PRACTICE_CLIP_NORMALISE = False`); recorders have limited dynamics, so it isn't needed to make clips audible. Don't trim silence automatically; it can cut a pickup note.
5. Save `audio_file` and `duration_seconds`, set `status='ready'`, and delete `original_file`.
6. **Then** send the notification email, so the teacher never gets an email for a clip that isn't playable yet.

Reuse or extend `apps/creator_studio/services/audio_processor.py`, which already calls ffmpeg through `subprocess`, rather than writing a second wrapper. Use an argument list, no shell, and a timeout. **ffmpeg is already installed on production** (`VPS_MIGRATION.md`, for pydub); check staging and note it in `DEPLOYMENT_GUIDE.md`. Confirm the Celery worker service is running on production, since clips stay at `processing` without it.

Staging runs Celery tasks immediately in the request (`CELERY_TASK_ALWAYS_EAGER = True`), so processing happens during the upload request there. That's fine at these sizes.

---

## Notifications

Extend `PracticeNotificationService` (`apps/practice/notifications.py`):

- `send_clip_shared_notification(entry)` → teacher: "<Student> shared a clip: <title>" (or "shared 3 clips"). One email per batch, not per clip. Each clip is processed in its own task, so batching works like this: when a clip becomes `ready`, lock the entry's clips; if any are still `processing`, do nothing; otherwise collect the ready clips with `teacher_notified_at` unset, set it on them, and send one email listing them. Failed clips don't hold up the email. Pending clips (no entry yet) wait until they're linked, and the save runs the same check.
- `send_clip_reply_notification(reply)` → student/guardian: "<Teacher> replied to your clip: <title>".
- `send_clip_followup_notification(reply)` → teacher: "<Student> followed up on: <title>".
- Both go through the existing `send_email_task` (async, with retries).
- Emails link to the page, never to the audio file.

---

## URLs and views

| URL | View | Who |
|---|---|---|
| `practice/clips/upload/` | `UploadPendingClipView` (POST, JSON) | Student (on Log practice) |
| `practice/<uuid:entry_id>/clips/add/` | `AddClipView` (POST, JSON) | Entry owner |
| `practice/clips/<uuid:pk>/delete/` | `DeleteClipView` | Entry owner (or teacher) |
| `practice/clips/<uuid:pk>/audio/` | `ClipAudioView` | Owner, teacher |
| `practice/clips/<uuid:pk>/keep/` | toggle `keep` | Owner, teacher |
| `teacher/clips/` | `TeacherClipInboxView` | Teacher |
| `teacher/clips/<uuid:pk>/` | `TeacherClipDetailView` (marks listened) | Teacher of that entry |
| `teacher/clips/<uuid:pk>/reply/` | `AddClipReplyView` (text and/or audio) | Teacher |
| `teacher/clips/<uuid:pk>/done/` | mark resolved without reply | Teacher |
| `practice/clips/<uuid:pk>/reply/` | `AddStudentFollowUpView` (text and/or audio) | Entry owner |
| `practice/clip-replies/<uuid:pk>/audio/` | `ClipReplyAudioView` | Owner, teacher |

All views check access with one shared helper:
- **Student side:** `entry.student == request.user` (adult or guardian), or `clip.uploaded_by == request.user` for a pending clip.
- **Teacher side:** `entry.teacher == request.user` **and** an accepted, non-deleted `Lesson` between that teacher and the entry's student still exists. This is the same check the practice views already use, so a former teacher loses access.
- Superusers: always.

**Rate limiting:** there's no rate limiting in the project yet. Add a small cache-based counter (e.g. 20 uploads per user per hour for add/upload, 30 for replies and follow-ups) using Django's cache. `settings.py` has no `CACHES` setting, so Django uses its default in-memory cache, which is separate in each gunicorn worker (production runs 3), so a user could get 3× the limit. Add a `CACHES` setting pointing at the Redis server Celery already uses (`django.core.cache.backends.redis.RedisCache`, a different Redis database number from the broker) as part of phase 1.

---

## Templates and UI

- **Practice entry form:** a Clips section with the recorder and a list of attached clips (player, title, note, delete).
- **Student practice log** (`practice_log`): clips shown inline under each entry, with the reply thread and a **Follow up** button (text box and recorder). A "New reply" badge until `read_at` is set.
- **Teacher student practice view** (`teacher_student_practice`): clips inline, with a reply button.
- **Teacher clip inbox:** a new page, plus a nav badge with the count of unresolved clips.
- **Print view** (`practice_log_print`): list clip titles and notes, plus text replies. Audio is omitted.
- Use the existing site styles and the audioplayer look where possible.

---

## Privacy, safeguarding and retention

- **Access:** only the student/guardian, the assigned teacher and superusers. No sharing links, downloads hidden in the UI (`controlsList="nodownload"`, which is a courtesy, not a security measure).
- **Teacher change:** a teacher has access only while an accepted, non-deleted `Lesson` with the student exists (see URLs and views). When the relationship ends, the former teacher loses access; the student keeps the clips and replies.
- **Deletion:**
  - Students/guardians can delete their own clips at any time, which deletes the files immediately.
  - Deleting a practice entry or the account cascades to its clips and files. Delete the files in a `post_delete` signal, or through a task for reliability.
- **Retention task:** a management command, `purge_practice_clips`, run daily by cron (like the lesson reminders; there's no Celery beat). It deletes clips and their replies where `keep=False` and `last_activity_at` is more than 12 months ago, plus pending clips older than 24 hours. Log the counts.
- **Privacy policy:** add a section on practice recordings: purpose, who can hear them, retention, and how to delete them. Children's recordings are made and shared by the guardian.
- **Backups:** include `private_media/` in backups. Deleted clips will remain in older backups until those expire; say so in the policy.
- **No AI or third-party processing** of recordings without separate consent.

---

## Testing

`apps/practice/tests/test_clips.py` (create `apps/practice/tests/` as a package; run it with the label `apps.practice.tests`):
- Permissions: owner, guardian, teacher, other teacher, former teacher (lesson no longer accepted), other student, another guardian, anonymous → correct 200/404 on every view, including the audio endpoints.
- Pending clips: uploaded on Log practice, linked on save, can't be linked to someone else's entry, purged after 24 hours.
- Limits: 4th clip rejected (including two concurrent uploads), oversize upload rejected in the view before saving, over-length audio rejected after processing.
- Reply constraint: a reply with neither text nor audio is rejected.
- Processing: a fixture webm and m4a convert to a playable m4a and get a duration (skip if ffmpeg is missing in CI).
- Notifications: sent after processing, not before; one email for a batch of clips; a failed clip doesn't block the email.
- Rate limit: the 21st upload in an hour is refused.
- Follow-ups: owner can follow up, others get 404; a follow-up reopens a resolved clip, emails the teacher, and is limited to 90 s.
- Retention: old unkept clips deleted with their files, kept clips left alone.
- Cascade: deleting an entry removes its files from disk.

Manual testing: iOS Safari, Android Chrome, desktop Chrome/Firefox/Safari, with recording, playback, seeking and denied mic permission.

---

## Delivery phases

1. **Backend:** models, migration, private storage, serving view, nginx `internal` location and backup of `private_media/`, processing task, permissions, rate limiting and tests.
2. **Student recording:** recorder component, upload fallback, clip UI on entry form and practice log.
3. **Teacher side and threads:** inbox, clip detail, text and audio replies, student follow-ups, nav badge, notifications in both directions.
4. **Housekeeping:** retention task, delete cascade, privacy policy, print view, deployment docs (ffmpeg, `PRIVATE_MEDIA_ROOT`, nginx).

Release phases 1–4 together. Use the usual feature branch → staging → test → main → production, and test on real phones on staging before merging.

**Before release, check on production and staging:**
- The Celery worker service is running (`systemctl list-units | grep -i celery`). Without it, clips stay "Processing" for ever. Staging runs tasks in the request, so it won't catch this.
- `ffmpeg -version` works on staging (it's already on production).
- Redis is running, for the new `CACHES` setting.

## Later ideas

- Comments pinned to points in a clip ("at 0:14…").
- "Progress on this passage": play earlier clips with the same title side by side.
- Attach a clip to a lesson's notes, for discussion in the next lesson.
- Share the recorder component with the Aural Trainer redesign (sing-back and clap-back tests).

---

## As built (2026-11-27)

Differences from the plan above:
- **No link to an audioplayer `Piece`** in the first release. The clip's title does that job; add the link later if it's wanted.
- **Teachers can't delete clips.** They mark them done; deleting stays with the student/guardian, who owns the recording.
- **Failed processing isn't emailed.** The clip shows the reason ("longer than 90 seconds", "doesn't look like an audio file") on the form and in the practice log.
- **ffmpeg code:** a small `apps/practice/audio.py` (ffprobe + ffmpeg through `subprocess`) rather than Creator Studio's `AudioProcessor`, which uses pydub and writes temporary files under the public `MEDIA_ROOT`.
- **Replies** have a `from_teacher` flag, and `status='none'` for text-only replies. The database rule is "text, or audio was attached".
- **Teacher nav:** a **Clips** link with a count badge in the private-teaching teacher nav, which now also shows on practice pages.

Main files: `apps/practice/clips.py` (access rules, limits, notifications), `clip_views.py`, `tasks.py`, `audio.py`, `signals.py`, `management/commands/purge_practice_clips.py`, `static/js/audio-recorder.js`, `templates/practice/partials/`, `templates/practice/teacher_clip_*.html`. Tests: `apps/practice/tests/test_clips.py` (need a working ffmpeg).

## Deployment steps

**Staging** (old IONOS server):
1. `ffmpeg -version` works.
2. `mkdir -p /var/www/recorder_ed_staging/private_media && chown www-data:www-data` it (staging's `PRIVATE_MEDIA_ROOT` default).
3. Pull the branch, `migrate`, `collectstatic`, restart gunicorn. Staging serves audio through Django (`PRIVATE_MEDIA_X_ACCEL` stays False) and runs Celery tasks in the request.

**Production** (after merging to main):
1. Add to `.env`:
   ```
   CACHE_REDIS_URL=redis://localhost:6379/1
   PRIVATE_MEDIA_ROOT=/var/www/recorder_ed/private_media
   PRIVATE_MEDIA_X_ACCEL=True
   ```
2. `mkdir -p /var/www/recorder_ed/private_media && chown www-data:www-data /var/www/recorder_ed/private_media && chmod 750 /var/www/recorder_ed/private_media`
3. In `/etc/nginx/sites-enabled/recorder_ed`, inside the HTTPS `server` block, next to `location /media/`:
   ```nginx
   location /protected/ {
       internal;
       alias /var/www/recorder_ed/private_media/;
   }
   ```
   Then `nginx -t && systemctl reload nginx`. Without this, audio returns 404 on production.
4. `git pull`, then `./deploy.sh` (migrate, collectstatic, restart gunicorn_recordered and celery_recordered).
5. Add to root's crontab:
   ```
   30 3 * * * cd /var/www/recorder_ed && /var/www/recorder_ed/venv/bin/python3 manage.py purge_practice_clips >> /var/log/recordered/practice_clips.log 2>&1
   ```
6. Check: record a clip as a test student, confirm it plays for the student and teacher, and that another account gets a 404 on the audio URL.

`private_media/` is under `/var/www/recorder_ed`, so the whole-server Backup Package should already include it. Confirm that in the IONOS backup settings.

