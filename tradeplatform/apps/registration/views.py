from django.contrib.auth.models import User
from rest_framework import generics, mixins, status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.registration.customfilters import UserProfileFilter
from apps.registration.custompermission import IsOwnerOrReadOnly
from apps.registration.models import UserProfile
from apps.registration.serializers import (ChangeUserEmailSerializer,
                                           RequestChangeEmailAddressSerializer,
                                           RequestResetPasswordSerializer,
                                           ResetUserPasswordSerializer,
                                           UserProfileSerializer,
                                           UserSerializer)
from apps.registration.services.tokens import (
    confirm_user_email_by_given_token, validate_given_user_token)
from apps.registration.services.user_statistic_logic import \
    get_statistics_attribute
from apps.registration.services.views_logic import (
    change_user_offer_after_changing_email, update_user_password)
from apps.registration.tasks import (change_email_address,
                                     send_change_email_address_mail,
                                     send_confirmation_mail_message,
                                     send_reset_password_mail)


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for User model"""

    serializer_class = UserSerializer
    queryset = User.objects.all()

    permission_classes = (IsAuthenticated,)

    filterset_fields = ("username", "email", "is_active")
    search_fields = ("username", "email")
    ordering_fields = ("username", "email")


class UserProfileViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """ViewSet for User Profile model"""

    serializer_class = UserProfileSerializer
    queryset = UserProfile.objects.all()

    permission_classes = (IsAuthenticated, IsOwnerOrReadOnly)

    filterset_class = UserProfileFilter
    search_fields = ("user__username", "user__email")
    ordering_fields = ("user__username", "user__email")

    def retrieve(self, request, *args, **kwargs):
        """Returns detail information about user's profile with his statistic"""

        response_data = (
            super(UserProfileViewSet, self).retrieve(request, *args, **kwargs).data
        )

        statistic_data = get_statistics_attribute(user_profile_id=kwargs["pk"])

        return Response(
            data=dict(list(response_data.items()) + list(statistic_data.items())),
            status=status.HTTP_200_OK,
        )

    def update(self, request, *args, **kwargs):
        """Update user's profile fields and get detail information about user's statistic by the given date"""

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        response_data = (
            super(UserProfileViewSet, self).update(request, *args, **kwargs).data
        )

        statistic_data = get_statistics_attribute(
            user_profile_id=kwargs["pk"], to_date=request.data["to_date"]
        )

        return Response(
            data=dict(list(response_data.items()) + list(statistic_data.items())),
            status=status.HTTP_201_CREATED,
        )


class SignUpView(generics.ListAPIView, generics.CreateAPIView):
    """View for user's registration"""

    serializer_class = UserSerializer

    permission_classes = (AllowAny,)

    def get(self, request, *args, **kwargs):
        """Function for getting information about view"""

        message = {"details": "Please write information below"}
        return Response(data=message, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        """Function for creating a request to reset user's password"""

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        send_confirmation_mail_message.delay(username=request.data["username"])

        headers = self.get_success_headers(serializer.data)

        message = {
            "details": "You are successfully registered. "
            "Please confirm your email address to complete the registration."
        }
        return Response(data=message, status=status.HTTP_201_CREATED, headers=headers)


class ActivateUserEmailView(generics.ListAPIView):
    """View for confirmation user's mail address"""

    permission_classes = (AllowAny,)

    def get(self, request, *args, **kwargs):
        """Return response to user with information about email confirmation"""

        if validate_given_user_token(token=kwargs["token"]):
            confirm_user_email_by_given_token(token=kwargs["token"])
            message = {"details": "Thank you for your email confirmation."}
            return Response(data=message, status=status.HTTP_200_OK)

        message = {"details": "Invalid link!"}
        return Response(data=message, status=status.HTTP_400_BAD_REQUEST)


class RequestResetPasswordView(generics.ListAPIView, generics.CreateAPIView):
    """View to request a password change"""

    serializer_class = RequestResetPasswordSerializer

    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        """Function for creating a request to reset user's password"""

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        send_reset_password_mail.delay(email=request.data["email"])

        message = {"details": "We send you confirmation mail for reset your password."}
        return Response(data=message, status=status.HTTP_201_CREATED)

    def get(self, request, *args, **kwargs):
        """Function for getting information about view"""

        message = {"details": "Please write your email address to reset password."}
        return Response(data=message, status=status.HTTP_200_OK)


class ResetPasswordView(generics.ListAPIView, generics.CreateAPIView):
    """View for confirmation of changing user's password"""

    serializer_class = ResetUserPasswordSerializer

    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        """Function for changing user's password"""

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if validate_given_user_token(token=kwargs["token"]):
            update_user_password(
                token=kwargs["token"], password=request.data["password"]
            )
            message = {"details": "Password has been successfully changed."}
            return Response(data=message, status=status.HTTP_201_CREATED)

        message = {"details": "Invalid link!"}
        return Response(data=message, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, *args, **kwargs):
        """Function for getting information about view"""

        if validate_given_user_token(token=kwargs["token"]):
            message = {"details": "Please write new password and confirm it."}
            return Response(data=message, status=status.HTTP_200_OK)

        message = {"details": "Invalid link!"}
        return Response(data=message, status=status.HTTP_400_BAD_REQUEST)


class RequestChangeEmailAddressView(generics.ListAPIView, generics.CreateAPIView):
    """View for make a request to change user's email address"""

    serializer_class = RequestChangeEmailAddressSerializer

    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        """Function for getting information about view"""

        message = {
            "details": "You need to write password and confirm it "
            "to change your account email address"
        }
        return Response(data=message, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        """Function for changing user's password"""

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        send_change_email_address_mail.delay(username=self.request.user.username)

        message = {
            "details": "We send you confirmation mail for change your email address."
        }
        return Response(data=message, status=status.HTTP_201_CREATED)


class ChangeEmailAddressView(generics.ListAPIView, generics.CreateAPIView):
    """View for write new user's email address"""

    serializer_class = ChangeUserEmailSerializer

    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        """Function for getting information about view"""

        if validate_given_user_token(token=kwargs["token"]):
            message = {"details": "Write new email address below."}
            return Response(data=message, status=status.HTTP_200_OK)

        message = {"details": "Invalid link!"}
        return Response(data=message, status=status.HTTP_400_BAD_REQUEST)

    def create(self, request, *args, **kwargs):
        """Function for changing user's password"""

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if validate_given_user_token(token=kwargs["token"]):
            change_email_address(
                username=self.request.user.username,
                to_email=request.data["email"],
                token=kwargs["token"],
            )
            message = {
                "details": "We send you confirmation mail for "
                "change your email address."
            }
            return Response(data=message, status=status.HTTP_201_CREATED)

        message = {"details": "Invalid link!"}
        return Response(data=message, status=status.HTTP_400_BAD_REQUEST)


class ActivateChangeEmail(generics.ListAPIView):
    """View for confirmation new user's mail address"""

    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        """Return response to user with information about new user's email confirmation"""

        if validate_given_user_token(token=kwargs["token"]):
            confirm_user_email_by_given_token(token=kwargs["token"])
            change_user_offer_after_changing_email(token=kwargs["token"], value=True)
            message = {"details": "Thank for your new email address confirmation."}
            return Response(data=message, status=status.HTTP_200_OK)

        message = {"details": "Invalid link!"}
        return Response(data=message, status=status.HTTP_400_BAD_REQUEST)
