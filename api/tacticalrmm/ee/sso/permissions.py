"""
Copyright (c) 2024-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

from rest_framework import permissions
from allauth.socialaccount.models import SocialAccount
from accounts.utils import is_superuser


class SSOLoginPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        if is_superuser(r.user):
            return True
        return SocialAccount.objects.filter(user=r.user).exists()
