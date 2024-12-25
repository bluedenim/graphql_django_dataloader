from collections import defaultdict

import strawberry
from graphql_sync_dataloaders import DeferredExecutionContext
from strawberry_django.optimizer import DjangoOptimizerExtension

from myapp.models import Review as DjangoReview, Business as DjangoBusiness
from django.contrib.auth.models import User as DjangoUser


USE_DATALOADERS = True



@strawberry.type
class User:
    id: strawberry.ID
    email: str

    @strawberry.field
    def name(self, root: "User", info: strawberry.Info) -> str:
        return root.username


@strawberry.type
class Review:
    id: strawberry.ID
    rating: int
    comment: str

    @strawberry.field
    def author(self, root: "Review", info: strawberry.Info) -> User:
        if USE_DATALOADERS:
            dataloader = info.context.dataloaders["review_author"]
            return dataloader.load(root.id)
        else:
            return DjangoUser.objects.get(id=root.user_id)


def dataloader_business_reviews(keys: list[int]) -> list[list[Review]]:
    """
    Dataloader for reviews of businesses

    :param keys: IDs of Businesses to retrieve Reviews for

    :return: Reviews of Businesses in the same order of the Business IDs
    """
    reviews = DjangoReview.objects.filter(business_id__in=keys)

    review_by_business_id = defaultdict(list)
    for r in reviews:
        review_by_business_id[r.business_id].append(r)

    return [review_by_business_id.get(pk, []) for pk in keys]


def dataloader_review_author(keys: list[int]) -> list[User]:
    """
    Dataloader for review authors

    :param keys: IDs of Reviews to retrieve Users for

    :return: Users authoring the reviews in the same order of the Review IDs in keys
    """
    author_by_review_id = {}
    for r in DjangoReview.objects.filter(id__in=keys).select_related("user"):
        author_by_review_id[r.id] = r.user

    return [author_by_review_id.get(key) for key in keys]


@strawberry.type
class Business:
    id: strawberry.ID
    name: str
    description: str

    @strawberry.field
    def reviews(self, root: "Business", info: strawberry.Info) -> list[Review]:
        if USE_DATALOADERS:
            dataloader = info.context.dataloaders["business_reviews"]
            return dataloader.load(root.id)
        else:
            return DjangoReview.objects.filter(business_id=root.id)


def resolve_businesses():
    return DjangoBusiness.objects.all()


@strawberry.type
class Query:
    businesses: list[Business] = strawberry.field(resolver=resolve_businesses)


schema = strawberry.Schema(
    query=Query, execution_context_class=DeferredExecutionContext, extensions=[DjangoOptimizerExtension]
)
