"""
Migrate course quiz data into the unified quizzes tables.
Courses quiz models (Quiz, QuizQuestion, QuizAnswer, QuizAttempt) are read-only
historical data here; their DB tables remain until a cleanup migration.
"""
from django.db import migrations


def migrate_course_quizzes(apps, schema_editor):
    CourseQuiz = apps.get_model('courses', 'Quiz')
    CourseQuizQuestion = apps.get_model('courses', 'QuizQuestion')
    CourseQuizAnswer = apps.get_model('courses', 'QuizAnswer')
    CourseQuizAttempt = apps.get_model('courses', 'QuizAttempt')

    Quiz = apps.get_model('quizzes', 'Quiz')
    QuizQuestion = apps.get_model('quizzes', 'QuizQuestion')
    QuizAnswer = apps.get_model('quizzes', 'QuizAnswer')
    QuizAssignment = apps.get_model('quizzes', 'QuizAssignment')
    QuizAttempt = apps.get_model('quizzes', 'QuizAttempt')

    for cq in CourseQuiz.objects.select_related('lesson__topic__course').all():
        course = cq.lesson.topic.course
        instructor = course.instructor

        new_quiz = Quiz.objects.create(
            title=cq.title,
            description=cq.description,
            pass_percentage=cq.pass_percentage,
            status=cq.status,
            course_lesson=cq.lesson,
            created_by=instructor,
        )

        # Map old question id → new question object
        question_map = {}
        for qq in CourseQuizQuestion.objects.filter(quiz=cq).order_by('order'):
            new_q = QuizQuestion.objects.create(
                quiz=new_quiz,
                text=qq.text,
                order=qq.order,
                points=qq.points,
                explanation='',
            )
            question_map[str(qq.id)] = new_q

            for qa in CourseQuizAnswer.objects.filter(question=qq).order_by('order'):
                QuizAnswer.objects.create(
                    question=new_q,
                    text=qa.text,
                    is_correct=qa.is_correct,
                    order=qa.order,
                )

        # Migrate attempts → create one QuizAssignment per (quiz, enrollment) pair
        for attempt in CourseQuizAttempt.objects.filter(quiz=cq).select_related('enrollment'):
            enrollment = attempt.enrollment
            assignment, _ = QuizAssignment.objects.get_or_create(
                quiz=new_quiz,
                course_enrollment=enrollment,
                defaults={'status': 'completed'},
            )

            # Remap answers_data keys from old question IDs to new question IDs
            new_answers = {}
            for old_q_id, answer_val in (attempt.answers_data or {}).items():
                new_q = question_map.get(old_q_id)
                if new_q:
                    new_answers[str(new_q.id)] = answer_val

            QuizAttempt.objects.create(
                assignment=assignment,
                submitted_at=attempt.submitted_at,
                score=attempt.score,
                passed=attempt.passed,
                answers_data=new_answers,
            )


def reverse_migrate_course_quizzes(apps, schema_editor):
    """Delete all quizzes that have a course_lesson set (i.e., migrated from courses)."""
    Quiz = apps.get_model('quizzes', 'Quiz')
    Quiz.objects.filter(course_lesson__isnull=False).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('quizzes', '0001_initial'),
        ('courses', '0022_course_courses_cou_instruc_f1fbcf_idx'),
    ]

    operations = [
        migrations.RunPython(migrate_course_quizzes, reverse_migrate_course_quizzes),
    ]
