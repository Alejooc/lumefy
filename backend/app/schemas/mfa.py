from pydantic import BaseModel, Field


class MFACodeRequest(BaseModel):
    code: str = Field(min_length=6, max_length=32)


class MFAChallengeRequest(MFACodeRequest):
    challenge_token: str = Field(min_length=20)


class MFASetupResponse(BaseModel):
    enabled: bool
    secret: str
    otpauth_uri: str


class MFAStatusResponse(BaseModel):
    enabled: bool
    configured: bool
    recovery_codes_remaining: int


class MFAEnableResponse(BaseModel):
    enabled: bool
    recovery_codes: list[str]


class MFAVerifyResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

