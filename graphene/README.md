# Graphene/Django GraphQL Demo #

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

## Graphene ##

This subdir is a small Django project illustrating using the [Graphene GraphQL library](https://docs.graphene-python.org/projects/django/en/latest/) for Python/Django
and getting a working Dataloader setup.

Libraries used are:
- [graphene](https://docs.graphene-python.org/en/latest/quickstart/) -- GraphQL library for Python
- [graphene-django](https://docs.graphene-python.org/projects/django/en/latest/) -- More library to work with Django on Python.
- graphql-core -- GraphQL logic.
- [graphql-sync-dataloaders](https://ariadnegraphql.org/docs/dataloaders) -- Dataloader (synchronous) support.

### Dataloader setup with graphene-django ###

Set up the execution context class of `DeferredExecutionContext` when registering the GraphQL endpoint:

**urls.py:**
```
from django.views.decorators.csrf import csrf_exempt
from graphene_django.views import GraphQLView

from graphql_sync_dataloaders import DeferredExecutionContext


urlpatterns = [
    ...
    path("graphql", csrf_exempt(GraphQLView.as_view(graphiql=True, execution_context_class=DeferredExecutionContext))),
]
```

Hooking up dataloaders to Graphene is a bit tricky. At the current time, the async dataloader support is suspicious.
This project uses the **synchronous** library **graphql-sync-dataloaders** instead.

**schema.py:**
```
...

def review_author_data_loader(keys: list[int]) -> list[User]:
    """
    Data loader for authors of reviews

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

...

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

```

The `schema` and `data_loader_middleware` are then configured in `settings.py`:

**settings.py:**
```
...

GRAPHENE = {
    "SCHEMA": "main.schema.schema",
    "MIDDLEWARE": [
        "main.schema.data_loader_middleware"
    ]
}

....
```