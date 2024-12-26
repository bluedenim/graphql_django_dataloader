# Ariadne/Django GraphQL Demo #

See parent README.md for the background of the data models.

## Ariadne ##

This subdir is a small Django project illustrating using the [Ariadne GraphQL library](https://ariadnegraphql.org/) for Python/Django
and getting a working Dataloader setup.

Libraries used are:
- [ariadne](https://ariadnegraphql.org/) -- GraphQL library for Python.
- [ariadne-django](https://ariadnegraphql.org/docs/django-integration.html) -- More library to work with Django on Python.
- graphql-core -- GraphQL logic.
- [graphql-sync-dataloaders](https://ariadnegraphql.org/docs/dataloaders) -- Dataloader (synchronous) support.

### Dataloader setup with ariadne-django ###

There is some missing documention on getting dataloader set up with ariadne-django. Here is the process
(based on https://ariadnegraphql.org/docs/dataloaders):

**urls.py:**
```
class GraphQLViewWithSyncDataloaders(GraphQLView):
    """
    Custom GraphQLView to hook up dataloaders
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.context_value = self.get_context_value

    def get_context_value(self, request: HttpRequest) -> dict:
        context_value = {
            "request": request,
            "data_loaders": {
                "reviews_for_businesses": SyncDataLoader(get_reviews_for_businesses),
                "authors_for_reviews": SyncDataLoader(get_authors_for_reviews),
            },
        }
        return context_value

    def get_kwargs_graphql(self, request: HttpRequest) -> dict:
        kwargs = super().get_kwargs_graphql(request)
        kwargs["execution_context_class"] = DeferredExecutionContext
        return kwargs


urlpatterns = [
    ...
    path('graphql/', GraphQLViewWithSyncDataloaders.as_view(schema=schema), name='graphql'),
]
```

The typical dataloader usage in a resolver is as documented with few changes:

**schema.py:**
```
...

@business.field("reviews")
def resolve_business_reviews(business, info):
    data_loader = info.context["data_loaders"]["reviews_for_businesses"]
    reviews = data_loader.load(business.id)
    return reviews

...

@review.field("author")
def resolve_review_author(review, info):
    data_loader = info.context["data_loaders"]["authors_for_reviews"]
    author = data_loader.load(review.id)
    return author

....

```

## Building ##
- cd into the subdir for the implementation, then build with docker-compose:
  ```
  cd ariadne
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
