# Aural Training System - Implementation Plan

## Overview
Aural training system for private teaching students to develop listening skills required for music examinations. Not just playing in tune, but hearing and identifying intervals, cadences, chord progressions, rhythm patterns, and more.

## Technology Options

### **Recommended: Tone.js (built on Web Audio API)**
This is the recommended solution because:
- **Browser-based** - no plugins needed
- **Generative** - create unlimited exercises on the fly
- **Precise timing** - critical for rhythm exercises
- **Rich features** - synthesizers, samplers, effects, scheduling
- **Active community** and good documentation

Example capabilities:
- Generate any interval instantly
- Play chord progressions with proper voicing
- Control tempo, articulation, dynamics
- Use different timbres (piano, strings, etc.)

### Alternative: Pre-recorded Audio
- **Pros**: More realistic sound quality, predictable
- **Cons**: Large storage requirements, less flexible, can't randomize easily

### Hybrid Approach
- Use Tone.js for most exercises
- Pre-record specific examples for demonstration/tutorials
- Could integrate with VexFlow (which you already use) to show notation

## Feature Ideas

### **Interval Training**
- Melodic intervals (played sequentially)
- Harmonic intervals (played together)
- Ascending/descending
- Within/outside octave
- Progressive difficulty (start with 2nds/3rds, work up to 7ths)

### **Cadence Recognition**
- Perfect (V-I)
- Plagal (IV-I)
- Imperfect (I-V, ii-V, etc.)
- Interrupted/Deceptive (V-vi)
- Different keys and inversions
- Could show Roman numeral analysis after

### **Rhythm Exercises**
- Clap-back (hear rhythm, reproduce it)
- Rhythm dictation
- Identify time signature
- Syncopation recognition

### **Chord Quality**
- Major, minor, diminished, augmented
- 7th chords (major 7th, dominant 7th, etc.)
- Extended chords for advanced levels

### **Melodic Dictation**
- Short phrases (2-4 bars)
- Student notates what they hear
- Could use your existing VexFlow notation editor!
- Check against correct answer

### **Harmonic Progressions**
- Identify chord progressions (I-IV-V-I, etc.)
- Common patterns used in exam boards

## Implementation Architecture

```
┌─────────────────────────────────────────┐
│  Exercise Database                      │
│  - Type (interval, cadence, etc.)      │
│  - Difficulty level                     │
│  - Parameters (key, tempo, etc.)       │
│  - Correct answers                      │
└─────────────────────────────────────────┘
           │
           ↓
┌─────────────────────────────────────────┐
│  Student Practice Interface             │
│  - Play button                          │
│  - Answer input (buttons/notation)     │
│  - Replay/Hint options                  │
│  - Immediate feedback                   │
└─────────────────────────────────────────┘
           │
           ↓
┌─────────────────────────────────────────┐
│  Tone.js Audio Engine                   │
│  - Generate audio on demand             │
│  - Play with appropriate timbre         │
│  - Handle timing/scheduling             │
└─────────────────────────────────────────┘
           │
           ↓
┌─────────────────────────────────────────┐
│  Progress Tracking                      │
│  - Score per exercise type              │
│  - Time spent                           │
│  - Difficulty progression               │
│  - Teacher dashboard view               │
└─────────────────────────────────────────┘
```

## Practical Considerations

### **Exam Board Alignment**
- Map exercises to specific exam board requirements (ABRSM, Trinity, etc.)
- Grade-specific content (Grade 1-8)
- Mock exam mode with timed sections

### **Adaptive Learning**
- Start easy, increase difficulty based on performance
- If student gets 3 wrong in a row, give hints or easier examples
- Track weak areas and focus practice there

### **Gamification**
- Points/badges for milestones
- Daily practice streaks
- Leaderboards (optional, per class)
- Achievement unlocks

### **Teacher Features**
- Assign specific exercises as homework
- View student progress/weak spots
- Custom exercises
- Assessment mode (graded practice)

## Integration with Existing System

### Seamless Integration Points
- Use existing assignment system for aural training homework
- VexFlow for showing notation answers
- Private teaching dashboard shows aural progress
- Link from lesson plans to specific exercises

### Database Integration
- Extend existing PrivateLessonAssignment model for aural exercises
- Track progress alongside regular assignments
- Include in teacher student progress view

## Implementation Phases

### **Phase 1: Proof of Concept**
**Goal**: Validate approach with minimal viable product

**Deliverables**:
- Simple interval recognition exercise
- 10-15 practice intervals
- Basic scoring system
- Test with small group of students

**Technical Tasks**:
1. Set up Tone.js library
2. Create basic audio playback for intervals
3. Build simple UI with answer buttons
4. Implement immediate feedback
5. Basic score tracking

**Success Metrics**:
- Students can complete exercises without technical issues
- Audio quality is acceptable
- Students find it helpful
- Teachers can view results

**Estimated Effort**: 2-3 weeks

### **Phase 2: Expansion**
**Goal**: Build out core feature set

**Deliverables**:
- Add cadence recognition
- Add chord quality recognition
- Implement 3 difficulty levels per exercise type
- Progress tracking dashboard
- Exercise history

**Technical Tasks**:
1. Extend audio engine for chords and progressions
2. Create cadence playback system
3. Build difficulty progression algorithm
4. Design progress tracking database schema
5. Create student progress view
6. Add teacher assignment interface

**Success Metrics**:
- Cover major exam board requirements for Grades 1-3
- Students show measurable improvement
- Teachers actively assign exercises
- 80%+ completion rate for assigned exercises

**Estimated Effort**: 4-6 weeks

### **Phase 3: Full System**
**Goal**: Complete, production-ready aural training platform

**Deliverables**:
- All exercise types implemented
- Adaptive learning algorithm
- Comprehensive teacher tools
- Exam preparation mode
- Mobile-responsive design
- Full exam board coverage (Grades 1-8)

**Technical Tasks**:
1. Implement rhythm exercises
2. Build melodic dictation with notation input
3. Create harmonic progression exercises
4. Develop adaptive difficulty system
5. Build exam board-specific content
6. Create mock exam mode with timing
7. Implement custom exercise builder for teachers
8. Add detailed analytics and reporting
9. Performance optimization
10. Accessibility improvements

**Features**:
- **Rhythm Exercises**: Clap-back, rhythm dictation
- **Melodic Dictation**: Use VexFlow notation editor for input
- **Adaptive Learning**: Automatically adjust difficulty based on performance
- **Mock Exams**: Timed practice sessions matching real exam formats
- **Custom Exercises**: Teachers can create bespoke exercises
- **Analytics Dashboard**: Detailed student performance metrics
- **Achievement System**: Badges, streaks, milestones
- **Mobile App**: Optional native mobile version

**Success Metrics**:
- 90%+ student satisfaction
- Measurable improvement in exam results
- Teachers use it as core part of curriculum
- Students practice 3+ times per week average
- System handles 100+ concurrent users

**Estimated Effort**: 8-12 weeks

## Example Implementation Approach

### Interval Training Flow
1. Student clicks "Practice Intervals"
2. System randomly generates: root note, interval type, direction
3. Tone.js plays the two notes (melodic or harmonic)
4. Student selects answer from buttons (M2, m2, M3, m3, P4, P5, etc.)
5. Immediate feedback with correct answer shown
6. Display notation using VexFlow showing the interval
7. Option to replay or move to next
8. Track score and time

### Cadence Recognition Flow
1. Student selects "Cadence Practice"
2. System generates chord progression ending with target cadence
3. Plays progression (e.g., I - IV - V - I for perfect cadence)
4. Student identifies cadence type
5. System shows Roman numeral analysis
6. Display notation with chord symbols
7. Move to next exercise

## Database Schema (Initial Proposal)

### AuralExercise Model
```python
- id
- exercise_type (interval, cadence, chord, rhythm, melody, progression)
- difficulty_level (1-10)
- parameters (JSON field for flexible storage)
- correct_answer
- exam_board (ABRSM, Trinity, etc.)
- grade_level (1-8)
- created_by (teacher, system)
```

### AuralExerciseAttempt Model
```python
- id
- student (FK to User)
- exercise (FK to AuralExercise)
- student_answer
- is_correct (boolean)
- time_taken (seconds)
- timestamp
- replay_count
```

### AuralProgress Model
```python
- id
- student (FK to User)
- exercise_type
- current_difficulty_level
- total_attempts
- correct_attempts
- average_time
- last_practiced
- streak_days
```

### AuralAssignment Model (extends existing Assignment system)
```python
- id
- teacher (FK to User)
- student (FK to User)
- exercise_type
- difficulty_range
- target_count (number of exercises to complete)
- due_date
- completion_percentage
```

## Next Steps / Action Items

1. **Research Phase**
   - [ ] Review ABRSM Grade 1-8 aural requirements
   - [ ] Review Trinity aural requirements
   - [ ] Research competing aural training apps
   - [ ] Test Tone.js capabilities with prototype

2. **Design Phase**
   - [ ] Create wireframes for student interface
   - [ ] Design teacher dashboard mockups
   - [ ] Plan database schema in detail
   - [ ] Design audio generation architecture

3. **Development Phase 1**
   - [ ] Set up Tone.js in project
   - [ ] Create simple interval exercise
   - [ ] Build basic UI
   - [ ] Implement scoring
   - [ ] User testing

4. **Decisions Needed**
   - Which exam board(s) to prioritize?
   - Which exercise types for Phase 1?
   - Mobile-first or desktop-first design?
   - Integration with existing assignment system or separate module?

## Resources

### Libraries
- **Tone.js**: https://tonejs.github.io/
- **VexFlow**: https://github.com/0xfe/vexflow (already in use)
- **Web Audio API**: https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API

### Reference Materials
- ABRSM Aural Training Requirements: https://gb.abrsm.org/en/our-exams/
- Trinity College London: https://www.trinitycollege.com/qualifications/music
- Music Theory: intervals, cadences, chord progressions

### Similar Tools (for research)
- musictheory.net
- teoria.com
- Auralia
- EarMaster

## Notes

- Consider starting with Grade 1-3 content for Phase 1
- May want to add recording capability for rhythm clap-back exercises
- Could integrate with speech recognition for singing exercises in future
- Consider accessibility: visual indicators for audio playback, keyboard navigation
- Think about offline mode for mobile app (Phase 3)
