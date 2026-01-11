from django.urls import path
from .views import (
    GoalListView, GoalCreateView, GoalUpdateView, GoalDetailView, GoalDeleteView,
    CASUploadView, CASListView, ExternalHoldingListView
)
app_name = 'analytics'
urlpatterns = [
    # Goal Planning
    path('goals/', GoalListView.as_view(), name='goal_list'),
    path('goals/create/', GoalCreateView.as_view(), name='goal_create'),
    path('goals/<int:pk>/', GoalDetailView.as_view(), name='goal_detail'),
    path('goals/<int:pk>/update/', GoalUpdateView.as_view(), name='goal_update'),
    path('goals/<int:pk>/delete/', GoalDeleteView.as_view(), name='goal_delete'),

    # CAS Import
    path('cas/upload/', CASUploadView.as_view(), name='cas_upload'),
    path('cas/list/', CASListView.as_view(), name='cas_list'),
    path('cas/holdings/', ExternalHoldingListView.as_view(), name='external_holdings'),
]
