"""
URL configuration for main project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from dataclasses import dataclass

from django.contrib import admin
from django.http import HttpRequest, HttpResponse
from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from graphql_sync_dataloaders import SyncDataLoader

from strawberry.django.context import StrawberryDjangoContext
from strawberry.django.views import GraphQLView


from main.schema import schema, dataloader_business_reviews


@dataclass
class Context(StrawberryDjangoContext):
    """
    Extend the default context from Strawberry to add a dataloader property that will contain our dataloaders.
    """
    dataloaders: dict


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
            }
        )


urlpatterns = [
    path('admin/', admin.site.urls),

    path("graphql/", csrf_exempt(GraphQLViewWithDataLoaders.as_view(schema=schema))),
]
