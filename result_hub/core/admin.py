# admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Department, Profile, Student, Subject, Result, Notification


# Inline to edit Profile directly inside the User admin page
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'


# Extend the default User admin to include ProfileInline
class CustomUserAdmin(UserAdmin):
    inlines = [ProfileInline]


# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'role')
    raw_id_fields = ('user',)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('reg_no', 'get_full_name', 'department', 'semester', 'phone', 'college_name')
    list_filter = ('department', 'semester')
    search_fields = ('reg_no', 'user__username', 'user__first_name', 'user__last_name', 'phone')
    raw_id_fields = ('user', 'department')
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'reg_no')
        }),
        ('Personal Details', {
            'fields': ('father_name', 'mother_name', 'phone', 'place')
        }),
        ('Academic Details', {
            'fields': ('department', 'semester', 'college_name')
        }),
        ('Images', {
            'fields': ('image', 'signature'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('reg_no',)   # Registration number is usually not edited later

    def get_full_name(self, obj):
        return obj.user.get_full_name()
    get_full_name.short_description = 'Full Name'
    get_full_name.admin_order_field = 'user__first_name'


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'credits')
    search_fields = ('code', 'name')
    list_filter = ('credits',)
    ordering = ('code',)


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'semester', 'grade', 'grade_point', 'is_pass')
    list_filter = ('semester', 'is_pass', 'subject')
    search_fields = ('student__reg_no', 'student__user__first_name', 'student__user__last_name', 'subject__name')
    raw_id_fields = ('student', 'subject')
    list_editable = ('grade', 'grade_point', 'is_pass')
    list_select_related = ('student', 'student__user', 'subject')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message_preview', 'is_read')
    list_filter = ('is_read',)
    search_fields = ('user__username', 'message')
    list_editable = ('is_read',)

    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message (preview)'