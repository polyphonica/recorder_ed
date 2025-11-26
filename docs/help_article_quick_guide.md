# Quick Guide: Creating Help Articles with Videos

## Adding Videos to Help Articles

### Method 1: YouTube Embed (Recommended)

1. **Upload your Camtasia video to YouTube**
   - Set visibility to "Unlisted" (not public, but viewable via link)
   - Add a descriptive title and description

2. **Get the video ID**
   - From URL: `https://www.youtube.com/watch?v=dQw4w9WgXcQ`
   - The ID is: `dQw4w9WgXcQ`

3. **In CKEditor:**
   - Option A: Click "Source" button and paste this HTML:
   ```html
   <iframe width="560" height="315"
   src="https://www.youtube.com/embed/YOUR_VIDEO_ID"
   frameborder="0" allowfullscreen></iframe>
   ```
   - Option B: Just paste the YouTube URL directly - CKEditor will auto-embed it!

### Method 2: Self-Hosted Video (Not Recommended)

- Videos should be hosted externally (YouTube/Vimeo) to save server resources
- Only use for very small clips (<5MB)

---

## Adding Screenshots

### In Django Admin CKEditor:

1. Click the **"Image"** button in the toolbar
2. Click **"Upload"** tab
3. Choose your screenshot file
4. Add **Alt text** (describes the image for accessibility)
5. Click **"OK"**

### Screenshot Best Practices:

- **Resolution:** 1200px wide max
- **Format:** PNG for UI screenshots, JPG for photos
- **Compress:** Use TinyPNG.com to reduce file size
- **Highlight:** Use colored boxes/arrows in Camtasia to highlight important areas
- **Consistency:** Use same browser/theme for all screenshots

---

## Adding Callout Boxes

### Tip Box (Blue):
```html
<div style="background-color: #dbeafe; border-left: 4px solid #3b82f6; padding: 15px; margin: 20px 0;">
    <p><strong>💡 Tip:</strong> Your tip text here</p>
</div>
```

### Important Note (Yellow):
```html
<div style="background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0;">
    <p><strong>📌 Important:</strong> Your important note here</p>
</div>
```

### Success Note (Green):
```html
<div style="background-color: #dcfce7; border-left: 4px solid #22c55e; padding: 15px; margin: 20px 0;">
    <p><strong>✅ Success:</strong> Your success message here</p>
</div>
```

### Warning (Red):
```html
<div style="background-color: #fee2e2; border-left: 4px solid #ef4444; padding: 15px; margin: 20px 0;">
    <p><strong>⚠️ Warning:</strong> Your warning text here</p>
</div>
```

---

## Article Structure Template

Every article should follow this structure:

1. **Title** (H1) - Clear, descriptive
2. **Intro paragraph** - What this article covers
3. **Video section** (optional) - For visual learners
4. **Step-by-step instructions** - Numbered lists
5. **Screenshots** - Show each major step
6. **Troubleshooting** - Common issues and solutions
7. **Related articles** - Links to similar content
8. **Still need help?** - Link to support

---

## Camtasia Export Settings

### For YouTube:
- **Format:** MP4
- **Resolution:** 1920x1080 (1080p) or 1280x720 (720p)
- **Frame Rate:** 30 fps
- **Quality:** High (80-90%)

### For GIF Animations:
- **Format:** Animated GIF
- **Frame Rate:** 15 fps
- **Duration:** Keep under 10 seconds
- **Size:** 800px wide max
- **Quality:** Medium (to keep file size small)

---

## Workflow Checklist

### Before Recording:
- [ ] Script your narration
- [ ] Clear browser cache/cookies
- [ ] Use incognito/private mode (clean UI, no extensions)
- [ ] Set browser zoom to 100%
- [ ] Close unnecessary tabs
- [ ] Check audio levels

### During Recording:
- [ ] Slow down mouse movements
- [ ] Pause on important screens (2-3 seconds)
- [ ] Speak clearly and at moderate pace
- [ ] Follow your script but stay natural

### After Recording in Camtasia:
- [ ] Add cursor effects (highlight/ripple)
- [ ] Add callouts and arrows where helpful
- [ ] Zoom in on small UI elements
- [ ] Trim dead space at start/end
- [ ] Add subtle background music (optional)
- [ ] Add captions/subtitles (for accessibility)

### Before Publishing Article:
- [ ] Test all video embeds
- [ ] Check all screenshots display correctly
- [ ] Test all internal links
- [ ] Proofread for typos
- [ ] Preview on mobile
- [ ] Set article to "Published" status
- [ ] Mark as "Promoted" if it's a key article

---

## Common Mistakes to Avoid

❌ **Don't:**
- Use "Click here" as link text (not accessible)
- Skip alt text on images
- Make videos longer than 10 minutes
- Use poor quality audio
- Forget to slow down mouse movements
- Use inconsistent screenshot sizes
- Leave out troubleshooting section

✅ **Do:**
- Use descriptive link text ("View our refund policy")
- Always add alt text to images
- Keep videos 2-5 minutes ideal
- Test audio before full recording
- Add zoom effects for small UI elements
- Compress images before uploading
- Include "Still need help?" section

---

## Estimated Time Per Article

- **Simple article** (text + screenshots only): 30-45 minutes
- **Medium article** (text + screenshots + short video): 2-3 hours
- **Complex article** (text + screenshots + narrated video + editing): 4-6 hours

---

## Tools You Need

### Essential:
- ✅ Camtasia (for screen recording and editing)
- ✅ Decent microphone (for voice-overs)
- ✅ YouTube account (for hosting videos)

### Optional but Helpful:
- TinyPNG.com (compress images)
- Grammarly (proofread articles)
- Loom (quick alternative to Camtasia for simple demos)
- Audacity (edit audio if needed)

---

## Getting Help

- **CKEditor documentation:** Built into Django Admin (click help icons)
- **Camtasia tutorials:** YouTube has hundreds of tutorials
- **Example articles:** See `help_article_ckeditor_example.html` in this folder
- **Category guide:** See `help_center_categories.md` for article ideas

---

**Ready to create your first article?** Start with "Welcome to Recorder-ed" - it's text-only and doesn't need a video!
