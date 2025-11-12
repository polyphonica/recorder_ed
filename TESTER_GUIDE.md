# Recorder-Ed Testing Guide

Thank you for helping test the Recorder-Ed platform! This guide will walk you through creating an account and testing key features.

## Getting Started

### 1. Create Your Account
- Go to: **https://www.recorder-ed.com/**
- Click **Sign Up** or go directly to https://www.recorder-ed.com/accounts/signup/
- Enter your email and create a password
- Complete your profile with your details

**Note for Guardian Testing:**
- If you want to test as a parent/guardian managing a child's account, check the "I am a guardian" box during signup
- You'll need to provide child details (name, date of birth)

### 2. Complete Your Profile
After signing up, you'll be prompted to complete your profile:
- Add your name, phone number, address
- Upload a profile picture (optional)
- Save your profile

## What to Test

### Private Teaching Domain
Test the private lesson request workflow:

1. **Browse Teachers**
   - Navigate to the Private Teaching section
   - Browse available teachers by instrument/specialty
   - View teacher profiles, bios, and availability

2. **Apply to Study with a Teacher**
   - Select a teacher you'd like to study with
   - Submit an application
   - Wait for acceptance (may require admin approval for testing)

3. **Request and Pay for Lessons**
   - Once accepted, request a lesson
   - Select date/time preferences
   - Proceed to payment

### Workshops Domain
Test workshop registration:

1. **Browse Workshops**
   - Navigate to Workshops section
   - Search and filter by category/instrument
   - View workshop details (dates, times, instructor, capacity)

2. **Register for a Workshop**
   - Select a workshop session
   - Complete registration form
   - Proceed to payment

3. **Test Waitlist** (if applicable)
   - Try registering for a full workshop
   - Verify waitlist functionality

### Courses Domain
Test course enrollment:

1. **Browse Courses**
   - Navigate to Courses section
   - View available courses and descriptions

2. **Enroll in a Course**
   - Select a course
   - Complete enrollment
   - Proceed to payment

3. **Access Course Content**
   - View enrolled courses in your dashboard
   - Check course progress tracking
   - Test messaging with instructor (if available)

## Payment Testing

**IMPORTANT:** The system is in **TEST MODE** - no real charges will be made.

Use these **Stripe test card numbers**:

### Successful Payment
- **Card Number:** `4242 4242 4242 4242`
- **Expiry:** Any future date (e.g., 12/25)
- **CVC:** Any 3 digits (e.g., 123)
- **ZIP:** Any 5 digits (e.g., 12345)

### Test Different Scenarios
- **Card Declined:** `4000 0000 0000 0002`
- **Insufficient Funds:** `4000 0000 0000 9995`
- **Processing Error:** `4000 0000 0000 0119`

## What We're Looking For

Please test and provide feedback on:

### Usability
- Is the signup/registration process clear and easy?
- Can you navigate the site intuitively?
- Are instructions and labels clear?
- Any confusing workflows or unclear steps?

### Functionality
- Does everything work as expected?
- Any errors or broken features?
- Do payments process correctly (with test cards)?
- Are confirmation emails being sent?

### Design & Experience
- Is the site visually appealing?
- Does it work well on your device (desktop/tablet/mobile)?
- Any layout issues or display problems?
- Loading speed acceptable?

### Specific Issues to Report
- Error messages encountered
- Features that don't work
- Confusing or unclear interface elements
- Suggestions for improvement

## Reporting Feedback

Please provide feedback on:
1. **What worked well**
2. **What didn't work or was confusing**
3. **Any errors or bugs encountered**
4. **Suggestions for improvement**

Include screenshots if possible when reporting issues!

## Need Help?

If you encounter any blocking issues during testing, please reach out with:
- What you were trying to do
- What happened instead
- Any error messages (screenshots helpful)
- Your browser and device type

---

**Thank you for helping make Recorder-Ed better!**
