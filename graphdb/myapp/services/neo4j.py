import logging
from dataclasses import dataclass
from typing import Any, Callable, Optional, ParamSpec

from django.conf import settings
from django.contrib.auth.models import User as DjangoUser
from neo4j.graph import Relationship, Node

from neo4j import GraphDatabase, Result, EagerResult

P = ParamSpec("P")

ResultConsumer = Callable[[Result], None]


logger = logging.getLogger(__name__)


class Neo4jService:
    """
    Service wrapper around Neo4j SDK/library. This should be a singleton and should not be instantiated multiple times.
    The way to use this service is to use the global instance `NEO4JSERVICE` defined at the bottom of this file.

    The reason for the singleton is here: https://neo4j.com/docs/python-manual/current/connect/:

      "Driver objects are immutable, thread-safe, and expensive to create, so your application should create only one
       instance and pass it around (you may share Driver instances across threads)."
    """

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None
    ):
        uri = uri or settings.NEO4J_URI
        user = user or settings.NEO4J_USERNAME
        password = password or settings.NEO4J_PASSWORD
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def session_read(
        self,
        query: str,
        result_consumer: Optional[ResultConsumer] = None,
        params: Optional[dict[str, Any]] = None
    ) -> None:
        with self.driver.session() as session:
            try:
                session.execute_read(
                    lambda tx: (
                        result_consumer(tx.run(query, parameters=params))
                        if result_consumer
                        else tx.run(query, parameters=params)
                    )
                )
            finally:
                session.close()

    def session_write(
        self,
        query: str,
        result_consumer: Optional[ResultConsumer] = None,
        params: Optional[dict[str, Any]] = None
    ) -> None:
        with self.driver.session() as session:
            try:
                session.execute_write(
                    lambda tx: (
                        result_consumer(tx.run(query, parameters=params))
                        if result_consumer
                        else tx.run(query, parameters=params)
                    )
                )
            finally:
                session.close()

    def execute_query(self, query: str, **kwargs) -> EagerResult:
        return self.driver.execute_query(query, **kwargs)

    def close(self):
        self.driver.close()


# Global instance of the Neo4jService. This should be used throughout the application. Do not instantiate the
# Neo4jService class directly.
NEO4JSERVICE = Neo4jService()


@dataclass
class Business:
    id: str
    name: str
    description: str

    @classmethod
    def from_node(cls, node: Node) -> "Business":
        inst = cls(
            id=node["externalID"],
            name=node["name"],
            description=node["description"]
        )
        return inst


@dataclass
class User:
    id: str
    name: str
    email: str

    @classmethod
    def from_node(cls, node: Node) -> "User":
        inst = cls(
            id=node["externalID"],
            name=node["name"],
            email=node["email"]
        )
        return inst


@dataclass
class Review:
    id: str
    rating: int
    comment: str
    author: User
    business: Business

    @classmethod
    def from_relationship(cls, relationship: Relationship) -> "Review":

        # Reviews are relationships from User to Business. An alternative is to pass in the User and Business nodes
        # and use them to construct the User and Business objects. However, using the start/end nodes of the
        # relationship leverages the data integrity of the relationship and avoids the bug caused by passing in the
        # wrong nodes.
        return cls(
            id=relationship.element_id,
            rating=relationship["rating"],
            comment=relationship["comment"],
            author=User.from_node(relationship.start_node),
            business=Business.from_node(relationship.end_node)
        )


@dataclass
class Category:
    name: str
    description: str


class Neo4jDAO:
    """
    Data Access Object for interacting with Neo4j. This class contains methods for upserting and reading data from
    Neo4j. The methods in this class should be used by the application to interact with the Neo4j database.

    See https://neo4j.com/docs/python-manual/current/ for more info on the Neo4j Python driver.

    One exception is the Neo4jService#execute_query method. This method is exposed for advanced use cases where the
    DAO methods are not sufficient. It should be used sparingly. To use it, either:
    - use NEO4JSERVICE.execute_query() directly or
    - use Neo4jDAO.service.execute_query()
    """

    def __init__(self, service: Optional[Neo4jService] = None):
        self.service = service or NEO4JSERVICE

    # UPSERT OPERATIONS

    def upsert_user(self, user: DjangoUser) -> User:
        neo4j_user: Optional[User] = None

        def _result_to_django_user(result: Result) -> None:
            nonlocal neo4j_user

            record = result.single()
            neo4j_user = User.from_node(record["u"])

        self.service.session_write(
            "MERGE (u:User {externalID: $externalID}) ON CREATE SET u.name = $name, u.email = $email RETURN u",
            result_consumer=_result_to_django_user,
            params={"name": user.get_full_name(), "email": user.email, "externalID": str(user.pk)}
        )
        assert neo4j_user
        return neo4j_user

    def upsert_business(self, external_id: str, name: str, description: str) -> Business:
        business: Optional[Business] = None

        def _result_to_business(result: Result) -> None:
            nonlocal business

            record = result.single()
            business = Business.from_node(record["b"])

        self.service.session_write(
            (
                "MERGE (b:Business {externalID: $externalID}) "
                "ON CREATE SET b.name = $name, b.description = $description "
                "RETURN b"
            ),
            result_consumer=_result_to_business,
            params={"externalID": external_id, "name": name, "description": description}
        )
        assert business
        return business

    def upsert_category(self, name: str, description: str) -> Category:
        category: Optional[Category] = None

        def _result_to_category(result: Result) -> None:
            nonlocal category
            record = result.single()
            category_node = record["c"]

            category = Category(
                name=category_node["name"],
                description=category_node["description"]
            )

        self.service.session_write(
            (
                "MERGE (c:Category {name: $name}) "
                "ON CREATE SET c.description = $description "
                "RETURN c"
            ),
            result_consumer=_result_to_category,
            params={"name": name, "description": description}
        )
        assert category
        return category

    def upsert_business_category(self, business: Business, category: Category) -> None:
        self.service.session_write(
            (
                "MATCH (b:Business {externalID: $businessID}), (c:Category {name: $categoryName}) "
                "MERGE (b)-[:IN_CATEGORY]->(c)"
            ),
            params={"businessID": business.id, "categoryName": category.name}
        )

    def upsert_review(self, business: Business, author: User, rating: int, comment: str) -> Review:
        review: Optional[Review] = None

        def _result_to_review(result: Result) -> None:
            nonlocal review

            record = result.single()
            review_relationship = record["r"]

            review = Review.from_relationship(review_relationship)

        self.service.session_write(
            (
                "MATCH (b:Business {externalID: $businessID}), (u:User {externalID: $authorID}) "
                "MERGE (u)-[r:REVIEWED]->(b) "
                "ON CREATE SET r.rating = $rating, r.comment = $comment "
                "RETURN r, u"
            ),
            result_consumer=_result_to_review,
            params={"businessID": business.id, "authorID": author.id, "rating": rating, "comment": comment}
        )
        assert review
        return review

    # READ OPERATIONS

    def get_businesses(self) -> list[Business]:
        businesses: list[Business] = []
        def _extract_businesses(records) -> None:
            businesses.extend([
                Business.from_node(r["b"])
                for r in records
            ])
        
        self.service.session_read(
            "MATCH (b:Business) RETURN b",
            _extract_businesses
        )
        return businesses

    def get_reviews_of_businesses(self, business_ids: list[str]) -> list[Review]:
        
        # https://neo4j.com/docs/api/python-driver/current/api.html#core-data-types
        reviews = []
        def _extract_reviews(records) -> None:
            for r in records:
                review_relationship: Relationship = r["r"]
                # business_node = r["b"]
                # user_node = r["u"]N
                reviews.append(
                    Review.from_relationship(review_relationship)
                )

        # Even though we don't explicitly use b and u, we need to include them in the RETURN clause to extract the
        # start/end nodes. If we don't include them, the start/end nodes will not contain the necessary data to
        # construct the Business and User fields.
        self.service.session_read(
            "MATCH (b:Business)<-[r:REVIEWED]-(u:User) WHERE b.externalID in $ids RETURN b, r, u",
            _extract_reviews,
            params={"ids": business_ids}
        )
        return reviews
