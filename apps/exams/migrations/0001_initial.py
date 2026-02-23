"""
State-only migration: register ExamBoard, ExamRegistration, ExamPiece in the exams app.

The underlying tables are 'private_teaching_examboard',
'private_teaching_examregistration', and 'private_teaching_exampiece' (unchanged).
No database operations are performed.
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '__first__'),
        ('audioplayer', '__first__'),
        ('private_teaching', '0035_remove_practiceentry'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='ExamBoard',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('name', models.CharField(
                            choices=[
                                ('abrsm', 'ABRSM (Associated Board of the Royal Schools of Music)'),
                                ('trinity', 'Trinity College London'),
                                ('mtb', "Music Teachers' Board"),
                            ],
                            help_text='Examination board name',
                            max_length=50,
                            unique=True,
                        )),
                        ('description', models.TextField(blank=True, help_text='Description of the examination board')),
                        ('website', models.URLField(blank=True, help_text='Official website URL')),
                        ('is_active', models.BooleanField(default=True, help_text='Whether this board is currently available for selection')),
                    ],
                    options={
                        'verbose_name': 'Examination Board',
                        'verbose_name_plural': 'Examination Boards',
                        'ordering': ['name'],
                        'db_table': 'private_teaching_examboard',
                    },
                ),
                migrations.CreateModel(
                    name='ExamRegistration',
                    fields=[
                        ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                        # PayableModel fields
                        ('child_profile', models.ForeignKey(
                            blank=True,
                            help_text='If for a child, link to their child profile',
                            null=True,
                            on_delete=django.db.models.deletion.SET_NULL,
                            related_name='%(app_label)s_%(class)s_set',
                            to='accounts.childprofile',
                        )),
                        ('payment_status', models.CharField(
                            choices=[
                                ('not_required', 'Not Required'),
                                ('pending', 'Pending Payment'),
                                ('completed', 'Payment Completed'),
                                ('failed', 'Payment Failed'),
                            ],
                            default='not_required',
                            help_text='Current payment status',
                            max_length=20,
                        )),
                        ('payment_amount', models.DecimalField(
                            decimal_places=2,
                            default=0.0,
                            help_text='Amount paid or to be paid',
                            max_digits=10,
                        )),
                        ('stripe_payment_intent_id', models.CharField(
                            blank=True,
                            help_text='Stripe PaymentIntent ID for tracking',
                            max_length=255,
                        )),
                        ('stripe_checkout_session_id', models.CharField(
                            blank=True,
                            help_text='Stripe Checkout Session ID',
                            max_length=255,
                        )),
                        ('paid_at', models.DateTimeField(
                            blank=True,
                            help_text='Timestamp when payment was completed',
                            null=True,
                        )),
                        # ExamRegistration-specific fields
                        ('grade_type', models.CharField(
                            choices=[
                                ('practical', 'Practical Grade'),
                                ('performance', 'Performance Grade'),
                                ('theory', 'Music Theory'),
                            ],
                            help_text='Type of exam (Practical, Performance, or Theory)',
                            max_length=20,
                        )),
                        ('grade_level', models.PositiveIntegerField(help_text='Grade level (1-8 for Practical/Performance, 1-6 for Theory)')),
                        ('exam_date', models.DateField(blank=True, help_text='Date of the exam', null=True)),
                        ('submission_deadline', models.DateField(blank=True, help_text='Deadline for submitting recordings/videos', null=True)),
                        ('registration_number', models.CharField(blank=True, help_text='Registration number from the exam board', max_length=100)),
                        ('venue', models.CharField(blank=True, help_text='Exam venue or submission method', max_length=200)),
                        ('scales', models.TextField(blank=True, help_text='Required scales')),
                        ('arpeggios', models.TextField(blank=True, help_text='Required arpeggios')),
                        ('sight_reading', models.TextField(blank=True, help_text='Sight reading requirements or notes')),
                        ('aural_tests', models.TextField(blank=True, help_text='Aural test requirements or notes')),
                        ('status', models.CharField(
                            choices=[
                                ('registered', 'Registered'),
                                ('submitted', 'Exam Submitted'),
                                ('results_received', 'Results Received'),
                            ],
                            default='registered',
                            help_text='Current exam status',
                            max_length=20,
                        )),
                        ('mark_achieved', models.PositiveIntegerField(blank=True, help_text='Numerical mark achieved', null=True)),
                        ('grade_achieved', models.CharField(
                            blank=True,
                            choices=[
                                ('pass', 'Pass'),
                                ('merit', 'Merit'),
                                ('distinction', 'Distinction'),
                                ('fail', 'Fail'),
                            ],
                            help_text='Grade achieved',
                            max_length=20,
                        )),
                        ('examiner_comments', models.TextField(blank=True, help_text='Comments from the examiner')),
                        ('certificate_received_date', models.DateField(blank=True, help_text='Date when certificate was received', null=True)),
                        ('fee_amount', models.DecimalField(decimal_places=2, default=0.0, help_text='Exam registration fee set by teacher', max_digits=8)),
                        ('teacher_notes', models.TextField(blank=True, help_text='Private teacher notes about this exam')),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('updated_at', models.DateTimeField(auto_now=True)),
                        ('exam_board', models.ForeignKey(
                            help_text='Examination board',
                            on_delete=django.db.models.deletion.PROTECT,
                            related_name='exam_registrations',
                            to='exams.examboard',
                        )),
                        ('student', models.ForeignKey(
                            help_text='For adults: the student. For children: the guardian/parent.',
                            on_delete=django.db.models.deletion.CASCADE,
                            related_name='exam_registrations',
                            to=settings.AUTH_USER_MODEL,
                        )),
                        ('subject', models.ForeignKey(
                            help_text='Subject/instrument for the exam',
                            on_delete=django.db.models.deletion.CASCADE,
                            related_name='exam_registrations',
                            to='private_teaching.subject',
                        )),
                        ('teacher', models.ForeignKey(
                            help_text='Teacher registering the student for the exam',
                            on_delete=django.db.models.deletion.CASCADE,
                            related_name='student_exam_registrations',
                            to=settings.AUTH_USER_MODEL,
                        )),
                    ],
                    options={
                        'verbose_name': 'Exam Registration',
                        'verbose_name_plural': 'Exam Registrations',
                        'ordering': ['-exam_date', '-created_at'],
                        'db_table': 'private_teaching_examregistration',
                        'indexes': [
                            models.Index(fields=['teacher', 'exam_date'], name='private_tea_teacher_e9ebce_idx'),
                            models.Index(fields=['student', 'exam_date'], name='private_tea_student_a03a98_idx'),
                            models.Index(fields=['exam_board', 'grade_type', 'grade_level'], name='private_tea_exam_bo_e9e288_idx'),
                        ],
                    },
                ),
                migrations.CreateModel(
                    name='ExamPiece',
                    fields=[
                        ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                        ('piece_number', models.PositiveIntegerField(help_text='Piece number in the exam (1, 2, 3, 4, etc.)')),
                        ('title', models.CharField(help_text='Title of the piece', max_length=200)),
                        ('composer', models.CharField(help_text='Composer name', max_length=200)),
                        ('syllabus_list', models.CharField(blank=True, help_text="Syllabus list (e.g., 'A', 'B', 'C', 'Own Choice')", max_length=50)),
                        ('playalong_piece', models.ForeignKey(
                            blank=True,
                            help_text='Link to playalong piece for practice',
                            null=True,
                            on_delete=django.db.models.deletion.SET_NULL,
                            related_name='exam_pieces',
                            to='audioplayer.piece',
                        )),
                        ('teacher_notes', models.TextField(blank=True, help_text='Teacher notes about practice progress or readiness')),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('updated_at', models.DateTimeField(auto_now=True)),
                        ('exam_registration', models.ForeignKey(
                            help_text='Exam registration this piece belongs to',
                            on_delete=django.db.models.deletion.CASCADE,
                            related_name='pieces',
                            to='exams.examregistration',
                        )),
                    ],
                    options={
                        'verbose_name': 'Exam Piece',
                        'verbose_name_plural': 'Exam Pieces',
                        'ordering': ['piece_number'],
                        'db_table': 'private_teaching_exampiece',
                        'unique_together': {('exam_registration', 'piece_number')},
                        'indexes': [
                            models.Index(fields=['exam_registration', 'piece_number'], name='private_tea_exam_re_40107e_idx'),
                        ],
                    },
                ),
            ],
            database_operations=[],
        ),
    ]
