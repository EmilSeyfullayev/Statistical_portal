from django import template

from apps.accounts.services import get_user_display_name, is_admin

register = template.Library()


@register.filter
def user_display_name(user):
    return get_user_display_name(user)


@register.filter
def user_is_admin(user):
    return is_admin(user)
