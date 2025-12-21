# Phase 1 - End-to-End Testing Guide
## Teacher Availability Calendar System

This guide provides step-by-step instructions for testing the complete teacher availability calendar booking flow.

---

## Prerequisites

Before starting tests, ensure:
- ✅ All Phase 1 migrations have been run
- ✅ Development server is running
- ✅ You have test accounts for both teacher and student roles
- ✅ Teacher has completed their profile
- ✅ Student has an accepted application with the teacher

---

## Test Scenario 1: Teacher Sets Up Availability Calendar

### Objective
Verify that teachers can configure their availability calendar settings and weekly schedule.

### Steps

1. **Access Availability Editor**
   - Log in as a teacher
   - Navigate to Teacher Dashboard
   - Click on "Availability Calendar" or go to `/private-teaching/teacher/availability/`
   - ✅ Verify the availability editor page loads

2. **Configure Booking Settings**
   - Locate the "Booking Settings" card at the top
   - Toggle "Enable Availability Calendar" to ON
   - ✅ Verify the settings form appears
   - Set buffer time: `15` minutes
   - Set minimum notice: `24` hours
   - Set booking window: `90` days
   - Check "Auto-approve bookings"
   - ✅ Verify settings save automatically (success notification appears)

3. **Set Weekly Availability**
   - Scroll to "Weekly Availability" section
   - ✅ Verify you see a 7-day grid (Mon-Sun) with hourly time slots
   - Click and drag to select Monday 9:00 AM - 5:00 PM
     - Click on Monday 9:00 AM cell
     - Hold and drag down to 5:00 PM
     - ✅ Verify cells turn blue/primary color
   - Repeat for Wednesday 10:00 AM - 6:00 PM
   - ✅ Verify "Availability Summary" shows correct ranges:
     - Monday: 09:00 - 17:00
     - Wednesday: 10:00 - 18:00
   - Click "Save Schedule"
   - ✅ Verify success notification appears

4. **Add a Block Exception**
   - Scroll to "Exceptions & Blocks" section
   - Click "Add Exception"
   - Select:
     - Type: "Block Time"
     - Date: (choose a Monday 2 weeks from now)
     - Start Time: 11:00
     - End Time: 13:00
     - Reason: "Lunch meeting"
   - Click "Add"
   - ✅ Verify exception appears in the list with red "Blocked" badge

5. **Add Special Hours Exception**
   - Click "Add Exception" again
   - Select:
     - Type: "Special Hours"
     - Date: (choose a Tuesday 2 weeks from now)
     - Start Time: 14:00
     - End Time: 16:00
     - Reason: "Extra availability"
   - Click "Add"
   - ✅ Verify exception appears with green "Available" badge

6. **Verification**
   - Refresh the page
   - ✅ Verify all settings are persisted
   - ✅ Verify weekly schedule is displayed
   - ✅ Verify both exceptions are listed

**Expected Results:**
- All settings saved successfully
- Weekly schedule displayed correctly
- Exceptions created and visible
- No errors in browser console

---

## Test Scenario 2: Student Views Available Slots

### Objective
Verify that students can see teacher's available time slots and that exceptions are respected.

### Steps

1. **Access Booking Page**
   - Log in as a student
   - Navigate to "My Teachers"
   - Click on the teacher you just configured
   - ✅ Verify you're redirected to `/private-teaching/book/<teacher_id>/`
   - ✅ Verify you see "Book Lessons" heading (not "Request Lessons")

2. **Configure Booking Parameters**
   - Select a subject from the dropdown
   - ✅ Verify available subjects are listed with prices
   - Select lesson duration: "60 minutes"
   - Select location: "Online"
   - ✅ Verify calendar grid appears below

3. **View Weekly Calendar**
   - ✅ Verify calendar shows current week by default
   - ✅ Verify date range is displayed at top
   - Click "Next Week"
   - ✅ Verify week advances
   - Click "Today" button
   - ✅ Verify calendar returns to current week

4. **Verify Available Slots**
   - Navigate to a week that includes dates you configured
   - ✅ Verify available slots appear as green buttons on:
     - Monday (9:00 AM - 5:00 PM)
     - Wednesday (10:00 AM - 6:00 PM)
   - ✅ Verify NO slots appear on other days
   - Navigate to the Monday where you added 11:00-13:00 block
   - ✅ Verify those hours are NOT available (blocked exception working)
   - Navigate to the Tuesday where you added special hours
   - ✅ Verify 14:00-16:00 slots ARE available (available exception working)

5. **Check Booking Constraints**
   - Try to navigate to today's date
   - ✅ Verify slots within next 24 hours are NOT shown (min notice working)
   - Navigate 95 days into the future (if possible)
   - ✅ Verify no slots shown beyond 90-day window (max window working)

**Expected Results:**
- Calendar displays only available time slots
- Exceptions are properly reflected
- Booking constraints are enforced
- Time slots match teacher's configured availability

---

## Test Scenario 3: Student Books Multiple Lessons

### Objective
Verify that students can select multiple time slots and submit a booking request.

### Steps

1. **Select Time Slots**
   - Navigate to a week with available slots
   - Click on Monday 10:00 AM slot
   - ✅ Verify slot changes to blue/primary color
   - ✅ Verify "Selected Lessons" summary appears at bottom
   - Click on Monday 2:00 PM slot
   - Click on Wednesday 11:00 AM slot
   - ✅ Verify all 3 slots are highlighted
   - ✅ Verify summary shows "Selected Lessons (3)"

2. **Review Booking Summary**
   - Check the "Selected Lessons" card
   - ✅ Verify each lesson is listed with:
     - Date and time
     - Duration (60 minutes)
     - Price per lesson
   - ✅ Verify lessons are sorted chronologically
   - ✅ Verify total cost is calculated correctly:
     - Total = Price per lesson × 3

3. **Add Message**
   - Enter message: "Looking forward to lessons!"
   - ✅ Verify text appears in textarea

4. **Remove a Slot**
   - Click the X button on one of the selected lessons
   - ✅ Verify lesson is removed from summary
   - ✅ Verify slot color reverts to green in calendar
   - ✅ Verify total cost updates
   - Re-add the removed slot

5. **Submit Booking**
   - Click "Book Now" button
   - ✅ Verify button shows loading state
   - Wait for submission to complete
   - ✅ Verify redirect to "My Requests" page
   - ✅ Verify new lesson request appears in list
   - ✅ Verify success message is displayed

6. **Verify Created Lessons**
   - Click on the new lesson request
   - ✅ Verify all 3 lessons are listed
   - ✅ Verify each lesson shows:
     - Correct date and time
     - Correct duration
     - Correct subject
     - Location: Online
     - Status: "Accepted" (if auto-approve enabled) or "Pending"
     - Message appears in request details

**Expected Results:**
- Multi-slot selection works smoothly
- Cost calculation is accurate
- Booking submission succeeds
- Lessons are created correctly
- Auto-approval works (if enabled)

---

## Test Scenario 4: Availability Conflicts

### Objective
Verify that the system prevents double-booking and respects buffer time.

### Steps

1. **Create First Booking**
   - As student, book Monday 10:00 AM (60 min) lesson
   - ✅ Verify booking succeeds

2. **Attempt Double Booking**
   - Return to booking page
   - Try to select Monday 10:00 AM again
   - ✅ Verify slot is NO LONGER available (grayed out or hidden)
   - Try to select Monday 10:30 AM (overlapping time)
   - ✅ Verify slot is NO LONGER available

3. **Test Buffer Time**
   - If teacher set 15-minute buffer:
   - Try to book Monday 11:00 AM (immediately after 10:00-11:00 lesson)
   - ✅ Verify slot is NOT available (buffer time working)
   - Try to book Monday 11:15 AM
   - ✅ Verify slot IS available (respects buffer)

4. **Verify in Teacher View**
   - Log in as teacher
   - Go to "Incoming Requests" or "Schedule"
   - ✅ Verify the booked lesson appears
   - ✅ Verify time slot shows as occupied

**Expected Results:**
- System prevents double-booking
- Buffer time is enforced correctly
- Occupied slots are hidden from students
- Teacher can see booked lessons

---

## Test Scenario 5: Toggle Calendar On/Off

### Objective
Verify that disabling the calendar reverts to traditional booking flow.

### Steps

1. **Disable Calendar (Teacher)**
   - Log in as teacher
   - Go to Availability Editor
   - Toggle "Enable Availability Calendar" to OFF
   - ✅ Verify success notification
   - ✅ Verify weekly schedule and exceptions sections are hidden

2. **Verify Student View (Traditional Form)**
   - Log in as student
   - Navigate to book with teacher page
   - ✅ Verify heading is "Request Lessons" (not "Book Lessons")
   - ✅ Verify traditional form is displayed
   - ✅ Verify NO calendar grid is shown
   - ✅ Verify form has manual date/time input fields

3. **Re-enable Calendar**
   - Log in as teacher
   - Toggle "Enable Availability Calendar" to ON
   - Log in as student
   - ✅ Verify calendar interface returns

**Expected Results:**
- Calendar can be toggled on/off
- Student view changes accordingly
- Settings are preserved when re-enabled

---

## Test Scenario 6: API Endpoint Testing

### Objective
Verify that REST API endpoints work correctly.

### Steps

1. **Test Available Slots API**
   - Open browser dev tools
   - Navigate to student booking page (with calendar enabled)
   - Open Network tab
   - Select a subject and change date range
   - ✅ Verify API call to `/private-teaching/api/student/available-slots/`
   - ✅ Verify response contains array of slots with:
     - `datetime`
     - `duration`
     - `available`
     - `end_datetime`
   - ✅ Verify HTTP 200 status

2. **Test Booking Submission API**
   - Select time slots
   - Open Network tab
   - Click "Book Now"
   - ✅ Verify POST request to `/private-teaching/api/student/submit-booking/`
   - ✅ Verify request payload contains:
     - `teacher_id`
     - `subject_id`
     - `location`
     - `message`
     - `lessons` array with datetime and duration
   - ✅ Verify response contains:
     - `success: true`
     - `lesson_request_id`
     - `redirect_url`
   - ✅ Verify HTTP 200 status

3. **Test Teacher Availability API (logged in as teacher)**
   - Open `/private-teaching/api/teacher-availability/` in browser
   - ✅ Verify JSON response with teacher's availability slots
   - Open `/private-teaching/api/availability-exceptions/`
   - ✅ Verify JSON response with exceptions
   - Open `/private-teaching/api/availability-settings/my_settings/`
   - ✅ Verify JSON response with settings

**Expected Results:**
- All API endpoints return valid JSON
- Authentication is enforced
- Data matches database state

---

## Test Scenario 7: Error Handling

### Objective
Verify that errors are handled gracefully.

### Steps

1. **No Subject Selected**
   - Go to student booking page
   - Try to select a time slot without selecting a subject
   - ✅ Verify message: "Please select a subject to view available time slots"

2. **Empty Booking**
   - Select a subject but no time slots
   - ✅ Verify "Book Now" button is not shown

3. **Slot Becomes Unavailable**
   - (Advanced) Simulate race condition:
     - Open booking page in two browser windows as different students
     - Select same slot in both
     - Submit in first window
     - Submit in second window
   - ✅ Verify second submission fails with error message

4. **Network Error**
   - Open dev tools
   - Enable offline mode
   - Try to submit booking
   - ✅ Verify error message is displayed

**Expected Results:**
- User-friendly error messages
- No crashes or blank pages
- Graceful degradation

---

## Test Scenario 8: Mobile Responsiveness

### Objective
Verify that calendar interfaces work on mobile devices.

### Steps

1. **Teacher Availability Editor**
   - Open teacher availability editor
   - Resize browser to mobile width (< 768px) or use device emulator
   - ✅ Verify weekly grid is horizontally scrollable
   - ✅ Verify settings form stacks vertically
   - ✅ Verify buttons remain accessible

2. **Student Booking Calendar**
   - Open student booking page
   - Resize to mobile width
   - ✅ Verify calendar grid is scrollable
   - ✅ Verify date navigation works
   - ✅ Verify summary card is readable
   - ✅ Verify "Book Now" button is accessible

**Expected Results:**
- Interfaces are usable on small screens
- No horizontal overflow
- Touch interactions work
- Content remains readable

---

## Bug Tracking Template

Use this template to report any issues found during testing:

```markdown
### Bug Report

**Test Scenario:** [Scenario number and name]
**Step:** [Step number where issue occurred]
**Severity:** [Critical/High/Medium/Low]

**Description:**
[Clear description of what went wrong]

**Expected Behavior:**
[What should have happened]

**Actual Behavior:**
[What actually happened]

**Steps to Reproduce:**
1. [First step]
2. [Second step]
3. [...]

**Screenshots/Errors:**
[Paste screenshots or console errors]

**Environment:**
- Browser: [Browser and version]
- User Role: [Teacher/Student]
- Date/Time: [When you tested]
```

---

## Success Criteria

Phase 1 implementation is considered successful if:

- ✅ All 8 test scenarios pass without critical errors
- ✅ Teacher can configure availability calendar
- ✅ Student can view and book available slots
- ✅ Booking constraints (buffer, notice, window) are enforced
- ✅ Exceptions (blocks and special hours) work correctly
- ✅ Auto-approval works when enabled
- ✅ System prevents double-booking
- ✅ Traditional booking still works when calendar is disabled
- ✅ API endpoints return correct data
- ✅ Interfaces are responsive
- ✅ No major errors in browser console

---

## Next Steps After Testing

1. **Document Issues:** Use bug tracking template for any failures
2. **Fix Critical Bugs:** Address blocking issues before Phase 2
3. **Gather Feedback:** Share with test users for UX feedback
4. **Plan Phase 2:** Begin planning notification system and analytics

---

## Developer Notes

### Database Queries to Verify Data

```sql
-- Check teacher availability settings
SELECT * FROM private_teaching_teacheravailabilitysettings WHERE teacher_id = [TEACHER_ID];

-- Check weekly availability
SELECT * FROM private_teaching_teacheravailability WHERE teacher_id = [TEACHER_ID] ORDER BY day_of_week, start_time;

-- Check exceptions
SELECT * FROM private_teaching_availabilityexception WHERE teacher_id = [TEACHER_ID] ORDER BY date;

-- Check created lessons
SELECT * FROM lessons_lesson WHERE teacher_id = [TEACHER_ID] ORDER BY lesson_date, lesson_time;
```

### Console Debugging

```javascript
// In browser console on student booking page
// Check loaded availability data
window.Alpine.data('calendarBooking')().availableSlots

// Check selected slots
window.Alpine.data('calendarBooking')().selectedSlots

// Check settings
window.Alpine.data('calendarBooking')().settings
```

---

## Test Completion Checklist

- [ ] Scenario 1: Teacher Sets Up Availability Calendar
- [ ] Scenario 2: Student Views Available Slots
- [ ] Scenario 3: Student Books Multiple Lessons
- [ ] Scenario 4: Availability Conflicts
- [ ] Scenario 5: Toggle Calendar On/Off
- [ ] Scenario 6: API Endpoint Testing
- [ ] Scenario 7: Error Handling
- [ ] Scenario 8: Mobile Responsiveness
- [ ] All bugs documented
- [ ] Phase 1 sign-off obtained

---

**Testing Date:** _________________
**Tester Name:** _________________
**Sign-off:** _________________
