from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import UserProfile, Order, Product, ProductVariant, ProductImage, Category, UniformType, SizeOption, StoreClosure


FIELD_CLASS = (
    'w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 '
    'outline-none transition focus:border-navy-700 focus:ring-2 focus:ring-navy-100'
)
SELECT_CLASS = FIELD_CLASS + ' pr-9'
CHECKBOX_CLASS = 'h-4 w-4 rounded border-gray-300 text-navy-700 focus:ring-navy-100'


class RegisterForm(UserCreationForm):
    student_id = forms.CharField(max_length=50, required=True)
    full_name = forms.CharField(max_length=120, required=True)
    school_level = forms.ModelChoiceField(
        queryset=Category.objects.all().order_by('name'),
        required=True,
        empty_label='— Select School Level —',
    )
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('student_id', 'full_name', 'school_level', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = FIELD_CLASS
            field.widget.attrs['autocomplete'] = 'off'
        self.fields['student_id'].widget.attrs['placeholder'] = 'Student ID'
        self.fields['full_name'].widget.attrs['placeholder'] = 'Full Name'
        self.fields['email'].widget.attrs['placeholder'] = 'Email Address'
        self.fields['password1'].widget.attrs['placeholder'] = 'Password'
        self.fields['password2'].widget.attrs['placeholder'] = 'Confirm Password'

    def clean_student_id(self):
        student_id = self.cleaned_data.get('student_id', '').strip()
        if User.objects.filter(username=student_id).exists():
            raise forms.ValidationError('An account with this Student ID already exists.')
        if UserProfile.objects.filter(student_id=student_id).exists():
            raise forms.ValidationError('An account with this Student ID already exists.')
        return student_id

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        full_name = self.cleaned_data['full_name'].strip()
        parts = full_name.split(None, 1)
        user.username = self.cleaned_data['student_id']
        user.first_name = parts[0]
        user.last_name = parts[1] if len(parts) > 1 else ''
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': FIELD_CLASS,
            'placeholder': 'Student ID or staff username',
        })
        self.fields['password'].widget.attrs.update({
            'class': FIELD_CLASS,
            'placeholder': 'Password',
        })


class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = FIELD_CLASS


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('phone', 'school_level', 'address', 'avatar')
        widgets = {
            'phone': forms.TextInput(attrs={'class': FIELD_CLASS, 'placeholder': '+63 9XX XXX XXXX'}),
            'school_level': forms.Select(attrs={'class': SELECT_CLASS}),
            'address': forms.Textarea(attrs={'class': FIELD_CLASS, 'rows': 3}),
            'avatar': forms.FileInput(attrs={'class': FIELD_CLASS}),
        }


class StaffAccountForm(forms.ModelForm):
    role = forms.ChoiceField(
        choices=[
            (UserProfile.ROLE_STAFF, 'Staff / Store Clerk'),
            (UserProfile.ROLE_MANAGER, 'Admin / Store Manager'),
        ],
        widget=forms.Select(attrs={'class': SELECT_CLASS}),
    )
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': FIELD_CLASS,
            'placeholder': 'Leave blank to keep current password',
            'autocomplete': 'new-password',
        }),
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'is_active')
        widgets = {
            'username': forms.TextInput(attrs={'class': FIELD_CLASS, 'autocomplete': 'off'}),
            'first_name': forms.TextInput(attrs={'class': FIELD_CLASS}),
            'last_name': forms.TextInput(attrs={'class': FIELD_CLASS}),
            'email': forms.EmailInput(attrs={'class': FIELD_CLASS}),
            'is_active': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            profile = getattr(self.instance, 'profile', None)
            if profile:
                self.fields['role'].initial = profile.role
        else:
            self.fields['password'].required = True
            self.fields['password'].widget.attrs['placeholder'] = 'Temporary password'

    def clean_email(self):
        email = self.cleaned_data.get('email')
        qs = User.objects.filter(email=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        qs = User.objects.filter(username=username)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('This username is already taken.')
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_staff = True
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        if commit:
            user.save()
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = self.cleaned_data['role']
            profile.save()
        return user


class StudentAccountForm(forms.ModelForm):
    student_id = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={'class': FIELD_CLASS}),
    )
    school_level = forms.ModelChoiceField(
        queryset=Category.objects.all().order_by('name'),
        required=False,
        empty_label='— Select School Level —',
        widget=forms.Select(attrs={'class': SELECT_CLASS}),
    )
    role = forms.ChoiceField(
        choices=UserProfile.ROLE_CHOICES,
        widget=forms.Select(attrs={'class': SELECT_CLASS}),
    )
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': FIELD_CLASS,
            'placeholder': 'Leave blank to keep current password',
            'autocomplete': 'new-password',
        }),
    )

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'is_active')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': FIELD_CLASS}),
            'last_name': forms.TextInput(attrs={'class': FIELD_CLASS}),
            'email': forms.EmailInput(attrs={'class': FIELD_CLASS}),
            'is_active': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        profile = getattr(self.instance, 'profile', None)
        if profile:
            self.fields['student_id'].initial = profile.student_id or self.instance.username
            self.fields['school_level'].initial = profile.school_level
            self.fields['role'].initial = profile.role

    def clean_student_id(self):
        student_id = self.cleaned_data.get('student_id', '').strip()
        user_qs = User.objects.filter(username=student_id)
        profile_qs = UserProfile.objects.filter(student_id=student_id)
        if self.instance and self.instance.pk:
            user_qs = user_qs.exclude(pk=self.instance.pk)
            profile_qs = profile_qs.exclude(user=self.instance)
        if user_qs.exists() or profile_qs.exists():
            raise forms.ValidationError('An account with this Student ID already exists.')
        return student_id

    def clean_email(self):
        email = self.cleaned_data.get('email')
        qs = User.objects.filter(email=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        role = self.cleaned_data['role']
        user.username = self.cleaned_data['student_id']
        user.is_staff = role in {UserProfile.ROLE_STAFF, UserProfile.ROLE_MANAGER}
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        if commit:
            user.save()
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.student_id = self.cleaned_data['student_id']
            profile.school_level = self.cleaned_data.get('school_level')
            profile.role = role
            profile.save()
        return user


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ('contact_email',)
        widgets = {
            'contact_email': forms.EmailInput(attrs={'class': FIELD_CLASS, 'placeholder': 'student@email.com'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['contact_email'].label = 'Email Address'
        self.fields['contact_email'].required = True


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ('category', 'uniform_type', 'name', 'description', 'image', 'is_available')
        widgets = {
            'category': forms.CheckboxSelectMultiple(attrs={'class': 'level-checkbox-group'}),
            'uniform_type': forms.Select(attrs={'class': SELECT_CLASS}),
            'name': forms.TextInput(attrs={'class': FIELD_CLASS, 'placeholder': 'Product name'}),
            'description': forms.Textarea(attrs={'class': FIELD_CLASS, 'rows': 4}),
            'image': forms.FileInput(attrs={'class': FIELD_CLASS, 'accept': 'image/*'}),
            'is_available': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].label = 'School Level(s)'
        self.fields['uniform_type'].label = 'Uniform Type'
        self.fields['description'].required = False
        self.fields['description'].widget.attrs['placeholder'] = 'Optional product details'


class ProductVariantForm(forms.ModelForm):
    class Meta:
        model = ProductVariant
        fields = ('size', 'stock', 'price')
        widgets = {
            'size': forms.Select(attrs={'class': SELECT_CLASS}),
            'stock': forms.NumberInput(attrs={'class': FIELD_CLASS, 'min': '0'}),
            'price': forms.NumberInput(attrs={'class': FIELD_CLASS, 'step': '0.01', 'min': '0', 'placeholder': 'Required'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['size'].queryset = SizeOption.objects.filter(is_active=True)
        self.fields['size'].empty_label = '— Select Size —'
        # Stock defaults to 0 if left blank so users don't have to type it
        self.fields['stock'].required = False
        self.fields['price'].required = False
        if (
            self.instance
            and self.instance.pk
            and self.instance.price is None
            and self.instance.product.price is not None
        ):
            self.fields['price'].initial = self.instance.product.price

    def has_changed(self):
        # If no size is selected, treat the whole row as blank and skip it
        if not self.data.get(self.add_prefix('size')):
            return False
        return super().has_changed()

    def clean_stock(self):
        stock = self.cleaned_data.get('stock')
        return stock if stock is not None else 0

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('size') and cleaned_data.get('price') is None:
            self.add_error('price', 'Price is required for this size.')
        return cleaned_data


class BaseProductVariantFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        filled = [
            f for f in self.forms
            if f.cleaned_data and not f.cleaned_data.get('DELETE') and f.cleaned_data.get('size')
        ]
        if not filled:
            raise forms.ValidationError('Please add at least one size variant.')


ProductVariantFormSet = forms.inlineformset_factory(
    Product, ProductVariant,
    form=ProductVariantForm,
    formset=BaseProductVariantFormSet,
    extra=20,
    max_num=20,
    can_delete=True,
)


class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ('image',)
        widgets = {
            'image': forms.FileInput(attrs={'class': FIELD_CLASS, 'accept': 'image/*'}),
        }


ProductImageFormSet = forms.inlineformset_factory(
    Product, ProductImage,
    form=ProductImageForm,
    extra=5,
    max_num=5,
    validate_max=True,
    can_delete=True,
)


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ('name', 'description')
        widgets = {
            'name': forms.TextInput(attrs={'class': FIELD_CLASS}),
            'description': forms.Textarea(attrs={'class': FIELD_CLASS, 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].label = 'School Level Name'


class UniformTypeForm(forms.ModelForm):
    class Meta:
        model = UniformType
        fields = ('name', 'description')
        widgets = {
            'name': forms.TextInput(attrs={'class': FIELD_CLASS}),
            'description': forms.Textarea(attrs={'class': FIELD_CLASS, 'rows': 3}),
        }


class SizeOptionForm(forms.ModelForm):
    class Meta:
        model = SizeOption
        fields = ('code', 'label', 'is_active')
        widgets = {
            'code': forms.TextInput(attrs={'class': FIELD_CLASS, 'style': 'text-transform:uppercase;'}),
            'label': forms.TextInput(attrs={'class': FIELD_CLASS}),
            'is_active': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASS}),
        }

    def clean_code(self):
        return self.cleaned_data['code'].upper()


class StoreClosureForm(forms.ModelForm):
    class Meta:
        model = StoreClosure
        fields = ('start_date', 'end_date', 'reason', 'is_active')
        widgets = {
            'start_date': forms.DateInput(attrs={'class': FIELD_CLASS, 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': FIELD_CLASS, 'type': 'date'}),
            'reason': forms.TextInput(attrs={'class': FIELD_CLASS, 'placeholder': 'Holiday / Store Closed'}),
            'is_active': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASS}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        if start_date and end_date and end_date < start_date:
            self.add_error('end_date', 'End date cannot be before start date.')
        return cleaned_data


class PickupDateForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ('pickup_date',)
        widgets = {
            'pickup_date': forms.DateInput(attrs={'class': FIELD_CLASS, 'type': 'date'}),
        }

    def clean_pickup_date(self):
        from datetime import date
        pickup_date = self.cleaned_data['pickup_date']
        if pickup_date < date.today():
            raise forms.ValidationError('Pickup date cannot be in the past.')
        if pickup_date.weekday() >= 5:
            raise forms.ValidationError('The school store is closed on weekends. Please choose a weekday.')
        if StoreClosure.objects.filter(
            is_active=True,
            start_date__lte=pickup_date,
            end_date__gte=pickup_date,
        ).exists():
            raise forms.ValidationError('The school store is closed on this date. Please choose another pickup date.')
        return pickup_date


class OrderStatusForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        status_choices = kwargs.pop('status_choices', None)
        super().__init__(*args, **kwargs)
        if status_choices is not None:
            self.fields['status'].choices = status_choices

    class Meta:
        model = Order
        fields = ('status',)
        widgets = {
            'status': forms.Select(attrs={'class': SELECT_CLASS}),
        }

