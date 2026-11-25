# Practice Log Audio Clips: Implementation Plan

**Status:** Proposed · **Date:** 2026-11-25 · **App:** `apps/practice`

## Summary

Let students record short audio excerpts of passages, scales or exercises they're struggling with and attach them to a practice log entry. The teacher listens and replies with a text and/or **recorded audio** reply, giving specific practice advice between lessons.

### Decisions already made
- **Available to all students.** No per-student switch.
- **Included in the practice log.** Not a paid extra.
- **Audio replies from the start**, as well as text replies.
- **Audio only.** No video.

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
4. Save. The teacher gets an email.
5. When the teacher replies, the student gets an email, and the reply (text and/or audio) appears under the clip in the practice log.

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
| Max upload size | 10 MB | Below the nginx `client_max_body_size` of 15 MB |
| Accepted upload types | webm, ogg, mp4/m4a, mp3, wav | Content-sniffed, not trusted from the extension |
| Retention | 12 months after the last reply | Either party can **Keep** a clip to exempt it |

Put these in `settings.py` (`PRACTICE_CLIP_MAX_SECONDS`, etc.) so they can be tuned.

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
    entry = ForeignKey(PracticeEntry, on_delete=CASCADE, related_name='clips')
    uploaded_by = ForeignKey(User, on_delete=SET_NULL, null=True)

    kind = CharField(max_length=20, choices=KIND_CHOICES)
    title = CharField(max_length=200)
    note = TextField(blank=True)                 # "what do you want help with?"
    piece = ForeignKey('audioplayer.Piece', null=True, blank=True, on_delete=SET_NULL)

    original_file = FileField(storage=private_storage, upload_to=clip_upload_path)
    audio_file = FileField(storage=private_storage, upload_to=clip_upload_path, blank=True)  # converted
    duration_seconds = PositiveIntegerField(null=True)
    status = CharField(max_length=20, choices=STATUS_CHOICES, default='processing')

    teacher_listened_at = DateTimeField(null=True, blank=True)
    resolved_at = DateTimeField(null=True, blank=True)   # teacher replied or marked done
    keep = BooleanField(default=False)                   # exempt from retention
    created_at = DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [Index(fields=['entry']), Index(fields=['resolved_at', 'created_at'])]


class PracticeClipReply(models.Model):
    id = UUIDField(primary_key=True, default=uuid4, editable=False)
    clip = ForeignKey(PracticeClip, on_delete=CASCADE, related_name='replies')
    author = ForeignKey(User, on_delete=SET_NULL, null=True)   # teacher (or student follow-up)
    text = TextField(blank=True)
    original_file = FileField(storage=private_storage, upload_to=reply_upload_path, blank=True)
    audio_file = FileField(storage=private_storage, upload_to=reply_upload_path, blank=True)
    duration_seconds = PositiveIntegerField(null=True, blank=True)
    status = CharField(max_length=20, default='ready')   # 'processing' when audio attached
    read_at = DateTimeField(null=True, blank=True)       # student opened it
    created_at = DateTimeField(auto_now_add=True)
    # constraint: text or original_file must be set
```

- Upload paths are made from UUIDs, not names: `practice_clips/<entry_id>/<uuid>.<ext>`.
- Add `history = HistoricalRecords()`? **No.** The audit value is low, and history would keep metadata for deleted clips. Deletions are instead recorded in the application log.
- Optional, later: let students send a short follow-up reply in the thread ("tried it, better?"). The model already allows this.

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
4. Add `private_media/` to `.gitignore` and to the backup script / `deploy.sh` checks.

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
4. Optionally normalise loudness (`loudnorm`) so quiet student recordings are audible. Don't trim silence automatically; it can cut a pickup note.
5. Save `audio_file` and `duration_seconds`, set `status='ready'`, and delete `original_file`.
6. **Then** send the notification email, so the teacher never gets an email for a clip that isn't playable yet.

`pydub` is already in requirements, but calling `ffmpeg`/`ffprobe` directly with `subprocess` (argument list, no shell, timeout) is simpler and avoids the extra layer. **Add ffmpeg to the server provisioning** (`apt install ffmpeg` on production and staging), and note it in `DEPLOYMENT_GUIDE.md`.

Staging runs Celery tasks immediately in the request (`CELERY_TASK_ALWAYS_EAGER = True`), so processing happens during the upload request there. That's fine at these sizes.

---

## Notifications

Extend `PracticeNotificationService` (`apps/practice/notifications.py`):

- `send_clip_shared_notification(clip)` → teacher: "<Student> shared a clip: <title>". Send it once per entry save, not once per clip, if several clips are uploaded together.
- `send_clip_reply_notification(reply)` → student/guardian: "<Teacher> replied to your clip: <title>".
- Both go through the existing `send_email_task` (async, with retries).
- Emails link to the page, never to the audio file.

---

## URLs and views

| URL | View | Who |
|---|---|---|
| `practice/<uuid:entry_id>/clips/add/` | `AddClipView` (POST, JSON) | Entry owner |
| `practice/clips/<uuid:pk>/delete/` | `DeleteClipView` | Entry owner (or teacher) |
| `practice/clips/<uuid:pk>/audio/` | `ClipAudioView` | Owner, teacher |
| `practice/clips/<uuid:pk>/keep/` | toggle `keep` | Owner, teacher |
| `teacher/clips/` | `TeacherClipInboxView` | Teacher |
| `teacher/clips/<uuid:pk>/` | `TeacherClipDetailView` (marks listened) | Teacher of that entry |
| `teacher/clips/<uuid:pk>/reply/` | `AddClipReplyView` (text and/or audio) | Teacher |
| `teacher/clips/<uuid:pk>/done/` | mark resolved without reply | Teacher |
| `practice/clip-replies/<uuid:pk>/audio/` | `ClipReplyAudioView` | Owner, teacher |

All views check ownership through the entry (`entry.student == request.user` or `entry.teacher == request.user`), using a shared helper. Rate-limit the add and reply endpoints.

---

## Templates and UI

- **Practice entry form:** a Clips section with the recorder and a list of attached clips (player, title, note, delete).
- **Student practice log** (`practice_log`): clips shown inline under each entry, with the reply thread. A "New reply" badge until `read_at` is set.
- **Teacher student practice view** (`teacher_student_practice`): clips inline, with a reply button.
- **Teacher clip inbox:** a new page, plus a nav badge with the count of unresolved clips.
- **Print view** (`practice_log_print`): list clip titles and notes, plus text replies. Audio is omitted.
- Use the existing site styles and the audioplayer look where possible.

---

## Privacy, safeguarding and retention

- **Access:** only the student/guardian, the assigned teacher and superusers. No sharing links, downloads hidden in the UI (`controlsList="nodownload"`, which is a courtesy, not a security measure).
- **Teacher change:** if a student's teacher relationship ends, the former teacher loses access (the check uses `entry.teacher` *and* an active relationship check). Decide and document this rule.
- **Deletion:**
  - Students/guardians can delete their own clips at any time, which deletes the files immediately.
  - Deleting a practice entry or the account cascades to its clips and files. Delete the files in a `post_delete` signal, or through a task for reliability.
- **Retention task:** a daily Celery beat or cron job that deletes clips and replies where `keep=False` and the last activity was more than 12 months ago. Log the counts.
- **Privacy policy:** add a section on practice recordings: purpose, who can hear them, retention, and how to delete them. Children's recordings are made and shared by the guardian.
- **Backups:** include `private_media/` in backups. Deleted clips will remain in older backups until those expire; say so in the policy.
- **No AI or third-party processing** of recordings without separate consent.

---

## Testing

`apps/practice/tests/test_clips.py`:
- Permissions: owner, guardian, teacher, other teacher, other student, anonymous → correct 200/404 on every view, including the audio endpoints.
- Limits: 4th clip rejected, oversize upload rejected, over-length audio rejected after processing.
- Processing: a fixture webm and m4a convert to a playable m4a and get a duration (skip if ffmpeg is missing in CI).
- Notifications: sent after processing, not before; batched per entry.
- Retention: old unkept clips deleted with their files, kept clips left alone.
- Cascade: deleting an entry removes its files from disk.

Manual testing: iOS Safari, Android Chrome, desktop Chrome/Firefox/Safari, with recording, playback, seeking and denied mic permission.

---

## Delivery phases

1. **Backend:** models, migration, private storage, serving view and nginx `internal` location, processing task, permissions and tests.
2. **Student recording:** recorder component, upload fallback, clip UI on entry form and practice log.
3. **Teacher side:** inbox, clip detail, text and audio replies, nav badge, notifications in both directions.
4. **Housekeeping:** retention task, delete cascade, privacy policy, print view, deployment docs (ffmpeg, `PRIVATE_MEDIA_ROOT`, nginx).

Ship phases 1–4 together, since audio replies are wanted from the start. Use the usual feature branch → staging → test → main → production. Test on real phones on staging before merging.

## Later ideas

- Comments pinned to points in a clip ("at 0:14…").
- "Progress on this passage": play earlier clips with the same title side by side.
- Student follow-up replies in the thread.
- Attach a clip to a lesson's notes, for discussion in the next lesson.
- Share the recorder component with the Aural Trainer redesign (sing-back and clap-back tests).
