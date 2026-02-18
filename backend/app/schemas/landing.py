from typing import List, Optional
from pydantic import BaseModel

class LandingHero(BaseModel):
    title: str = "Software SaaS Moderno"
    subtitle: str = "Toda la potencia que tu negocio necesita en una sola plataforma."
    cta_text: str = "Empezar Gratis"
    cta_link: str = "/register"
    image_url: str = "assets/images/landing/hero.png"

class LandingFeature(BaseModel):
    title: str
    description: str
    icon: str = "check-circle"

class LandingClient(BaseModel):
    name: str
    logo_url: str

class LandingSocial(BaseModel):
    facebook: Optional[str] = None
    twitter: Optional[str] = None
    instagram: Optional[str] = None
    linkedin: Optional[str] = None

class LandingContact(BaseModel):
    email: str = "contacto@lumefy.io"
    phone: str = "+57 300 123 4567"
    address: str = "Calle 123, Bogota"

from app.schemas.plan import Plan as PlanSchema

class LandingConfig(BaseModel):
    enabled: bool = True
    hero: LandingHero = LandingHero()
    features: List[LandingFeature] = []
    clients: List[LandingClient] = []
    social: LandingSocial = LandingSocial()
    contact: LandingContact = LandingContact()
    pricing_visible: bool = True
    plans: List[dict] = [] # List of Plan objects (serialized)
