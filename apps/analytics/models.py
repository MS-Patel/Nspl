from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.users.models import User, InvestorProfile
from apps.reconciliation.models import Holding

class Goal(models.Model):
    """
    Represents a financial goal for an investor.
    """
    CATEGORY_CHOICES = [
        ('RETIREMENT', 'Retirement'),
        ('EDUCATION', 'Child Education'),
        ('HOUSE', 'House Purchase'),
        ('CAR', 'Car Purchase'),
        ('VACATION', 'Vacation'),
        ('EMERGENCY', 'Emergency Fund'),
        ('OTHER', 'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_goals', help_text="The user who created this goal")
    investor = models.ForeignKey(InvestorProfile, on_delete=models.CASCADE, related_name='goals', help_text="The beneficiary of this goal")

    name = models.CharField(max_length=255)
    target_amount = models.DecimalField(max_digits=20, decimal_places=2)
    target_date = models.DateField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='OTHER')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['target_date']

    def __str__(self):
        return f"{self.name} ({self.investor})"

    @property
    def current_value(self):
        """
        Calculates the current value of the goal based on mapped holdings.
        """
        total = 0
        for mapping in self.mappings.all():
            if mapping.holding.current_value:
                total += (mapping.holding.current_value * mapping.allocation_percentage / 100)
        return total

    @property
    def achievement_percentage(self):
        if self.target_amount <= 0:
            return 0
        return min((self.current_value / self.target_amount) * 100, 100)


class GoalMapping(models.Model):
    """
    Maps a portion of a holding to a specific goal.
    """
    goal = models.ForeignKey(Goal, on_delete=models.CASCADE, related_name='mappings')
    holding = models.ForeignKey(Holding, on_delete=models.CASCADE, related_name='goal_mappings')
    allocation_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Percentage of holding allocated to this goal (0-100)"
    )

    class Meta:
        unique_together = ('goal', 'holding')

    def __str__(self):
        return f"{self.goal.name} - {self.holding} ({self.allocation_percentage}%)"
