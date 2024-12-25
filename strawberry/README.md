# Strawberry/Django GraphQL Demo #

The demo data model is this set of models:
- User (default model from Django)
- Business -- a business entity
- Review -- a review of a business
- Category -- the category of a business (unused)

```
+----------+  1    m  +--------+  m   1  +------+
| Business |<---------| Review |-------->| User |
+==========+          +========+         +======+
     ^  m   n  +----------+
     +---------| Category |
               +==========+
```

In short:
- **Business** has 0 to many **Review**s. A **Review** is mapped to exactly 1 **Business**.
- **User** may write 0-many **Review**s, but a **Review** has exactly 1 author/**User**.
- **Business** has a many-to-many relationship to **Category**.

The demo is to expose **Business**, **Review**, and **User** via GraphQL. As mentioned,
**Category** is unused at this time.

## Dataloaders ##

RDBMSes (aka SQL DBs) are **NOT** friends with GraphQL, so naive implementations of GraphQL
resolvers will inevitably run into the N+1 query problem.

The ugly duct tape solution is **Dataloader**s, so a typical set of operations of server devs working
with _GraphQL + SQL DB_ will be to write boilerplate Dataloaders all day.

Without using Dataloaders, a query like:
```
{
  businesses {
    id
    name
    reviews {
      id
      rating
      comment
      author {
        id
        name
        email
      }
    }
  }
}
```
will trigger these SQL queries:
```
# Get the Businesses
(0.004) SELECT ... FROM "myapp_business"; args=(); alias=default

# Get reviews for Business 1
(0.002) SELECT ... FROM "myapp_review" WHERE "myapp_review"."business_id" = 1; args=(1,); alias=default

# Get author/user for review
(0.002) SELECT ... FROM "auth_user" WHERE "auth_user"."id" = 3 LIMIT 21; args=(3,); alias=default

# Get reviews for Business 2
(0.002) SELECT ... FROM "myapp_review" WHERE "myapp_review"."business_id" = 2; args=(2,); alias=default

# Get author/user for review
(0.002) SELECT ... FROM "auth_user" WHERE "auth_user"."id" = 2 LIMIT 21; args=(2,); alias=default

# Get reviews for Business 3
(0.001) SELECT ... FROM "myapp_review" WHERE "myapp_review"."business_id" = 3; args=(3,); alias=default

# Get author/user for reviews
(0.001) SELECT ... FROM "auth_user" WHERE "auth_user"."id" = 2 LIMIT 21; args=(2,); alias=default
(0.001) SELECT ... FROM "auth_user" WHERE "auth_user"."id" = 3 LIMIT 21; args=(3,); alias=default
```

With Dataloaders, however, these SQL queries are used:
```
# Get the Businesses
(0.005) SELECT ... FROM "myapp_business"; args=(); alias=default

# Get reviews of the businesses 1, 2, and 3
(0.002) SELECT ... FROM "myapp_review" WHERE "myapp_review"."business_id" IN (1, 2, 3); args=(1, 2, 3); alias=default

# Get authors/users of the reviews
(0.002) SELECT ... FROM "myapp_review" INNER JOIN "auth_user" ON ("myapp_review"."user_id" = "auth_user"."id") WHERE "myapp_review"."id" IN (4, 3, 1, 2); args=(4, 3, 1, 2); alias=default
```

This is definitely an improvement over N+1 (and recursively so), but it's still 1 query per level (e.g. Business -> Review -> User)


While there are some opportunities for dynamic programming to have a set of reusable
classes to handle this, the process of thinking about Dataloaders is inescapable.

## Strawberry ##

This subdir is a small Django project illustrating using the [Strawberry GraphQL library](https://strawberry.rocks/) for Python/Django
and getting a working Dataloader setup.

Libraries used are:
- [strawberry-graphql](https://strawberry.rocks/) -- Strawberry library
- strawberry-graphql-django -- Library to integrate with Django
- graphql-core -- GraphQL logic.
- [graphql-sync-dataloaders](https://ariadnegraphql.org/docs/dataloaders) -- Dataloader (synchronous) support. Strawberry's own DataLoader only 
  supports Async.

### Dataloader setup with strawberry ###

The [documentation from Strawberry](https://strawberry.rocks/docs/guides/dataloaders#usage-with-context) _suggests_ that its DataLoader only works in **asynchronous** flows 
(does that require using ASGI?). To be consistent with the other demos, I'm hacking this set up to also use
a **synchronous** dataloader from **graphql-sync-dataloaders**.

Set up the execution context class of `DeferredExecutionContext` when instantiating the Schema object. 

⚠ And this is only by luck (?) that the Strawberry code allows me to specify a different execution context class 
(`DeferredExecutionContext`) than their own **and they still work correctly**:

**schema.py:**
```
import strawberry
from graphql_sync_dataloaders import DeferredExecutionContext

...

schema = strawberry.Schema(
    query=Query, execution_context_class=DeferredExecutionContext, extensions=[DjangoOptimizerExtension]
)
```

Extend the default Strawberry context to add a field to hold our dataloaders:

**urls.py:**
```
from strawberry.django.context import StrawberryDjangoContext

...

@dataclass
class Context(StrawberryDjangoContext):
    """
    Extend the default context from Strawberry to add a dataloader property that will contain our dataloaders.
    """
    dataloaders: dict
```

Also extend the `GraphQLView` (the one from **Strawberry**, not 
the one from **graphql-core**) and override the `get_context` to return our context with the dataloaders:

**urls.py:**
```
from main.schema import schema, dataloader_business_reviews, dataloader_review_author
from strawberry.django.views import GraphQLView


...

class GraphQLViewWithDataLoaders(GraphQLView):
    """
    Override the get_context to return our Context (with the dataloader property) for resolvers to use.
    """

    def get_context(self, request: HttpRequest, response: HttpResponse) -> Context:
        strawberry_context = super().get_context(request, response)

        return Context(
            request=strawberry_context.request,
            response=strawberry_context.response,
            dataloaders={
                "business_reviews": SyncDataLoader(dataloader_business_reviews),
                "review_author": SyncDataLoader(dataloader_review_author),
            }
        )
    
...
        
urlpatterns = [
    ...
    
    path("graphql/", csrf_exempt(GraphQLViewWithDataLoaders.as_view(schema=schema))),
]
```

**schema.py:**

The dataloader functions referenced above:

```
...

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

...

```

and how they are used in the resolvers:
```
...

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
            
...

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

```



## Building ##
- cd into the subdir for the implementation, then build with docker-compose:
  ```
  cd strawberry
  docker-compose build
  ```
- shell in to seed data
  ```
  docker-compose run --rm app /bin/bash
  python manage.py migrate
  python manage.py seed_data
  exit
  ```
## Running ##
- start up the app
  ```
  docker-compose up
  ```
- Bring up the GraphQL client at http://localhost:8000/graphql
- Run this query:
  ```
  {
    businesses {
      id
      name
      reviews {
        id
        rating
        comment
        author {
          id
          name
          email
        }
      }
    }
  }
  ```
- From the logs, you should see only 3 queries to the DB thanks to the dataloaders.