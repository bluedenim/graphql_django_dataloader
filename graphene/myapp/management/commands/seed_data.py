from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from myapp.models import Business, Category, BusinessCategory, Review


class Command(BaseCommand):

    def handle(self, *args, **options):
        """
        Seed test data for GraphQL demo
        """

        # Users
        root = User.objects.filter(username="root").first()
        if not root:
            root = User.objects.create_superuser("root", password="password")

        van, _ = User.objects.get_or_create(username="vancly", password="password", first_name="Van", last_name="Ly")
        emma, _ = User.objects.get_or_create(username="emmaly", password="password", first_name="Emma", last_name="Ly")

        # Categories
        category_dining, _ = Category.objects.get_or_create(
            name="dining", defaults={"description": "Restaurants, diners, etc."}
        )
        category_entertainment, _ = Category.objects.get_or_create(
            name="entertainment", defaults={"description": "General entertainment business."}
        )
        category_finance, _ = Category.objects.get_or_create(
            name="finance", defaults={"description": "Banks, credit unions, etc."}
        )

        # Businesses w/ Categories and Reviews
        joes, _ = Business.objects.get_or_create(name="Joe's", defaults={
            "description": "Eat at Joe's!"}
        )
        BusinessCategory.objects.get_or_create(business=joes, category=category_dining)
        Review.objects.get_or_create(business=joes, user=emma, defaults={
            "rating": 5, "comment": "I love their clam chowder!"
        })
        Review.objects.get_or_create(business=joes, user=van, defaults={
            "rating": 4, "comment": "Food is good but too expensive."
        })

        movies_and_burgers, _ = Business.objects.get_or_create(name="Movies & Burgers", defaults={
            "description": "Have a burger and the movie's on us!"}
        )
        BusinessCategory.objects.get_or_create(business=movies_and_burgers, category=category_dining)
        BusinessCategory.objects.get_or_create(business=movies_and_burgers, category=category_entertainment)
        Review.objects.get_or_create(business=movies_and_burgers, user=emma, defaults={
            "rating": 3, "comment": "Burger was disappointing."
        })
        Review.objects.get_or_create(business=movies_and_burgers, user=van, defaults={
            "rating": 4, "comment": "Food is good. Movie was OK."
        })

        super_plex, _ = Business.objects.get_or_create(name="SuperPlex", defaults={
            "description": "20 theaters for your pleasure!"}
        )
        BusinessCategory.objects.get_or_create(business=super_plex, category=category_entertainment)
