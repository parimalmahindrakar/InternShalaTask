from django.contrib import admin
from .models import TakeReview
# Register your models here.
class TakeReviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'review']
    
admin.site.register(TakeReview,TakeReviewAdmin)