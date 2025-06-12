from rest_framework import permissions


class MyDefaultPermission(permissions.BasePermission):
    message = 'No Permission, Please check DEFAULT_PERMISSION_CLASSES in settings.py.'

    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):
        return True


class MyPermission(permissions.BasePermission):
    message = 'You have not permissions to do this.'

    def has_permission(self, request, view):
        return False

    def has_object_permission(self, request, view, obj):
        return True