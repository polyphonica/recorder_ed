# Practice Diary Feature - Deployment Guide

## Deployment Steps

### 1. Push Code to Remote Server

First, commit and push all changes to your git repository:

```bash
git add .
git commit -m "Add practice diary feature with exam/performance preparation tracking"
git push origin main
```

### 2. Pull Changes on Remote Server

SSH into your production server and pull the latest changes:

```bash
ssh your-server
cd /path/to/recordered
git pull origin main
```

### 3. Run Migration on Remote Server

Run the migration to create the `PracticeEntry` table:

```bash
python manage.py migrate private_teaching
```

Expected output:
```
Running migrations:
  Applying private_teaching.0014_practiceentry... OK
```

### 4. Restart Application Server

Restart your application server (Gunicorn, uWSGI, etc.):

```bash
# If using systemd:
sudo systemctl restart recordered

# Or if using supervisor:
sudo supervisorctl restart recordered

# Or if using direct gunicorn:
sudo systemctl restart gunicorn
```

### 5. Verify Deployment

1. **Check Student Dashboard**:
   - Navigate to `/private-teaching/dashboard/`
   - Verify "Practice Log" button appears in Quick Actions

2. **Test Log Practice**:
   - Click "Practice Log" → "Log Practice Session"
   - Fill out form and submit
   - Verify it appears in practice log

3. **Test Teacher View**:
   - As teacher, go to "My Students"
   - Click "Practice Log" for a student
   - Verify statistics and entries display

4. **Test Teacher Comments**:
   - On a practice entry, click "Add Teacher Comment"
   - Add a comment and submit
   - Verify comment appears

## Files Changed

### New Files
- `apps/private_teaching/migrations/0014_practiceentry.py`
- `templates/private_teaching/practice/log_practice.html`
- `templates/private_teaching/practice/practice_log.html`
- `templates/private_teaching/practice/teacher_student_practice.html`
- `docs/PRACTICE_DIARY_SPEC.md`
- `docs/PRACTICE_DIARY_DEPLOYMENT.md` (this file)

### Modified Files
- `apps/private_teaching/models.py` (added PracticeEntry model)
- `apps/private_teaching/forms.py` (added PracticeEntryForm)
- `apps/private_teaching/views.py` (added 4 new views)
- `apps/private_teaching/urls.py` (added 4 new URLs)
- `apps/private_teaching/templates/private_teaching/student_dashboard.html` (added Practice Log button)
- `apps/private_teaching/templates/private_teaching/teacher_students_list.html` (added Practice Log button)

## Rollback Plan

If you need to rollback the migration:

```bash
python manage.py migrate private_teaching 0013
```

This will remove the `PracticeEntry` table. Note: This will delete all practice diary data!

## Monitoring

After deployment, monitor for:

- **Error logs**: Check for any 500 errors related to practice diary URLs
- **Database performance**: Monitor query performance on practice entry queries
- **User adoption**: Track how many students start using the practice log
- **Teacher engagement**: Monitor teacher comment activity

## Database Indexes

The migration includes these indexes for optimal performance:
- `(student, -practice_date)` - Student chronological queries
- `(teacher, -practice_date)` - Teacher views of student practice

## Known Limitations

1. **No migration needed locally**: Since your local database can't connect, the migration only needs to run on the remote server
2. **Teacher selection**: Students must select a teacher when logging practice (filtered to teachers they have lessons with)
3. **Child profile**: Only shown if user is a guardian with child profiles

## Testing Checklist

- [ ] Migration runs successfully
- [ ] Student can log practice session
- [ ] Student can view practice log with statistics
- [ ] Student can filter by teacher, child, exam prep, performance prep
- [ ] Teacher can view student practice log
- [ ] Teacher can add comment to practice entry
- [ ] Practice Log button appears on student dashboard
- [ ] Practice Log button appears on teacher students list
- [ ] Guardian can log practice for children
- [ ] Exam preparation entries are highlighted
- [ ] Performance preparation entries are highlighted

## Support

If you encounter issues:

1. Check server error logs: `tail -f /var/log/recordered/error.log`
2. Check database connection: `python manage.py dbshell`
3. Verify migration status: `python manage.py showmigrations private_teaching`
4. Test queries: `python manage.py shell`
   ```python
   from apps.private_teaching.models import PracticeEntry
   PracticeEntry.objects.count()  # Should work after migration
   ```

## Next Steps After Deployment

1. **Communicate to Users**: Send announcement about new practice diary feature
2. **Emphasize Exam Prep**: Highlight the exam preparation tracking in announcement
3. **Gather Feedback**: Monitor usage and gather user feedback for Phase 2 features
4. **Plan Phase 2**: Review `PRACTICE_DIARY_SPEC.md` for future enhancements

---

**Deployment Date**: _____________________
**Deployed By**: _____________________
**Issues Encountered**: _____________________
