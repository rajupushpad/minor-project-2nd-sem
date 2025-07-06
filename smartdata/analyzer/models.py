from django.db import models
import os
import uuid

def upload_to(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('uploads', filename)

class UploadedFile(models.Model):
    file = models.FileField(upload_to=upload_to)
    original_name = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.original_name and hasattr(self.file, 'name'):
            self.original_name = self.file.name
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.original_name or str(self.file)