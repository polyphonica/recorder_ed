# Course Media Management Guide

## Overview

This guide explains how to organize and upload media files (images, audio, PDFs) for your courses using FTP and reference them in your lesson content.

---

## Folder Structure

All course media files are organized in a hierarchical structure that mirrors your course organization:

```
media/
├── courses/
│   ├── images/                           # Course cover images (uploaded via Django)
│   ├── content/                          # Lesson content media (FTP upload)
│   │   ├── {course-slug}/
│   │   │   ├── {topic-number}-{topic-slug}/
│   │   │   │   ├── {lesson-number}-{lesson-slug}/
│   │   │   │   │   ├── images/           # SVGs, PNGs, JPGs
│   │   │   │   │   ├── audio/            # MP3, WAV, OGG files
│   │   │   │   │   ├── documents/        # PDFs, sheet music
│   │   │   │   │   └── files/            # Other files
│   │   ├── shared/                       # Resources used across multiple courses
│   │   │   ├── images/
│   │   │   ├── audio/
│   │   │   └── documents/
│   ├── documents/                        # Downloadable attachments (via LessonAttachment model)
├── uploads/                              # CKEditor quick uploads (auto-managed)
```

### Real Example

For a course "Recorder Basics - Grade 1" with topic "First Notes" and lesson "Note B":

```
media/courses/content/
└── recorder-basics-grade-1/
    └── 01-first-notes/
        └── 01-note-b/
            ├── images/
            │   ├── fingering-chart-b.svg
            │   └── photo-hand-position.jpg
            ├── audio/
            │   ├── note-b-slow.mp3
            │   ├── note-b-medium.mp3
            │   └── note-b-fast.mp3
            └── documents/
                └── sheet-music-note-b.pdf
```

---

## Naming Conventions

Use clear, descriptive names that indicate what the file contains:

### Format
```
{type}-{descriptor}-{variation}.{ext}
```

### Examples

**Images:**
- `fingering-chart-b.svg`
- `fingering-chart-a-g.svg`
- `diagram-recorder-parts.svg`
- `photo-hand-position-01.jpg`
- `photo-embouchure-correct.jpg`

**Audio:**
- `note-b-slow.mp3`
- `note-b-medium.mp3`
- `note-b-fast.mp3`
- `exercise-scale-c-major-slow.mp3`
- `exercise-scale-c-major-fast.mp3`
- `song-hot-cross-buns-demo.mp3`
- `song-hot-cross-buns-backing-track.mp3`

**Documents:**
- `sheet-music-hot-cross-buns.pdf`
- `worksheet-note-reading-practice.pdf`
- `handout-care-maintenance.pdf`

### Naming Rules

✅ **Do:**
- Use lowercase letters
- Use hyphens (-) for spaces
- Be descriptive but concise
- Include variation (slow/fast, v1/v2) when needed
- Use standard file extensions

❌ **Don't:**
- Use spaces: `note b slow.mp3` ❌
- Use special characters: `note_b@slow!.mp3` ❌
- Use generic names: `audio1.mp3` ❌
- Use uppercase: `Note-B-Slow.MP3` ❌

---

## FTP Upload Process

### 1. Connect to Server

**FTP Credentials:**
- Host: `ftp.recorder-ed.com` (or your server IP)
- Username: [Your FTP username]
- Password: [Your FTP password]
- Port: 21 (or 22 for SFTP)

**Recommended FTP Clients:**
- **FileZilla** (Free, Windows/Mac/Linux)
- **Cyberduck** (Free, Mac/Windows)
- **Transmit** (Paid, Mac)
- **WinSCP** (Free, Windows)

### 2. Navigate to Media Folder

After connecting, navigate to:
```
/home/[username]/recorder_ed/media/courses/content/
```

### 3. Create Folder Structure

If your course folders don't exist yet, create them:

```
Right-click → Create Directory → Name it
```

Example for new lesson:
1. Navigate to `media/courses/content/`
2. Create folder: `recorder-basics-grade-1` (if it doesn't exist)
3. Inside that, create: `01-first-notes`
4. Inside that, create: `01-note-b`
5. Inside that, create subfolders: `images`, `audio`, `documents`

### 4. Upload Files

**Drag and drop** or **right-click → Upload** your files into the appropriate subfolder:
- `.svg`, `.jpg`, `.png` → `images/`
- `.mp3`, `.wav`, `.ogg` → `audio/`
- `.pdf` → `documents/`

### 5. Verify Upload

- Check file appears in correct folder
- Note the full path (you'll need this for CKEditor)

---

## Using Media in CKEditor

### Getting the File URL

Once uploaded, your file has a URL following this pattern:
```
/media/courses/content/{course-slug}/{topic-slug}/{lesson-slug}/{type}/{filename}
```

**Example:**
```
/media/courses/content/recorder-basics-grade-1/01-first-notes/01-note-b/images/fingering-chart-b.svg
```

### Inserting Images

#### Method 1: Image Button (Recommended for inline images)

1. In CKEditor, click the **Image** button
2. Choose "Insert image via URL"
3. Paste your media URL
4. Add alt text (e.g., "Fingering chart for note B")
5. Click Insert

#### Method 2: Source Code (For advanced control)

1. Click the **Source** button in CKEditor
2. Insert HTML directly:

```html
<figure class="image">
    <img src="/media/courses/content/recorder-basics-grade-1/01-first-notes/01-note-b/images/fingering-chart-b.svg"
         alt="Fingering chart for note B">
    <figcaption>Fingering Chart: Note B</figcaption>
</figure>
```

#### Responsive Images

For images that should scale on mobile:
```html
<img src="/media/courses/content/.../diagram.svg"
     alt="Recorder parts diagram"
     style="max-width: 100%; height: auto;">
```

### Inserting Audio Files

CKEditor doesn't have a built-in audio button, so use HTML:

1. Click the **Source** button
2. Insert HTML5 audio player:

```html
<div class="audio-player">
    <h4>Listen: Note B (Slow)</h4>
    <audio controls>
        <source src="/media/courses/content/recorder-basics-grade-1/01-first-notes/01-note-b/audio/note-b-slow.mp3" type="audio/mpeg">
        Your browser does not support the audio element.
    </audio>
</div>
```

#### Multiple Speeds Example

```html
<div class="audio-examples">
    <h4>Practice Note B at Different Speeds</h4>

    <div class="audio-item">
        <strong>Slow:</strong>
        <audio controls>
            <source src="/media/courses/content/recorder-basics-grade-1/01-first-notes/01-note-b/audio/note-b-slow.mp3" type="audio/mpeg">
        </audio>
    </div>

    <div class="audio-item">
        <strong>Medium:</strong>
        <audio controls>
            <source src="/media/courses/content/recorder-basics-grade-1/01-first-notes/01-note-b/audio/note-b-medium.mp3" type="audio/mpeg">
        </audio>
    </div>

    <div class="audio-item">
        <strong>Fast:</strong>
        <audio controls>
            <source src="/media/courses/content/recorder-basics-grade-1/01-first-notes/01-note-b/audio/note-b-fast.mp3" type="audio/mpeg">
        </audio>
    </div>
</div>
```

### Inserting Downloadable Links

For PDFs and documents students should download:

```html
<div class="download-link">
    <a href="/media/courses/content/recorder-basics-grade-1/01-first-notes/01-note-b/documents/sheet-music-note-b.pdf"
       download
       class="btn btn-primary">
        <i class="fas fa-download"></i> Download Sheet Music (PDF)
    </a>
</div>
```

---

## Shared Resources

For media used across multiple lessons (e.g., a diagram of recorder parts), use the `shared/` folder:

### Upload to Shared

```
media/courses/content/shared/
├── images/
│   ├── diagram-recorder-parts.svg
│   └── diagram-music-staff.svg
├── audio/
│   └── tuning-reference-a440.mp3
└── documents/
    └── fingering-chart-complete.pdf
```

### Reference Shared Files

```html
<img src="/media/courses/content/shared/images/diagram-recorder-parts.svg"
     alt="Parts of the recorder">
```

**Benefit:** Update one file, and it updates everywhere it's used.

---

## Quick Reference

### Common Paths Template

Copy and modify these templates:

**Image:**
```html
<img src="/media/courses/content/COURSE-SLUG/TOPIC-SLUG/LESSON-SLUG/images/FILENAME.svg" alt="DESCRIPTION">
```

**Audio:**
```html
<audio controls>
    <source src="/media/courses/content/COURSE-SLUG/TOPIC-SLUG/LESSON-SLUG/audio/FILENAME.mp3" type="audio/mpeg">
</audio>
```

**Download Link:**
```html
<a href="/media/courses/content/COURSE-SLUG/TOPIC-SLUG/LESSON-SLUG/documents/FILENAME.pdf" download class="btn btn-primary">
    Download PDF
</a>
```

### Finding Your Slugs

**Course Slug:** Check your course URL: `/courses/COURSE-SLUG/`
**Topic Slug:** Usually `{number}-{topic-name}` (e.g., `01-first-notes`)
**Lesson Slug:** Usually `{number}-{lesson-name}` (e.g., `01-note-b`)

---

## File Type Reference

### Images

| Extension | Use Case | Notes |
|-----------|----------|-------|
| `.svg` | Diagrams, charts, fingering charts | Vector graphics, scales perfectly, small file size |
| `.jpg` | Photos | Good for photographs, smaller file size |
| `.png` | Screenshots, images with transparency | Lossless quality |
| `.gif` | Simple animations | Keep under 1MB |
| `.webp` | Modern format | Best compression, not all browsers support |

**Recommended:** Use SVG for diagrams/charts, JPG for photos

### Audio

| Extension | Use Case | Notes |
|-----------|----------|-------|
| `.mp3` | General audio | Best compatibility, good compression |
| `.ogg` | Alternative format | Open source, good quality |
| `.wav` | High quality | Large file size, use sparingly |
| `.m4a` | Apple devices | Good quality, smaller than MP3 |

**Recommended:** Use MP3 (compatibility) or OGG (quality + size)

### Documents

| Extension | Use Case | Notes |
|-----------|----------|-------|
| `.pdf` | Sheet music, worksheets, handouts | Universal format |
| `.doc`/`.docx` | Editable documents | If students need to edit |

**Recommended:** Use PDF for read-only content

---

## Troubleshooting

### Files Not Appearing

**Problem:** Uploaded file, but getting 404 error
**Solution:**
1. Check file path is exactly correct (case-sensitive)
2. Verify file was uploaded to correct folder
3. Check file permissions (should be 644 for files, 755 for folders)
4. Try accessing directly: `https://recorder-ed.com/media/courses/content/...`

### SVG Not Displaying

**Problem:** SVG shows as broken image
**Solution:**
1. Check SVG file is valid (open in web browser locally first)
2. Ensure SVG doesn't have embedded scripts (security risk)
3. Try viewing directly in browser: add domain before path

### Audio Not Playing

**Problem:** Audio player shows but won't play
**Solution:**
1. Check file path is correct
2. Verify audio file isn't corrupted (test locally)
3. Check file format is supported (MP3 is safest)
4. Try including multiple formats:
```html
<audio controls>
    <source src=".../audio.mp3" type="audio/mpeg">
    <source src=".../audio.ogg" type="audio/ogg">
</audio>
```

### Permission Denied

**Problem:** Can't upload via FTP
**Solution:**
1. Check FTP credentials are correct
2. Verify you have write permissions to `media/courses/content/`
3. Contact system administrator

---

## Best Practices

### File Size Optimization

**Images:**
- SVG: Keep under 200KB
- JPG/PNG: Resize to appropriate dimensions before upload
  - Full width: 1200px max
  - Thumbnails: 400px max
- Compress images using tools like TinyPNG or ImageOptim

**Audio:**
- Use 128kbps or 192kbps for MP3s (good quality, reasonable size)
- Mono for speech, stereo for music
- Trim silence from beginning/end
- Target: 1-2MB per minute of audio

**Documents:**
- Compress PDFs before upload
- Use "web optimized" PDF export if available
- Target: Under 5MB per PDF

### Accessibility

**Images:**
- Always include descriptive alt text
- Use empty alt (`alt=""`) for decorative images
- Caption important diagrams

**Audio:**
- Provide text transcript for longer audio
- Use descriptive labels ("Slow," "Medium," "Fast")

### Organization Tips

1. **Create folder structure first** before uploading files
2. **Upload in batches** by lesson to stay organized
3. **Keep a spreadsheet** of uploaded files with paths (optional)
4. **Test files** in a draft lesson before publishing
5. **Backup locally** - keep originals on your computer

---

## Example: Complete Lesson Setup

Let's walk through uploading media for "Lesson 1: Note B"

### 1. Prepare Files Locally

Create a folder on your computer:
```
note-b-lesson/
├── fingering-chart-b.svg
├── photo-hand-position.jpg
├── note-b-slow.mp3
├── note-b-medium.mp3
├── note-b-fast.mp3
└── sheet-music-note-b.pdf
```

### 2. Upload via FTP

Connect and navigate to:
```
media/courses/content/recorder-basics-grade-1/01-first-notes/01-note-b/
```

Create subfolders and upload:
- `fingering-chart-b.svg` → `images/`
- `photo-hand-position.jpg` → `images/`
- `note-b-slow.mp3` → `audio/`
- `note-b-medium.mp3` → `audio/`
- `note-b-fast.mp3` → `audio/`
- `sheet-music-note-b.pdf` → `documents/`

### 3. Add to Lesson Content (CKEditor)

```html
<h2>Introduction to Note B</h2>

<p>Note B is the first note we'll learn on the recorder. Here's the fingering chart:</p>

<figure class="image">
    <img src="/media/courses/content/recorder-basics-grade-1/01-first-notes/01-note-b/images/fingering-chart-b.svg"
         alt="Fingering chart for note B"
         style="max-width: 400px;">
    <figcaption>Fingering Chart: Note B</figcaption>
</figure>

<h3>Proper Hand Position</h3>
<p>Make sure your left hand is on top and your right hand is on the bottom:</p>

<img src="/media/courses/content/recorder-basics-grade-1/01-first-notes/01-note-b/images/photo-hand-position.jpg"
     alt="Correct hand position on recorder">

<h3>Listen and Play Along</h3>
<p>Practice playing note B at different speeds. Start slow and gradually increase tempo:</p>

<div class="audio-examples">
    <div class="audio-item">
        <strong>Slow (60 BPM):</strong>
        <audio controls>
            <source src="/media/courses/content/recorder-basics-grade-1/01-first-notes/01-note-b/audio/note-b-slow.mp3" type="audio/mpeg">
        </audio>
    </div>

    <div class="audio-item">
        <strong>Medium (90 BPM):</strong>
        <audio controls>
            <source src="/media/courses/content/recorder-basics-grade-1/01-first-notes/01-note-b/audio/note-b-medium.mp3" type="audio/mpeg">
        </audio>
    </div>

    <div class="audio-item">
        <strong>Fast (120 BPM):</strong>
        <audio controls>
            <source src="/media/courses/content/recorder-basics-grade-1/01-first-notes/01-note-b/audio/note-b-fast.mp3" type="audio/mpeg">
        </audio>
    </div>
</div>

<h3>Sheet Music</h3>
<p>Download the practice sheet to follow along:</p>

<div class="download-link">
    <a href="/media/courses/content/recorder-basics-grade-1/01-first-notes/01-note-b/documents/sheet-music-note-b.pdf"
       download
       class="btn btn-primary">
        <i class="fas fa-download"></i> Download Practice Sheet (PDF)
    </a>
</div>
```

---

## Need Help?

If you encounter issues not covered in this guide:

1. Check the troubleshooting section above
2. Verify your files locally before uploading
3. Contact technical support with:
   - Description of the problem
   - File path you're trying to use
   - Screenshot of error (if applicable)

---

## Summary Checklist

Before you start uploading:

- [ ] Files are properly named (lowercase, hyphens, descriptive)
- [ ] Files are optimized (compressed, appropriate size)
- [ ] You know your course/topic/lesson slugs
- [ ] FTP connection is working

During upload:

- [ ] Folder structure matches course organization
- [ ] Files are in correct subfolders (images/, audio/, documents/)
- [ ] File permissions are set correctly (if needed)

After upload:

- [ ] Test file URLs directly in browser
- [ ] Add to lesson content with proper HTML
- [ ] Preview lesson as student to verify everything works
- [ ] Check on mobile device for responsiveness

---

*Last updated: January 2025*
