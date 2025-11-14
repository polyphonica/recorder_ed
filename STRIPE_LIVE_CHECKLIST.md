# Stripe Live Payments - Pre-Production Checklist

## ✅ COMPLETED

### Security Improvements
- [x] Replace print() statements with proper logging in webhook handlers
- [x] Webhook signature verification implemented
- [x] CSRF exemption for webhooks properly configured
- [x] Environment variables used for all sensitive keys

---

## 🔧 REQUIRED ACTIONS BEFORE GOING LIVE

### 1. Stripe Dashboard Configuration

#### A. Get Live API Keys
1. Log into [Stripe Dashboard](https://dashboard.stripe.com)
2. Switch to **Live Mode** (toggle in top left)
3. Go to **Developers → API keys**
4. Copy the following keys:
   - **Publishable key** (starts with `pk_live_`)
   - **Secret key** (starts with `sk_live_`)

#### B. Configure Webhook Endpoint
1. Go to **Developers → Webhooks**
2. Click **+ Add endpoint**
3. Enter endpoint URL: `https://www.recorder-ed.com/payments/webhook/`
4. Select events to listen for:
   - `checkout.session.completed`
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`
5. Click **Add endpoint**
6. **Copy the Webhook signing secret** (starts with `whsec_`)

### 2. Update Production Environment Variables

Update your production `.env` file with the live keys:

```bash
# Stripe Live Keys (NOT test keys!)
STRIPE_PUBLISHABLE_KEY=pk_live_xxxxxxxxxxxxx
STRIPE_SECRET_KEY=sk_live_xxxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxx
```

**IMPORTANT**: Make sure you're NOT using test keys (pk_test_, sk_test_)

### 3. Verify SSL Certificate

Ensure your production site has a valid SSL certificate:
- [ ] Visit `https://www.recorder-ed.com` and verify the padlock icon
- [ ] Stripe webhooks require HTTPS - test mode webhooks won't work
- [ ] Check certificate expiration date

### 4. Test Payment Flows (End-to-End)

Test each payment flow in **test mode first**, then in **live mode with small amounts**:

#### Private Teaching Payments
- [ ] Student requests lessons
- [ ] Student adds to cart
- [ ] Student completes checkout
- [ ] Verify lesson status updates to "Paid"
- [ ] Verify order status updates to "completed"
- [ ] Check emails sent to student and teacher

#### Workshop Payments
- [ ] Single registration payment
- [ ] Cart with multiple registrations
- [ ] Verify registration status updates
- [ ] Check confirmation emails
- [ ] Verify instructor notifications

#### Course Payments
- [ ] Course enrollment payment
- [ ] Verify enrollment created
- [ ] Check confirmation emails

### 5. Email Notification Testing

Verify all payment-related emails are working:
- [ ] Student payment confirmation (all domains)
- [ ] Teacher/instructor payment notifications
- [ ] Failed payment notifications
- [ ] Test with real email addresses

### 6. Webhook Testing

#### Test webhooks are being received:
1. Make a test payment in live mode (£0.50 or similar small amount)
2. Check Stripe Dashboard → Developers → Webhooks → [your endpoint]
3. Verify webhook events show status `succeeded`
4. Check production logs for webhook processing

#### Verify webhook handlers:
- [ ] `checkout.session.completed` creates StripePayment record
- [ ] `payment_intent.succeeded` marks payment as completed
- [ ] `payment_intent.payment_failed` marks payment as failed
- [ ] Domain-specific handlers execute correctly

### 7. Logging & Monitoring

Verify logging is working in production:
- [ ] Check logs for webhook events: `logger.info()` messages
- [ ] Verify error logging: `logger.error()` for failures
- [ ] Set up log monitoring/alerts (optional but recommended)

### 8. Database Backup

Before going live:
- [ ] Create full database backup
- [ ] Test database restore procedure
- [ ] Document rollback plan

### 9. Refund/Cancellation Testing

Test refund procedures:
- [ ] Make a test payment
- [ ] Process refund through Stripe Dashboard
- [ ] Verify refund appears in StripePayment record
- [ ] Test partial refunds if applicable

### 10. User Communication

Prepare users for live payments:
- [ ] Update Terms of Service (if needed)
- [ ] Update Privacy Policy (payment data handling)
- [ ] Add payment FAQs or help documentation
- [ ] Prepare support responses for payment questions

---

## 🚨 COMMON ISSUES & TROUBLESHOOTING

### Webhooks Not Working
**Symptoms**: Payments succeed but orders/registrations don't update

**Solutions**:
1. Check webhook endpoint URL is correct in Stripe Dashboard
2. Verify `STRIPE_WEBHOOK_SECRET` in `.env` matches Stripe Dashboard
3. Check production logs for webhook errors
4. Ensure HTTPS is working (webhooks require SSL)
5. Test webhook endpoint: `curl -X POST https://www.recorder-ed.com/payments/webhook/`

### Payment Succeeds But Order Doesn't Update
**Cause**: Metadata not properly passed to Stripe

**Check**:
- Review logs for "Unknown domain" warnings
- Verify metadata is included in checkout session creation
- Check domain value matches: 'private_teaching', 'workshops', or 'courses'

### Email Notifications Not Sending
**Solutions**:
1. Check `DEFAULT_FROM_EMAIL` in settings
2. Verify SMTP settings are configured
3. Check email service quotas/limits
4. Review logs for email send failures

---

## 📊 POST-LAUNCH MONITORING

### Week 1 After Going Live

Monitor closely:
- [ ] Daily check of successful vs failed payments
- [ ] Review webhook processing logs
- [ ] Monitor customer support for payment issues
- [ ] Check for any payment amount discrepancies
- [ ] Verify commission calculations are correct

### Stripe Dashboard Monitoring

Regularly check:
- **Home → Dashboard**: Overview of payments
- **Payments → All payments**: Individual transaction review
- **Developers → Webhooks**: Event delivery status
- **Reports**: Revenue reports, balance, etc.

---

## 🔐 SECURITY REMINDERS

1. **Never commit API keys to git** - Always use environment variables
2. **Restrict API key permissions** in Stripe Dashboard if possible
3. **Enable 2FA** on your Stripe account
4. **Monitor unusual activity** in Stripe Dashboard
5. **Keep webhook secrets secure** - rotate if compromised

---

## 📞 SUPPORT CONTACTS

- **Stripe Support**: https://support.stripe.com
- **Stripe Status Page**: https://status.stripe.com
- **Documentation**: https://stripe.com/docs

---

## ✅ FINAL GO-LIVE CHECKLIST

Before switching to live payments, verify ALL items:

- [ ] Live API keys added to production `.env`
- [ ] Webhook endpoint registered in Stripe Dashboard
- [ ] Webhook secret added to production `.env`
- [ ] SSL certificate valid and working
- [ ] End-to-end payment testing completed
- [ ] Email notifications tested and working
- [ ] Webhook processing tested and verified
- [ ] Database backup created
- [ ] Logging verified in production
- [ ] Support team briefed on payment system
- [ ] Rollback plan documented

**Only proceed when ALL items are checked!**

---

## 🎉 GOING LIVE

Once all checks are complete:

1. Update environment variables with live keys
2. Restart web server: `sudo systemctl restart gunicorn` (or your server)
3. Make a small test payment (£0.50) with a real card
4. Verify the entire flow works end-to-end
5. Monitor logs for the next hour
6. If successful, announce live payments to users!

---

**Last Updated**: 2025-11-14
**Status**: Ready for live deployment after checklist completion
