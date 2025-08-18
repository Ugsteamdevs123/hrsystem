from django.contrib.auth.base_user import BaseUserManager 

class CustomUserManager(BaseUserManager):

    def create_user(self,full_name,email,designation,gender,contact,password=None,**extra_fields):

        # create and save user with email and password
        if not email:
            raise ValueError("The Email must be set for this field")
        if not full_name:
            raise ValueError('The Fullname Must be set')
        
        # if not designation:
        #     raise ValueError('The Designation Must be set')
        
        if not gender:
            raise ValueError('Please Provide Gender')
        if not contact:
            raise ValueError('Please Provide Contact Number')
        
        
        email = self.normalize_email(email)
        # user = self.model(email=email , full_name=full_name , designation=designation , gender=gender , password=password , contact=contact ,**extra_fields)
        user = self.model(email=email , full_name=full_name , gender=gender , password=password , contact=contact ,**extra_fields)
        user.is_staff = True
        user.is_active = True
        user.is_superuser = False
        user.set_password(password)
        user.save(using=self._db)

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
        