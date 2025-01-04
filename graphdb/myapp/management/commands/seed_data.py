from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from myapp.services.neo4j import Neo4jDAO


class Command(BaseCommand):

    def handle(self, *args, **options):
        """
        Seed test data for GraphQL demo. Other than Users that are managed by Django, all other data are managed by
        Neo4j. Users are exported into Neo4j as well, however, in order to model review relationships.
        """

        # Users
        root = User.objects.filter(username="root").first()
        if not root:
            User.objects.create_superuser("root", password="password")

        django_van, _ = User.objects.get_or_create(
            username="vancly", password="password", first_name="Van", last_name="Ly"
        )
        django_emma, _ = User.objects.get_or_create(
            username="emmaly", password="password", first_name="Emma", last_name="Ly"
        )

        # Insert into Neo4j
        dao = Neo4jDAO()

        # Establish some constraints. Unique constraints imply indexes.
        constraints = [
            "CREATE CONSTRAINT user_uniq_externalID IF NOT EXISTS FOR (n:User) REQUIRE n.externalID IS UNIQUE",
            "CREATE CONSTRAINT business_uniq_externalID IF NOT EXISTS FOR (n:Business) REQUIRE n.externalID IS UNIQUE",
            "CREATE CONSTRAINT business_uniq_name IF NOT EXISTS FOR (n:Business) REQUIRE n.name IS UNIQUE",
            "CREATE CONSTRAINT category_uniq_name IF NOT EXISTS FOR (n:Category) REQUIRE n.name IS UNIQUE",
        ]

        for constraint in constraints:
            dao.service.execute_query(constraint)

        # Export users into Neo4j. We use the Django User ID as the externalID for the User node in Neo4j because
        # the User ID is guaranteed to be unique across all Django instances while the elementID from Neo4j is not
        # guaranteed to be unique across multiple Neo4j instances.
        van = dao.upsert_user(django_van)
        emma = dao.upsert_user(django_emma)

        # Businesses. We generate some UUIDs for the externalID since the elementID from Neo4j is not guaranteed to be
        # unique across multiple Neo4j instances.
        joes = dao.upsert_business(
            "9a96caca-409d-4bb6-bd89-6366733c3c7c", "Joe's", "Eat at Joe's"
        )
        m_b = dao.upsert_business(
            "C93328FA-3FA3-4207-9E93-860D8E59CD13",
            "Movies & Burgers",
            "Have a burger and the movie's on us!"
        )
        sp = dao.upsert_business(
            "215E79FB-BB8B-401C-B92B-6CECFD33FDAF",
            "SuperPlex",
            "20 theaters for your pleasure!"
        )

        # Categories
        category_dining = dao.upsert_category("dining", "Restaurants, diners, etc.")
        category_entertainment = dao.upsert_category("entertainment", "General entertainment business.")
        category_finance = dao.upsert_category("finance", "Banks, credit unions, etc.")

        # Business Categories
        dao.upsert_business_category(joes, category_dining)
        dao.upsert_business_category(m_b, category_dining)
        dao.upsert_business_category(m_b, category_entertainment)
        dao.upsert_business_category(sp, category_entertainment)

        # Reviews
        van_joes = dao.upsert_review(joes, van, 4, "Food is good but too expensive.")
        emma_joes = dao.upsert_review(joes, emma, 5, "I love their clam chowder!")
        van_m_b = dao.upsert_review(m_b, van, 4, "Food is good. Movie was OK.")
        emma_m_b = dao.upsert_review(m_b, emma, 3, "Burger was disappointing.")
