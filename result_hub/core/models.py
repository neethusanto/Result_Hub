from django.db import models
from django.contrib.auth.models import User

class Department(models.Model):
    name = models.CharField(max_length=100)

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10)

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    reg_no = models.CharField(max_length=20)
    semester = models.IntegerField()

    department = models.ForeignKey(Department, on_delete=models.CASCADE)

     # New fields
    place = models.CharField(max_length=100, blank=True, null=True)
    college_name = models.CharField(max_length=200, blank=True, null=True)
    image = models.ImageField(upload_to='student_images/', blank=True, null=True)
    signature = models.ImageField(upload_to='signatures/', blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    father_name = models.CharField(max_length=100, blank=True, null=True)
    mother_name = models.CharField(max_length=100, blank=True, null=True)
    
    def __str__(self):
        return f"{self.reg_no} - {self.user.get_full_name()}"

class Subject(models.Model):
    code = models.CharField(max_length=10)
    name = models.CharField(max_length=100)
    semester = models.IntegerField()
    credits = models.IntegerField()

class Result(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    grade = models.CharField(max_length=2)
    grade_point = models.FloatField()
    semester = models.IntegerField()
    is_pass = models.BooleanField(default=True)

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    is_read = models.BooleanField(default=False)