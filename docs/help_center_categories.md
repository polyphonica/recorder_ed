# Recommended Help Center Categories for Recorder-ed

This document outlines the recommended category structure for the Help Center, including suggested articles for each category.

---

## 1. 🚀 Getting Started

**Icon:** `fa-solid fa-rocket`
**Description:** New to Recorder-ed? Start here for setup guides and platform basics.
**Target:** All users (students & teachers)
**Order:** 1

### Suggested Articles:
- Welcome to Recorder-ed
- How to create an account
- How to complete your profile
- Platform overview and navigation
- How to apply to become a teacher

---

## 2. 🎓 Courses

**Icon:** `fa-solid fa-graduation-cap`
**Description:** Help with enrolling, accessing, and completing online courses.
**Target:** Students
**Order:** 2

### Suggested Articles:
- How to enroll in a course
- How to access my enrolled courses
- How to track my course progress
- How to download course materials
- How to message my course instructor
- Understanding course certificates
- 7-day trial period and refunds
- How to mark a lesson as complete
- Accessing quizzes and assessments
- Using the play-along audio player

---

## 3. 🎪 Workshops

**Icon:** `fa-solid fa-users`
**Description:** Workshop bookings, sessions, and group learning.
**Target:** Students
**Order:** 3

### Suggested Articles:
- How to book a workshop
- How to find workshops near me / online
- Workshop cancellation and refund policy
- What to bring to a workshop
- How to access workshop materials
- Workshop attendance requirements
- Understanding workshop age restrictions
- Booking workshops for children

---

## 4. 🎹 Private Lessons

**Icon:** `fa-solid fa-music`
**Description:** Booking private lessons and managing your learning schedule.
**Target:** Students
**Order:** 4

### Suggested Articles:
- How to book a private lesson
- How to find a teacher
- How to reschedule or cancel a lesson
- Private lesson cancellation policy
- How to message your teacher
- How to access lesson materials
- Booking lessons for children
- Setting up a child profile
- Online vs in-person lessons
- Preparing for your first lesson

---

## 5. 👨‍🏫 Teaching on Recorder-ed

**Icon:** `fa-solid fa-chalkboard-teacher`
**Description:** Guides for teachers managing courses, workshops, and private lessons.
**Target:** Teachers
**Order:** 5

### Suggested Articles:
- How to create a course
- How to add lessons and topics to my course
- How to create a workshop
- How to set my availability for private lessons
- How to manage student enrollments
- How to view my earnings and payments
- How to handle cancellation requests
- How to message students
- Best practices for online teaching
- Using the quiz builder
- Adding play-along audio to lessons
- Managing course terms and conditions
- Publishing vs draft courses
- Understanding "Coming Soon" courses
- Setting up your teacher profile

---

## 6. 💳 Payments & Billing

**Icon:** `fa-solid fa-credit-card`
**Description:** Payment methods, invoices, refunds, and financial questions.
**Target:** Students & Teachers
**Order:** 6

### Suggested Articles:

#### For Students:
- What payment methods do you accept?
- How do I get a refund?
- Where can I find my invoices?
- Understanding your receipt
- Failed payment - what to do?
- Refund processing times
- 7-day trial period for courses
- Cancellation policies by product type

#### For Teachers:
- How do I get paid?
- Payment schedule and thresholds
- Setting up your payment details
- Understanding teacher earnings
- Viewing payment history
- Tax information for teachers

---

## 7. 👤 Account & Profile

**Icon:** `fa-solid fa-user-circle`
**Description:** Managing your account settings, profile, and preferences.
**Target:** All users
**Order:** 7

### Suggested Articles:

#### General Account Management:
- How to update my profile
- How to change my password
- How to reset a forgotten password
- How to add a profile photo
- Managing email notifications
- How to close my account
- Privacy and data settings
- Switching between student and teacher roles

#### Parent/Guardian & Children:
- Setting up a child profile
- How to manage child accounts as a parent
- Adding multiple children to your account
- Booking courses for children
- Booking workshops for children
- Booking private lessons for children
- Understanding child data protection
- Viewing your child's progress
- Managing child profile information
- Age restrictions and requirements
- Parental consent and terms

---

## 8. 🔧 Technical Support

**Icon:** `fa-solid fa-wrench`
**Description:** Troubleshooting technical issues and browser compatibility.
**Target:** All users
**Order:** 8

### Suggested Articles:
- Supported browsers and devices
- Video playback issues
- Audio player troubleshooting
- Can't log in - troubleshooting
- Upload errors and file size limits
- Browser cache and cookies
- Mobile device compatibility
- Slow loading times
- CKEditor rich text issues (for teachers)
- File attachment problems
- Email delivery issues
- Session timeout problems

---

## 9. 📜 Policies & Terms (Optional)

**Icon:** `fa-solid fa-file-contract`
**Description:** Platform policies, terms of service, and legal information.
**Target:** All users
**Order:** 9

### Suggested Articles:
- Terms and Conditions
- Privacy Policy
- Refund Policy
- Cancellation Policy
- Code of Conduct for Students
- Code of Conduct for Teachers
- Copyright and Content Policy
- GDPR and Data Protection
- Cookie Policy
- Child Protection Policy
- Teacher Application Requirements
- Acceptable Use Policy

---

## Implementation Priority

Start with these **essential categories** first:

1. ✅ **Getting Started** (most important for new users)
2. ✅ **Courses** (your main product)
3. ✅ **Payments & Billing** (reduces support tickets)
4. ✅ **Account & Profile** (common questions, especially parent/child management)

Then add the others as you have time and see what questions come up frequently:

5. **Private Lessons** (if this is a popular offering)
6. **Workshops** (if this is a popular offering)
7. **Teaching on Recorder-ed** (for teacher onboarding)
8. **Technical Support** (as technical issues arise)
9. **Policies & Terms** (can link to existing policy pages)

---

## How to Add Categories in Django Admin

1. Navigate to `/admin/help_center/category/`
2. Click **"Add Category"**
3. Fill in the fields:
   - **Name:** Copy from the category heading (e.g., "Getting Started")
   - **Slug:** Will auto-generate from the name
   - **Description:** Copy the description text
   - **Icon:** Copy the Font Awesome class (e.g., `fa-solid fa-rocket`)
   - **Order:** Use the order number listed above (1-9)
   - **Is active:** ✓ Check this box to make it visible
4. Click **Save**

---

## Article Writing Tips

When creating articles:

1. **Use clear, descriptive titles** starting with "How to..."
2. **Add step-by-step instructions** with numbered lists
3. **Include screenshots** where helpful (upload via CKEditor)
4. **Write in simple language** - avoid jargon
5. **Add a summary** for the article listing pages
6. **Mark important articles as promoted** to show on homepage
7. **Update articles** when features change
8. **Monitor view counts** to see what's popular
9. **Check helpfulness scores** to identify articles that need improvement

---

## Promoting Articles

Use the **"Is promoted"** checkbox for these types of articles:
- Most frequently asked questions
- New feature announcements
- Important policy changes
- Getting started guides
- Popular how-to articles

Promoted articles appear on the Help Center homepage for easy discovery.

---

## Notes

- Categories can be reordered by changing the **Order** field
- Inactive categories won't show on the site but remain in admin
- Each category automatically shows its article count
- Articles must be set to **"Published"** status to be visible
- Use the search function to help users find articles quickly
