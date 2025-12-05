# Accessibility Guidelines for Recorder-ed Platform

## Overview

This document outlines the accessibility standards and testing procedures for the Recorder-ed educational platform. We are committed to ensuring WCAG 2.1 Level AA compliance.

## What We've Implemented

### 1. Semantic HTML & Landmarks

✅ **Skip Navigation Link** - Allows keyboard users to skip directly to main content
- Location: `templates/base.html:77`
- Press Tab on page load to see it

✅ **Semantic Landmarks**
- `<nav role="navigation">` for navigation areas
- `<main role="main" id="main-content">` for main content
- `<footer role="contentinfo">` for footer

### 2. Keyboard Navigation

✅ **Focus Indicators** - All interactive elements have visible focus states
- Custom CSS in `static/css/custom.css:212-228`
- Blue outline (2px) on all focusable elements

✅ **Keyboard Accessible Components**
- All buttons and links are keyboard accessible
- Dropdowns work with keyboard (Tab, Enter, Escape)
- Forms support full keyboard navigation

### 3. Screen Reader Support

✅ **ARIA Labels**
- Icon-only buttons have descriptive `aria-label` attributes
- Shopping cart announces item count
- Messages button announces unread count
- User menu identifies user by name

✅ **ARIA Live Regions**
- Error messages use `aria-live="polite"` and `role="alert"`
- Critical errors use `aria-live="assertive"`
- Form validation errors are announced

✅ **ARIA States**
- Buttons show `aria-expanded` states
- Dropdowns use `aria-haspopup="true"`
- Invalid form fields have `aria-invalid="true"`
- Required fields have `aria-required="true"`

### 4. Forms

✅ **Accessible Form Fields** (`templates/components/form_field.html`)
- All inputs have associated `<label>` elements
- Error messages linked via `aria-describedby`
- Help text properly associated with inputs
- Required fields clearly marked

### 5. Modals & Dialogs

✅ **Accessible Modals** (`templates/components/modal.html`)
- Uses native `<dialog>` element
- Proper `role="dialog"` and `aria-labelledby`
- Escape key closes modals
- Focus trapped within modal when open

### 6. Color & Contrast

✅ **Meeting WCAG AA Standards**
- Text contrast ratio: minimum 4.5:1 for normal text
- Large text contrast: minimum 3:1
- DaisyUI themes tested for contrast compliance

---

## Testing Procedures

### Automated Testing

#### 1. Install Testing Tools

```bash
# Install Pa11y for CI/CD
npm install --save-dev pa11y

# Install axe-core for browser testing
npm install --save-dev axe-core
```

#### 2. Run Automated Tests

```bash
# Test a single page
npx pa11y http://localhost:8000

# Test multiple pages
npx pa11y http://localhost:8000/courses/
npx pa11y http://localhost:8000/private-teaching/
npx pa11y http://localhost:8000/workshops/
```

#### 3. Browser DevTools Lighthouse

1. Open Chrome DevTools (F12)
2. Go to "Lighthouse" tab
3. Select "Accessibility" category
4. Click "Analyze page load"
5. Review and fix issues scoring below 90

### Manual Testing

#### Keyboard Navigation Test

**Goal**: Navigate entire site using only keyboard

1. **Tab Key** - Move forward through interactive elements
2. **Shift+Tab** - Move backward through elements
3. **Enter** - Activate buttons and links
4. **Space** - Toggle checkboxes, activate buttons
5. **Escape** - Close modals and dropdowns
6. **Arrow Keys** - Navigate within dropdown menus

**Checklist**:
- [ ] All interactive elements reachable via Tab
- [ ] Focus indicator clearly visible
- [ ] Logical tab order (left to right, top to bottom)
- [ ] No keyboard traps (can navigate away from all elements)
- [ ] Skip link works (Tab on page load, then Enter)

#### Screen Reader Test

**macOS - VoiceOver** (Cmd+F5)

```bash
# Basic commands:
# VO = Control + Option

VO + A              # Start reading
VO + Right Arrow    # Next item
VO + Left Arrow     # Previous item
VO + Space          # Activate element
VO + U              # Open rotor (navigation menu)
```

**Windows - NVDA** (Free download)

```bash
# Basic commands:
Insert + Down Arrow  # Read next
Insert + Up Arrow    # Read previous
Insert + Space       # Activate
Insert + F7          # Elements list
```

**Test Checklist**:
- [ ] All images have alt text
- [ ] Form labels read correctly
- [ ] Error messages announced
- [ ] Button purposes clear
- [ ] Page landmarks identified (header, nav, main, footer)
- [ ] Dynamic content changes announced

#### Color Contrast Test

**Browser Extension**: "WCAG Color contrast checker"

1. Install extension
2. Click icon on each page
3. Review flagged elements
4. Fix any failing contrast ratios

**Manual Check**:
- [ ] Text on backgrounds meets 4.5:1 ratio
- [ ] Button text meets 4.5:1 ratio
- [ ] Link text distinguishable without color alone
- [ ] Error messages visible in high contrast mode

#### Zoom & Responsive Test

1. Zoom browser to 200% (Cmd/Ctrl + +)
2. Check for:
   - [ ] No horizontal scrolling (except data tables)
   - [ ] Text remains readable
   - [ ] No content overlap
   - [ ] All functionality still works

---

## Component Accessibility Reference

### Button Component

```django
{% include 'components/button.html' with
    text='Submit Form'
    variant='primary'
    aria_label='Submit registration form'
    disabled=False
%}
```

**Accessibility Features**:
- Focus ring with 2px outline
- Disabled state communicated to screen readers
- Optional aria-label for additional context

### Form Field Component

```django
{% include 'components/form_field.html' with
    field=form.email
    label='Email Address'
    placeholder='you@example.com'
%}
```

**Accessibility Features**:
- Label automatically linked to input
- Required fields marked with asterisk and `aria-required`
- Errors linked via `aria-describedby`
- Help text properly associated
- Invalid state communicated via `aria-invalid`

### Modal Component

```django
{% include 'components/modal.html' with
    id='confirmModal'
    title='Confirm Action'
    content='Are you sure?'
%}

<!-- Trigger button -->
<button @click="$refs.confirmModal.showModal()">Open</button>
```

**Accessibility Features**:
- Native `<dialog>` element
- Escape key closes modal
- Focus managed properly
- Title announced to screen readers

### Alert Component

```django
{% include 'components/alert.html' with
    type='success'
    message='Account created successfully!'
    dismissible=True
%}
```

**Accessibility Features**:
- `role="alert"` for screen reader announcement
- `aria-live` region (assertive for errors, polite for others)
- Dismissible with keyboard (Tab to close button, Enter)

---

## Common Accessibility Issues to Avoid

### ❌ Don't Do This

```html
<!-- Missing alt text -->
<img src="course.jpg">

<!-- Button without label -->
<button><i class="icon"></i></button>

<!-- Clickable div (not keyboard accessible) -->
<div onclick="doSomething()">Click me</div>

<!-- Color only to convey meaning -->
<span style="color: red;">Error</span>

<!-- Form without label -->
<input type="text" placeholder="Name">
```

### ✅ Do This Instead

```html
<!-- Descriptive alt text -->
<img src="course.jpg" alt="Introduction to Recorder - Beginner Course">

<!-- Button with aria-label -->
<button aria-label="Add to cart">
    <i class="icon" aria-hidden="true"></i>
</button>

<!-- Semantic button -->
<button onclick="doSomething()">Click me</button>

<!-- Text + icon for errors -->
<span role="alert" aria-live="polite">
    <i class="error-icon" aria-hidden="true"></i>
    Error: Invalid email address
</span>

<!-- Proper label -->
<label for="name">Name</label>
<input id="name" type="text" placeholder="Enter your name">
```

---

## Continuous Testing

### Pre-Deployment Checklist

Before deploying changes that affect UI:

- [ ] Run Pa11y on affected pages
- [ ] Test with keyboard navigation
- [ ] Test with VoiceOver/NVDA (spot check)
- [ ] Check color contrast
- [ ] Test at 200% zoom
- [ ] Verify focus indicators visible

### Automated CI/CD Integration

Add to your GitHub Actions or deployment pipeline:

```yaml
# .github/workflows/accessibility.yml
name: Accessibility Tests
on: [push, pull_request]
jobs:
  a11y:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Pa11y
        run: |
          npm install -g pa11y-ci
          pa11y-ci --config .pa11yci.json
```

### Monthly Audit

Schedule monthly comprehensive audits:
- [ ] Full keyboard navigation test
- [ ] Screen reader test on key pages
- [ ] Color contrast verification
- [ ] Review new features for compliance
- [ ] Update this document with findings

---

## Resources

### Official Guidelines
- **WCAG 2.1**: https://www.w3.org/WAI/WCAG21/quickref/
- **ARIA Authoring Practices**: https://www.w3.org/WAI/ARIA/apg/

### Testing Tools
- **Pa11y**: https://pa11y.org/
- **axe DevTools**: https://www.deque.com/axe/devtools/
- **WAVE**: https://wave.webaim.org/
- **Lighthouse**: Built into Chrome DevTools

### Learning Resources
- **WebAIM**: https://webaim.org/
- **A11y Project**: https://www.a11yproject.com/
- **DaisyUI Accessibility**: https://daisyui.com/docs/accessibility/

### Screen Readers
- **VoiceOver** (macOS): Built-in (Cmd+F5)
- **NVDA** (Windows): https://www.nvaccess.org/download/
- **JAWS** (Windows): https://www.freedomscientific.com/products/software/jaws/

---

## Getting Help

If you encounter accessibility issues:

1. Check this guide for solutions
2. Test with automated tools (Pa11y, Lighthouse)
3. Consult WCAG guidelines
4. Create an issue in the project repository
5. Consider accessibility expert review for complex issues

---

## Version History

- **v1.0** (2025-12-05): Initial accessibility implementation
  - Skip navigation links
  - ARIA labels for icon buttons
  - Accessible forms with error handling
  - Keyboard-accessible modals
  - Screen reader optimized alerts
  - Focus indicators and keyboard navigation

---

**Last Updated**: December 5, 2025
**Maintained By**: Development Team
**WCAG Target**: 2.1 Level AA
