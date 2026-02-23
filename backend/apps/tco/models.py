"""Total Cost of Ownership models.

PostgreSQL schemas:
  tco  — TCOModel, CityReferenceData
  users — UserTCOProfile (lives in users schema alongside other user data)
"""
import uuid

from django.db import models


class TCOModel(models.Model):
    """Calculation model definition for a TCO-enabled product category.

    Stores the input schema (what data is needed) and cost components
    (the formula to compute total cost) for each category version.
    """

    category = models.ForeignKey(
        "products.Category", on_delete=models.CASCADE, related_name="tco_models"
    )
    name = models.CharField(max_length=200)
    version = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
    # JSON schema describing required user inputs (e.g. usage_hours, ownership_years)
    input_schema = models.JSONField()
    # JSON describing cost component formulas (purchase, electricity, maintenance, etc.)
    cost_components = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tco"."models'
        unique_together = [("category", "version")]

    def __str__(self) -> str:
        return f"{self.name} v{self.version} (category={self.category_id})"


class CityReferenceData(models.Model):
    """Reference data for Indian cities: electricity tariffs, climate, water rates."""

    city_name = models.CharField(max_length=200)
    state = models.CharField(max_length=100)
    # ₹ per kWh, residential slab average
    electricity_tariff_residential = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    # Number of days per year where cooling is needed (for AC TCO)
    cooling_days_per_year = models.IntegerField(null=True, blank=True)
    # low | medium | high
    humidity_level = models.CharField(max_length=20, blank=True)
    # ₹ per kilolitre
    water_tariff_per_kl = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    # soft | medium | hard
    water_hardness = models.CharField(max_length=20, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tco"."city_reference_data'
        unique_together = [("city_name", "state")]

    def __str__(self) -> str:
        return f"{self.city_name}, {self.state}"


class UserTCOProfile(models.Model):
    """User's saved TCO preferences — city, tariff override, usage habits.

    Lives in the users schema alongside other user data.
    Moved here from apps.accounts to keep TCO logic co-located.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        "accounts.User", on_delete=models.CASCADE, related_name="tco_profile"
    )
    city = models.ForeignKey(
        CityReferenceData, on_delete=models.SET_NULL, null=True, blank=True
    )
    # If user overrides the city default (e.g. they're on industrial tariff)
    electricity_tariff_override = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    ac_hours_per_day = models.SmallIntegerField(null=True, blank=True)
    ownership_years = models.SmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users"."tco_profiles'

    def __str__(self) -> str:
        city_name = self.city.city_name if self.city else "no city"
        return f"{self.user.email} — {city_name}"
