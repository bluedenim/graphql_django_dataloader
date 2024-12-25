# Ariadne/Django GraphQL Demo #

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
