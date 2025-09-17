from django.contrib.auth.base_user import BaseUserManager 
import random
import string
from django.core.mail import send_mail
from django.conf import settings


class CustomUserManager(BaseUserManager):

    def generate_password(self):
        """
        Generate an 8-character password with:
        - at least 1 uppercase letter
        - at least 1 digit
        - at least 1 special character
        """
        uppercase = random.choice(string.ascii_uppercase)
        digit = random.choice(string.digits)
        special = random.choice("!@#$%^&*()_+-=<>?")

        # Remaining characters (8 - 3 = 5)
        others = ''.join(random.choices(string.ascii_letters + string.digits, k=5))

        # Combine all
        password_list = list(uppercase + digit + special + others)

        # Shuffle to randomize positions
        random.shuffle(password_list)

        return ''.join(password_list)




    def create_user(self,full_name,email,gender,contact,password=None,**extra_fields):

        # create and save user with email and password
        if not email:
            raise ValueError("The Email must be set for this field")
        if not full_name:
            raise ValueError('The Fullname Must be set')
        if not gender:
            raise ValueError('Please Provide Gender')
        if not contact:
            raise ValueError('Please Provide Contact Number')
        
        # Generate secure password if not provided
        if password is None:
            password = self.generate_password()

            print(password , 'password')
        
        
        email = self.normalize_email(email)
        user = self.model(
            email=email , 
            full_name=full_name , 
            gender=gender , 
            # password=password , 
            contact=contact ,
            **extra_fields
        )
        user.is_staff = True
        user.is_active = True
        user.is_superuser = False
        user.set_password(password)
        user.save(using=self._db)

        # Send password to user via email
        # self.send_password_email(user.email, password, user.full_name)

        return user 
        

    def create_superuser(self,email,password=None):

        # create and save superuser with email and password 
        email = self.normalize_email(email)
        user = self.model(email=email)
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)

        designation = self.model.group_check('Admin')
        user.designation = designation
        
        user.save()
        return user 
    
    def send_password_email(self, email, password, full_name=None):
        """Send generated password to user's email"""
        subject = "Welcome to Our Platform – Your Account Credentials"
        greeting_name = full_name if full_name else "User"

        message = (
            f"Dear {greeting_name},\n\n"
            f"Your account has been successfully created on our platform.\n\n"
            f"Here are your login details:\n"
            f"--------------------------------------\n"
            f"Email: {email}\n"
            f"Password: {password}\n"
            f"--------------------------------------\n\n"
            f"🔐 Security Notice:\n"
            f"- Upon your first login, you will be automatically redirected to change your password.\n"
            f"- Please choose a strong password that meets the following requirements:\n"
            f"   • Minimum 8 characters in length\n"
            f"   • At least 1 uppercase letter (A–Z)\n"
            f"   • At least 1 number (0–9)\n"
            f"   • At least 1 special character (!@#$%^&* etc.)\n\n"
            f"⚠️ Important: Do not share this password with anyone.\n\n"
            f"Best Regards,\n"
            f"The Support Team"
        )

        from_email = settings.DEFAULT_FROM_EMAIL
        send_mail(subject, message, from_email, [email])





