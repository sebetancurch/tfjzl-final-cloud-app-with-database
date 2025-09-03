from django.shortcuts import render
from django.http import HttpResponseRedirect
# <HINT> Import any new Models here
from .models import Course, Enrollment, Exam, Question, Choice, Submission
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import generic
from django.contrib.auth import login, logout, authenticate
import logging
# Get an instance of a logger
logger = logging.getLogger(__name__)
# Create your views here.


def registration_request(request):
    context = {}
    if request.method == 'GET':
        return render(request, 'onlinecourse/user_registration_bootstrap.html', context)
    elif request.method == 'POST':
        # Check if user exists
        username = request.POST['username']
        password = request.POST['psw']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']
        user_exist = False
        try:
            User.objects.get(username=username)
            user_exist = True
        except:
            logger.error("New user")
        if not user_exist:
            user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name,
                                            password=password)
            login(request, user)
            return redirect("onlinecourse:index")
        else:
            context['message'] = "User already exists."
            return render(request, 'onlinecourse/user_registration_bootstrap.html', context)


def login_request(request):
    context = {}
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['psw']
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('onlinecourse:index')
        else:
            context['message'] = "Invalid username or password."
            return render(request, 'onlinecourse/user_login_bootstrap.html', context)
    else:
        return render(request, 'onlinecourse/user_login_bootstrap.html', context)


def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')


def check_if_enrolled(user, course):
    is_enrolled = False
    if user.id is not None:
        # Check if user enrolled
        num_results = Enrollment.objects.filter(user=user, course=course).count()
        if num_results > 0:
            is_enrolled = True
    return is_enrolled


# CourseListView
class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        user = self.request.user
        courses = Course.objects.order_by('-total_enrollment')[:10]
        for course in courses:
            if user.is_authenticated:
                course.is_enrolled = check_if_enrolled(user, course)
        return courses


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_detail_bootstrap.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.object
        exams = Exam.objects.filter(course=course)
        context['exams'] = exams
        return context

def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    is_enrolled = check_if_enrolled(user, course)
    if not is_enrolled and user.is_authenticated:
        # Create an enrollment
        Enrollment.objects.create(user=user, course=course, mode='honor')
        course.total_enrollment += 1
        course.save()

    return HttpResponseRedirect(reverse(viewname='onlinecourse:course_details', args=(course.id,)))

def take_exam(request, exam_id):
    exam = get_object_or_404(Exam, pk=exam_id)
    questions = []
    exam_questions = Question.objects.filter(exam=exam)
    for question in exam_questions:
        choices = Choice.objects.filter(question=question)
        questions.append({'question': question, 'choices': choices})
    course = get_object_or_404(Course, pk=exam.course.id)
    context = {
        'questions': questions,
        'course_id': course.id
    }
    return render(request, 'onlinecourse/exam_bootstrap.html', context)


def submit(request, course_id):
    user = request.user
    course = Course.objects.get(id=course_id)
    enrollment =Enrollment.objects.get(user=user, course=course)
    selected_choices = request.POST
    new_submission = Submission(enrollment=enrollment)
    new_submission.save()
    for key, values in selected_choices.lists():
        if key == 'csrfmiddlewaretoken':
            continue
        choice_ids = list(map(int, values))
        for choice_id in choice_ids:
            choice = Choice.objects.get(id=choice_id)
            new_submission.choices.add(choice)
    return HttpResponseRedirect(reverse(viewname='onlinecourse:show_exam_result', args=(new_submission.id,)))


def show_exam_result(request, submission_id):
    submission = Submission.objects.get(id=submission_id)
    enrollment = submission.enrollment
    questions = set()
    for choice in submission.choices:
        choice = choice
        choice_question = choice.question
        questions.add(choice_question)
    exam_grade = sum(question_to_grade.grade for question_to_grade in questions)
    question_choices = []
    for question in questions:
        choices_ = Choice.objects.filter(question=question)
        choices_submission = []
        grade_submitted = 0
        for question_choice in choices_:
            isSelected = Submission.objects.filter(choices=question_choice).exists()
            isCorrect = question_choice.is_correct
            if isSelected and isCorrect:
                grade_submitted += question.grade
            choices_submission.append({'text': question_choice.text, 'isSelected': isSelected, 'isCorrect': isCorrect})
        question_choices.append({'question': question, 'choices': choices_submission})
    grade = int((100*grade_submitted)/exam_grade)
    context = {
        'questions': question_choices,
        'grade': str(grade),
        'course': enrollment.course
    }
    return render(request, 'onlinecourse/exam_result_bootstrap.html', context)


# 404 Not found error view
def error_404(request, exception):
    return render(request, 'onlinecourse/not_found.html', status=404)

# 403 Not authorized 
def error_403(request, exception):
    return render(request, 'onlinecourse/not_authorized.html', status=403)