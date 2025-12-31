# CKEditor Integration Comparison: POC vs Main App

## Template Inheritance

### POC
- Extends: `ckeditor_poc/base_isolated.html`
- Framework: None (pure HTML/CSS)
- Container width: No restriction

### Main App (Lesson Templates)
- Extends: `base.html`
- Framework: Tailwind CSS + DaisyUI
- Container width: `max-w-6xl` (1152px)

## CSS Loaded

### POC
```html
<!-- Only CKEditor official CSS -->
<link rel="stylesheet" href="https://cdn.ckeditor.com/ckeditor5/43.2.0/ckeditor5.css">

<!-- Minimal inline CSS (~170 lines) -->
- Basic layout and buttons
- CKEditor fixes:
  * Left-align for tables without styles
  * Table width: 100% of parent figure
```

### Main App
```html
<!-- Tailwind CSS -->
<link rel="stylesheet" href="/static/css/dist/styles.css">

<!-- Custom CSS -->
<link rel="stylesheet" href="/static/css/custom.css">

<!-- CKEditor CSS (via {{ form.media }}) -->
- Official CKEditor CSS
- /static/css/ckeditor_custom.css (300+ lines)
- /static/css/imagestyle.css

<!-- Tailwind Typography (prose class) -->
Applied to content viewing areas
```

## JavaScript Loaded

### POC
```html
<!-- ONLY CKEditor's own JavaScript -->
- No custom scripts
- No audio upload helper
- No other app JavaScript
```

### Main App
```html
<!-- Alpine.js -->
<script defer src="alpinejs"></script>

<!-- Driver.js (product tours) -->
<script src="driver.js"></script>

<!-- CKEditor Audio Upload Helper -->
<script src="/static/js/ckeditor_audio_upload.js"></script>

<!-- CKEditor JavaScript (via {{ form.media }}) -->
- Official CKEditor JS
```

## CKEditor Configuration

### Both Use
- Same config: `config_name='default'` from `settings.py`
- Same toolbar items
- Same table/image plugins
- Same htmlSupport settings

## CSS Specificity Issues

### POC - Clean Environment
```css
/* Only 2 CKEditor-specific rules */
.ck-content figure.table:not([style*="float"]):not([style*="margin"]) {
    margin-left: 0;
    margin-right: auto;
}

.ck-content figure.table > table {
    width: 100%;
}
```

### Main App - Complex Environment
```css
/* From ckeditor_custom.css - 300+ lines including: */

/* Tailwind prose conflicts */
.prose figure.image { /* overrides */ }

/* Nested figure handling */
.ck-content:not(.ck-editor__editable) figure:has(> figure.image:not(.image_resized))

/* Image alignment overrides */
.ck-content figure.image.image_resized:not(...) { margin-left: 0 !important; }

/* Table styling */
.ck-content figure.table { /* complex rules */ }

/* Plus 200+ more lines for:
   - Image resizing
   - Image alignment
   - Table alignment
   - Headings
   - Typography
   - Responsive design
*/
```

## Key Differences

### 1. Prose Class Conflicts
**POC:** No prose class
**Main App:** `<div class="ck-content prose max-w-none">` can override styles

### 2. Nested Figures
**POC:** No special handling needed
**Main App:** Complex CSS to handle nested figures from CKEditor

### 3. Tailwind Resets
**POC:** No CSS resets
**Main App:** Tailwind's normalize/reset can affect CKEditor elements

### 4. JavaScript Interference
**POC:** Zero JavaScript conflicts
**Main App:** Audio upload script, Alpine.js, etc. could theoretically interfere

### 5. CSS Specificity Wars
**POC:** Simple, low specificity
**Main App:** Multiple !important flags to override Tailwind/prose

## What Works Where

| Feature | POC | Main App | Notes |
|---------|-----|----------|-------|
| Image alignment | ✅ | ✅ | Fixed with prose overrides |
| Image resizing | ✅ | ✅ | Fixed with CSS exclusions |
| Table left-align | ✅ | ✅ | Fixed by handling CKEditor's missing styles |
| Table center/right | ✅ | ✅ | Works in both |
| Table resizing | ✅ | ✅ | Both have table width CSS |

## Root Causes Identified

### CKEditor 5 Issues (Not Our Fault)
1. **Left table alignment outputs NO styles** - CKEditor assumes default is left
2. **Table width requires CSS** - Need `table { width: 100% }` to constrain inner table

### Main App Issues (Fixed)
1. ~~Tailwind prose centering images~~ - FIXED with prose overrides
2. ~~display:contents breaking resized images~~ - FIXED with exclusions
3. ~~CSS overriding inline width styles~~ - FIXED by removing override

## Conclusion

The POC proves that with **minimal, correct CSS (15 lines)**, CKEditor 5 works perfectly.

The main app needed **300+ lines of CSS** to work around:
- Tailwind conflicts
- Prose class overrides
- Nested figure handling
- Image/table alignment edge cases

**All main app issues have been fixed. The apps now behave identically.**

## Future Use

When encountering CKEditor issues:
1. **Test in POC first** - If it works there, it's a main app CSS/JS conflict
2. **Test in main app** - If it fails in both, it's a CKEditor bug
3. **Compare HTML output** - Look for differences in generated markup
4. **Check browser console** - Look for JavaScript errors in main app

The POC is your baseline for "correct" CKEditor behavior.
