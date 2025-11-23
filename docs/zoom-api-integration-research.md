# Zoom API Integration Research for RECORDER-ED
## Research Date: November 23, 2025

---

## Executive Summary

This document outlines the requirements, costs, and implementation considerations for integrating Zoom into the RECORDER-ED platform to provide teachers without paid Zoom accounts access to unlimited meeting capabilities through the platform's account.

### Key Findings:
- **Recommended Approach:** Zoom REST API for programmatic meeting creation
- **Estimated Base Cost:** $16.99/month per licensed user (Pro plan)
- **API Rate Limit:** 100 meetings per user per day
- **Best Use Case:** Automated meeting creation when lessons are booked

---

## 1. Integration Options Overview

### Option A: Zoom REST API (Recommended for RECORDER-ED)
**Purpose:** Server-side operations for managing meetings, users, and accounts programmatically

**What it does:**
- Creates, edits, and deletes meetings programmatically
- Manages users and webinars
- Provides access to post-meeting information for reporting and analytics
- Schedules and displays meeting information

**Best for:** Backend meeting management when lessons are booked on the platform

### Option B: Zoom Meeting SDK
**Purpose:** Client-side embedding of Zoom's meeting interface into your application

**What it does:**
- Embeds the familiar Zoom meeting interface directly in your website/app
- Provides either full Zoom interface (Client view) or modular Component view
- Maintains Zoom's familiar look while fitting into your layout

**Best for:** Embedding Zoom directly in the platform (more complex, less necessary for RECORDER-ED)

### Option C: Zoom Video SDK
**Purpose:** Fully custom video experiences with complete control

**What it does:**
- Provides Zoom's video, audio, and screen sharing as a service
- Allows complete customization of the video interface
- Supports up to 1,000 participants

**Best for:** Custom-branded video experiences (overkill for RECORDER-ED needs)

---

## 2. Recommended Solution: Zoom REST API

### Why This Approach?
For RECORDER-ED, the **Zoom REST API** is the optimal choice because:
1. ✅ Automatically creates meetings when lessons are booked
2. ✅ No need to embed video interface (teachers/students use regular Zoom)
3. ✅ Simpler implementation than SDK options
4. ✅ Lower cost than custom video solutions
5. ✅ Meetings hosted under platform account = no 40-minute limit for teachers
6. ✅ Platform can track, record (with consent), and monitor for safeguarding

### How It Works:
1. Student books a lesson with a teacher
2. Platform automatically creates Zoom meeting via API
3. Meeting is hosted under platform's licensed account
4. Both teacher and student receive unique join links
5. Meeting details stored with lesson record in database
6. No 40-minute time limit (uses platform's paid account)

---

## 3. Pricing Structure

### Base Zoom Plans (2025)

| Plan | Price | Meeting Duration | Participants | API Access |
|------|-------|------------------|--------------|------------|
| **Free** | $0 | 40 min (group), 24h (1-on-1) | 100 | Limited |
| **Pro** | $16.99/user/month or $159.90/year | 30 hours | 100 | ✅ Full |
| **Business** | $21.99/user/month or $219.90/year | 30 hours | 300 | ✅ Full |
| **Enterprise** | Custom pricing | 30 hours | 1,000 | ✅ Full |

### Cost Considerations for RECORDER-ED

#### Concurrent Meeting Requirements
**Critical:** Multiple concurrent meetings require multiple licenses.

**Example Scenarios:**
- **10 simultaneous lessons** = 10 licensed users needed = $169.90/month (Pro plan)
- **25 simultaneous lessons** = 25 licensed users needed = $424.75/month (Pro plan)
- **50 simultaneous lessons** = 50 licensed users needed = $849.50/month (Pro plan)

#### Scaling Cost Model
```
Monthly Cost = Number of Concurrent Meetings × $16.99
Annual Cost = Number of Concurrent Meetings × $159.90
```

**Note:** You only need licenses for the maximum number of simultaneous meetings, not total meetings per day/month.

### API Access Costs
**Good News:** API access is included with Pro, Business, and Enterprise plans at no additional cost.

**Exception:** Video SDK HIPAA compliance costs $14.99/month extra (not needed for standard teaching)

---

## 4. API Rate Limits

### Meeting Creation Limit
- **100 meetings per user per day** (create/update/delete combined)
- Limit resets at GMT 00:00:00 each day
- Applied per userId (meeting host)

### Impact on RECORDER-ED

**Example Calculation:**
- 5 licensed users = 500 meetings can be created per day
- 10 licensed users = 1,000 meetings can be created per day

**Important:** This limit applies to creation/scheduling, not conducting meetings. Once created, meetings can run without counting against the limit.

### Workaround Strategies
1. Distribute meeting creation across multiple licensed users
2. Create recurring meetings for regular weekly lessons (counts as 1 API call)
3. Pre-create meetings during off-peak times
4. Each licensed user account gets separate 100/day allocation

---

## 5. Authentication Requirements

### Server-to-Server OAuth (Recommended for RECORDER-ED)

**Why Server-to-Server?**
- No user interaction required for authentication
- Secure machine-to-machine communication
- Perfect for automated backend systems

**Required Credentials:**
1. **Account ID** - Your Zoom account identifier
2. **Client ID** - Application identifier
3. **Client Secret** - Secret key for authentication

### Setup Process
1. Sign in to Zoom App Marketplace
2. Navigate to "Develop" → "Build App"
3. Choose "Server-to-Server OAuth" app type
4. Define API scopes (meeting:read, meeting:write, user:read, etc.)
5. Activate the app with name and email
6. Receive credentials (Account ID, Client ID, Client Secret)

### Security Considerations
- Store credentials securely (environment variables, not in code)
- Use HTTPS for all API communications
- Rotate secrets periodically
- Implement proper error handling and logging

---

## 6. Implementation Requirements

### Technical Stack
**Backend (Django/Python):**
- HTTP client library (requests, httpx)
- Async support for better performance (optional but recommended)
- Database models for storing meeting details
- Celery or background tasks for API calls

### Required API Endpoints
```
POST /users/{userId}/meetings - Create meeting
GET /meetings/{meetingId} - Get meeting details
PATCH /meetings/{meetingId} - Update meeting
DELETE /meetings/{meetingId} - Delete meeting
GET /users/{userId}/meetings - List user's meetings
```

### Database Schema Additions
```python
# Suggested fields to add to Lesson model
zoom_meeting_id = models.CharField(max_length=255, null=True, blank=True)
zoom_join_url = models.URLField(null=True, blank=True)
zoom_start_url = models.URLField(null=True, blank=True)  # For host
zoom_meeting_password = models.CharField(max_length=50, null=True, blank=True)
zoom_host_user_id = models.CharField(max_length=255, null=True, blank=True)
```

### API Integration Flow
```
1. Lesson Booked
   ↓
2. Trigger Meeting Creation (Celery task)
   ↓
3. Select Licensed User (round-robin or least-loaded)
   ↓
4. Call Zoom API: POST /users/{userId}/meetings
   ↓
5. Store meeting details in database
   ↓
6. Send join links to teacher & student via email
   ↓
7. (Optional) Configure audio settings for music teaching
```

### Sample Python Implementation
```python
import requests
import base64
import time

class ZoomAPIClient:
    def __init__(self, account_id, client_id, client_secret):
        self.account_id = account_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.token_expiry = 0

    def get_access_token(self):
        """Get OAuth access token"""
        if self.access_token and time.time() < self.token_expiry:
            return self.access_token

        auth = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()

        response = requests.post(
            "https://zoom.us/oauth/token",
            headers={"Authorization": f"Basic {auth}"},
            params={
                "grant_type": "account_credentials",
                "account_id": self.account_id
            }
        )

        data = response.json()
        self.access_token = data['access_token']
        self.token_expiry = time.time() + data['expires_in'] - 60
        return self.access_token

    def create_meeting(self, user_id, topic, start_time, duration=60):
        """Create a Zoom meeting"""
        token = self.get_access_token()

        response = requests.post(
            f"https://api.zoom.us/v2/users/{user_id}/meetings",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json={
                "topic": topic,
                "type": 2,  # Scheduled meeting
                "start_time": start_time,  # ISO 8601 format
                "duration": duration,
                "settings": {
                    "host_video": True,
                    "participant_video": True,
                    "join_before_host": False,
                    "mute_upon_entry": True,
                    "waiting_room": True,
                    "audio": "both",  # voip and telephony
                    "auto_recording": "none",  # or "cloud" with consent
                }
            }
        )

        return response.json()
```

---

## 7. Music Teaching Specific Considerations

### Audio Settings for Music Teaching
Zoom has specific audio settings that must be configured for music instruction:

**"Original Sound" Mode:**
- Disables echo cancellation
- Disables noise suppression
- Preserves full audio fidelity
- Essential for instrumental teaching

**API Setting:**
```json
{
  "settings": {
    "audio": "both",
    "use_pmi": false,
    "enable_original_sound": true  // Critical for music
  }
}
```

**Teacher Instructions Required:**
Teachers must also enable "Original Sound" in their Zoom client:
1. Join meeting
2. Click arrow next to "Mute" button
3. Select "Audio Settings"
4. Check "Show in-meeting option to 'Enable Original Sound'"
5. During meeting, click "Turn on Original Sound"

### Recording Considerations
For safeguarding purposes, the platform may want to record lessons:
- Cloud recording requires Business plan or higher
- Local recording available on Pro plan
- **Must obtain explicit consent from both parties**
- Consider GDPR/data protection requirements
- Storage costs for cloud recordings

---

## 8. Cost-Benefit Analysis

### Costs

#### Initial Setup
- Developer time: 20-40 hours ($2,000-$4,000 at $100/hr)
- Testing and QA: 10-20 hours ($1,000-$2,000)
- **Total Initial Cost: $3,000-$6,000**

#### Ongoing Monthly Costs
| Concurrent Lessons | Licenses Needed | Monthly Cost (Pro) | Annual Cost |
|-------------------|-----------------|-------------------|-------------|
| 5 | 5 | $84.95 | $799.50 |
| 10 | 10 | $169.90 | $1,599.00 |
| 25 | 25 | $424.75 | $3,997.50 |
| 50 | 50 | $849.50 | $7,995.00 |

### Benefits

#### For Teachers
- ✅ No need for personal paid Zoom account
- ✅ Unlimited lesson duration (no 40-minute cutoff)
- ✅ Professional appearance (platform-managed)
- ✅ No technical setup required
- ✅ Automatic meeting creation when lesson booked

#### For Platform
- ✅ Better teacher acquisition (remove barrier to entry)
- ✅ Quality control (audio settings pre-configured)
- ✅ Safeguarding (can monitor/record with consent)
- ✅ Professional service offering
- ✅ Competitive advantage over competitors
- ✅ Revenue opportunity (can charge teachers small fee)

#### For Students
- ✅ Consistent, professional experience
- ✅ Guaranteed no time limits
- ✅ Properly configured audio for music
- ✅ Seamless booking → meeting flow

### Revenue Model Options

**Option 1: Absorb Cost**
- Build into platform commission
- Marketing advantage: "Free unlimited Zoom for all teachers"

**Option 2: Small Teacher Fee**
- Charge teachers £5-10/month for Zoom access
- Still cheaper than Zoom Pro (£11.99/month)
- Cover partial costs

**Option 3: Per-Lesson Fee**
- Add £0.50-£1.00 to each online lesson booking
- Transparent to students
- Scales with usage

---

## 9. Alternative Solutions Considered

### Alternative 1: Google Meet
**Pros:**
- 60-minute free limit (vs Zoom's 40)
- Unlimited 1-on-1 meetings
- Can disable noise cancellation

**Cons:**
- Noise cancellation settings only on paid Workspace accounts
- Less established for music teaching
- API integration less mature
- Teachers less familiar with platform

**Verdict:** Not recommended as primary solution

### Alternative 2: Licensed Users Per Teacher
Give each teacher their own Zoom Pro license

**Pros:**
- Simple implementation
- Teachers have full control

**Cons:**
- Very expensive (£11.99 × number of teachers)
- No platform control
- No safeguarding oversight
- Teachers may leave and licenses wasted

**Verdict:** Not cost-effective for platform model

### Alternative 3: Zoom Rooms / Hardware
**Verdict:** Not applicable for RECORDER-ED use case

---

## 10. Risks and Mitigation

### Risk 1: API Rate Limits
**Risk:** 100 meetings/user/day may be exceeded
**Likelihood:** Medium (with growth)
**Mitigation:**
- Start with 5-10 licensed users for 500-1,000 daily capacity
- Implement round-robin distribution across users
- Monitor usage and add licenses proactively
- Use recurring meetings for regular weekly lessons

### Risk 2: Zoom Service Outages
**Risk:** Zoom downtime affects all lessons
**Likelihood:** Low (Zoom has 99.9% uptime SLA)
**Mitigation:**
- Have backup communication plan (email/SMS to reschedule)
- Consider fallback to Google Meet for emergencies
- Communicate clearly in booking confirmation

### Risk 3: Cost Scaling
**Risk:** Costs grow faster than revenue
**Likelihood:** Medium
**Mitigation:**
- Implement teacher fee contribution
- Monitor concurrent usage patterns
- Optimize license allocation
- Consider graduating to Business plan for better per-user pricing at scale

### Risk 4: Technical Integration Bugs
**Risk:** Meeting creation fails, wrong details sent
**Likelihood:** Medium (during development)
**Mitigation:**
- Comprehensive testing before launch
- Detailed error logging and monitoring
- Manual override option for staff
- Clear support process for teachers

### Risk 5: GDPR/Data Protection
**Risk:** Recording/storing meeting data inappropriately
**Likelihood:** Low (if implemented correctly)
**Mitigation:**
- Explicit consent for recordings
- Clear privacy policy
- Data retention policies
- Secure storage with encryption

---

## 11. Implementation Roadmap

### Phase 1: Setup & Development (4-6 weeks)
**Week 1-2: Initial Setup**
- Create Zoom App Marketplace account
- Set up Server-to-Server OAuth app
- Obtain credentials and test authentication
- Design database schema updates

**Week 3-4: Core Development**
- Build Zoom API client wrapper
- Implement meeting creation flow
- Add database models and migrations
- Create background task for API calls
- Build user management for licensed accounts

**Week 5-6: Integration & Testing**
- Integrate with lesson booking flow
- Implement email notifications with join links
- Configure audio settings for music teaching
- Comprehensive testing (unit, integration, end-to-end)
- User acceptance testing with small group

### Phase 2: Pilot Launch (2-3 weeks)
- Launch to 5-10 pilot teachers
- Monitor for issues and gather feedback
- Refine user experience
- Document teacher instructions
- Create support materials

### Phase 3: Full Rollout (2-4 weeks)
- Gradual rollout to all teachers
- Monitor license usage and scaling needs
- Collect feedback and iterate
- Optimize performance

### Phase 4: Optimization (Ongoing)
- Add analytics dashboard for Zoom usage
- Implement automatic license scaling
- Add recording features (with consent)
- Consider advanced features (waiting rooms, breakout rooms, etc.)

---

## 12. Recommended Next Steps

### Immediate Actions
1. ✅ **Decision:** Confirm approval for Zoom API integration approach
2. ✅ **Budget:** Approve initial development costs ($3,000-$6,000)
3. ✅ **Budget:** Approve 5-10 Zoom Pro licenses to start ($85-$170/month)
4. ⬜ **Account:** Create Zoom Pro/Business account
5. ⬜ **App:** Register Server-to-Server OAuth app in Zoom Marketplace
6. ⬜ **Planning:** Schedule development sprint

### Development Priorities
1. Authentication and API wrapper
2. Meeting creation on lesson booking
3. Email notifications with join links
4. Teacher dashboard showing upcoming Zoom meetings
5. Admin dashboard for license management

### Documentation Needs
1. Teacher guide: How online lessons work
2. Teacher guide: Enabling "Original Sound" for music
3. Student guide: Joining Zoom lessons
4. Technical documentation: API integration
5. Privacy policy update: Zoom data processing

---

## 13. Success Metrics

### Key Performance Indicators (KPIs)

**Technical Metrics:**
- API success rate (target: >99%)
- Meeting creation time (target: <5 seconds)
- Zero failed meeting creations due to rate limits

**Business Metrics:**
- Number of teachers using platform Zoom
- Online lessons booked per month
- Teacher satisfaction with Zoom integration
- Student satisfaction with lesson experience
- Cost per meeting (total Zoom cost ÷ meetings held)

**Growth Metrics:**
- Teacher acquisition rate improvement
- Percentage of teachers teaching online
- Month-over-month growth in online lessons
- Revenue from online lessons

---

## 14. Conclusion

### Recommendation: PROCEED with Zoom REST API Integration

**Why This Makes Business Sense:**
1. **Removes major barrier** for teachers without paid Zoom accounts
2. **Competitive advantage** - many competitors don't offer this
3. **Reasonable costs** at scale (£1.70 per concurrent lesson capacity)
4. **Professional service** - platform-managed meetings
5. **Safeguarding benefits** - platform oversight and recording capability
6. **Teacher acquisition** - "Free unlimited Zoom" is compelling marketing

### Starting Point
- **Begin with 5 Zoom Pro licenses:** £85/month (500 meetings/day capacity)
- **Development investment:** £3,000-6,000 one-time
- **Timeline:** 8-12 weeks to production launch
- **Break-even:** If 10-15 teachers each book 20 online lessons/month

### Long-term Value
This integration positions RECORDER-ED as a comprehensive, professional platform that removes friction for both teachers and students, directly supporting the platform's mission to make music education accessible.

---

## 15. Sources & References

### Pricing & Plans
- [Zoom Pricing Guide 2025](https://pumble.com/zoom-pricing)
- [Zoom Plans & Pricing](https://zoom.us/pricing)
- [Zoom Pricing Complete Guide](https://screenapp.io/blog/zoom-pricing-complete-guide-pro-cost-worth-it)
- [Zoom Pricing All Plans Explained](https://tech.co/web-conferencing/zoom-pricing-guide)

### API Documentation & Integration
- [Zoom Developer APIs](https://developers.zoom.us/docs/api/)
- [Zoom Meetings API](https://developers.zoom.us/docs/api/meetings/)
- [Zoom Meeting SDK Documentation](https://developers.zoom.us/docs/meeting-sdk/)
- [Zoom SDK Pricing & Features](https://dyte.io/blog/zoom-sdk-pricing/)

### Authentication
- [Server-to-Server OAuth](https://developers.zoom.us/docs/internal-apps/s2s-oauth/)
- [Create Server-to-Server OAuth App](https://developers.zoom.us/docs/internal-apps/create/)
- [Server-to-Server Python Sample](https://github.com/zoom/server-to-server-python-sample)

### Rate Limits & Technical Details
- [Zoom API Rate Limits](https://developers.zoom.us/docs/api/rate-limits/)
- [Daily Rate Limit Discussion](https://devforum.zoom.us/t/daily-rate-limit-100-of-meeting-create-update-api/107220)
- [Meeting Creation Rate Limits](https://devforum.zoom.us/t/rate-limit-for-meeting-creation/15385)

### SDK Comparisons
- [Zoom Meeting SDK vs API vs Video SDK](https://webrtc.ventures/2025/08/embed-or-create-zoom-web-sdk-guide-meeting-vs-video/)
- [Video SDK and Meeting SDK Comparison](https://support.zoom.com/hc/en/article?id=zm_kb&sysparm_article=KB0064689)

### Google Meet Alternative Research
- [Google Meet Noise Cancellation](https://www.bluedothq.com/blog/google-meet-noise-cancellation)
- [Filter Noise from Meetings - Google Meet Help](https://support.google.com/meet/answer/9919960?hl=en&co=GENIE.Platform%3DDesktop)
- [Google Meet Time Limit 2025](https://www.meetingtimer.io/blog/google-meet-time-limit-explained-2025)
- [Google Meet vs Zoom Comparison 2025](https://meetgeek.ai/blog/google-meet-vs-zoom)

---

**Document Version:** 1.0
**Last Updated:** November 23, 2025
**Author:** Research compiled for RECORDER-ED platform
**Next Review:** Q1 2026 or upon significant Zoom pricing/feature changes
