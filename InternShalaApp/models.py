from django.db import models
from django.contrib.auth.models import User
# Create your models here.
class TakeReview(models.Model):
    user = models.CharField(max_length=120)
    date = models.DateTimeField(auto_now_add=True)
    email = models.EmailField()
    review = models.TextField()
