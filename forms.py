# forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo, Optional, ValidationError
from flask_login import current_user
from models import User

class ChangeAccountInfoForm(FlaskForm):
    username = StringField('Nové uživatelské jméno', 
                           validators=[Optional(), Length(min=2, max=20)])
    
    current_password = PasswordField('Současné heslo', 
                                     validators=[DataRequired(message="Současné heslo je povinné.")])

    new_password = PasswordField('Nové heslo', 
                                 validators=[Optional(), Length(min=6, message="Nové heslo musí mít alespoň 6 znaků.")])
    
    confirm_password = PasswordField('Potvrdit nové heslo', 
                                     validators=[Optional(), EqualTo('new_password', message='Nová hesla se musí shodovat.')])

    submit_account = SubmitField('Uložit změny')

    def validate_username(self, username):
        """Zkontroluje, zda nové jméno už neexistuje."""
        if username.data != current_user.username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('Toto uživatelské jméno je již obsazeno.')