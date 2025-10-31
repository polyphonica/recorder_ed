# RECORDERED Platform Testing Guide

## Test Environment Setup

### Required Test Accounts
Create these accounts for comprehensive testing:

**Teachers:**
- Teacher 1: Adult private lessons & workshops
- Teacher 2: Course creator
- Teacher 3: Handles both children and adults

**Students:**
- Adult Student 1: Tests private lessons
- Adult Student 2: Tests workshops and courses
- Guardian 1: Has 2 child profiles (ages 8 and 12)
- Guardian 2: Has 1 child profile (age 10)

---

## Domain 1: PRIVATE TEACHING

### Content to Create (As Teacher):

**1. Teacher Profile Setup**
- Complete profile with bio, photo, experience
- Set max students: 10
- Enable "Accepting new students"

**2. Subjects & Pricing**
Create at least 3 subjects:
- Recorder - Beginner (£25/lesson)
- Recorder - Intermediate (£30/lesson)  
- Recorder - Advanced (£35/lesson)

**3. Availability**
Set realistic availability for next 2 weeks

---

### Test Scenarios - Private Teaching

#### **Scenario PT-1: Student Application & Acceptance (Happy Path)**
**Role:** Adult Student 1
1. Browse teachers
2. Click "Apply to Study"
3. Write application message
4. Submit application
5. **Expected:** Application appears in "My Applications"

**Role:** Teacher
6. View incoming applications
7. Accept application with welcome message
8. **Expected:** Student appears in "My Students"
9. **Expected:** Email sent to student

**Role:** Adult Student 1
10. **Expected:** See acceptance in dashboard
11. **Expected:** Receive acceptance email

**Success Criteria:**
- ✅ Application system works end-to-end
- ✅ Emails sent correctly
- ✅ Status updates properly

---

#### **Scenario PT-2: Lesson Request & Payment (Happy Path)**
**Role:** Adult Student 1 (accepted student)
1. Click "Request Lessons"
2. Select subject: Recorder - Beginner
3. Request 3 lessons:
   - Lesson 1: Next Monday, 3:00 PM
   - Lesson 2: Next Wednesday, 3:00 PM
   - Lesson 3: Next Friday, 3:00 PM
4. Add message: "Looking forward to learning!"
5. Submit request
6. **Expected:** Request appears in "My Requests"

**Role:** Teacher
7. View incoming lesson requests
8. Accept all 3 lessons
9. Add message: "See you Monday!"
10. **Expected:** Email sent to student
11. **Expected:** Lessons appear in teacher calendar

**Role:** Adult Student 1
12. **Expected:** Receive acceptance email
13. Click "Add All to Cart"
14. Review cart (total: £75.00)
15. Click "Checkout"
16. Complete Stripe payment (test card: 4242...)
17. **Expected:** Redirect to success page
18. **Expected:** Order status: "completed"
19. **Expected:** Lessons status: "Paid"
20. **Expected:** Receive payment confirmation email
21. View calendar - see all 3 lessons

**Role:** Teacher
22. View calendar - see all 3 lessons
23. Click lesson 1 - update to "Assigned" status
24. **Expected:** Student receives "lesson ready" email

**Success Criteria:**
- ✅ Complete payment flow works
- ✅ Webhook updates order/lessons
- ✅ Confirmation email received
- ✅ Calendar shows lessons for both parties
- ✅ Commission calculated (10%)
- ✅ Platform receives £7.50, teacher receives £67.50

---

#### **Scenario PT-3: Guardian Applying for Child**
**Role:** Guardian 1
1. Complete profile setup
2. Add child profile: "Emma, age 8"
3. Apply to teacher on behalf of child
4. Select child from dropdown
5. Submit application

**Role:** Teacher
6. Accept child application
7. **Expected:** Email to guardian (not child)

**Role:** Guardian 1
8. Request lessons for Emma
9. Select child profile
10. Add lessons to cart and pay
11. **Expected:** Guardian pays, lessons registered to child

**Success Criteria:**
- ✅ Guardian can manage child profiles
- ✅ Lessons associated with correct child
- ✅ Emails go to guardian

---

#### **Scenario PT-4: Multiple Lessons from Different Teachers**
**Role:** Adult Student 2
1. Apply to Teacher 1 and Teacher 2
2. Get accepted by both
3. Request lessons from Teacher 1 (2 lessons, £50)
4. Request lessons from Teacher 2 (2 lessons, £60)
5. Both teachers accept
6. Add all to cart (total: £110)
7. Checkout and pay

**Expected:**
- ✅ Cart handles multiple teachers
- ✅ Single payment for all lessons
- ✅ Commission calculated per teacher
- ✅ Each teacher sees only their lessons

---

#### **Scenario PT-5: Teacher Rejecting Lessons**
**Role:** Teacher
1. Receive lesson request
2. Reject 2 out of 3 lessons
3. Add message explaining why

**Role:** Student
4. **Expected:** Receive rejection email
5. **Expected:** Only accepted lessons in cart
6. **Expected:** Can request new dates

---

#### **Scenario PT-6: Student Waitlisting**
**Role:** Teacher
1. Set max students: 5
2. Accept 5 students

**Role:** Student (6th applicant)
3. Apply to teacher
4. **Expected:** Application received

**Role:** Teacher
5. Waitlist the 6th application
6. Add message: "Full now, will contact in January"

**Role:** Student
7. **Expected:** Receive waitlist email
8. **Expected:** Cannot request lessons yet

---

## Domain 2: WORKSHOPS

### Content to Create (As Teacher):

**1. Workshop Categories**
Create 2-3 categories:
- Beginner Workshops
- Advanced Techniques
- Ensemble Playing

**2. Workshop Sessions**
Create 3 workshops:

**Workshop A: "Introduction to Recorder"**
- Date: 2 weeks from now
- Time: 10:00 AM - 12:00 PM
- Max participants: 8
- Price: £45
- Description: Perfect for beginners...

**Workshop B: "Advanced Techniques"**
- Date: 3 weeks from now
- Time: 2:00 PM - 5:00 PM
- Max participants: 6
- Price: £65
- Description: For experienced players...

**Workshop C: "Full Workshop"** (for testing waitlist)
- Max participants: 2
- Register 2 students immediately

---

### Test Scenarios - Workshops

#### **Scenario W-1: Browse & Register (Happy Path)**
**Role:** Adult Student
1. Navigate to Workshops
2. Browse workshop categories
3. Click "Introduction to Recorder"
4. Read description, date, time, price
5. Click "Register"
6. Complete registration form
7. **Expected:** Registration confirmation
8. **Expected:** Email confirmation (if payment not required)

**Success Criteria:**
- ✅ Workshop details clear
- ✅ Registration process smooth
- ✅ Confirmation received

---

#### **Scenario W-2: Guardian Registering Child**
**Role:** Guardian 1
1. Browse workshops
2. Select "Introduction to Recorder"
3. Click "Register"
4. Select child: "Emma, age 8"
5. Complete registration

**Expected:**
- ✅ Child associated with registration
- ✅ Guardian email for confirmations

---

#### **Scenario W-3: Workshop at Capacity / Waitlist**
**Role:** Adult Student
1. Try to register for "Full Workshop"
2. **Expected:** See "Workshop Full" or "Join Waitlist" option
3. Join waitlist if available
4. **Expected:** Waitlist confirmation

**Role:** Teacher
5. Cancel one registration
6. **Expected:** First waitlist person notified (if implemented)

---

#### **Scenario W-4: Multiple Registrations**
**Role:** Guardian 2
1. Register self for "Introduction to Recorder"
2. Register child for same workshop
3. **Expected:** 2 separate registrations
4. **Expected:** Both names on registration list

---

#### **Scenario W-5: Workshop Cancellation (If Implemented)**
**Role:** Teacher
1. Cancel workshop
2. **Expected:** All registered participants notified
3. **Expected:** Refunds processed (if paid)

---

## Domain 3: COURSES

### Content to Create (As Teacher):

**1. Create Course Structure**

**Course A: "Beginner Recorder Course"**
- Description: 6-week beginner course
- Price: £120
- Max students: 12

**Topics (3):**
- Week 1-2: Getting Started
- Week 3-4: First Songs
- Week 5-6: Playing Together

**Lessons (6):**
- Lesson 1: Your First Notes
- Lesson 2: Reading Music
- Lesson 3: Simple Songs
- Lesson 4: Rhythm Practice
- Lesson 5: Duets
- Lesson 6: Final Performance

**Content for Each Lesson:**
- Video or text content
- 2-3 documents (PDFs, sheet music)
- 1-2 external links
- 1 quiz with 3-5 questions

**Course B: "Advanced Techniques"**
- 4 topics, 8 lessons
- Price: £180
- Prerequisite: Beginner course (for testing)

---

### Test Scenarios - Courses

#### **Scenario C-1: Course Enrollment (Happy Path)**
**Role:** Adult Student
1. Navigate to Courses
2. Browse course catalog
3. Click "Beginner Recorder Course"
4. Read course description
5. Click "Enroll"
6. **Expected:** Enrollment confirmation
7. **Expected:** Course appears in "My Courses"

**Success Criteria:**
- ✅ Course details clear
- ✅ Enrollment process smooth
- ✅ Access to course content

---

#### **Scenario C-2: Course Progress Tracking**
**Role:** Adult Student (enrolled)
1. Open "Beginner Recorder Course"
2. Navigate to Lesson 1
3. Watch/read content
4. Download PDF documents
5. Click external links
6. Mark lesson as complete
7. **Expected:** Progress bar updates
8. Complete quiz
9. **Expected:** Quiz results shown
10. **Expected:** Progress percentage increases
11. Complete all 6 lessons
12. **Expected:** Course marked as completed
13. **Expected:** Certificate available (if implemented)

**Success Criteria:**
- ✅ Content accessible
- ✅ Progress tracked accurately
- ✅ Quiz functionality works
- ✅ Completion tracked

---

#### **Scenario C-3: Guardian Enrolling Child**
**Role:** Guardian 1
1. Browse courses
2. Enroll child "Emma" in Beginner course
3. **Expected:** Course appears in child's dashboard
4. **Expected:** Guardian can monitor progress

---

#### **Scenario C-4: Course with Prerequisites**
**Role:** Adult Student (not completed beginner)
1. Try to enroll in "Advanced Techniques"
2. **Expected:** See prerequisite warning
3. **Expected:** Cannot enroll yet

**Role:** Same Student (completed beginner)
4. Complete Beginner course
5. Try to enroll in "Advanced Techniques"
6. **Expected:** Can now enroll

---

#### **Scenario C-5: Instructor Analytics**
**Role:** Teacher/Instructor
1. Navigate to course management
2. View "Beginner Recorder Course"
3. Check enrollment numbers
4. View student progress:
   - Who completed lessons
   - Quiz scores
   - Overall progress percentage
5. Send message to all enrolled students (if implemented)

---

## Cross-Domain Scenarios

#### **Scenario X-1: Multi-Domain Student Journey**
**Role:** Adult Student
1. Enroll in "Beginner Recorder Course" (Courses)
2. Complete 3 lessons
3. Register for "Introduction" workshop (Workshops)
4. Apply for private lessons (Private Teaching)
5. Get accepted, request lessons
6. Pay for private lessons
7. View unified calendar showing:
   - Course deadlines
   - Workshop date
   - Private lesson times

**Expected:**
- ✅ Seamless experience across domains
- ✅ Calendar shows all commitments
- ✅ Profile consistent across domains

---

#### **Scenario X-2: Teacher Managing Multiple Domains**
**Role:** Teacher
1. Check Private Teaching applications
2. Review workshop registrations
3. Monitor course enrollments
4. View income across all three domains (when revenue dashboard is built)

---

## Account Management Scenarios

#### **Scenario A-1: Profile Management**
**Role:** Any user
1. Update profile photo
2. Change contact information
3. Update bio (if teacher)
4. **Expected:** Changes reflected everywhere

---

#### **Scenario A-2: Password Reset**
1. Logout
2. Click "Forgot Password"
3. Enter email
4. **Expected:** Reset email received
5. Follow link, set new password
6. Login with new password

---

#### **Scenario A-3: Email Verification** (If Implemented)
1. Sign up new account
2. **Expected:** Verification email sent
3. Click verification link
4. **Expected:** Account activated

---

## Payment & Financial Scenarios

#### **Scenario F-1: Refund Process** (If Implemented)
**Role:** Teacher/Admin
1. Process refund for a paid lesson
2. **Expected:** Stripe refund created
3. **Expected:** Student notified
4. **Expected:** Lesson status updated

---

#### **Scenario F-2: Platform Commission Tracking**
**Role:** Admin
1. View all transactions
2. Filter by teacher
3. Calculate total commission
4. Verify 10% applied correctly

---

## Edge Cases & Error Handling

#### **Error E-1: Payment Failure**
1. Student completes checkout
2. Use declining test card: `4000 0000 0000 0002`
3. **Expected:** Payment declined gracefully
4. **Expected:** Clear error message
5. **Expected:** Can retry with different card

---

#### **Error E-2: Network Timeout**
1. Start checkout process
2. Close browser mid-payment
3. Return to site
4. **Expected:** Order exists but pending
5. **Expected:** Can complete or cancel

---

#### **Error E-3: Duplicate Lesson Request**
1. Student requests lessons
2. Try to request same date/time again
3. **Expected:** Validation prevents duplicates

---

## Test Data Summary

### Create This Content:

**Private Teaching:**
- 3 teachers with complete profiles
- 3 subjects each with pricing
- 5 accepted students per teacher

**Workshops:**
- 5 workshops in next 2 months
- Mix of available/full/past workshops
- 2-3 categories

**Courses:**
- 2 complete courses:
  - Beginner (6 lessons)
  - Advanced (8 lessons) with prerequisite
- Each lesson with content, PDFs, quizzes

**Users:**
- 5 adult students
- 3 guardians (with 4 total children)
- 3 teachers (who also run workshops/courses)

---

## Test Execution Tracking

Use this checklist:

### Private Teaching
- [ ] PT-1: Application & Acceptance
- [ ] PT-2: Lesson Request & Payment
- [ ] PT-3: Guardian for Child
- [ ] PT-4: Multiple Teachers
- [ ] PT-5: Teacher Rejecting
- [ ] PT-6: Waitlisting

### Workshops
- [ ] W-1: Browse & Register
- [ ] W-2: Guardian Registering Child
- [ ] W-3: Workshop at Capacity
- [ ] W-4: Multiple Registrations
- [ ] W-5: Cancellation

### Courses
- [ ] C-1: Course Enrollment
- [ ] C-2: Progress Tracking
- [ ] C-3: Guardian Enrolling Child
- [ ] C-4: Prerequisites
- [ ] C-5: Instructor Analytics

### Cross-Domain
- [ ] X-1: Multi-Domain Journey
- [ ] X-2: Teacher Multi-Domain

### Accounts
- [ ] A-1: Profile Management
- [ ] A-2: Password Reset
- [ ] A-3: Email Verification

### Payments
- [ ] F-1: Refunds
- [ ] F-2: Commission Tracking

### Errors
- [ ] E-1: Payment Failure
- [ ] E-2: Network Timeout
- [ ] E-3: Duplicate Request

---

## Success Metrics

After testing, you should have:

**Functionality:**
- ✅ All critical paths working
- ✅ No broken links or 500 errors
- ✅ All emails sending correctly
- ✅ Payments processing successfully

**User Experience:**
- ✅ Intuitive navigation
- ✅ Clear error messages
- ✅ Mobile-friendly (test on phone)
- ✅ Fast load times

**Data Integrity:**
- ✅ Commission calculated correctly (10%)
- ✅ No orphaned records
- ✅ Proper cascade on deletions
- ✅ Audit trail of all transactions

---

## Beta Tester Instructions

### For Testers:

**You will receive:**
- Test account credentials
- This testing guide
- Bug report template

**Please test:**
1. Your assigned scenarios
2. General navigation and usability
3. Mobile responsiveness (if you can)
4. Any edge cases you think of

**Report issues with:**
- What you were doing
- What you expected
- What actually happened
- Screenshots if possible

**Test cards for Stripe:**
- Success: `4242 4242 4242 4242`
- Decline: `4000 0000 0000 0002`
- Expiry: Any future date
- CVC: Any 3 digits

---

## Post-Testing Checklist

Before going live:

- [ ] All critical bugs fixed
- [ ] Payment flow tested end-to-end 10+ times
- [ ] Emails received in all scenarios
- [ ] Mobile experience acceptable
- [ ] Load testing completed (if expecting traffic)
- [ ] Backup procedures tested
- [ ] Stripe switched to LIVE mode
- [ ] Terms of Service added
- [ ] Privacy Policy added
- [ ] Contact/support page added
- [ ] Analytics installed (Google Analytics, etc.)

