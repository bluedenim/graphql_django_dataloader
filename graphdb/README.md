# Strawberry/Neo4j GraphQL Demo #

This is a demo project to show how to use Strawberry with Neo4j as the data store instead 
of Django's ORM.

Any of the GraphQL libraries (e.g. Ariadne, Graphene) can be used instead, but I chose
Strawberry just based on personal preference.

## Strawberry ##

Libraries used are:
- [strawberry-graphql](https://strawberry.rocks/) -- Strawberry library
- graphql-core -- GraphQL logic.
- [graphql-sync-dataloaders](https://ariadnegraphql.org/docs/dataloaders) -- Dataloader (synchronous) support. Strawberry's own DataLoader only 
  supports Async.

### Setup ###

The setup is very similar to those in the `../strawberry` subdir. To avoid duplication, I won't repeat the setup here.

## Neo4j ##

Docker image:
- [neo4j](https://hub.docker.com/_/neo4j) -- Neo4j Docker image to get a locally running instance. See `docker-compose.yml`.

Libraries used are:
- [neo4j](https://neo4j.com/docs/getting-started/languages-guides/neo4j-python/) -- Neo4j driver for Python.

One thing to note is that, due to the lack of an ORM layer on top of Neo4j, we have to write our own DAO class. It's 
significantly more work than just using Django's ORM, including having to learn Cypher, Neo4j's query language. This
DAO and support code are in `myapp/services/neo4j.py`.

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

The logging for Neo4j is set to DEBUG, so it's quite verbose. I believe grepping for "RUN" should show the Cypher 
queries being run.

Formatted example:
```
app-1    | DEBUG 2025-01-03 23:53:43,699 _bolt5 14 140417880295104 [#858E]  
  C: RUN 'MATCH (b:Business) RETURN b' {} {}

...

app-1    | DEBUG 2025-01-03 23:53:43,719 _bolt5 14 140417880295104 [#858E]  
  C: RUN 'MATCH (b:Business)<-[r:REVIEWED]-(u:User) WHERE b.externalID in $ids 
  RETURN b, r, u' {'ids': ['9a96caca-409d-4bb6-bd89-6366733c3c7c', 'C93328FA-3FA3-4207-9E93-860D8E59CD13', 
    '215E79FB-BB8B-401C-B92B-6CECFD33FDAF']} {}
```

## Notes ##

### Modeling ###
For this demo, I skipped an explicit **Review** model and just used a relationship between **Business** and **User**. 
The resulting data model in Neo4j is something like this and is different than the one from the parent directory:

```
+----------+  m                     n  +------+
| Business |<--------- Reviewed -------| User |
+==========+                           +======+
     |  m           n +----------+
     +-In Category--->| Category |
                      +==========+
```

The graph looks like this after running `seed_data.py`:
<img width="815" alt="Screenshot 2024-12-28 at 22 01 39" src="https://github.com/user-attachments/assets/4a4d4461-0c7d-4ec6-ad18-59f7d148fbc7" />


This is because a relationship in Neo4j can have properties (like a joining/intersection table in SQL). Assuming the
data model is such that each user can only write at most 1 review for each business, then this works.

### What's the Difference? ###
So. The BIG question is: what does using Neo4j (or any Graph DB) get us? We **still need a Dataloader** to batch 
queries. At least I had to for the setup I have. There may be a way to do it without a Dataloader, but I so far
haven't found it. Admittedly, I'm still a newbie to Neo4j.

One benefit I see is that _implementing_ the Dataloader code is a bit more straightforward since relationships are
a first-class entity in a Graph DB as opposed to a nebulous join between tables. The closest thing I can imagine is
a joining/intersection table in SQL, but then working with those tables in SQL involves multiple joins, so a 
"relationship" and a joining/intersection table are not really the same. 

And the Cypher query (see the 2nd query above) is a bit more straightforward than the equivalent SQL query _once I got
a bit more familiar with Cypher_.

On the other hand, because the Neo4j Python driver is NOT an ORM, I had to write a lot more code (e.g. the wrapper, the
DAO, the "model" classes, etc.). All the Django magic are not applicable. This applied to the run-time code as well as
the data seeding code (see `myapp/management/commands/seed_data.py`). I suspect every team that takes this approach
will have to do something similar.

### Worth it? ###

_Disclaimer again: I'm new to Neo4j. So keep this in mind._

**For Python** and just GraphQL, I'm not sure that it's worth it. The Dataloader is still necessary, and the Cypher queries
are not necessarily easier to write than Django QuerySet queries (especially for people new to Neo4j). The lack of an 
ORM layer means more code to write and maintain. And do Cypher concepts and programming model transferable to other 
Graph DBs? Both Django's ORM and SQL are pretty much standardized (for most of what I do anyway) across DB vendors.

One option that may help is [neomodel](https://neomodel.readthedocs.io/en/latest/index.html) which I haven't tested yet. And
let's say it makes working with Neo4j as pleasant as working with Django's QuerySet, it still doesn't eliminate the need to
work with **Dataloaders**. 

However, if I were building a system that has a huge graph of relationships that I need to analyze and traverse, then
Neo4j (or another Graph DB) might be the way to go. In other words, the use of Neo4j should be driven by the business
logic and not because of GraphQL.

**For Javascript**, the story might be different. There is a [Neo4j GraphQL Library](https://neo4j.com/docs/graphql/current/) 
that might help working with GraphQL and Neo4j. I am learning it now as time permits (to see if it eliminates the need for 
Dataloaders), but it certainly has more high-level support than just a driver. Of course, it's ONLY for Javascript currently.

