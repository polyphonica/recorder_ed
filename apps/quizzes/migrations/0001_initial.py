"""
Move quiz models from apps.private_teaching to apps.quizzes.
State-only for existing tables + real DB ops for 3 new columns + 2 nullable changes.
"""
import django.core.validators
import django.db.models.deletion
import django_ckeditor_5.fields
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0016_userprofile_workshop_email_notifications'),
        ('courses', '0022_course_courses_cou_instruc_f1fbcf_idx'),
        ('lesson_templates', '0001_initial'),
        ('lessons', '0015_update_exam_registration_fk'),
        ('private_teaching', '0037_remove_availability_models'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ------------------------------------------------------------------ #
        # Part 1 – state-only: register existing DB tables with Django        #
        # ------------------------------------------------------------------ #
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='Quiz',
                    fields=[
                        ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                        ('title', models.CharField(help_text="Quiz title (e.g., 'Grade 1 Theory Mock Exam')", max_length=200)),
                        ('description', models.TextField(blank=True, help_text='Overview of what this quiz covers')),
                        ('instructions', models.TextField(blank=True, help_text='Instructions for students taking the quiz')),
                        ('pass_percentage', models.IntegerField(default=70, help_text='Minimum percentage to pass (0-100)', validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                        ('time_limit_minutes', models.IntegerField(blank=True, help_text='Time limit in minutes (null = no limit)', null=True)),
                        ('randomize_questions', models.BooleanField(default=False, help_text='Randomize question order for each attempt')),
                        ('show_correct_answers', models.BooleanField(default=True, help_text='Show correct answers after submission')),
                        ('allow_retakes', models.BooleanField(default=True, help_text='Allow students to retake quiz')),
                        ('max_attempts', models.IntegerField(blank=True, help_text='Maximum attempts allowed (null = unlimited)', null=True)),
                        ('pagination_mode', models.CharField(choices=[('continuous', 'Continuous (Single Page)'), ('paginated', 'Paginated (One at a Time)')], default='continuous', help_text='Display mode for quiz questions', max_length=20)),
                        ('syllabus', models.CharField(blank=True, choices=[('abrsm', 'ABRSM'), ('trinity', 'Trinity College'), ('rcm', 'RCM'), ('mtb', 'Music Teachers Board'), ('custom', 'Custom')], max_length=50)),
                        ('grade_level', models.CharField(blank=True, help_text="e.g., '1', 'Beginner', 'Intermediate'", max_length=50)),
                        ('is_public', models.BooleanField(default=False, help_text='Make quiz available to other teachers')),
                        ('use_count', models.IntegerField(default=0)),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('updated_at', models.DateTimeField(auto_now=True)),
                        ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_quizzes', to=settings.AUTH_USER_MODEL)),
                        ('subject', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='private_teaching.subject')),
                        ('tags', models.ManyToManyField(blank=True, related_name='quizzes', to='lesson_templates.tag')),
                    ],
                    options={
                        'verbose_name': 'Quiz',
                        'verbose_name_plural': 'Quizzes',
                        'ordering': ['-created_at'],
                        'db_table': 'private_teaching_privatelessonquiz',
                    },
                ),
                migrations.CreateModel(
                    name='QuizQuestion',
                    fields=[
                        ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                        ('text', django_ckeditor_5.fields.CKEditor5Field(config_name='extends', help_text='Question text (supports images, music notation, etc.)')),
                        ('order', models.PositiveIntegerField(default=0)),
                        ('points', models.PositiveIntegerField(default=1, help_text='Points awarded for correct answer')),
                        ('explanation', models.TextField(blank=True, help_text='Explanation shown after answer (optional)')),
                        ('quiz', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='questions', to='quizzes.quiz')),
                    ],
                    options={
                        'verbose_name': 'Quiz Question',
                        'ordering': ['order'],
                        'db_table': 'private_teaching_privatelessonquizquestion',
                    },
                ),
                migrations.CreateModel(
                    name='QuizAnswer',
                    fields=[
                        ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                        ('text', django_ckeditor_5.fields.CKEditor5Field(config_name='default', help_text='Answer text (supports images, formatting, music notation)')),
                        ('is_correct', models.BooleanField(default=False, help_text='Mark as the correct answer')),
                        ('order', models.PositiveIntegerField(default=0)),
                        ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='answers', to='quizzes.quizquestion')),
                    ],
                    options={
                        'verbose_name': 'Quiz Answer',
                        'ordering': ['order'],
                        'db_table': 'private_teaching_privatelessonquizanswer',
                    },
                ),
                migrations.CreateModel(
                    name='QuizAssignment',
                    fields=[
                        ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                        ('assigned_date', models.DateTimeField(auto_now_add=True)),
                        ('due_date', models.DateTimeField(blank=True, help_text='Optional deadline', null=True)),
                        ('notes', models.TextField(blank=True, help_text='Teacher notes for student about this quiz')),
                        ('status', models.CharField(choices=[('assigned', 'Assigned'), ('in_progress', 'In Progress'), ('completed', 'Completed')], default='assigned', max_length=20)),
                        ('child_profile', models.ForeignKey(blank=True, help_text='If student is a guardian, specify which child', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_quizzes', to='accounts.childprofile')),
                        ('lesson', models.ForeignKey(blank=True, help_text='Link to specific private lesson (optional)', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='quiz_assignments', to='lessons.lesson')),
                        ('quiz', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assignments', to='quizzes.quiz')),
                        ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='received_quizzes', to=settings.AUTH_USER_MODEL)),
                        ('teacher', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assigned_quizzes', to=settings.AUTH_USER_MODEL)),
                    ],
                    options={
                        'verbose_name': 'Quiz Assignment',
                        'ordering': ['-assigned_date'],
                        'db_table': 'private_teaching_privatelessonquizassignment',
                    },
                ),
                migrations.CreateModel(
                    name='QuizAttempt',
                    fields=[
                        ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                        ('started_at', models.DateTimeField(auto_now_add=True)),
                        ('submitted_at', models.DateTimeField(blank=True, null=True)),
                        ('answers_data', models.JSONField(default=dict, help_text='Student answers as {question_id: answer_id}')),
                        ('score', models.DecimalField(decimal_places=2, default=0, help_text='Percentage score (0-100)', max_digits=5)),
                        ('passed', models.BooleanField(default=False)),
                        ('time_taken_minutes', models.IntegerField(blank=True, help_text='How long student took (minutes)', null=True)),
                        ('last_autosave_at', models.DateTimeField(blank=True, help_text='Timestamp of last auto-save operation', null=True)),
                        ('assignment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attempts', to='quizzes.quizassignment')),
                    ],
                    options={
                        'verbose_name': 'Quiz Attempt',
                        'ordering': ['-started_at'],
                        'db_table': 'private_teaching_privatelessonquizattempt',
                    },
                ),
                # Indexes
                migrations.AddIndex(
                    model_name='quiz',
                    index=models.Index(fields=['created_by', 'is_public'], name='private_tea_created_59baa1_idx'),
                ),
                migrations.AddIndex(
                    model_name='quiz',
                    index=models.Index(fields=['syllabus', 'grade_level'], name='private_tea_syllabu_55c321_idx'),
                ),
                migrations.AddIndex(
                    model_name='quizassignment',
                    index=models.Index(fields=['student', 'status'], name='private_tea_student_0a9066_idx'),
                ),
                migrations.AddIndex(
                    model_name='quizassignment',
                    index=models.Index(fields=['teacher', 'assigned_date'], name='private_tea_teacher_fcd363_idx'),
                ),
                migrations.AlterUniqueTogether(
                    name='quizassignment',
                    unique_together={('quiz', 'student', 'child_profile')},
                ),
                migrations.AddIndex(
                    model_name='quizattempt',
                    index=models.Index(fields=['assignment', 'submitted_at'], name='private_tea_assignm_41378e_idx'),
                ),
            ],
            database_operations=[],
        ),

        # ------------------------------------------------------------------ #
        # Part 2 – real DB operations: add new columns                        #
        # ------------------------------------------------------------------ #
        migrations.AddField(
            model_name='quiz',
            name='course_lesson',
            field=models.OneToOneField(
                blank=True,
                help_text='Course lesson this quiz is attached to (null for private lesson quizzes)',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='quiz',
                to='courses.lesson',
            ),
        ),
        migrations.AddField(
            model_name='quiz',
            name='status',
            field=models.CharField(
                blank=True,
                choices=[('draft', 'Draft'), ('published', 'Published')],
                help_text='DRAFT/PUBLISHED status (used by course quizzes only)',
                max_length=20,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name='quizassignment',
            name='teacher',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='assigned_quizzes',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name='quizassignment',
            name='student',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='received_quizzes',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='quizassignment',
            name='course_enrollment',
            field=models.ForeignKey(
                blank=True,
                help_text='Course enrollment (course context only)',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='quiz_assignments',
                to='courses.courseenrollment',
            ),
        ),
    ]
