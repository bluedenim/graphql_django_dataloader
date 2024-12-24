from collections import defaultdict

import graphene
import logging

from django.contrib.auth.models import User
from graphql_sync_dataloaders import SyncDataLoader

from myapp.models import Business, Review


USE_DATALOADERS = True

logger = logging.getLogger(__name__)


class UserType(graphene.ObjectType):
    id = graphene.NonNull(graphene.ID)
    name = graphene.NonNull(graphene.String)
    email = graphene.NonNull(graphene.String)

    def resolve_name(root, info):
        return root.username


def review_author_data_loader(keys: list[int]) -> list[User]:
    """
    Dataloader for authors of reviews

    :param keys: IDs of reviews

    :return: Users of the reviews in the same order of the review IDs
    """
    reviews = Review.objects.filter(id__in=keys).select_related("user")
    review_author_by_review_id = {r.id: r.user for r in reviews}
    return [review_author_by_review_id.get(pk) for pk in keys]


def business_review_data_loader(keys: list[int]) -> list[list[Review]]:
    """
    Dataloader for reviews of businesses

    :param keys: IDs of Businesses to retrieve Reviews for

    :return: Reviews of Businesses in the same order of the Business IDs
    """
    reviews = Review.objects.filter(business_id__in=keys)

    review_by_business_id = defaultdict(list)
    for r in reviews:
        review_by_business_id[r.business_id].append(r)

    return [review_by_business_id.get(pk, []) for pk in keys]


class ReviewType(graphene.ObjectType):
    id = graphene.NonNull(graphene.ID)
    rating = graphene.NonNull(graphene.Int)
    comment = graphene.NonNull(graphene.String)
    author = graphene.NonNull(UserType)

    def resolve_author(root, info):
        if USE_DATALOADERS:
            return info.context.data_loaders["review_author"].load(root.id)
        else:
            return root.user


class BusinessType(graphene.ObjectType):
    id = graphene.NonNull(graphene.ID)
    name = graphene.NonNull(graphene.String)
    description = graphene.NonNull(graphene.String)
    reviews = graphene.NonNull(graphene.List(graphene.NonNull(ReviewType)))

    def resolve_reviews(root, info):
        if USE_DATALOADERS:
            return info.context.data_loaders["business_review"].load(root.id)
        else:
            return Review.objects.filter(business=root)


class Query(graphene.ObjectType):
    businesses = graphene.List(graphene.NonNull(BusinessType))

    def resolve_businesses(root, info):
        return list(Business.objects.all())


def data_loader_middleware(next, root, info, **args):
    """
    Middleware used to inject dataloaders into the context of resolvers. This is injected in Django settings via the
    GRAPHENE["MIDDLEWARE"] property.
    """
    if USE_DATALOADERS:
        # The middleware is called multiple times even for a single request, so only inject the data loaders if they
        # don't already exist.
        if not hasattr(info.context, "data_loaders"):
            info.context.data_loaders = {
                "business_review": SyncDataLoader(business_review_data_loader),
                "review_author": SyncDataLoader(review_author_data_loader)
            }
    return next(root, info, **args)


# This can either be passed to the GraphQLView.as_view(...) or set in the Django settings via the GRAPHENE["SCHEMA"]
# property.
schema = graphene.Schema(query=Query)
