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
from django.contrib import admin
from django.urls import path
from main.schema import schema, get_reviews_for_businesses, get_authors_for_reviews
from ariadne_django.views import GraphQLView
from graphql_sync_dataloaders import DeferredExecutionContext, SyncDataLoader
from django.http import HttpRequest


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
    path('admin/', admin.site.urls),
    path('graphql/', GraphQLViewWithSyncDataloaders.as_view(schema=schema), name='graphql'),
]
