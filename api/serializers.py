from rest_framework.serializers import ModelSerializer
from django.contrib.auth.models import User
from .models import PredictionHistory, UserProfile

class RegisterSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['id','username','email','first_name','last_name']

class PredictionHistorySerializer(ModelSerializer):
    class Meta:
        model = PredictionHistory
        fields = '__all__'
        read_only_fields = ('user','created_at')


class UserProfileSerializer(ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['form_data', 'updated_at']