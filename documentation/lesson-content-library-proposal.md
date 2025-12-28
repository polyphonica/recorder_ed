# Lesson Content Library Feature Proposal

**Status:** Proposed
**Date:** December 28, 2024
**Author:** Feature Planning Discussion

## Overview

A Lesson Content Library would allow teachers to create, organize, and reuse lesson content templates across multiple students and courses. This is particularly valuable for standardized syllabi (ABRSM, Trinity, etc.) where the same lesson structure is repeated for multiple students.

## Use Case Scenario

1. Teacher teaches Grade 1 theory to a syllabus (e.g., ABRSM)
2. The teacher covers Grade 1 in 8 lessons
3. The teacher requests the student book all 8 lessons in advance
4. The teacher goes into each lesson and inserts pre-written content from the Lesson Content Library
5. The teacher can customize the content for each specific student if needed

---

## Current State vs. Proposed Solution

### Current Workflow

- **Manual Creation**: Teacher creates/updates each lesson individually
- **Copy/Paste**: Content must be manually copied/pasted or retyped for similar lessons
- **No Centralization**: No centralized repository of reusable lesson content
- **Inconsistency Risk**: Consistency across similar lessons requires manual effort
- **Time-Consuming**: Creating 8 similar lessons takes hours of repetitive work

### Proposed Workflow

- **Template Library**: Teacher creates lesson content templates in a centralized library
- **Organization**: Templates organized by subject, grade level, syllabus (ABRSM, Trinity, etc.)
- **One-Click Insertion**: Easy insertion of template content into lessons
- **Central Maintenance**: Update templates centrally, optionally apply to existing lessons
- **Efficiency**: Create 8 lessons in minutes instead of hours

---

## UX Design Considerations

### 1. Lesson Content Library Interface

Design following the same patterns as Assignment Library and Play-along Library:

```
┌─────────────────────────────────────────────────────────┐
│  Lesson Content Library                                 │
│  ┌─────────────────────────────────────────────────┐   │
│  │ [+ Create Template]  [View My Templates]        │   │
│  └─────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────┤
│  View Mode: [My Templates] [Browse All]                │
├─────────────────────────────────────────────────────────┤
│  Filters:                                               │
│  Search: [_________________________________]            │
│  Subject:   [All Subjects ▼]                           │
│  Syllabus:  [ABRSM/Trinity/Custom ▼]                   │
│  Grade:     [1-8 ▼]                                    │
│  Lesson #:  [1-12 ▼]                                   │
│  Tags:      [All Tags ▼]                               │
│  [Apply Filters] [Clear]                               │
├─────────────────────────────────────────────────────────┤
│  Results: 12 templates                                  │
│                                                         │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐  │
│  │ ABRSM        │ │ Trinity      │ │ ABRSM        │  │
│  │ Grade 1      │ │ Grade 2      │ │ Grade 1      │  │
│  │ Lesson 1     │ │ Lesson 1     │ │ Lesson 2     │  │
│  │              │ │              │ │              │  │
│  │ Intro to     │ │ Rhythm       │ │ Note         │  │
│  │ Notation     │ │ Patterns     │ │ Reading      │  │
│  │              │ │              │ │              │  │
│  │ [Preview]    │ │ [Preview]    │ │ [Preview]    │  │
│  │ [Edit]       │ │ [Edit]       │ │ [Edit]       │  │
│  │ [Use This]   │ │ [Use This]   │ │ [Use This]   │  │
│  └──────────────┘ └──────────────┘ └──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

**Key Features:**
- Grid layout with card-based design
- Search and multiple filter options
- Preview capability before using
- Direct edit access
- "Use This" button for quick insertion

### 2. Template Creation/Edit Form

```
┌─────────────────────────────────────────────────────┐
│ Create Lesson Content Template                     │
├─────────────────────────────────────────────────────┤
│                                                     │
│ Title: [ABRSM Grade 1 - Lesson 1: Introduction to  │
│         Notation                                ]   │
│                                                     │
│ Categorization:                                     │
│ Subject:  [Recorder ▼]                             │
│ Syllabus: [ABRSM ▼]                                │
│ Grade:    [1 ▼]                                    │
│ Lesson #: [1 ▼]                                    │
│ Tags:     [Notation] [Basics] [+ Add Tag]          │
│                                                     │
│ Visibility:                                         │
│ ☐ Make Public (share with other teachers)          │
│                                                     │
│ ─────────────────────────────────────────────────  │
│                                                     │
│ Content:                                            │
│ ┌─────────────────────────────────────────────┐   │
│ │ [CKEditor with full toolbar]                │   │
│ │                                             │   │
│ │ Lesson 1: Introduction to Music Notation   │   │
│ │                                             │   │
│ │ **Objectives:**                             │   │
│ │ - Understand the staff                      │   │
│ │ - Learn note names                          │   │
│ │                                             │   │
│ │ **Theory Concepts:**                        │   │
│ │ 1. The musical staff...                     │   │
│ │                                             │   │
│ │ **Practice Exercises:**                     │   │
│ │ - Note identification worksheet             │   │
│ │                                             │   │
│ │ **Homework:**                               │   │
│ │ - Complete pages 1-3 in workbook            │   │
│ └─────────────────────────────────────────────┘   │
│                                                     │
│ ─────────────────────────────────────────────────  │
│                                                     │
│ Linked Resources (Optional):                        │
│ Assignments:   [+ Add Assignment]                   │
│ Play-alongs:   [+ Add Piece]                        │
│ Documents:     [+ Add Document]                     │
│                                                     │
│ ─────────────────────────────────────────────────  │
│                                                     │
│ [Cancel] [Preview] [Save Template]                 │
└─────────────────────────────────────────────────────┘
```

### 3. Insertion into Lessons

**Option A: Sidebar Panel in Lesson Update**

```
┌────────────────────────────────────────────────────────┐
│ Update Lesson for John Smith (Dec 15, 2024)          │
├─────────────────────────┬──────────────────────────────┤
│                         │                              │
│ Lesson Content:         │ 📚 Template Library         │
│ ┌─────────────────────┐│ ┌──────────────────────────┐│
│ │ [CKEditor]          ││ │ [Search templates...]    ││
│ │                     ││ │                          ││
│ │ [Current content]   ││ │ ABRSM Grade 1 - Lesson 1││
│ │                     ││ │ Introduction to Notation││
│ │                     ││ │ [Preview] [Insert]      ││
│ │                     ││ │                          ││
│ │                     ││ │ ABRSM Grade 1 - Lesson 2││
│ │                     ││ │ Note Reading            ││
│ │                     ││ │ [Preview] [Insert]      ││
│ │                     ││ │                          ││
│ └─────────────────────┘│ │ [Browse All Templates]   ││
│                         │ └──────────────────────────┘│
│                         │                              │
└─────────────────────────┴──────────────────────────────┘
```

**Option B: Modal Popup**

```
[📚 Insert Template] button → Opens modal:

┌─────────────────────────────────────────────────┐
│ Select Template                          [×]    │
├─────────────────────────────────────────────────┤
│ Search: [_______________________] [🔍]          │
│                                                 │
│ Filters: [Subject ▼] [Syllabus ▼] [Grade ▼]   │
│                                                 │
│ ┌─────────────────────────────────────────┐   │
│ │ ⭐ ABRSM Grade 1 - Lesson 1            │   │
│ │   Introduction to Notation              │   │
│ │                                         │   │
│ │   [Preview] [Insert]                    │   │
│ ├─────────────────────────────────────────┤   │
│ │   ABRSM Grade 1 - Lesson 2             │   │
│ │   Note Reading                          │   │
│ │                                         │   │
│ │   [Preview] [Insert]                    │   │
│ └─────────────────────────────────────────┘   │
│                                                 │
│ Insert Mode:                                    │
│ ○ Replace current content                      │
│ ○ Append to current content                    │
│ ○ Prepend to current content                   │
│                                                 │
│             [Cancel] [Insert Selected]          │
└─────────────────────────────────────────────────┘
```

**Option C: Bulk Lesson Creation Wizard**

```
┌─────────────────────────────────────────────────┐
│ Create Lesson Series                            │
├─────────────────────────────────────────────────┤
│ Step 1: Select Template Series                  │
│                                                 │
│ Template Series: [ABRSM Grade 1 Full Course ▼] │
│                                                 │
│ This will create 8 lessons:                     │
│ ✓ Lesson 1: Introduction to Notation           │
│ ✓ Lesson 2: Note Reading                       │
│ ✓ Lesson 3: Rhythm Basics                      │
│ ... (5 more)                                    │
│                                                 │
│ ─────────────────────────────────────────────   │
│ Step 2: Configure Lessons                       │
│                                                 │
│ Student: [John Smith ▼]                         │
│ Subject: [Recorder - Grade 1 Theory]            │
│                                                 │
│ Lesson Dates:                                   │
│ ○ Use existing scheduled lessons (8 found)     │
│ ○ Create new lesson schedule                   │
│                                                 │
│            [Back] [Cancel] [Create 8 Lessons]   │
└─────────────────────────────────────────────────┘
```

---

## Recommended Implementation Approach

### Phase 1: MVP (Minimum Viable Product)

**Goal:** Basic template creation, library, and insertion functionality

#### 1. Database Models

```python
class LessonContentTemplate(models.Model):
    """
    Reusable lesson content templates
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    # Basic Information
    title = models.CharField(max_length=200)
    content = CKEditor5Field(config_name='default')

    # Categorization
    subject = models.ForeignKey(
        Subject,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    syllabus = models.CharField(
        max_length=50,
        choices=[
            ('abrsm', 'ABRSM'),
            ('trinity', 'Trinity College'),
            ('rcm', 'RCM'),
            ('custom', 'Custom'),
        ],
        blank=True
    )
    grade_level = models.CharField(
        max_length=10,
        blank=True,
        help_text="e.g., '1', '2', 'Beginner', 'Intermediate'"
    )
    lesson_number = models.IntegerField(
        null=True,
        blank=True,
        help_text="Position in course sequence (1-12, etc.)"
    )

    # Tagging
    tags = models.ManyToManyField('Tag', blank=True)

    # Sharing
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    is_public = models.BooleanField(
        default=False,
        help_text="Share with other teachers"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['syllabus', 'grade_level', 'lesson_number', 'title']
        indexes = [
            models.Index(fields=['created_by', '-created_at']),
            models.Index(fields=['syllabus', 'grade_level', 'lesson_number']),
        ]

class Tag(models.Model):
    """Tags for categorizing templates"""
    name = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
```

#### 2. Views

```python
# Similar to Assignment Library pattern

@login_required
def template_library(request):
    """
    Teacher's library of lesson content templates
    with search and filters
    """
    # Search and filter logic (similar to assignment_library)
    # View modes: my_templates / browse_all
    pass

@login_required
def template_create(request):
    """Create new template"""
    pass

@login_required
def template_edit(request, pk):
    """Edit existing template"""
    pass

@login_required
def template_preview(request, pk):
    """Preview template content"""
    pass
```

#### 3. Forms

```python
class LessonContentTemplateForm(forms.ModelForm):
    new_tags = forms.CharField(
        required=False,
        help_text='Create new tags (comma-separated)'
    )

    class Meta:
        model = LessonContentTemplate
        fields = [
            'title',
            'content',
            'subject',
            'syllabus',
            'grade_level',
            'lesson_number',
            'tags',
            'is_public',
        ]
```

#### 4. UI Templates

Create templates following Assignment Library pattern:
- `template_library.html` - Main library view with grid layout
- `template_create.html` - Create new template
- `template_edit.html` - Edit template
- `template_preview.html` - Preview template content

#### 5. Integration with Lesson Update

Add "Insert Template" functionality to lesson update form:

```javascript
// JavaScript to handle template insertion
function insertTemplate(templateId, mode) {
    // Fetch template content via AJAX
    // Insert into CKEditor based on mode (replace/append/prepend)
    // Show success message
}
```

**Implementation Time Estimate:** 2-3 days

---

### Phase 2: Enhanced Features

**Goal:** Improve usability and add template variables

#### 1. Template Variables

Support dynamic placeholders:

```python
# Template content:
"Hello {{student_name}}, today we'll work on {{topic}}..."

# When inserted, replace with:
"Hello John Smith, today we'll work on scales..."
```

Variables to support:
- `{{student_name}}`
- `{{student_first_name}}`
- `{{lesson_date}}`
- `{{next_lesson_date}}`
- `{{teacher_name}}`
- `{{subject_name}}`
- `{{grade_level}}`

#### 2. Bulk Lesson Creation

Create multiple lessons at once using a template sequence:

```python
@login_required
def bulk_create_lessons_from_templates(request):
    """
    Create multiple lessons using a template series
    """
    # Select template series (e.g., "ABRSM Grade 1 Full Course")
    # Select student and subject
    # Map templates to lesson dates
    # Create all lessons with pre-populated content
    pass
```

#### 3. Resource Linking

Track which resources should be added with each template:

```python
class TemplateResourceLink(models.Model):
    """Links assignments/pieces to templates"""
    template = models.ForeignKey(LessonContentTemplate)
    assignment = models.ForeignKey(Assignment, null=True, blank=True)
    piece = models.ForeignKey(Piece, null=True, blank=True)
    order = models.IntegerField(default=0)
```

When template is inserted:
1. Show list of linked resources
2. Allow teacher to select which to add
3. Auto-create associations to lesson

**Implementation Time Estimate:** 3-4 days

---

### Phase 3: Advanced Features

**Goal:** Template marketplace and collaboration

#### 1. Template Sharing Marketplace

- Public template gallery
- Rating and review system
- Download/use count tracking
- Featured templates
- Template collections (e.g., "Complete ABRSM Grade 1-3")

#### 2. Version Control

- Track template versions (v1.0, v1.1, etc.)
- "Update all lessons using this template" feature
- Diff view showing changes between versions
- Rollback capability

#### 3. Collaborative Editing

- Share templates with specific teachers
- Co-editing capability
- Comments and suggestions
- Template approval workflow for institutions

#### 4. Analytics

- Most popular templates
- Usage statistics
- Effectiveness tracking
- A/B testing different template versions

**Implementation Time Estimate:** 1-2 weeks

---

## Recommendation

### Immediate Action

**Implement Phase 1 (MVP)** following the proven patterns from the Assignment Library and Play-along Library implementations.

**Why now:**
1. **Code reuse**: The Assignment Library code provides a perfect blueprint
2. **UI consistency**: Users already familiar with library interface pattern
3. **Quick win**: Basic functionality delivers immediate value
4. **Foundation**: Sets up architecture for future enhancements

### Implementation Priority

```
High Priority (Phase 1):
├─ Template model and database
├─ Library view (search, filter, grid layout)
├─ Create/Edit/Preview templates
└─ Basic insertion into lessons

Medium Priority (Phase 2):
├─ Template variables
├─ Bulk lesson creation
└─ Resource linking

Low Priority (Phase 3):
├─ Marketplace features
├─ Version control
└─ Advanced collaboration
```

### Success Metrics

After Phase 1, measure:
- **Adoption rate**: % of teachers creating templates
- **Time savings**: Lesson creation time before/after
- **Template reuse**: Average times each template is used
- **User satisfaction**: Teacher feedback and feature requests

### Technical Considerations

1. **Database**: Add new `lesson_content_templates` app
2. **Permissions**: Teachers can only edit their own templates (unless public)
3. **Storage**: CKEditor content stored as HTML (same as lessons)
4. **Navigation**: Add "Lesson Templates" to "Resources" menu
5. **Icons**: Use 📚 or similar for template-related features

---

## Comparison to Existing Features

This feature complements existing functionality:

| Feature | Assignment Library | Play-along Library | **Lesson Templates** |
|---------|-------------------|-------------------|---------------------|
| **Purpose** | Reusable assignments | Reusable audio pieces | Reusable lesson content |
| **Content Type** | Notation/Written tasks | Multi-track audio + sheet music | Rich text lesson plans |
| **Usage** | Assign to students | Add to lessons | Populate lesson content |
| **Categorization** | Tags, difficulty, grading | Composer, grade, genre | Syllabus, grade, lesson # |
| **Sharing** | Public/Private | Public/Private | Public/Private |

All three follow the same **library pattern**, making implementation straightforward and user experience consistent.

---

## Next Steps

1. **Review this proposal** with stakeholders
2. **Prioritize Phase 1** features vs. other development
3. **Create detailed mockups** for UI/UX review
4. **Estimate development timeline** (suggested: 2-3 days for Phase 1)
5. **Plan testing strategy** with actual teachers
6. **Implement Phase 1** using Assignment Library as template
7. **Gather feedback** and iterate before Phase 2

---

## Appendix: Technical Implementation Notes

### URL Structure
```
/lesson-templates/                      # Library view
/lesson-templates/create/               # Create template
/lesson-templates/<uuid>/edit/          # Edit template
/lesson-templates/<uuid>/preview/       # Preview template
/lesson-templates/<uuid>/duplicate/     # Duplicate template
```

### API Endpoints (for AJAX)
```
/api/lesson-templates/<uuid>/content/   # Get template content
/api/lesson-templates/search/           # Search templates
```

### File Structure
```
apps/
  lesson_templates/
    models.py          # LessonContentTemplate, Tag
    views.py           # CRUD views
    forms.py           # TemplateForm
    urls.py            # URL patterns
    templates/
      lesson_templates/
        library.html   # Main library view
        create.html    # Create form
        edit.html      # Edit form
        preview.html   # Preview modal
```

---

**Document Status:** Ready for review and approval
**Next Review Date:** TBD
**Implementation Target:** TBD
