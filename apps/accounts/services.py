ADMIN_GROUP = "Administrator"
MODULE_RESPONSIBLE_GROUP = "Module Responsible"
WORKER_GROUP = "Ministry Worker"


def is_admin(user):
    return user.is_authenticated and (user.is_superuser or user.groups.filter(name=ADMIN_GROUP).exists())


def is_module_responsible(user):
    return user.is_authenticated and user.groups.filter(name=MODULE_RESPONSIBLE_GROUP).exists()


def can_import(user):
    return is_admin(user) or is_module_responsible(user)
