"""
Form widgets with DaisyUI styling.

This module provides a factory class for creating Django form widgets
with consistent DaisyUI/Tailwind CSS styling across the application.
"""

from django import forms


class DaisyUIWidgets:
    """
    Factory class for creating form widgets with DaisyUI styling.

    Provides consistent styling across all forms in the application using
    DaisyUI and Tailwind CSS classes.

    Usage:
        from apps.core.widgets import DaisyUIWidgets

        class MyForm(forms.Form):
            name = forms.CharField(widget=DaisyUIWidgets.text_input())
            description = forms.CharField(widget=DaisyUIWidgets.textarea())
            category = forms.ChoiceField(widget=DaisyUIWidgets.select())
    """

    # Base classes for all inputs
    BASE_INPUT_CLASSES = "input input-bordered w-full"
    BASE_TEXTAREA_CLASSES = "textarea textarea-bordered w-full"
    BASE_SELECT_CLASSES = "select select-bordered w-full"
    BASE_CHECKBOX_CLASSES = "checkbox checkbox-primary"
    BASE_RADIO_CLASSES = "radio radio-primary"

    @classmethod
    def text_input(cls, placeholder="", extra_classes="", **kwargs):
        """
        Create a text input widget with DaisyUI styling.

        Args:
            placeholder (str): Placeholder text
            extra_classes (str): Additional CSS classes
            **kwargs: Additional attributes for the widget

        Returns:
            forms.TextInput: Styled text input widget
        """
        attrs = {
            'class': f"{cls.BASE_INPUT_CLASSES} {extra_classes}".strip(),
            'placeholder': placeholder,
            **kwargs
        }
        return forms.TextInput(attrs=attrs)

    @classmethod
    def email_input(cls, placeholder="", extra_classes="", **kwargs):
        """
        Create an email input widget with DaisyUI styling.

        Args:
            placeholder (str): Placeholder text
            extra_classes (str): Additional CSS classes
            **kwargs: Additional attributes for the widget

        Returns:
            forms.EmailInput: Styled email input widget
        """
        attrs = {
            'class': f"{cls.BASE_INPUT_CLASSES} {extra_classes}".strip(),
            'placeholder': placeholder,
            **kwargs
        }
        return forms.EmailInput(attrs=attrs)

    @classmethod
    def password_input(cls, placeholder="", extra_classes="", **kwargs):
        """
        Create a password input widget with DaisyUI styling.

        Args:
            placeholder (str): Placeholder text
            extra_classes (str): Additional CSS classes
            **kwargs: Additional attributes for the widget

        Returns:
            forms.PasswordInput: Styled password input widget
        """
        attrs = {
            'class': f"{cls.BASE_INPUT_CLASSES} {extra_classes}".strip(),
            'placeholder': placeholder,
            **kwargs
        }
        return forms.PasswordInput(attrs=attrs)

    @classmethod
    def number_input(cls, placeholder="", extra_classes="", min_value=None, max_value=None, **kwargs):
        """
        Create a number input widget with DaisyUI styling.

        Args:
            placeholder (str): Placeholder text
            extra_classes (str): Additional CSS classes
            min_value (int/float): Minimum value
            max_value (int/float): Maximum value
            **kwargs: Additional attributes for the widget

        Returns:
            forms.NumberInput: Styled number input widget
        """
        attrs = {
            'class': f"{cls.BASE_INPUT_CLASSES} {extra_classes}".strip(),
            'placeholder': placeholder,
            **kwargs
        }

        if min_value is not None:
            attrs['min'] = min_value
        if max_value is not None:
            attrs['max'] = max_value

        return forms.NumberInput(attrs=attrs)

    @classmethod
    def textarea(cls, placeholder="", rows=4, extra_classes="", **kwargs):
        """
        Create a textarea widget with DaisyUI styling.

        Args:
            placeholder (str): Placeholder text
            rows (int): Number of rows
            extra_classes (str): Additional CSS classes
            **kwargs: Additional attributes for the widget

        Returns:
            forms.Textarea: Styled textarea widget
        """
        attrs = {
            'class': f"{cls.BASE_TEXTAREA_CLASSES} {extra_classes}".strip(),
            'placeholder': placeholder,
            'rows': rows,
            **kwargs
        }
        return forms.Textarea(attrs=attrs)

    @classmethod
    def select(cls, extra_classes="", **kwargs):
        """
        Create a select widget with DaisyUI styling.

        Args:
            extra_classes (str): Additional CSS classes
            **kwargs: Additional attributes for the widget

        Returns:
            forms.Select: Styled select widget
        """
        attrs = {
            'class': f"{cls.BASE_SELECT_CLASSES} {extra_classes}".strip(),
            **kwargs
        }
        return forms.Select(attrs=attrs)

    @classmethod
    def select_multiple(cls, extra_classes="", size=5, **kwargs):
        """
        Create a multiple select widget with DaisyUI styling.

        Args:
            extra_classes (str): Additional CSS classes
            size (int): Number of visible options
            **kwargs: Additional attributes for the widget

        Returns:
            forms.SelectMultiple: Styled multiple select widget
        """
        attrs = {
            'class': f"{cls.BASE_SELECT_CLASSES} {extra_classes}".strip(),
            'size': size,
            **kwargs
        }
        return forms.SelectMultiple(attrs=attrs)

    @classmethod
    def checkbox(cls, extra_classes="", **kwargs):
        """
        Create a checkbox widget with DaisyUI styling.

        Args:
            extra_classes (str): Additional CSS classes
            **kwargs: Additional attributes for the widget

        Returns:
            forms.CheckboxInput: Styled checkbox widget
        """
        attrs = {
            'class': f"{cls.BASE_CHECKBOX_CLASSES} {extra_classes}".strip(),
            **kwargs
        }
        return forms.CheckboxInput(attrs=attrs)

    @classmethod
    def radio_select(cls, extra_classes="", **kwargs):
        """
        Create a radio select widget with DaisyUI styling.

        Args:
            extra_classes (str): Additional CSS classes
            **kwargs: Additional attributes for the widget

        Returns:
            forms.RadioSelect: Styled radio select widget
        """
        attrs = {
            'class': f"{cls.BASE_RADIO_CLASSES} {extra_classes}".strip(),
            **kwargs
        }
        return forms.RadioSelect(attrs=attrs)

    @classmethod
    def date_input(cls, placeholder="", extra_classes="", **kwargs):
        """
        Create a date input widget with DaisyUI styling.

        Args:
            placeholder (str): Placeholder text
            extra_classes (str): Additional CSS classes
            **kwargs: Additional attributes for the widget

        Returns:
            forms.DateInput: Styled date input widget
        """
        attrs = {
            'class': f"{cls.BASE_INPUT_CLASSES} {extra_classes}".strip(),
            'type': 'date',
            'placeholder': placeholder,
            **kwargs
        }
        return forms.DateInput(attrs=attrs)

    @classmethod
    def time_input(cls, placeholder="", extra_classes="", **kwargs):
        """
        Create a time input widget with DaisyUI styling.

        Args:
            placeholder (str): Placeholder text
            extra_classes (str): Additional CSS classes
            **kwargs: Additional attributes for the widget

        Returns:
            forms.TimeInput: Styled time input widget
        """
        attrs = {
            'class': f"{cls.BASE_INPUT_CLASSES} {extra_classes}".strip(),
            'type': 'time',
            'placeholder': placeholder,
            **kwargs
        }
        return forms.TimeInput(attrs=attrs)

    @classmethod
    def datetime_input(cls, placeholder="", extra_classes="", **kwargs):
        """
        Create a datetime input widget with DaisyUI styling.

        Args:
            placeholder (str): Placeholder text
            extra_classes (str): Additional CSS classes
            **kwargs: Additional attributes for the widget

        Returns:
            forms.DateTimeInput: Styled datetime input widget
        """
        attrs = {
            'class': f"{cls.BASE_INPUT_CLASSES} {extra_classes}".strip(),
            'type': 'datetime-local',
            'placeholder': placeholder,
            **kwargs
        }
        return forms.DateTimeInput(attrs=attrs)

    @classmethod
    def file_input(cls, extra_classes="", **kwargs):
        """
        Create a file input widget with DaisyUI styling.

        Args:
            extra_classes (str): Additional CSS classes
            **kwargs: Additional attributes for the widget

        Returns:
            forms.FileInput: Styled file input widget
        """
        attrs = {
            'class': f"file-input file-input-bordered w-full {extra_classes}".strip(),
            **kwargs
        }
        return forms.FileInput(attrs=attrs)

    @classmethod
    def url_input(cls, placeholder="", extra_classes="", **kwargs):
        """
        Create a URL input widget with DaisyUI styling.

        Args:
            placeholder (str): Placeholder text
            extra_classes (str): Additional CSS classes
            **kwargs: Additional attributes for the widget

        Returns:
            forms.URLInput: Styled URL input widget
        """
        attrs = {
            'class': f"{cls.BASE_INPUT_CLASSES} {extra_classes}".strip(),
            'placeholder': placeholder,
            **kwargs
        }
        return forms.URLInput(attrs=attrs)

    @classmethod
    def hidden_input(cls, **kwargs):
        """
        Create a hidden input widget.

        Args:
            **kwargs: Additional attributes for the widget

        Returns:
            forms.HiddenInput: Hidden input widget
        """
        return forms.HiddenInput(attrs=kwargs)
