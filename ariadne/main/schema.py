from ariadne import ObjectType, QueryType, make_executable_schema
from django.contrib.auth.models import User
from myapp.models import Business, Review
from typing import Optional
from collections import defaultdict
import logging


USE_DATALOADERS = False


type_defs = """
    type Query {
        businesses: [Business!]!
    }

    type User {
        id: ID!
        name: String!
        email: String!
    }

    type Review {
        id: ID!
        rating: Int!
        comment: String!
        author: User!
    }
    
    type Business {
        id: ID!
        name: String!
        description: String!
        reviews: [Review!]!
    }
"""

logger = logging.getLogger(__name__)


query = QueryType()

user = ObjectType("User")
business = ObjectType("Business")
review = ObjectType("Review")


@user.field("id")
def resolve_user_id(user, info):
    return user.id


@user.field("name")
def resolve_user_name(user, info):
    return user.username


@user.field("email")
def resolve_user_email(user, info):
    return user.email or ""


@query.field("businesses")
def resolve_businesses(_, info):
    businesses = Business.objects.all()
    return businesses


@business.field("id")
def resolve_business_id(business, info):
    return business.id


@business.field("name")
def resolve_business_name(business, info):
    return business.name


@business.field("description")
def resolve_business_description(business, info):
    return business.description


@business.field("reviews")
def resolve_business_reviews(business, info):
    if USE_DATALOADERS:
        data_loader = info.context["data_loaders"]["reviews_for_businesses"]
        reviews = data_loader.load(business.id)
        return reviews
    else:
        return Review.objects.filter(business=business)


@review.field("id")
def resolve_review_id(review, info):
    return review.id


@review.field("rating")
def resolve_review_rating(review, info):
    return review.rating


@review.field("comment")
def resolve_review_comment(review, info):
    return review.comment


@review.field("author")
def resolve_review_author(review, info):
    if USE_DATALOADERS:
        data_loader = info.context["data_loaders"]["authors_for_reviews"]
        author = data_loader.load(review.id)
        return author
    else:
        return review.user


def get_reviews_for_businesses(business_ids: list[int]) -> list[Optional[list[Review]]]:
    """
    Dataloader for reviews by business id.

    :param business_ids: List of business ids.
    :return: List of reviews for each business id. If a business has no reviews, the list index corresponding
    to that business will be None. This is the typical dataloader convention.
    """
    reviews_by_business_id = defaultdict(list)
    for review in Review.objects.filter(business_id__in=business_ids):
        reviews_by_business_id[review.business_id].append(review)

    # Convert defaultdict to dict will have it return None for missing keys instead of an empty list.
    reviews_by_business_id = dict(reviews_by_business_id)
    return [reviews_by_business_id.get(business_id, []) for business_id in business_ids]


def get_authors_for_reviews(review_ids: list[int]) -> list[Optional[User]]:
    """
    Dataloader for authors by review id.

    :param review_ids: List of review ids.
    :return: List of authors for each review id. If a review has no author, the list index corresponding
    to that review will be None. This is the typical dataloader convention.
    """
    authors_by_review_id = {}
    for review in Review.objects.filter(id__in=review_ids).select_related("user"):
        authors_by_review_id[review.id] = review.user

    return [authors_by_review_id.get(review_id) for review_id in review_ids]


schema = make_executable_schema(type_defs, query, user, business, review)
