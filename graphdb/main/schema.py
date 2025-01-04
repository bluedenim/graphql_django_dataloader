from collections import defaultdict

import strawberry
from graphql_sync_dataloaders import DeferredExecutionContext

from myapp.services.neo4j import Neo4jDAO

USE_DATALOADERS = True



@strawberry.type
class User:
    """
    A Strawberry type representing a user. This is NOT the same type (though they share field names) as the
    User dataclass from the Neo4jService or the Django User model.
    """
    id: strawberry.ID
    email: str
    name: str


@strawberry.type
class Review:
    """
    A Strawberry type representing a review. This is NOT the same type (though they share field names) as the
    Review dataclass from the Neo4jService.
    """
    id: strawberry.ID
    rating: int
    comment: str
    author: User


@strawberry.type
class Business:
    """
    A Strawberry type representing a business. This is NOT the same type (though they share field names) as the
    Business dataclass from the Neo4jService.
    """
    id: strawberry.ID
    name: str
    description: str

    @strawberry.field
    def reviews(self, root: "Business", info: strawberry.Info) -> list[Review]:
        if USE_DATALOADERS:
            dataloader = info.context.dataloaders["business_reviews"]
            return dataloader.load(root.id)
        else:
            raise NotImplementedError("Dataloaders are not enabled")


def dataloader_business_reviews(keys: list[str]) -> list[list[Review]]:
    """
    Dataloader for reviews of businesses

    :param keys: IDs of Businesses to retrieve Reviews for

    :return: Reviews of Businesses in the same order of the Business IDs
    """
    dao = Neo4jDAO()
    reviews = dao.get_reviews_of_businesses(keys)

    review_by_business_id = defaultdict(list)
    for r in reviews:
        review_by_business_id[r.business.id].append(r)

    return [review_by_business_id.get(pk, []) for pk in keys]


@strawberry.type
class Query:

    @strawberry.field
    def businesses(self, info: strawberry.Info) -> list[Business]:
        dao = Neo4jDAO()
        return dao.get_businesses()


schema = strawberry.Schema(query=Query, execution_context_class=DeferredExecutionContext)
