from django.contrib import admin
from myapp.models import Business, Category, BusinessCategory, Review


class BusinessAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')

admin.site.register(Business, BusinessAdmin)

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')

admin.site.register(Category, CategoryAdmin)

class BusinessCategoryAdmin(admin.ModelAdmin):
    list_display = ('business', 'category', 'created_at')

admin.site.register(BusinessCategory, BusinessCategoryAdmin)

class ReviewAdmin(admin.ModelAdmin):
    list_display = ('business', 'user', 'rating', 'comment', 'created_at')

admin.site.register(Review, ReviewAdmin)
