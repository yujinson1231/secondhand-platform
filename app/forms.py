from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileSize
from wtforms import StringField, PasswordField, TextAreaField, IntegerField, SelectField
from wtforms.validators import (
    DataRequired,
    Length,
    Regexp,
    NumberRange,
    EqualTo,
    ValidationError,
)


USERNAME_RE = r"^[A-Za-z0-9_]{3,20}$"


class RegisterForm(FlaskForm):
    username = StringField(
        "아이디",
        validators=[
            DataRequired(),
            Regexp(USERNAME_RE, message="아이디는 영문/숫자/밑줄 3~20자만 가능합니다."),
        ],
    )
    password = PasswordField(
        "비밀번호",
        validators=[DataRequired(), Length(min=8, max=128, message="비밀번호는 8자 이상이어야 합니다.")],
    )
    password_confirm = PasswordField(
        "비밀번호 확인",
        validators=[DataRequired(), EqualTo("password", message="비밀번호가 일치하지 않습니다.")],
    )


class LoginForm(FlaskForm):
    username = StringField("아이디", validators=[DataRequired(), Length(max=30)])
    password = PasswordField("비밀번호", validators=[DataRequired(), Length(max=128)])


class ProductForm(FlaskForm):
    name = StringField("상품명", validators=[DataRequired(), Length(max=100)])
    description = TextAreaField("상품 설명", validators=[DataRequired(), Length(max=3000)])
    price = IntegerField("가격", validators=[DataRequired(), NumberRange(min=0, max=1_000_000_000)])
    image = FileField(
        "상품 사진",
        validators=[
            FileAllowed(["png", "jpg", "jpeg", "gif", "webp"], "이미지 파일만 업로드 가능합니다."),
            FileSize(max_size=5 * 1024 * 1024, message="이미지는 5MB 이하만 업로드 가능합니다."),
        ],
    )


class ReportForm(FlaskForm):
    reason = TextAreaField(
        "신고 사유", validators=[DataRequired(), Length(min=5, max=1000, message="신고 사유를 5자 이상 입력하세요.")]
    )


class TransferForm(FlaskForm):
    receiver_username = StringField("받는 사람 아이디", validators=[DataRequired(), Length(max=30)])
    amount = IntegerField("송금액", validators=[DataRequired(), NumberRange(min=1, max=1_000_000_000)])


class BioForm(FlaskForm):
    bio = TextAreaField("소개글", validators=[Length(max=500)])


class PasswordChangeForm(FlaskForm):
    current_password = PasswordField("현재 비밀번호", validators=[DataRequired()])
    new_password = PasswordField(
        "새 비밀번호", validators=[DataRequired(), Length(min=8, max=128, message="비밀번호는 8자 이상이어야 합니다.")]
    )
    new_password_confirm = PasswordField(
        "새 비밀번호 확인",
        validators=[DataRequired(), EqualTo("new_password", message="비밀번호가 일치하지 않습니다.")],
    )


class ChatMessageForm(FlaskForm):
    content = StringField("메시지", validators=[DataRequired(), Length(max=2000)])
