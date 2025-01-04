# graphql_django_dataloader
Demos of GraphQL on Django **with synchronous DataLoaders**.

## Sample Data Model ##

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

This is definitely an improvement over N+1 (and recursively so), but it's still 1 query per level (e.g. 3 queries for Business -> Review -> User)


While there are some opportunities for clever meta programming to have a set of reusable
classes to handle this, the process of thinking about Dataloaders is unavoidable.


## Examples for Various GraphQL Frameworks ##

This repo contains some sample Django apps using different GraphQL frameworks, complete with the plumbing to inject Dataloader support. Each subdir is its own independent Django project with a set of Docker files to build and bring up the Django app.

One superuser is created with `root` / `password`. A pair of test users, test reviews, and test businesses are also created by the `seed_data.py` custom Django command.

See the `README.md` in each **subdirectory** for instructions.

### ariadne ###
Example of GraphQL w/ Dataloaders on Django using [Ariadne](https://ariadnegraphql.org/)

### graphene ###
Example of GraphQL w/ Dataloaders on Django using [Graphene](https://graphene-python.org/)

### sStrawberry ###
Example of GraphQL w/ Dataloaders on Django using [Strawberry](https://strawberry.rocks/)

### graphdb ###
Example of GraphQL w/ Dataloaders on Django & [Neo4j Graph DB](https://neo4j.com/product/neo4j-graph-database/)
