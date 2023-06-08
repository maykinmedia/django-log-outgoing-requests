from django.db import models
from django.utils.translation import gettext_lazy as _


class SaveLogsChoice(models.TextChoices):
    use_default = "use_default", _("Use default")
    yes = "yes", _("Yes")
    no = "no", _("No")
