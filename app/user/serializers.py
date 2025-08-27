from .models import (
    CustomUser,
)

from rest_framework import serializers
from django.contrib.auth import authenticate



class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()   
    password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ['email', 'password']


    def validate(self, data):
        email = data.get("email")
        password = data.get("password")

        # IMPORTANT: Django expects "username", not "email"
        user = authenticate(username=email, password=password)

        if not user:
            raise serializers.ValidationError("Invalid email or password.")
        if not user.is_active:
            raise serializers.ValidationError("User account is disabled.")

        return {"user": user}




