import pandas as pd
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Count, Avg
from .models import *
import csv
from django.http import HttpResponse


from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from django.http import FileResponse
import io


from .forms import StudentProfileForm

# Helper role checks
def is_student(user):
    return hasattr(user, 'profile') and user.profile.role == 'student'

def is_faculty(user):
    return hasattr(user, 'profile') and user.profile.role == 'faculty'

def redirect_role_based(user):
    try:
        role = user.profile.role
        if role == 'student':
            return redirect('student_dashboard')
        elif role == 'faculty':
            return redirect('faculty_dashboard')
    except Profile.DoesNotExist:
        pass
    return redirect('login')

# Public views
def login_view(request):
    if request.user.is_authenticated:
        return redirect_role_based(request.user)
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user is not None:
            login(request, user)
            return redirect_role_based(user)
        else:
            messages.error(request, "Invalid username or password")
    return render(request, 'login.html')

def register(request):
    if Department.objects.count() == 0:
        Department.objects.create(name="General")
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        role = request.POST.get('role')
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect('register')
        user = User.objects.create_user(username=username, password=password)
        Profile.objects.create(user=user, role=role)
        if role == 'student':
            default_dept = Department.objects.first()
            Student.objects.create(
                user=user,
                reg_no=user.username,   # username as reg_no
                semester=1,
                department=default_dept
            )
        messages.success(request, "Account created successfully! Please login.")
        return redirect('login')
    return render(request, 'register.html')

@login_required
@user_passes_test(is_student, login_url='login')
def edit_profile(request):
    student = get_object_or_404(Student, user=request.user)
    if request.method == 'POST':
        form = StudentProfileForm(request.POST, request.FILES, instance=student, user=request.user)
        if form.is_valid():
            # Update User model fields
            user = request.user
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.email = form.cleaned_data['email']
            user.save()
            # Save student profile (includes image, signature, etc.)
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('student_dashboard')
        else:
            # Print form errors to debug
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = StudentProfileForm(instance=student, user=request.user)
    return render(request, 'edit_profile.html', {'form': form, 'student': student})



@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

# Student dashboard
@login_required
@user_passes_test(is_student, login_url='login')
def student_dashboard(request):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        dept = Department.objects.first()
        if not dept:
            dept = Department.objects.create(name="General")
        student = Student.objects.create(
            user=request.user,
            reg_no=request.user.username,
            semester=1,
            department=dept
        )
        messages.info(request, "Your student profile was automatically created.")
    
    results = Result.objects.filter(student=student).select_related('subject')
    
    # Build dictionaries required by the template
    semesters = {}
    semester_gpa = {}
    for r in results:
        sem = r.semester
        semesters.setdefault(sem, []).append(r)
    
    for sem, res_list in semesters.items():
        sgpa = round(sum(r.grade_point for r in res_list) / len(res_list), 2) if res_list else 0
        semester_gpa[sem] = sgpa
    
    overall_sgpa = round(sum(semester_gpa.values()) / len(semester_gpa), 2) if semester_gpa else 0
    notifications = Notification.objects.filter(user=request.user)
    
    return render(request, 'student_dashboard.html', {
        'student': student,
        'semesters': semesters,
        'semester_gpa': semester_gpa,
        'overall_sgpa': overall_sgpa,
        'notifications': notifications
    })




# Faculty dashboard (unchanged)
@login_required
@user_passes_test(is_faculty, login_url='login')
def faculty_dashboard(request):
    students = Student.objects.select_related('department', 'user').all()
    total_students = students.count()
    total_results = Result.objects.count()
    return render(request, 'faculty_dashboard.html', {
        'students': students,
        'total_students': total_students,
        'total_results': total_results
    })

# Upload (unchanged)
@login_required
@user_passes_test(is_faculty, login_url='login')
def upload(request):
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        try:
            df = pd.read_excel(file)
            required_cols = {'RegNo', 'Subject', 'Sem', 'Grade', 'GP'}
            if not required_cols.issubset(df.columns):
                messages.error(request, f"Excel must contain columns: {required_cols}")
                return redirect('upload')
            for _, row in df.iterrows():
                try:
                    student = Student.objects.get(reg_no=row['RegNo'])
                except Student.DoesNotExist:
                    messages.warning(request, f"Student {row['RegNo']} not found, skipped")
                    continue
                subject, _ = Subject.objects.get_or_create(
                    code=row['Subject'],
                    defaults={'name': row['Subject'], 'credits': 3}
                )
                Result.objects.update_or_create(
                    student=student,
                    subject=subject,
                    semester=int(row['Sem']),
                    defaults={
                        'grade': row['Grade'],
                        'grade_point': float(row['GP']),
                        'is_pass': row['Grade'] != 'F'
                    }
                )
                Notification.objects.create(
                    user=student.user,
                    message=f"Result for {subject.name} (Sem {row['Sem']}) published: {row['Grade']}"
                )
            messages.success(request, "Results uploaded successfully!")
        except Exception as e:
            messages.error(request, f"Error processing file: {str(e)}")
        return redirect('faculty_dashboard')
    return render(request, 'upload.html')

# Analytics & Toppers (unchanged)
@login_required
@user_passes_test(is_faculty, login_url='login')
def analytics(request):
    failed = Result.objects.filter(is_pass=False).values('subject__name').annotate(count=Count('id'))
    total_results = Result.objects.count()
    pass_count = Result.objects.filter(is_pass=True).count()
    pass_percent = (pass_count / total_results * 100) if total_results else 0
    return render(request, 'analytics.html', {
        'failed': failed,
        'pass_percent': round(pass_percent, 2),
        'total_results': total_results
    })


@login_required
@user_passes_test(is_faculty, login_url='login')
def toppers(request):
    toppers = (Result.objects.values('student__reg_no', 'student__user__username')
               .annotate(avg_gpa=Avg('grade_point'))
               .order_by('-avg_gpa')[:10])
    return render(request, 'toppers.html', {'toppers': toppers})




@login_required
@user_passes_test(is_student, login_url='login')
def download_marklist(request):
    student = Student.objects.get(user=request.user)
    semester_filter = request.GET.get('semester')
    
    # Filter results by semester if provided
    results = Result.objects.filter(student=student).select_related('subject')
    if semester_filter and semester_filter != 'all':
        try:
            semester_int = int(semester_filter)
            results = results.filter(semester=semester_int)
        except ValueError:
            pass
    
    if not results.exists():
        messages.warning(request, "No results found for the selected semester.")
        return redirect('student_dashboard')
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    elements = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, alignment=1, spaceAfter=12)
    heading_style = ParagraphStyle('HeadingStyle', parent=styles['Heading2'], fontSize=12, alignment=0, spaceAfter=6)
    normal_style = styles['Normal']
    
    # Title
    if semester_filter and semester_filter != 'all':
        elements.append(Paragraph(f"Marklist - Semester {semester_filter}", title_style))
    else:
        elements.append(Paragraph("Complete Marklist", title_style))
    elements.append(Spacer(1, 6))
    
    # Student details: only name, reg no, college name, semester
    details = [
        [f"<b>Name:</b> {student.user.get_full_name() or student.user.username}"],
        [f"<b>Reg No:</b> {student.reg_no}"],
        [f"<b>College:</b> {student.college_name or 'Not set'}"],
        [f"<b>Semester:</b> {semester_filter if semester_filter and semester_filter != 'all' else 'All'}"],
    ]
    details_table = Table(details, colWidths=[5*inch])
    details_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(details_table)
    elements.append(Spacer(1, 12))
    
    # Group results by semester (if all semesters, group; else single group)
    if semester_filter and semester_filter != 'all':
        semesters = {int(semester_filter): list(results)}
    else:
        semesters = {}
        for r in results:
            semesters.setdefault(r.semester, []).append(r)
    
    for sem, sem_results in sorted(semesters.items()):
        elements.append(Paragraph(f"<b>Semester {sem} Results</b>", heading_style))
        
        data = [['Subject', 'Grade', 'Grade Point', 'Status']]
        for r in sem_results:
            data.append([r.subject.name, r.grade, str(r.grade_point), 'Pass' if r.is_pass else 'Fail'])
        
        # Calculate SGPA
        total_gp = sum(r.grade_point for r in sem_results)
        sgpa = total_gp / len(sem_results) if sem_results else 0
        data.append(['', '', 'SGPA:', f'{sgpa:.2f}'])
        
        table = Table(data, colWidths=[2.5*inch, 0.8*inch, 0.8*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 10),
            ('BOTTOMPADDING', (0,0), (-1,0), 8),
            ('BACKGROUND', (0,1), (-1,-2), colors.beige),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('SPAN', (0,-1), (2,-1)),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 10))
    
    # Overall SGPA (if multiple semesters)
    if not semester_filter or semester_filter == 'all':
        all_gp = [r.grade_point for r in results]
        overall = sum(all_gp) / len(all_gp) if all_gp else 0
        elements.append(Paragraph(f"<b>Overall SGPA: {overall:.2f}</b>", normal_style))
    
    doc.build(elements)
    buffer.seek(0)
    filename = f"{student.reg_no}_marklist"
    if semester_filter and semester_filter != 'all':
        filename += f"_sem{semester_filter}"
    filename += ".pdf"
    return FileResponse(buffer, as_attachment=True, filename=filename)