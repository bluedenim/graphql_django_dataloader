# Graphene/Django GraphQL Demo #

See parent README.md for the background of the data models.

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

## Building ##
- cd into the subdir for the implementation, then build with docker-compose:
  ```
  cd graphene
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
