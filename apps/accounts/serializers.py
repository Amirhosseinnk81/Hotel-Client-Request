from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User


class OperatorTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Operator login: standard username + password, but only accounts with
    role OPERATOR or ADMIN are allowed to obtain a token here.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        if self.user.role not in (User.Role.OPERATOR, User.Role.ADMIN):
            raise serializers.ValidationError(
                "This login is for operators only."
            )

        data["role"] = self.user.role
        return data
